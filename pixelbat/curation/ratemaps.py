"""Rate maps of spikes on positions."""
import numpy as np
import scipy.ndimage
import scipy.signal


# From GridBat, release/gridbat/ratemaps.py, verbatim
def bin_spikes_on_pos(spike_pos, pos, bins, n_dims, dt, min_occupancy_threshold_sec, sigma, nnb_matrix,
                      occupancy, smoothed_occupancy):
    """2-D or 3-D rate map from spike positions and positions sampled every dt. Returns a dict."""
    pos_fs = 1 / dt

    spike_hist = np.histogramdd(spike_pos[:, :n_dims], bins=bins[:n_dims])[0]
    spike_counts = np.flipud(np.moveaxis(spike_hist, [0, 1], [1, 0]))
    if occupancy is None:
        pos_hist = np.histogramdd(pos[:, :n_dims], bins=bins[:n_dims])[0]
        occupancy = np.flipud(np.moveaxis(pos_hist, [0, 1], [1, 0]) / pos_fs)

    # Occupancy mask
    low_occupancy = occupancy < min_occupancy_threshold_sec
    spike_counts[low_occupancy] = 0
    occupancy[low_occupancy] = 0

    with np.errstate(invalid='ignore'):
        raw_rate = spike_counts / occupancy

    # Smooth counts and occupancy, then divide
    smoothed_counts = scipy.ndimage.gaussian_filter(spike_counts, sigma)
    if smoothed_occupancy is None:
        smoothed_occupancy = scipy.ndimage.gaussian_filter(occupancy, sigma)
    with np.errstate(divide='ignore', invalid='ignore'):
        smoothed_rate = smoothed_counts / smoothed_occupancy

    # Neighbour mask
    if nnb_matrix is None:
        neighbour_kernel = np.ones([3] * n_dims)
        nnb_matrix = scipy.signal.convolve(occupancy, neighbour_kernel, mode='same', method='direct') > 0
    smoothed_rate[~nnb_matrix] = np.nan

    out = {}
    out['occupancy'] = smoothed_occupancy
    out['rate'] = smoothed_rate
    out['raw_occupancy'] = occupancy
    out['raw_spikerate'] = raw_rate
    out['spikecounts'] = spike_counts
    out['max_rate'] = np.nanmax(smoothed_rate)
    out['min_rate'] = np.nanmin(smoothed_rate)
    out['max_occupancy'] = np.nanmax(smoothed_occupancy)
    out['min_occupancy'] = np.nanmin(smoothed_occupancy)
    out['nnb_matrix'] = nnb_matrix
    return out
