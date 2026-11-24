"""Kilosort 2.5's contamination ratio (ccg.m and set_cutoff.m: Q = min(Qi) / max(Q00, Q01)) on the full spike train of
units, beside Kilosort 4's: ks25_contamination.py SORT UNIT [UNIT ...].

Kilosort 2.5 reports this ratio after its own per-unit amplitude cutoff, which is not reproduced here.
"""
import sys

import numpy as np
from kilosort.CCG import check_CCG, compute_CCG

sort = sys.argv[1]
spike_times = np.load(f'{sort}/spike_times.npy').ravel() / 30000
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
nbins, tbin = 500, 1 / 1000
for unit in map(int, sys.argv[2:]):
    st = spike_times[spike_clusters == unit]
    K, T = compute_CCG(st, st, nbins=nbins, tbin=tbin)
    norm = tbin * len(st) * len(st) / T
    # Index ranges of ccg.m, zero-based
    far = np.r_[1:nbins // 2, 3 * nbins // 2:2 * nbins]
    Q00 = K[far].sum() / (len(far) * norm)
    Q01 = max(K[nbins - 50:nbins - 10].sum() / (40 * norm), K[nbins + 11:nbins + 50].sum() / (39 * norm))
    K[nbins] = 0
    Qi = [K[nbins - i:nbins + i + 1].sum() / (2 * i * norm) for i in range(1, 11)]
    print(f'unit {unit}: Kilosort 2.5 ratio {min(Qi) / max(Q00, Q01):.3f}, Kilosort 4 ratio {check_CCG(st)[2]:.3f}')
