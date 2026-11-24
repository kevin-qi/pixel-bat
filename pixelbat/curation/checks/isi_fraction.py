"""Share of inter-spike intervals under 2 ms and under 1 ms, and mean rate, of units: isi_fraction.py SORT UNIT [UNIT ...].

Gardner et al. 2022 (Nature) discard a unit when more than 1% of its intervals are under 2 ms, or its mean rate is under 0.05 Hz or over 10 Hz.
"""
import sys

import numpy as np

sort = sys.argv[1]
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
duration = spike_times.max() / 30000
for unit in map(int, sys.argv[2:]):
    intervals = np.diff(spike_times[spike_clusters == unit]) / 30
    print(f'unit {unit}: {len(intervals) + 1} spikes, {(len(intervals) + 1) / duration:.2f} Hz, '
          f'{100 * np.mean(intervals < 2):.2f}% of intervals under 2 ms ({np.sum(intervals < 2)}), '
          f'{100 * np.mean(intervals < 1):.2f}% under 1 ms ({np.sum(intervals < 1)})')
