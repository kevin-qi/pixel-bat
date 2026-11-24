"""Display waveforms of a unit: the sites shown and a density image of its single spikes."""
import numpy as np

SITES = 16           # sites nearest the peak site
WINDOW = slice(60, 150)  # samples kept of the 3 ms before / 3 ms after waveform: 1 ms before to 2 ms after the trough
TIME_BINS, AMPLITUDE_BINS = 45, 24


def nearest_sites(channel_xy, sites, peak_site):
    """The unit's recorded sites nearest its peak site, nearest first."""
    return sites[np.argsort(np.linalg.norm(channel_xy[sites] - channel_xy[peak_site], axis=1))[:SITES]]


def waveform_density(waveforms, half_range):
    """Counts of single-spike samples per site, time bin and amplitude bin over +-half_range uV (samples beyond it in
    the edge bins), scaled 0-255 by the unit's fullest bin."""
    n_spikes, n_samples, n_sites = waveforms.shape
    time_bin = np.arange(n_samples) * TIME_BINS // n_samples
    amplitude_bin = np.clip(np.floor((waveforms + half_range) / (2 * half_range) * AMPLITUDE_BINS).astype(int), 0, AMPLITUDE_BINS - 1)
    density = np.zeros((n_sites, TIME_BINS, AMPLITUDE_BINS))
    spike, sample, site = np.indices(waveforms.shape)
    np.add.at(density, (site.ravel(), time_bin[sample.ravel()], amplitude_bin.ravel()), 1)
    return np.round(255 * density / density.max()).astype(np.uint8)
