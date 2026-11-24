"""Could a contaminated unit be cleaned by splitting? unit_feature_space.py SORT UNIT OUT_PNG.

Marks the spikes that take part in an interval of 2 ms or less (one of each such pair is foreign) and shows where they
sit among the unit's spikes: in Kilosort amplitude, principal components on the two largest channels, estimated position
and time. Prints Kilosort's contamination after dropping the smallest spikes, and for the two halves of a two-component
Gaussian mixture on the features.
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from kilosort.CCG import check_CCG
from sklearn.mixture import GaussianMixture

sort, unit, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
spike_times = np.load(f'{sort}/spike_times.npy').ravel().astype(np.int64)
ours = np.flatnonzero(np.load(f'{sort}/spike_clusters.npy').ravel() == unit)
times = spike_times[ours] / 30000
amplitude = np.load(f'{sort}/amplitudes.npy').ravel()[ours]
position = np.load(f'{sort}/spike_positions.npy', mmap_mode='r')[ours]
features = np.load(f'{sort}/pc_features.npy', mmap_mode='r')[ours]
# Spikes in an interval of 2 ms or less
short = np.diff(times) <= 0.002
violator = np.r_[short, False] | np.r_[False, short]
print(f'unit {unit}: {len(ours)} spikes, {violator.sum()} in intervals of 2 ms or less; '
      f'Kilosort contamination {check_CCG(times)[2]:.3f}')

## Principal components on the two channels with the largest feature energy
energy = (np.asarray(features) ** 2).sum(axis=(0, 1))
first, second = np.argsort(-energy)[:2]
panels = [(amplitude, features[:, 0, first], 'Kilosort amplitude', 'PC1, largest channel'),
          (features[:, 0, first], features[:, 1, first], 'PC1, largest channel', 'PC2, largest channel'),
          (features[:, 0, first], features[:, 0, second], 'PC1, largest channel', 'PC1, second channel'),
          (position[:, 0], position[:, 1], 'estimated x (um)', 'estimated depth (um)'),
          (times / 60, amplitude, 'time (min)', 'Kilosort amplitude')]
fig, axes = plt.subplots(2, 3, figsize=(16, 9.5), facecolor='white')
for ax, (x, y, xlabel, ylabel) in zip(axes.ravel(), panels):
    ax.plot(x, y, '.', color='#999999', markersize=1.5)
    ax.plot(np.asarray(x)[violator], np.asarray(y)[violator], '.', color='#D55E00', markersize=5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
ax = axes[1, 2]
bins = np.linspace(amplitude.min(), amplitude.max(), 50)
ax.hist(amplitude, bins, density=True, color='#999999', label='all spikes')
ax.hist(amplitude[violator], bins, density=True, histtype='step', color='#D55E00', linewidth=1.8, label='in intervals of 2 ms or less')
ax.set_xlabel('Kilosort amplitude')
ax.set_ylabel('density')
ax.legend(frameon=False)
fig.suptitle(f'unit {unit}: grey, all {len(ours)} spikes; orange, the {violator.sum()} spikes in intervals of 2 ms or less')
fig.tight_layout()
fig.savefig(out, dpi=75)

## Dropping the smallest spikes
for share in [0, 0.1, 0.2, 0.3, 0.5]:
    kept = amplitude >= np.quantile(amplitude, share)
    print(f'drop the smallest {share:.0%}: {kept.sum()} spikes, contamination {check_CCG(times[kept])[2]:.3f}')

## Two-component mixture on the first three components of the three largest channels
chosen = np.asarray(features[:, :3, np.argsort(-energy)[:3]]).reshape(len(ours), -1)
label = GaussianMixture(2, random_state=0).fit_predict(chosen)
for part in (0, 1):
    print(f'mixture part {part}: {np.sum(label == part)} spikes, contamination {check_CCG(times[label == part])[2]:.3f}, '
          f'median amplitude {np.median(amplitude[label == part]):.1f}')
