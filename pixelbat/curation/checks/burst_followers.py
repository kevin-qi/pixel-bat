"""Is one unit the burst followers of another? Share of each unit's spikes that come shortly after a spike of the other: burst_followers.py SORT CACHE UNIT_A UNIT_B."""
import sys

import numpy as np
import pandas as pd

sort, cache, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
times = np.load(f'{sort}/spike_times.npy').ravel() / 30000
clusters = np.load(f'{sort}/spike_clusters.npy').ravel()
units = pd.read_csv(f'{cache}/units.csv', index_col='cluster_id')
trains = {u: times[clusters == u] for u in [a, b]}
shape = pd.read_csv(f'{cache}/shape_draw0.csv', index_col=0)
print(units.loc[[a, b], ['num_spikes', 'firing_rate', 'amplitude_median', 'ch']].join(
    shape.loc[[a, b], ['peak_to_trough_duration', 'trough_half_width']]).to_string())

## Spikes that follow, or precede, a spike of the other unit
for first, second in [(a, b), (b, a)]:
    before = np.searchsorted(trains[first], trains[second])
    lag_after = trains[second] - trains[first][np.clip(before - 1, 0, None)]
    lag_before = trains[first][np.clip(before, None, len(trains[first]) - 1)] - trains[second]
    lag_after[before == 0] = np.inf
    lag_before[before == len(trains[first])] = np.inf
    for window in [0.005, 0.010, 0.020]:
        print(f'{second}: {100 * np.mean(lag_after <= window):.1f}% of its {len(trains[second])} spikes come within '
              f'{1000 * window:.0f} ms after a spike of {first}; {100 * np.mean(lag_before <= window):.1f}% within '
              f'{1000 * window:.0f} ms before one')
    close = lag_after[lag_after <= 0.020] * 1000
    print(f'  lag after {first} when within 20 ms: median {np.median(close):.2f} ms, quartiles '
          f'{np.quantile(close, 0.25):.2f}-{np.quantile(close, 0.75):.2f} ms; shortest {lag_after.min() * 1000:.2f} ms')

## Chance level: the same shares after shifting one train by 1 s
for first, second in [(a, b), (b, a)]:
    shifted = trains[second] + 1.0
    before = np.searchsorted(trains[first], shifted)
    lag_after = shifted - trains[first][np.clip(before - 1, 0, None)]
    print(f'chance ({second} shifted 1 s): {100 * np.mean(lag_after[before > 0] <= 0.010):.1f}% within 10 ms after a spike of {first}')
