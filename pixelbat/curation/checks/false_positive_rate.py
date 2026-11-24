"""Fraction of a unit's spikes that come from other cells, estimated from its refractory violations scaled by its firing
rate: false_positive_rate.py SORT UNIT [UNIT ...].

With N spikes in T seconds, a fraction f of them foreign and unrelated to the cell, the pairs closer than tau number
N^2 tau / T x (1 - (1 - f)^2), so f = 1 - sqrt(1 - violations x T / (N^2 tau)) (Llobet et al. 2022; Hill et al. 2011 for one
contaminating cell). tau excludes the 0.25 ms in which Kilosort drops the second spike. The same relation on Kilosort's
ratio, which uses the unit's own 10-50 ms shoulder as the rate, gives f = 1 - sqrt(1 - ratio).
"""
import sys

import numpy as np
from kilosort.CCG import check_CCG

sort = sys.argv[1]
spike_times = np.load(f'{sort}/spike_times.npy').ravel() / 30000
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
duration = spike_times.max()
for unit in map(int, sys.argv[2:]):
    st = spike_times[spike_clusters == unit]
    estimates = []
    for window_ms in (1, 2):
        violations = np.sum(np.diff(st) < window_ms / 1000)
        share = violations * duration / (len(st) ** 2 * (window_ms - 0.25) / 1000)
        estimates.append(f'{window_ms} ms: {violations} violations, {"over 100%" if share > 1 else f"{100 * (1 - np.sqrt(1 - share)):.1f}%"}')
    ratio = check_CCG(st)[2]
    print(f'unit {unit} ({len(st) / duration:.1f} Hz): by mean rate, {"; ".join(estimates)}; by Kilosort ratio {ratio:.3f}: {100 * (1 - np.sqrt(1 - min(ratio, 1))):.1f}%')
