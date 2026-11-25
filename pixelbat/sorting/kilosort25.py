"""Kilosort 2.5 with the Moser patch set (Gardner et al. 2022) on one recording, for curation.

MATLAB sorts the recording into <out>/uncut (uncut, unmerged Phy folder and every diagnostic) and runs step 3 into
<out>, the sort folder: every split made, the stock amplitude cutoff, no merge, the merges Kilosort 2.5 would make saved
as proposals. Python then adds to <out> what the curator reads.
"""
import json
import os
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
from scipy.io import loadmat, savemat
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from pixelbat.sorting.probe import trodes_probe

# Patched Kilosort 2.5, npy-matlab and the MATLAB drivers shipped with this package
KILOSORT25_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kilosort25_moser')


def windows_path(path, shares):
    """Windows path of a WSL path: through its network share when under one of the mounts, else as wslpath gives it."""
    for mount, share in shares.items():
        if path.startswith(mount + '/'):
            return share + path[len(mount):].replace('/', '\\')
    return subprocess.run(['wslpath', '-w', path], capture_output=True, text=True, check=True).stdout.strip()


def number(x):
    """JSON value of a statistic that may be infinite or undefined."""
    return float(x) if np.isfinite(x) else None


def sort_kilosort25(binary, coordinates, masked_channels, spikes_positive, nblocks, out, scratch, matlab, kilosort25_dir,
                    gpu, windows_shares):
    """Sort of one recording into out and out/uncut; MATLAB stages whose output exists are skipped."""
    t0 = time.time()
    uncut = os.path.join(out, 'uncut')
    fproc = os.path.join(scratch, os.path.basename(binary).removesuffix('.dat'))
    os.makedirs(uncut, exist_ok=True)

    ## Paths as MATLAB sees them: Windows MATLAB called from WSL, or MATLAB on this machine
    on_windows = matlab.lower().endswith('.exe')
    m_binary, m_out, m_uncut, m_fproc, m_tree = [windows_path(p, windows_shares) if on_windows else p
                                                 for p in (binary, out, uncut, fproc, kilosort25_dir)]
    setup = (f"gpuDevice({gpu}); addpath('{m_tree}'); addpath(genpath(fullfile('{m_tree}', 'Kilosort-2.5-moser'))); "
             f"addpath(fullfile('{m_tree}', 'npy-matlab')); ")

    ## Full sort, ending with step 3 (skipped when rez_step2.mat exists)
    if not os.path.exists(os.path.join(uncut, 'rez_step2.mat')):
        # Channel map: masked channels not connected; MATLAB indices start at 1
        sites = trodes_probe(coordinates)
        connected = ~np.isin(sites['chanMap'], masked_channels)
        savemat(os.path.join(uncut, 'chanmap.mat'), {
            'chanMap': (sites['chanMap'].astype(np.float64) + 1).reshape(-1, 1),
            'xcoords': sites['xc'].astype(np.float64).reshape(-1, 1), 'ycoords': sites['yc'].astype(np.float64).reshape(-1, 1),
            'kcoords': (sites['kcoords'].astype(np.float64) + 1).reshape(-1, 1), 'connected': connected.reshape(-1, 1)})
        print(f'{sites["n_chan"]} channels, {int((~connected).sum())} masked', flush=True)
        os.makedirs(fproc, exist_ok=True)
        # Kilosort 2.5 multiplies the raw data by ops.sign so that spikes are negative-going
        command = (f"run_ks25_moser('{m_binary}', fullfile('{m_uncut}', 'chanmap.mat'), {sites['n_chan']}, "
                   f"{-1 if spikes_positive else 1}, {nblocks}, '{m_fproc}', '{m_uncut}', '{m_out}'); disp('SORT_DONE')")
        with open(os.path.join(uncut, 'kilosort25.log'), 'w') as log:
            subprocess.run([matlab, '-batch', setup + command], cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True)
        shutil.rmtree(fproc)
        print(f'sorted in {time.time() - t0:.0f} s', flush=True)

    ## Step 3 of an existing sort (skipped when its sort.json exists)
    if not os.path.exists(os.path.join(out, 'sort.json')):
        with open(os.path.join(uncut, 'kilosort25_step3.log'), 'w') as log:
            subprocess.run([matlab, '-batch', setup + f"redo_step3('{m_uncut}', '{m_out}'); disp('STEP3_DONE')"], cwd=scratch, stdout=log,
                           stderr=subprocess.STDOUT, check=True)

    ## Channels sorted, in the order of the binary
    config = json.load(open(os.path.join(out, 'sort.json')))['config']
    chanmap = loadmat(os.path.join(uncut, 'chanmap.mat'))
    connected = chanmap['connected'].ravel().astype(bool)
    np.save(os.path.join(out, 'channel_map.npy'), (chanmap['chanMap'].ravel()[connected] - 1).astype(np.int32))
    np.save(os.path.join(out, 'channel_shanks.npy'), (chanmap['kcoords'].ravel()[connected] - 1).astype(np.int32))

    ## Whitening that was applied: whitened = raw @ whitening_mat
    whitening = np.load(os.path.join(out, 'Wrot.npy')) / config['scaleproc']
    np.save(os.path.join(out, 'whitening_mat.npy'), whitening)
    np.save(os.path.join(out, 'whitening_mat_inv.npy'), np.linalg.inv(whitening))

    ## Raw binary and settings the curator reads
    with open(os.path.join(out, 'params.py'), 'w') as f:
        f.write(f"n_channels_dat = {config['NchanTOT']}\noffset = 0\nsample_rate = {config['fs']}\ndtype = 'int16'\n"
                f"hp_filtered = False\ndat_path = {binary!r}\n")
    # Kilosort 2.5: merge test Q < 0.2 (find_merges.m:44), contamination 0.1 (set_cutoff.m:28), no duplicate removal
    np.save(os.path.join(out, 'ops.npy'), {'settings': {'fs': config['fs'], 'duplicate_spike_ms': 0, 'acg_threshold': 0.1,
                                                             'ccg_threshold': 0.2}}, allow_pickle=True)

    ## Cluster tables: units with spikes
    spike_clusters = np.load(os.path.join(out, 'spike_clusters.npy')).ravel()
    units, counts = np.unique(spike_clusters, return_counts=True)
    for column in ['KSLabel', 'ContamPct', 'Amplitude', 'group']:
        path = os.path.join(out, f'cluster_{column}.tsv')
        table = pd.read_csv(path, sep='\t')
        table[table['cluster_id'].isin(units)].to_csv(path, sep='\t', index=False)

    ## Merge proposals: merges of find_merges on the split units, and splits made despite a correlogram dip
    merge_log = np.load(os.path.join(out, 'merge_log.npy')).reshape(-1, 4)
    merge_pairs = np.load(os.path.join(out, 'merge_pairs.npy')).reshape(-1, 5)
    split_log = np.load(os.path.join(out, 'split_log.npy')).reshape(-1, 9)
    vetoed = split_log[(split_log[:, 7] == 1) & (split_log[:, 8] >= 0)]
    merged_pairs = merge_log[:, :2].astype(int)
    vetoed_pairs = vetoed[:, [0, 8]].astype(int)
    linked = np.concatenate([merged_pairs, vetoed_pairs])
    n_units = len(np.load(os.path.join(out, 'cutoff_Th.npy')))
    links = coo_matrix((np.ones(len(linked)), (linked[:, 0], linked[:, 1])), shape=(n_units, n_units))
    _, component = connected_components(links, directed=False)
    groups = [np.flatnonzero(component == c) for c in np.unique(component[linked])]
    groups = [np.intersect1d(group, units) for group in groups]
    groups = [group for group in groups if len(group) > 1]
    group_sources = [{'find_merges': bool(np.isin(merged_pairs, group).any()), 'vetoed_split': bool(np.isin(vetoed_pairs, group).any())}
                     for group in groups]
    with open(os.path.join(out, 'proposed_merges.json'), 'w') as f:
        json.dump({'groups': [group.tolist() for group in groups], 'r_thresh': 0.5,
                   'spikes_per_unit': dict(zip(units.tolist(), counts.tolist())),
                   'source': 'Kilosort 2.5: find_merges on the split units; splits made despite a correlogram dip',
                   'group_sources': group_sources,
                   'log': [{'unit': int(unit), 'into': int(into), 'Q': number(Q), 'R': number(R)} for unit, into, Q, R in merge_log],
                   'vetoed_splits': [{'units': [int(unit), int(child)], 'Q12': number(Q12), 'R': number(R)}
                                     for unit, _, Q12, R, _, _, _, _, child in vetoed],
                   'pairs': [{'units': [int(i), int(j)], 'similarity': float(similarity), 'Q': number(Q), 'R': number(R)}
                             for i, j, similarity, Q, R in merge_pairs]}, f)
    print(f'{len(units)} units with spikes; merge proposals: {len(merge_log)} merges of find_merges, {len(vetoed)} splits made despite '
          f'a correlogram dip; {len(groups)} groups ({sum(g["find_merges"] and not g["vetoed_split"] for g in group_sources)} find_merges only, '
          f'{sum(g["vetoed_split"] and not g["find_merges"] for g in group_sources)} vetoed split only, '
          f'{sum(g["find_merges"] and g["vetoed_split"] for g in group_sources)} both)')
    print(f'SORT_DONE {out} in {time.time() - t0:.0f} s')
