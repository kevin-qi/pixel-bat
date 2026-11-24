"""Inter-spike intervals of one unit below 6 ms in 0.25 ms bins, against the count a Poisson train of its rate would give: short_intervals.py SORT UNIT."""
import sys

import numpy as np

sort, unit = sys.argv[1], int(sys.argv[2])
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
train = spike_times[np.load(f'{sort}/spike_clusters.npy').ravel() == unit]
duration = spike_times.max() / 30000
# All spike pairs up to 6 ms apart, as in the autocorrelogram
last = np.searchsorted(train, train + 180, side='right')
lags = np.concatenate([train[i + 1:j] - train[i] for i, j in enumerate(last)]) / 30
counts = np.histogram(lags, np.arange(0, 6.25, 0.25))[0]
expected = len(train) ** 2 / duration * 0.00025
print(f'{len(train)} spikes, {len(train) / duration:.2f} Hz; expected per 0.25 ms bin at this rate: {expected:.1f}')
for edge, count in zip(np.arange(0, 6, 0.25), counts):
    print(f'{edge:4.2f}-{edge + 0.25:4.2f} ms: {count}')
