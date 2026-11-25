"""Curated sort of one sort folder as a Phy-format folder: pixelbat-curate export SORT.

Applies the logged merges and labels to the Kilosort output and writes <SORT>/curation/phy: spike arrays, cluster_group.tsv,
cluster_info.tsv, cluster_members.tsv and the small files Phy needs. A merged unit loses duplicate spikes by Kilosort's
own rule. From Python: export(sort, log, out) writes the same folder to out.
"""
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd
from kilosort.CCG import check_CCG

from pixelbat.curation.labels import foreign_spikes, short_interval_share
from pixelbat.curation.state import current_state, duplicate_window, not_duplicate, not_undone, read_log, refractory_thresholds


def cluster_table(spike_times, spike_clusters, spike_templates, templates, unwhiten, channel_map, channel_xy, channel_shank, duration_s):
    """Spike count, rate, peak channel, depth and shank per cluster, as Phy's cluster_info lists them: the channel is
    the largest of the unwhitened template that gave the cluster most of its spikes."""
    counts = pd.crosstab(spike_clusters, spike_templates)
    rows = []
    for cluster, by_template in counts.iterrows():
        peak = np.ptp(templates[by_template.idxmax()] @ unwhiten, axis=0).argmax()
        rows.append({'cluster_id': cluster, 'ch': channel_map[peak], 'depth': channel_xy[peak, 1],
                     'fr': by_template.sum() / duration_s, 'n_spikes': by_template.sum(), 'sh': int(channel_shank[peak])})
    return pd.DataFrame(rows).set_index('cluster_id')


def export(sort, log, out):
    """Writes the curated Phy folder out from a sort folder and its decision log; returns the summary line."""
    details = json.load(open(os.path.join(sort, 'curation', 'recording.json')))
    os.makedirs(out, exist_ok=True)
    params = {}
    exec(open(os.path.join(sort, 'params.py')).read(), params)

    ## Kilosort output
    spike_times = np.load(os.path.join(sort, 'spike_times.npy')).ravel()
    spike_clusters = np.load(os.path.join(sort, 'spike_clusters.npy')).ravel()
    spike_templates = np.load(os.path.join(sort, 'spike_templates.npy')).ravel()
    amplitudes = np.load(os.path.join(sort, 'amplitudes.npy')).ravel()
    kilosort = pd.concat([pd.read_csv(os.path.join(sort, f'cluster_{column}.tsv'), sep='\t').set_index('cluster_id')
                          for column in ['Amplitude', 'ContamPct', 'KSLabel']], axis=1)

    ## Decisions
    logged = read_log(log)
    members, labels, _, _, floors = current_state(kilosort.index, not_undone(logged))
    window = duplicate_window(sort)

    ## Amplitude floors: the spikes of a unit below its floor become a unit of their own, labelled noise
    original = {}
    for unit, (floor, below_id) in floors.items():
        original[below_id] = unit
        below = (spike_clusters == unit) & (amplitudes < floor)
        spike_clusters = np.where(below, below_id, spike_clusters)
        for cluster in (unit, below_id):
            is_refractory, _, contamination = check_CCG(spike_times[spike_clusters == cluster] / params['sample_rate'], **refractory_thresholds(sort))
            kilosort.loc[cluster] = [kilosort.loc[unit, 'Amplitude'], round(100 * contamination, 1), 'good' if is_refractory else 'mua']
        members[below_id] = [below_id]
        labels[below_id] = 'noise'
    merged = {unit: parts for unit, parts in members.items() if len(parts) > 1}

    ## Merges: new cluster id, duplicate spikes dropped, Kilosort's refractory test on the merged train
    keep = np.ones(len(spike_times), dtype=bool)
    curated = spike_clusters.copy()
    for unit, parts in merged.items():
        spikes = np.flatnonzero(np.isin(spike_clusters, parts))
        kept = not_duplicate(spike_times[spikes], window)
        keep[spikes[~kept]] = False
        curated[spikes] = unit
        is_refractory, _, contamination = check_CCG(spike_times[spikes[kept]] / params['sample_rate'], **refractory_thresholds(sort))
        counts = np.array([np.sum(spike_clusters == p) for p in parts])
        kilosort.loc[unit] = [round(np.average(kilosort.loc[parts, 'Amplitude'], weights=counts), 1), round(100 * contamination, 1),
                              'good' if is_refractory else 'mua']
    kilosort = kilosort.loc[sorted(members)]

    ## Phy tables
    n_samples = os.path.getsize(details['binary']) // (params['n_channels_dat'] * np.dtype(params['dtype']).itemsize)
    info = cluster_table(spike_times[keep], curated[keep], spike_templates[keep], np.load(os.path.join(sort, 'templates.npy')),
                         np.load(os.path.join(sort, 'whitening_mat_inv.npy')), np.load(os.path.join(sort, 'channel_map.npy')).ravel(),
                         np.load(os.path.join(sort, 'channel_positions.npy')),
                         np.load(os.path.join(sort, 'channel_shanks.npy')).ravel(), n_samples / params['sample_rate'])
    info = kilosort.join(info)
    info['group'] = pd.Series(labels).reindex(info.index)
    # A unit under the spike-count limit is few spikes without a decision, unless labelled
    few = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thresholds.json')))['mua']['num_spikes']['greater']
    info.loc[info['group'].isna() & (info['n_spikes'] < few), 'group'] = 'few'
    info.index.name = 'cluster_id'
    info = info[['Amplitude', 'ContamPct', 'KSLabel', 'ch', 'depth', 'fr', 'group', 'n_spikes', 'sh']]
    info.to_csv(os.path.join(out, 'cluster_info.tsv'), sep='\t')
    info['group'].dropna().to_csv(os.path.join(out, 'cluster_group.tsv'), sep='\t')
    for column in ['Amplitude', 'ContamPct', 'KSLabel']:
        info[column].to_csv(os.path.join(out, f'cluster_{column}.tsv'), sep='\t')

    ## Original Kilosort clusters of every exported unit
    pd.DataFrame([{'cluster_id': cluster, 'original_cluster_id': original.get(part, part)} for cluster in info.index for part in members[cluster]]
                 ).to_csv(os.path.join(out, 'cluster_members.tsv'), sep='\t', index=False)

    ## Continuous quality numbers of every exported unit, for stricter selection downstream
    quality = []
    for cluster in info.index:
        samples = spike_times[keep][curated[keep] == cluster]
        seen, expected, foreign = foreign_spikes(samples, params['sample_rate'])
        quality.append({'cluster_id': cluster, 'foreign_spikes': foreign, 'pairs_seen': seen, 'pairs_expected': expected,
                        'kilosort_ratio': info.loc[cluster, 'ContamPct'] / 100, 'intervals_0.25_to_1.25ms': short_interval_share(samples, params['sample_rate'])})
    pd.DataFrame(quality).to_csv(os.path.join(out, 'curation_quality.tsv'), sep='\t', index=False)

    ## Spike arrays and the files Phy opens a sort with
    np.save(os.path.join(out, 'spike_times.npy'), spike_times[keep])
    np.save(os.path.join(out, 'spike_clusters.npy'), curated[keep])
    np.save(os.path.join(out, 'spike_templates.npy'), spike_templates[keep])
    np.save(os.path.join(out, 'amplitudes.npy'), amplitudes[keep])
    with open(os.path.join(out, 'params.py'), 'w') as f:
        f.write(''.join(f'{key} = {value!r}\n' for key, value in {**{k: v for k, v in params.items() if not k.startswith('__')},
                                                                 'dat_path': details['binary']}.items()))
    for name in ['channel_map.npy', 'channel_positions.npy', 'channel_shanks.npy', 'templates.npy',
                 'templates_ind.npy', 'similar_templates.npy', 'whitening_mat.npy', 'whitening_mat_inv.npy']:
        shutil.copy(os.path.join(sort, name), os.path.join(out, name))
    with open(os.path.join(out, 'curation_log.jsonl'), 'w') as f:
        f.writelines(json.dumps(event) + '\n' for event in logged)
    counts = ', '.join(f'{n} {label}' for label, n in info['group'].value_counts().items())
    return (f'{len(info)} units ({len(merged)} merged, {len(floors)} with an amplitude floor): {counts or "none labelled"}, {int(info["group"].isna().sum())} without a label; '
          f'{int((~keep).sum())} duplicate spikes dropped')


if __name__ == '__main__':
    sort = os.path.normpath(sys.argv[1])
    print(export(sort, os.path.join(sort, 'curation', 'curation_log.jsonl'), os.path.join(sort, 'curation', 'phy')))
