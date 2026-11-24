"""Spikes of unit B around each spike of unit A within 2 ms, in 0.1 ms bins, and in 1 ms bins to 10 ms: fine_cross.py SORT A B."""
import sys

import numpy as np

sort, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
ta, tb = spike_times[spike_clusters == a], spike_times[spike_clusters == b]
first, last = np.searchsorted(tb, ta - 300), np.searchsorted(tb, ta + 300, side='right')
lags = np.concatenate([tb[i:j] - t for t, i, j in zip(ta, first, last)]) / 30
print(f'{a}: {len(ta)} spikes, {b}: {len(tb)} spikes')
print('0.1 ms bins from -2 to 2 ms:', np.histogram(lags, np.arange(-2, 2.05, 0.1))[0].tolist())
print('1 ms bins from -10 to 10 ms:', np.histogram(lags, np.arange(-10, 10.5, 1))[0].tolist())
