"""An opened sort: everything the app holds of one sort, computed once from its Kilosort output and prepared cache and
saved in <sort>/curation/opened, so that opening it again only reads it."""
import gzip
import hashlib
import json
import os
import pickle
import shutil
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from kilosort.CCG import CCG_metrics, compute_CCG, check_CCG

from pixelbat.curation.labels import DRAWS, HANDOFF, MAX_CONTAMINATION, block_rates, bombcell_labels, failed_tests, foreign_spikes, handoff, notch_rates, short_interval_share
from pixelbat.curation.ratemaps import bin_spikes_on_pos
from pixelbat.curation.state import duplicate_window, not_duplicate, refractory_thresholds
from pixelbat.curation.waveforms import WINDOW

SIMILARITY = 0.95  # waveform similarity above which units not proposed noise form a merge group
HERE = os.path.dirname(os.path.abspath(__file__))
# Results kept per unit or pair once computed, saved with the opened sort
CACHES = ['merged', 'pairs', 'blocks', 'footprints', 'footprint_pairs', 'evidence']
progress = {}  # what is being done to open each sort, in words, for the page


def build(sort):
    """Arrays, spike trains and proposal groups of one sort, computed from its Kilosort output and prepared cache."""
    progress[sort] = 'reading the spike times'
    curation = os.path.join(sort, 'curation')
    cache = os.path.join(curation, 'cache')
    params = {}
    exec(open(os.path.join(sort, 'params.py')).read(), params)
    units = pd.read_csv(os.path.join(cache, 'units.csv'), index_col='cluster_id')
    recording = json.load(open(os.path.join(cache, 'recording.json')))
    spike_times = np.load(os.path.join(sort, 'spike_times.npy')).ravel()
    spike_clusters = np.load(os.path.join(sort, 'spike_clusters.npy')).ravel()
    order = np.argsort(spike_clusters, kind='stable')
    bounds = np.searchsorted(spike_clusters[order], units.index.to_numpy())
    samples = dict(zip(units.index, np.split(spike_times[order], bounds[1:])))
    progress[sort] = 'contamination of every unit'
    # Bombcell label on each spike draw; its mua test is foreign spikes at most MAX_CONTAMINATION
    duration = recording['n_samples'] / recording['rate_hz']
    refractory = [foreign_spikes(samples[u], recording['rate_hz']) for u in units.index]
    units['rp_seen'] = [seen for seen, _, _ in refractory]
    units['rp_expected'] = [expected for _, expected, _ in refractory]
    units['rp_contamination'] = [foreign for _, _, foreign in refractory]
    units['refractory_good'] = (units['rp_contamination'] <= MAX_CONTAMINATION).astype(int)
    thresholds = json.load(open(os.path.join(HERE, 'thresholds.json')))
    for draw in range(DRAWS):
        shape = pd.read_csv(os.path.join(cache, f'shape_draw{draw}.csv'), index_col=0)
        units[f'bombcell_draw{draw}'] = bombcell_labels(units, shape, thresholds, False)
    # Non-somatic waveform shape (from the waveform as recorded) is a tag only: it does not enter the proposed label
    units['non_somatic'] = bombcell_labels(units, pd.read_csv(os.path.join(cache, 'shape_as_recorded.csv'), index_col=0), thresholds, True) == 'non_soma'
    shape = pd.read_csv(os.path.join(cache, 'shape_draw0.csv'), index_col=0)
    units['failed'] = failed_tests(units.join(shape), thresholds)
    units['duration_ms'] = 1000 * shape['peak_to_trough_duration']
    units['proposed'] = units['bombcell_draw0']
    draws = units.filter(like='bombcell_draw')
    units['flips'] = draws.nunique(axis=1) > 1
    units['draws'] = [', '.join(f'{n} {label}' for label, n in row.value_counts().items()) for _, row in draws.iterrows()]
    ks_amplitude = dict(zip(units.index, np.split(np.load(os.path.join(sort, 'amplitudes.npy')).ravel()[order], bounds[1:])))
    units['short_isi'] = [int(np.sum(np.diff(samples[u]) <= recording['rate_hz'] * 1e-3)) for u in units.index]
    units['short_fraction'] = [short_interval_share(samples[u], recording['rate_hz']) for u in units.index]
    progress[sort] = 'merge groups'
    # Merge groups: the sorter's would-be merges as they are, each with why the sorter proposes it; then, among the
    # other units not proposed noise, groups in which every pair has waveform similarity above the limit, the most
    # similar pairs first
    similarity = np.load(os.path.join(cache, 'similarity.npy'))
    proposed = os.path.join(sort, 'proposed_merges.json')
    proposals = json.load(open(proposed)) if os.path.exists(proposed) else {'groups': []}
    # Kilosort's decision on each group: Kilosort 2.5 names the sources of each group, Kilosort 4's are its final merge
    if 'group_sources' in proposals:
        sorter = 'Kilosort 2.5'
        decisions = ['merged (template match)' if s['find_merges'] else 'kept split (refractory check overruled)' for s in proposals['group_sources']]
    else:
        sorter = 'Kilosort 4'
        decisions = ['merged (its final merge)'] * len(proposals['groups'])
    kilosort = [sorted(g) for g in proposals['groups']]
    free = ~units['proposed'].isin(['noise', 'non_soma']).to_numpy() & ~units.index.isin([u for g in kilosort for u in g])
    linked = (similarity > SIMILARITY) & np.outer(free, free) & ~np.eye(len(units), dtype=bool)
    similar = []
    for i, j in zip(*np.unravel_index(np.argsort(-np.where(linked, similarity, -np.inf), axis=None), linked.shape)):
        if linked[i, j] and free[i] and free[j]:
            clique = [i, j]
            for k in np.argsort(-similarity[i]):
                if free[k] and k not in clique and linked[k, clique].all():
                    clique.append(k)
            free[clique] = False
            similar.append(sorted(units.index[clique].tolist()))
    neuron = ~units['proposed'].isin(['noise', 'non_soma']).to_numpy()
    groups = []
    for group, decision, proposer in [(g, d, sorter) for g, d in zip(kilosort, decisions)] + [(g, 'not proposed', None) for g in similar]:
        rows = units.index.get_indexer(group)
        outside = (similarity[rows] > SIMILARITY).any(axis=0) & neuron & ~units.index.isin(group)
        groups.append({'units': group, 'kilosort': decision, 'proposer': proposer, 'also_similar': units.index[outside].tolist(),
                       'all_noise': bool(units.loc[group, 'proposed'].isin(['noise', 'non_soma']).all())})
    groups = [g for g in groups if not g['all_noise']] + [g for g in groups if g['all_noise']]
    # Units under Bombcell's spike-count limit are proposed few unless proposed noise (after the groups, which follow Bombcell)
    few = thresholds['mua']['num_spikes']['greater']
    units.loc[(units['num_spikes'] < few) & (units['proposed'] != 'noise'), 'proposed'] = 'few'
    progress[sort] = 'arrays for the page'
    # Arrays the page loads once, one row per original unit
    channel_xy = np.load(os.path.join(cache, 'channel_positions.npy'))
    sites = np.load(os.path.join(cache, 'display_sites.npy'))
    arrays = {'waveform': np.load(os.path.join(cache, 'display_mean.npy')),
              'density': np.load(os.path.join(cache, 'display_density.npy')),
              'density_range': np.load(os.path.join(cache, 'display_range.npy')),
              'density_count': np.load(os.path.join(cache, 'display_count.npy')),
              'amplitude': np.load(os.path.join(cache, 'amplitude_sample.npy')),
              'similarity': similarity,
              'site_xy': np.where(sites[:, :, None] >= 0, channel_xy[sites], np.nan).astype(np.float32),
              'spike_offset': np.r_[0, np.cumsum([len(samples[u]) for u in units.index])].astype(np.uint32),
              # Each unit's samples as differences from the one before (its first from 0); the page sums them
              'spike_sample': np.concatenate([np.diff(samples[u].astype(np.int64), prepend=0) for u in units.index]).astype(np.uint32)}
    paths = {}
    flights = {}
    # Spikes on paths, from the sort's positions file
    if os.path.exists(os.path.join(curation, 'positions.npz')):
        position = np.load(os.path.join(curation, 'positions.npz'))
        # Rate maps: 0.1 m bins over all the paths
        everywhere = np.concatenate([position[k] for k in position.files if k.startswith('path_xy_')])
        flights = {'key': spike_times[position['spike_index']].astype(np.int64) * 100000 + spike_clusters[position['spike_index']],
                   'xy': position['spike_xy'], 'cluster': position['spike_path'], 'frame_rate_hz': float(position['frame_rate_hz']),
                   'paths': {int(k.removeprefix('path_xy_')): position[k] for k in position.files if k.startswith('path_xy_')},
                   'bins': [np.arange(np.floor(low / 0.1) * 0.1, high + 0.1, 0.1) for low, high in zip(everywhere.min(axis=0), everywhere.max(axis=0))]}
        # Spikes on paths grouped by original unit
        row = pd.Series(np.arange(len(units)), index=units.index)[spike_clusters[position['spike_index']]].to_numpy()
        by_unit = np.argsort(row, kind='stable')
        arrays['position_xy'] = position['spike_xy'][by_unit].astype(np.float32)
        arrays['position_cluster'] = position['spike_path'][by_unit].astype(np.uint8)
        arrays['position_offset'] = np.searchsorted(row[by_unit], np.arange(len(units) + 1)).astype(np.uint32)
        flights['rows'] = dict(zip(units.index, np.split(by_unit, arrays['position_offset'][1:-1])))
        # Paths, broken where consecutive frames are over 1 m apart
        for key in [k for k in position.files if k.startswith('path_xy_')]:
            xy = position[key][::4]
            jumps = np.flatnonzero(np.linalg.norm(np.diff(xy, axis=0), axis=1) > 1) + 1
            broken = np.insert(xy, jumps, np.nan, axis=0).round(3)
            paths[key.removeprefix('path_xy_')] = np.where(np.isnan(broken), None, broken.astype(object)).tolist()
    header = json.dumps({k: [str(v.dtype), list(v.shape)] for k, v in arrays.items()}).encode()
    blob = len(header).to_bytes(4, 'little') + header + b' ' * (-(4 + len(header)) % 8) \
        + b''.join(v.tobytes() + b'\0' * (-v.nbytes % 8) for v in arrays.values())
    # The blob compressed, beside the ranking below
    zipping = ThreadPoolExecutor(1).submit(gzip.compress, blob, 1, mtime=0)
    data = {'sort': sort, 'units': units, 'records': units.to_dict('index'), 'spikes': units['num_spikes'].to_dict(),
            'all_samples': samples, 'ks_amplitude': ks_amplitude, 'n_spikes_by_unit': [len(samples[u]) for u in units.index], 'groups': groups, 'blob': blob, 'paths': paths,
            'blob_tag': f'"{os.path.getmtime(os.path.join(cache, "units.csv"))}-{len(blob)}"',
            'rate_hz': recording['rate_hz'], 'n_samples': recording['n_samples'], 'few': few, 'merged': {}, 'pairs': {}, 'trains': {}, 'blocks': {},
            'footprints': {}, 'footprint_pairs': {}, 'evidence': {}, 'possible_slots': [], 'ratemaps': {}, 'shape': shape, 'thresholds': thresholds,
            'refractory_thresholds': refractory_thresholds(sort),
            'duplicate_window': duplicate_window(sort), 'sites': sites,
            'templates': np.load(os.path.join(cache, 'templates.npy'), mmap_mode='r'),
            'ks_similarity': np.load(os.path.join(sort, 'similar_templates.npy')),
            'traces': np.load(os.path.join(cache, 'display_spikes.npy'), mmap_mode='r'),
            'flights': flights, 'channel_xy': channel_xy, 'log': os.path.join(curation, 'curation_log.jsonl')}
    progress[sort] = 'refractory test of every merge group'
    # Order of the merge groups, fixed for the session: first those in which every pair passes Kilosort's refractory test,
    # then those with a pair too sparse to test, then those the tests argue against (a pair not refractory, or the merged
    # unit over the contamination limit); groups of units all proposed noise stay last
    for g in groups:
        verdicts = {pair['verdict'] for pair in refractory_pairs(data, [spikes_key([u], {}) for u in g['units']]).values()}
        against = 'not refractory' in verdicts or merged_unit(data, spikes_key(g['units'], {}))['rp_label'] != 'good'
        g['rank'] = 3 if g['all_noise'] else 2 if against else 1 if 'untestable' in verdicts else 0
    # A similar-waveform group the refractory test argues against is not a merge candidate: its units go to their own sections
    candidates = sorted([g for g in groups if not (g['proposer'] is None and g['rank'] == 2)], key=lambda g: g['rank'])
    # Groups under the spike-count limit in all are not listed: too small to matter whether merged or not
    data['groups'] = [g for g in candidates if sum(data['spikes'][u] for u in g['units']) >= few]
    data['blob_gzip'] = zipping.result()
    return data


def state_key(sort):
    """Hash of what an opened sort is computed from: the size and time of its files, and this code."""
    cache = os.path.join(sort, 'curation', 'cache')
    files = [os.path.join(sort, name) for name in ['spike_times.npy', 'spike_clusters.npy', 'amplitudes.npy', 'similar_templates.npy', 'ops.npy',
                                                   'proposed_merges.json']]
    files += [os.path.join(cache, 'units.csv'), os.path.join(cache, 'templates.npy'), os.path.join(sort, 'curation', 'positions.npz')]
    stamps = [(name, os.stat(name).st_size, os.stat(name).st_mtime_ns) for name in files if os.path.exists(name)]
    code = [open(os.path.join(HERE, name), 'rb').read() for name in ['opened.py', 'labels.py', 'state.py', 'ratemaps.py', 'waveforms.py', 'thresholds.json']]
    return hashlib.sha256(repr(stamps).encode() + b''.join(code)).hexdigest()


def save_caches(data):
    """The per-unit and per-pair results computed so far, saved beside the opened sort."""
    folder = os.path.join(data['sort'], 'curation', 'opened')
    with open(os.path.join(folder, 'caches.partial'), 'wb') as f:
        pickle.dump({name: data[name] for name in CACHES}, f, protocol=5)
    os.replace(os.path.join(folder, 'caches.partial'), os.path.join(folder, 'caches.pkl'))


def save_opened(data):
    """A built sort written to <sort>/curation/opened: spike samples and amplitudes by unit, the page's arrays, the rest pickled."""
    progress[data['sort']] = 'saving for next time'
    folder = os.path.join(data['sort'], 'curation', 'opened')
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(folder)
    units = data['units'].index
    np.save(os.path.join(folder, 'spike_sample.npy'), np.concatenate([data['all_samples'][u] for u in units]))
    np.save(os.path.join(folder, 'ks_amplitude.npy'), np.concatenate([data['ks_amplitude'][u] for u in units]))
    with open(os.path.join(folder, 'arrays.bin'), 'wb') as f:
        f.write(data['blob'])
    with open(os.path.join(folder, 'arrays.gz'), 'wb') as f:
        f.write(data['blob_gzip'])
    left_out = ['all_samples', 'ks_amplitude', 'blob', 'blob_gzip', 'templates', 'ks_similarity', 'traces', 'trains', 'ratemaps', 'possible_slots'] + CACHES
    with open(os.path.join(folder, 'opened.pkl'), 'wb') as f:
        pickle.dump({name: value for name, value in data.items() if name not in left_out}, f, protocol=5)
    save_caches(data)
    # The key is written last: a folder without it is not complete
    with open(os.path.join(folder, 'key.txt'), 'w') as f:
        f.write(state_key(data['sort']))


def read_opened(sort):
    """An opened sort from <sort>/curation/opened; the large arrays stay on disk and are read as they are used."""
    progress[sort] = 'reading the saved sort'
    folder = os.path.join(sort, 'curation', 'opened')
    cache = os.path.join(sort, 'curation', 'cache')
    data = pickle.load(open(os.path.join(folder, 'opened.pkl'), 'rb'))
    units = data['units'].index
    bounds = np.cumsum(data['n_spikes_by_unit'])[:-1]
    data['all_samples'] = dict(zip(units, np.split(np.load(os.path.join(folder, 'spike_sample.npy'), mmap_mode='r'), bounds)))
    data['ks_amplitude'] = dict(zip(units, np.split(np.load(os.path.join(folder, 'ks_amplitude.npy'), mmap_mode='r'), bounds)))
    data['templates'] = np.load(os.path.join(cache, 'templates.npy'), mmap_mode='r')
    data['ks_similarity'] = np.load(os.path.join(sort, 'similar_templates.npy'))
    data['traces'] = np.load(os.path.join(cache, 'display_spikes.npy'), mmap_mode='r')
    data['arrays'] = os.path.join(folder, 'arrays.bin')
    data['arrays_gzip'] = os.path.join(folder, 'arrays.gz')
    data.update(pickle.load(open(os.path.join(folder, 'caches.pkl'), 'rb')))
    data.update({'trains': {}, 'ratemaps': {}, 'possible_slots': []})
    return data


def load(sort):
    """An opened sort: read when saved from the files and code as they are now, else built and saved first."""
    key = os.path.join(sort, 'curation', 'opened', 'key.txt')
    if not os.path.exists(key) or open(key).read() != state_key(sort):
        save_opened(build(sort))
    return read_opened(sort)


def new_id(data, logged):
    """Number of the next unit a merge or a floor makes."""
    return max([int(data['units'].index.max())] + [e['id'] for e in logged if 'id' in e]) + 1


def spikes_key(parts, floors):
    """Original units, each with its amplitude floor (None without one): what every spike-train result is computed from."""
    return tuple((m, floors[m][0] if m in floors else None) for m in parts)


def unit_samples(data, unit, floor):
    """Spike samples of an original unit at or above its amplitude floor."""
    samples = data['all_samples'][unit]
    return samples if floor is None else samples[data['ks_amplitude'][unit] >= floor]


def merged_samples(data, key):
    """Spike samples of original units united, duplicates dropped as Kilosort does."""
    if key not in data['trains']:
        together = np.sort(np.concatenate([unit_samples(data, m, floor) for m, floor in key]))
        data['trains'][key] = together if len(key) == 1 else together[not_duplicate(together, data['duplicate_window'])]
    return data['trains'][key]


def merged_block_rates(data, key):
    """Spikes per sample in each 5-minute block of the unit made of original units."""
    if key not in data['blocks']:
        data['blocks'][key] = block_rates(merged_samples(data, key), data['n_samples'], data['rate_hz'])
    return data['blocks'][key]


def rate_maps(data, key):
    """GridBat rate map (Hz) per flight cluster of the unit made of original units: 0.1 m bins, smoothed by 1.2 bins,
    bins flown for under 0.03 s empty. Duplicates dropped as in the merged unit."""
    if key not in data['ratemaps']:
        flights = data['flights']
        trains = [unit_samples(data, m, floor) for m, floor in key]
        samples = np.concatenate(trains).astype(np.int64)
        unit = np.concatenate([np.full(len(train), m) for (m, _), train in zip(key, trains)])
        order = np.argsort(samples, kind='stable')
        kept = not_duplicate(samples[order], data['duplicate_window'])
        # Flight spikes of these original units that are kept
        rows = np.sort(np.concatenate([flights['rows'][m] for m, _ in key]))
        ours = rows[np.isin(flights['key'][rows], (samples[order] * 100000 + unit[order])[kept])]
        maps = {}
        for cluster, path in flights['paths'].items():
            spike_xy = flights['xy'][ours[flights['cluster'][ours] == cluster]]
            rate = bin_spikes_on_pos(spike_xy, path, flights['bins'], 2, 1 / flights['frame_rate_hz'], 0.03, 1.2, None, None, None)['rate']
            maps[cluster] = [None if np.isnan(v) else round(float(v), 3) for v in rate.ravel()]
        data['ratemaps'][key] = maps
    return data['ratemaps'][key]


def mean_template(data, parts):
    """Mean waveform on every channel of the unit made of original units: each site averaged over the members recorded on it."""
    rows = data['units'].index.get_indexer(parts)
    counts = data['units']['num_spikes'].to_numpy()[rows]
    templates = data['templates'][rows][:, WINDOW]
    recorded = (np.ptp(templates, axis=1) > 0) * counts[:, None]
    return (templates * recorded[:, None, :]).sum(axis=0) / recorded.sum(axis=0).clip(1)


def refractory_measures(data, samples):
    """Three contamination measures of one spike train: foreign spikes (with the pairs seen and expected behind it and the
    label it gives), Kilosort's refractory ratio, and the share of inter-spike intervals of 0.25 to 1.25 ms."""
    seen, expected, foreign = foreign_spikes(samples, data['rate_hz'])
    return {'rp_label': 'good' if foreign <= MAX_CONTAMINATION else 'mua', 'rp_contamination': number(foreign), 'rp_seen': seen,
            'rp_expected': number(expected), 'ks_ratio': number(check_CCG(samples / data['rate_hz'], **data['refractory_thresholds'])[2]),
            'short_fraction': number(short_interval_share(samples, data['rate_hz']))}


def merged_unit(data, key):
    """Statistics of the unit made by merging original units, duplicates dropped as Kilosort does."""
    if key not in data['merged']:
        parts = [m for m, _ in key]
        samples = merged_samples(data, key)
        rows = data['units'].index.get_indexer(parts)
        counts = data['units']['num_spikes'].to_numpy()[rows]
        occupied = np.histogram(samples, np.arange(0, data['n_samples'] + 1, 60 * data['rate_hz']))[0] > 0
        data['merged'][key] = {
            'n_spikes': len(samples), 'duplicates': sum(len(unit_samples(data, m, floor)) for m, floor in key) - len(samples),
            'presence': float(occupied.mean()), 'short_isi': int(np.sum(np.diff(samples) <= data['rate_hz'] * 1e-3)),
            **refractory_measures(data, samples),
            'amplitude': number(np.average(np.abs(data['units']['amplitude_median'].to_numpy()[rows]), weights=counts)),
            'depth': float(data['units']['depth'].to_numpy()[rows[counts.argmax()]]), 'site_row': int(rows[counts.argmax()])}
        data['merged'][key]['bombcell'] = merged_bombcell(data, data['merged'][key], parts[counts.argmax()])
    return data['merged'][key]


def merged_bombcell(data, merged, largest):
    """Bombcell label of a merged unit: its spike metrics with the waveform shape metrics of its largest member; few
    under the spike-count limit unless noise."""
    spike = pd.DataFrame({'num_spikes': [merged['n_spikes']], 'presence_ratio': [merged['presence']],
                          'refractory_good': [int(merged['rp_label'] == 'good')]}, index=[largest])
    label = bombcell_labels(spike, data['shape'].loc[[largest]], data['thresholds'], False)[0]
    return 'few' if merged['n_spikes'] < data['few'] and label != 'noise' else label


def merged_waveform(data, parts):
    """Mean waveform of the unit made of original units on the display sites of its largest one."""
    rows = data['units'].index.get_indexer(parts)
    sites = data['sites'][rows[data['units']['num_spikes'].to_numpy()[rows].argmax()]]
    return missing_none(np.where((sites >= 0) & recorded(data, parts)[sites], mean_template(data, parts)[:, sites], np.nan))


def recorded(data, parts):
    """Channels on which any original unit of the unit has a template (the others hold no data)."""
    rows = data['units'].index.get_indexer(parts)
    return (np.ptp(data['templates'][rows][:, WINDOW], axis=1) > 0).any(axis=0)


def missing_none(values):
    """Values rounded to 0.1 for JSON, None where missing (NaN)."""
    return np.where(np.isnan(values), None, values.round(1).astype(object)).tolist()


def footprint(data, parts):
    """Peak-to-peak amplitude on every channel of the unit made of original units."""
    key = tuple(parts)
    if key not in data['footprints']:
        data['footprints'][key] = np.ptp(mean_template(data, parts), axis=0)
    return data['footprints'][key]


def near_channels(data, footprints):
    """Channels within 100 um of the peak channel of the largest of these footprints."""
    peak = footprints[np.argmax([f.max() for f in footprints])].argmax()
    return np.linalg.norm(data['channel_xy'] - data['channel_xy'][peak], axis=1) <= 100


def footprint_correlation(data, a, b):
    """Correlation of two units' footprints on the channels within 100 um of the larger one's peak channel that both
    have data on."""
    key = (tuple(a), tuple(b))
    if key not in data['footprint_pairs']:
        footprints = [footprint(data, parts) for parts in (a, b)]
        near = near_channels(data, footprints) & recorded(data, a) & recorded(data, b)
        data['footprint_pairs'][key] = np.corrcoef(footprints[0][near], footprints[1][near])[0, 1]
    return data['footprint_pairs'][key]


def pair_evidence(data, a, b):
    """Footprint correlation, notch (None under 5 centre pairs expected) and hand-off of two units, each the spikes key
    of its original units, and whether they qualify as a possible merge."""
    key = tuple(sorted([a, b]))
    if key not in data['evidence']:
        train_a, train_b = merged_samples(data, key[0]), merged_samples(data, key[1])
        a, b = [[m for m, _ in k] for k in key]
        centre, flank = notch_rates(train_a, train_b, data['rate_hz'])
        # The notch is read from 5 centre pairs expected
        expected = flank * 1.5
        notch = number(centre / flank) if expected >= 5 else None
        score = handoff(merged_block_rates(data, key[0]), merged_block_rates(data, key[1]))
        correlation = footprint_correlation(data, a, b)
        data['evidence'][key] = {'footprint': number(correlation), 'notch': notch, 'handoff': number(score),
                                 'qualifies': bool(correlation >= 0.85 and ((notch is not None and notch <= 0.5) or score > HANDOFF))}
    return data['evidence'][key]


def possible_pairs(data, state, groups):
    """Possible merges the sorter did not propose: pairs of current units with peak channels within 100 um, neither
    proposed noise while unlabelled (a label never removes a pair: it stays listed with its decision), neither in an open proposed group, not together in a proposed
    group, that qualify; ranked by footprint, then notch; each unit in its best pair, except pairs kept apart, which stay
    at their place as decided (kept True)."""
    members, labels, flagged, kept, floors = state
    proposed = data['units']['proposed']
    busy = {u for g in groups if not g['kept'] and len(g['units']) > 1 and any(u not in labels for u in g['units']) for u in g['units']}
    units = sorted([u for u, parts in members.items() if not (u not in labels and parts == [u] and proposed[u] == 'noise') and u not in busy],
                   key=lambda u: members[u])
    # Neighbours
    peaks = data['channel_xy'][[footprint(data, members[u]).argmax() for u in units]]
    apart = np.linalg.norm(peaks[:, None] - peaks[None], axis=2)
    near = [(units[i], units[j]) for i, j in zip(*np.nonzero(np.triu(apart <= 100, 1)))]
    # Footprint, then the timing evidence
    similar = [(a, b) for a, b in near if footprint_correlation(data, members[a], members[b]) >= 0.85]
    together = {frozenset((x, y)) for g in groups for x in g['units'] for y in g['units']}
    unproposed = [(a, b, any(set(members[a] + members[b]) <= k for k in kept)) for a, b in similar if frozenset((a, b)) not in together]
    qualifying = [(a, b, e, apart) for a, b, apart in unproposed for e in [pair_evidence(data, spikes_key(members[a], floors), spikes_key(members[b], floors))] if e['qualifies']
                  and sum(data['spikes'][m] for m in members[a] + members[b]) >= data['few']]
    qualifying.sort(key=lambda pair: (-pair[2]['footprint'], np.inf if pair[2]['notch'] is None else pair[2]['notch']))
    # Each unit in its best open pair
    chosen, taken = [], set()
    for a, b, e, apart in qualifying:
        if apart or not {a, b} & taken:
            chosen.append((a, b, e, apart))
        if not apart:
            taken |= {a, b}
    return chosen


def refractory_levels(counts, n1, n2, span):
    """Kilosort's cross-refractory test as levels (x chance) on its 1 ms cross-correlogram: the flank level it compares
    against (far shoulders or 10-50 ms, the higher) and its least filled window of +-i bins around zero (the zero bin
    counted as empty), with i in ms."""
    chance = 1e-3 * n1 * n2 / span
    flank = max(counts[np.r_[1:250, 750:1000]].mean(), counts[450:490].mean(), counts[510:550].mean()) / chance
    centre = counts.copy()
    centre[500] = 0
    levels = [centre[500 - i:501 + i].sum() / (2 * i) / chance for i in range(1, 11)]
    return {'centre': float(min(levels)), 'flank': float(flank), 'window_ms': int(np.argmin(levels)) + 1}


def refractory_pairs(data, units):
    """Kilosort's cross-refractory test (the one its merge uses) for every pair of units, each the spikes key of its original units:
    refractory (ratio under the limit, significant), untestable (ratio under the limit, too few spikes to be significant)
    or not refractory; the correlation of their peak-to-peak footprints on the channels within 100 um of the larger
    one's peak channel; and their hand-off."""
    pairs = {}
    for i, a in enumerate(units):
        for b in units[i + 1:]:
            key = (a, b)
            if key not in data['pairs']:
                # The larger unit first, as in Kilosort's merge
                larger, smaller = sorted([a, b], key=lambda parts: len(merged_samples(data, parts)), reverse=True)
                trains = [merged_samples(data, larger), merged_samples(data, smaller)]
                counts, span = compute_CCG(trains[0] / data['rate_hz'], trains[1] / data['rate_hz'], nbins=500, tbin=1 / 1000)
                ratio, significance, _ = CCG_metrics(trains[0], trains[1], counts, span, nbins=500, tbin=1 / 1000)
                under = ratio < data['refractory_thresholds']['ccg_threshold']
                data['pairs'][key] = {'verdict': 'refractory' if under and significance < 0.05 else 'untestable' if under else 'not refractory',
                                      'ratio': number(ratio), 'p': number(significance), 'limit': data['refractory_thresholds']['ccg_threshold'],
                                      **refractory_levels(counts, len(trains[0]), len(trains[1]), span),
                                      'footprint': number(footprint_correlation(data, [m for m, _ in a], [m for m, _ in b])),
                                      'handoff': number(handoff(merged_block_rates(data, larger), merged_block_rates(data, smaller)))}
            pairs['|'.join(map(str, sorted([min(a)[0], min(b)[0]])))] = data['pairs'][key]
    return pairs


def group_pairs(data, members, floors, now):
    """Pairs of a group's current units; a group merged into one unit keeps the pairs of its original units."""
    return refractory_pairs(data, [spikes_key(members[u], floors) for u in now] if len(now) > 1 else [spikes_key([m], floors) for m in members[now[0]]])


def neighbour_evidence(data, members, floors, unit):
    """Units with peak channels within 100 um of one unit, each with its pair evidence."""
    peak = data['channel_xy'][footprint(data, members[unit]).argmax()]
    near = [u for u in members if u != unit and np.linalg.norm(data['channel_xy'][footprint(data, members[u]).argmax()] - peak) <= 100]
    return [{'unit': u, **pair_evidence(data, spikes_key(members[unit], floors), spikes_key(members[u], floors))} for u in near]


def partners(data, members, floors, unit):
    """A unit's neighbours with their pair evidence: qualifying first, by footprint."""
    found = neighbour_evidence(data, members, floors, unit)
    found.sort(key=lambda p: (not p['qualifies'], -p['footprint'], np.inf if p['notch'] is None else p['notch']))
    return found


def kilosort_similarity(data, originals):
    """Kilosort's template similarity among original units (cluster = template in an unmerged sort): the least similar pair."""
    block = data['ks_similarity'][np.ix_(originals, originals)]
    return float(block[np.triu_indices(len(originals), 1)].min())


def number(value):
    """A float for JSON, None when missing or infinite."""
    return None if pd.isna(value) or np.isinf(value) else float(value)


def unit_table(data, state):
    """One record per current unit with its review section, and every proposed group with its current units."""
    members, labels, flagged, kept, floors = state
    records, spikes = data['records'], data['spikes']
    duration = data['n_samples'] / data['rate_hz']
    current = {m: unit for unit, parts in members.items() for m in parts}
    summary = ['n_spikes', 'duplicates', 'short_isi', 'rp_label', 'rp_contamination', 'rp_seen', 'rp_expected', 'ks_ratio', 'short_fraction', 'presence', 'amplitude', 'bombcell']
    groups = []
    for g in data['groups']:
        now = list(dict.fromkeys(current[u] for u in g['units']))
        originals = sorted(m for u in now for m in members[u])
        groups.append({'units': now, 'kilosort': g['kilosort'], 'proposer': g['proposer'], 'section': 'groups', 'kept': any(set(g['units']) <= k for k in kept),
                       'also_similar': sorted({current[u] for u in g['also_similar']} - set(now)),
                       'if_merged': {k: merged_unit(data, spikes_key(originals, floors))[k] for k in summary},
                       'similarity': kilosort_similarity(data, originals), 'pairs': group_pairs(data, members, floors, now)})
    # Groups that a merge has joined are shown as one
    fused = []
    for g in groups:
        joined = [f for f in fused if set(f['units']) & set(g['units'])]
        for f in joined:
            fused.remove(f)
        if joined:
            now = list(dict.fromkeys(u for f in joined + [g] for u in f['units']))
            originals = sorted(m for u in now for m in members[u])
            g = {'units': now, 'kilosort': '; '.join(dict.fromkeys(f['kilosort'] for f in joined + [g])), 'section': 'groups',
                 'proposer': next((f['proposer'] for f in joined + [g] if f['proposer']), None),
                 'kept': all(f['kept'] for f in joined + [g]), 'if_merged': {k: merged_unit(data, spikes_key(originals, floors))[k] for k in summary},
                 'also_similar': sorted({u for f in joined + [g] for u in f['also_similar']} - set(now)),
                 'similarity': kilosort_similarity(data, originals), 'pairs': group_pairs(data, members, floors, now)}
        fused.append(g)
    groups = fused
    grouped = {u for g in groups for u in g['units']}
    # Possible merges, after the proposed groups, each in the place it was first listed: a pair merged since stays there
    # as its merged unit; pairs found later go after the others
    pairs = {frozenset(members[a] + members[b]): (a, b, apart) for a, b, e, apart in possible_pairs(data, state, groups)}
    data['possible_slots'] += [originals for originals in pairs if originals not in data['possible_slots']]
    possible = []
    for originals in data['possible_slots']:
        now = sorted({current[m] for m in originals})
        if originals in pairs:
            a, b, apart = pairs[originals]
            now = [a, b]
        elif len(now) != 1 or set(members[now[0]]) != originals:
            continue
        else:
            apart = False
        possible.append({'units': now, 'kilosort': 'not proposed', 'proposer': None, 'section': 'possible', 'kept': apart,
                         'also_similar': [], 'if_merged': {k: merged_unit(data, spikes_key(sorted(originals), floors))[k] for k in summary},
                         'similarity': kilosort_similarity(data, sorted(originals)), 'pairs': group_pairs(data, members, floors, now)})
    paired = {u for g in possible if not g['kept'] for u in g['units']}
    table = []
    for unit, parts in members.items():
        home = records[max(parts, key=spikes.get)]
        if len(parts) > 1:
            record = {**merged_unit(data, spikes_key(parts, floors)), 'proposed': merged_unit(data, spikes_key(parts, floors))['bombcell'], 'failed': [], 'flips': False, 'draws': '',
                      'snr': None, 'duration_ms': None, 'member_proposals': [records[m]['proposed'] for m in parts]}
        else:
            u = home
            record = {'n_spikes': int(u['num_spikes']), 'short_isi': int(u['short_isi']),
                      'rp_label': 'good' if u['refractory_good'] else 'mua', 'rp_contamination': number(u['rp_contamination']),
                      'rp_seen': int(u['rp_seen']), 'rp_expected': number(u['rp_expected']), 'ks_ratio': number(u['ContamPct'] / 100), 'short_fraction': number(u['short_fraction']),
                      'depth': float(u['depth']),
                      'proposed': u['proposed'], 'non_somatic': bool(u['non_somatic']), 'failed': u['failed'], 'flips': bool(u['flips']), 'draws': u['draws'],
                      'amplitude': number(abs(u['amplitude_median'])), 'snr': number(u['snr']),
                      'presence': number(u['presence_ratio']), 'duration_ms': number(u['duration_ms']),
                      'draw_labels': [u[f'bombcell_draw{d}'] for d in range(DRAWS)]}
        if len(parts) == 1 and unit in floors:
            # Spike-train numbers of the spikes above the floor; waveform numbers stay those of the whole unit
            above = merged_unit(data, spikes_key(parts, floors))
            record.update({k: above[k] for k in ['n_spikes', 'short_isi', 'rp_label', 'rp_contamination', 'rp_seen', 'rp_expected', 'ks_ratio', 'short_fraction', 'presence']})
            record['floor'] = floors[unit][0]
            record['below_floor'] = len(data['all_samples'][unit]) - above['n_spikes']
            # A unit that failed only the refractory test and passes it above the floor is proposed good
            if record['failed'] == ['refractory_good'] and above['rp_label'] == 'good':
                record.update({'failed': [], 'proposed': 'good'})
        record['floors'] = {m: floors[m][0] for m in parts if m in floors}
        record['section'] = 'groups' if unit in grouped else 'possible' if unit in paired else 'uncertain' if home['flips'] \
            else 'few' if record['proposed'] == 'few' else home['proposed']
        # A unit under the spike-count limit is few spikes without a decision, unless the curator labelled it
        table.append({'unit': unit, 'members': parts, 'label': labels.get(unit, 'few' if record['n_spikes'] < data['few'] else None),
                      'auto_few': unit not in labels and record['n_spikes'] < data['few'], 'rate': record['n_spikes'] / duration,
                      'flagged': unit in flagged, **record})
    return table, groups + possible
