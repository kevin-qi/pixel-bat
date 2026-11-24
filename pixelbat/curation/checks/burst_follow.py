"""Does one unit hold the later spikes of another unit's bursts? burst_follow.py SORT LARGE SMALL.

Share of each unit's spikes that come within 10 ms after a spike of the other unit, and after any spike of the two
together, against the share expected from the rates alone (1 - exp(-rate x 10 ms)).
"""
import sys

import numpy as np

sort, large, small = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
spike_clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
rate_hz = 30000
window = int(0.010 * rate_hz)
duration = spike_times.max() / rate_hz
trains = {unit: spike_times[spike_clusters == unit] for unit in (large, small)}
both = np.sort(np.concatenate([trains[large], trains[small]]))


def preceded(spikes, others):
    """Share of spikes with a spike of others in the 10 ms before them (the spike itself excluded)."""
    first = np.searchsorted(others, spikes - window, side='left')
    last = np.searchsorted(others, spikes, side='left')
    return ((last - first) > 0).mean()


for unit, other in [(small, large), (large, small)]:
    chance = 1 - np.exp(-len(trains[other]) / duration * 0.010)
    print(f'{unit}: {preceded(trains[unit], trains[other]):.3f} of its {len(trains[unit])} spikes follow a spike of {other} within 10 ms '
          f'(chance {chance:.3f}); {preceded(trains[unit], both):.3f} follow any spike of the two')
