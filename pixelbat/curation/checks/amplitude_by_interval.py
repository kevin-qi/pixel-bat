"""Is the amplitude of two units one smooth function of the time since the last spike of either? amplitude_by_interval.py SORT A B.

Per bin of the interval since the previous spike of the two units together: spikes of each unit and their median
Kilosort amplitude. One neuron whose amplitude drops in bursts gives one curve shared by both units; two neurons do not.
"""
import sys

import numpy as np
import pandas as pd

sort, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
amplitudes = np.load(f'{sort}/amplitudes.npy').ravel()
both = np.flatnonzero(np.isin(spike_clusters, [a, b]))
both = both[np.argsort(spike_times[both], kind='stable')]
interval_ms = np.diff(spike_times[both]) / 30
spikes = pd.DataFrame({'unit': spike_clusters[both][1:], 'amplitude': amplitudes[both][1:],
                       'interval': pd.cut(interval_ms, [0, 2, 4, 8, 16, 32, 64, 128, 512, np.inf])})
table = spikes.pivot_table(index='interval', columns='unit', values='amplitude', aggfunc=['count', 'median'], observed=False)
print(table.round(1).to_string())
