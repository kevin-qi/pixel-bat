"""The terms of Kilosort's cross-refractory test for two units, larger first: ks_refractory_terms.py SORT A B."""
import sys

import numpy as np
from kilosort.CCG import compute_CCG

sort, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
spike_times = np.load(f'{sort}/spike_times.npy').ravel() / 30000
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
st1, st2 = sorted([spike_times[spike_clusters == a], spike_times[spike_clusters == b]], key=len, reverse=True)
K, T = compute_CCG(st1, st2, nbins=500, tbin=1 / 1000)
nbins, tbin = 500, 1 / 1000
norm = tbin * len(st1) * len(st2) / T
R00 = K[np.r_[1:nbins // 2, 3 * nbins // 2:2 * nbins]].mean() / norm
R01 = max(K[nbins - 50:nbins - 10].mean(), K[nbins + 10:nbins + 50].mean()) / norm
print(f'counts per 1 ms bin, -5 to +5 ms: {K[nbins - 5:nbins + 6].astype(int).tolist()}')
print(f'expected per bin for independent trains: {norm:.2f}; far baseline {R00:.2f}x of that, 10-50 ms shoulder {R01:.2f}x')
for i in range(1, 11):
    window = K[nbins - i:nbins + i + 1].copy()
    window[i] = 0
    print(f'window +-{i} ms: {int(window.sum())} spikes, rate {window.sum() / (2 * i * norm):.2f}x, ratio to the larger baseline {window.sum() / (2 * i * norm) / max(R00, R01):.2f}')
