"""One-off for a cache prepared before display arrays existed: display_* arrays from its saved single-spike waveforms: display_from_singles.py CACHE."""
import os
import sys

import numpy as np

from pixelbat.curation.waveforms import AMPLITUDE_BINS, SITES, TIME_BINS, waveform_density

cache = sys.argv[1]
single = np.load(f'{cache}/single_waveforms.npy', mmap_mode='r')
sites = np.load(f'{cache}/single_channels.npy')
count = np.load(f'{cache}/single_count.npy')
mean = np.zeros((len(single), single.shape[2], SITES), dtype=np.float32)
density = np.zeros((len(single), SITES, TIME_BINS, AMPLITUDE_BINS), dtype=np.uint8)
half_range = np.zeros(len(single), dtype=np.float32)
for i in range(len(single)):
    waveforms = np.asarray(single[i, :count[i]], dtype=np.float32)
    mean[i] = waveforms.mean(axis=0)
    half_range[i] = 1.5 * np.abs(mean[i]).max()
    density[i] = waveform_density(waveforms, half_range[i])
density[sites < 0] = 0
np.save(f'{cache}/display_sites.npy', sites)
np.save(f'{cache}/display_mean.npy', mean)
np.save(f'{cache}/display_density.npy', density)
np.save(f'{cache}/display_range.npy', half_range)
print(f'{len(single)} units; spikes per unit min {count.min()}, median {int(np.median(count))}; sites per unit min {(sites >= 0).sum(axis=1).min()}')
