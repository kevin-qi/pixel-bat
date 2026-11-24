"""Positions file of one sort from a flight-room session: python -m pixelbat.curation.positions.flight_room SORT REC FLIGHT_PATHS OUT_NPZ.

REC is the Trodes .rec folder holding *_merged.kilosort/*_merged.timestamps.dat and *_merged.DIO/*_merged.dio_Controller_Din1.dat
(the 3 s sync TTL); FLIGHT_PATHS is the .mat with flightPaths and cortexData.global_sample_ts_usec. Flight clusters 2 and up
are the paths.
"""
import glob
import os
import sys

import numpy as np
import scipy.io

from pixelbat.utils.readTrodesExtractedDataFile import readTrodesExtractedDataFile


def global_time_usec(samples, sample_usec, local_ttl_usec):
    """Global time of sample indices: Trodes timestamp, then interpolation between 3 s TTLs (as local2GlobalTime).

    GridBat's processed spike times take the timestamp one sample earlier (33 us)."""
    local = sample_usec[samples]
    global_ttl = np.linspace(np.round(local_ttl_usec[0]), np.round(local_ttl_usec[0] + (len(local_ttl_usec) - 1) * 3e6),
                             len(local_ttl_usec))
    slope_first = (global_ttl[1] - global_ttl[0]) / (local_ttl_usec[1] - local_ttl_usec[0])
    slope_last = (global_ttl[-1] - global_ttl[-2]) / (local_ttl_usec[-1] - local_ttl_usec[-2])
    inside = np.interp(local, local_ttl_usec, global_ttl)
    before = global_ttl[0] + slope_first * (local - local_ttl_usec[0])
    after = global_ttl[-1] + slope_last * (local - local_ttl_usec[-1])
    extrapolated = np.where(local < local_ttl_usec[0], before, np.where(local > local_ttl_usec[-1], after, inside))
    return extrapolated - global_ttl[0]


def flight_spikes(spike_samples, rec, flight_paths_file):
    """Flight paths per cluster from 2 up, and index, x, y and flight cluster of the spikes fired on them."""
    # Spike times on the tracking clock
    timestamps = readTrodesExtractedDataFile(glob.glob(os.path.join(rec, '*_merged.kilosort', '*_merged.timestamps.dat'))[0])
    sample_usec = np.ravel(timestamps['data']['time']).astype(float) * 1e6 / float(timestamps['clockrate'])
    ttl = readTrodesExtractedDataFile(glob.glob(os.path.join(rec, '*_merged.DIO', '*_merged.dio_Controller_Din1.dat'))[0])
    rising = np.ravel(ttl['data']['state']) == 1
    local_ttl_usec = np.ravel(ttl['data']['time'])[rising].astype(float) * 1e6 / float(ttl['clockrate'])
    spike_usec = global_time_usec(spike_samples.astype(np.int64), sample_usec, local_ttl_usec)
    # Flight cluster of every tracking frame
    data = scipy.io.loadmat(flight_paths_file)
    paths = data['flightPaths'][0][0]
    frame_usec = np.ravel(data['cortexData'][0][0]['global_sample_ts_usec'])
    trajectory = paths['trajectoriesContinous'].T
    frame_cluster = np.zeros(len(frame_usec), dtype=int)
    flights = zip(np.ravel(paths['id']), np.ravel(paths['flight_starts_idx']), np.ravel(paths['flight_ends_idx']))
    for cluster, start, end in flights:
        frame_cluster[start - 1:end] = cluster
    clusters = [int(c) for c in np.unique(frame_cluster) if c >= 2]
    flight_xy = {cluster: trajectory[frame_cluster == cluster, :2] for cluster in clusters}
    # Spikes on clustered flights
    # Nearest tracking frame
    after = np.clip(np.searchsorted(frame_usec, spike_usec), 1, len(frame_usec) - 1)
    frame = np.where(spike_usec - frame_usec[after - 1] < frame_usec[after] - spike_usec, after - 1, after)
    in_session = (spike_usec >= frame_usec[0]) & (spike_usec <= frame_usec[-1])
    on_flight = np.flatnonzero(in_session & (frame_cluster[frame] >= 2))
    return flight_xy, on_flight, trajectory[frame[on_flight], :2], frame_cluster[frame[on_flight]]


def frame_rate_hz(flight_paths_file):
    """Tracking frames per second."""
    frame_usec = np.ravel(scipy.io.loadmat(flight_paths_file)['cortexData'][0][0]['global_sample_ts_usec'])
    return 1e6 / np.median(np.diff(frame_usec))


if __name__ == '__main__':
    sort, rec, flight_paths, out = sys.argv[1:5]
    spike_times = np.load(os.path.join(sort, 'spike_times.npy')).ravel()
    flight_xy, on_flight, spike_xy, spike_flight_cluster = flight_spikes(spike_times, rec, flight_paths)
    np.savez(out, spike_index=on_flight, spike_xy=spike_xy.astype(np.float32), spike_path=spike_flight_cluster,
             frame_rate_hz=frame_rate_hz(flight_paths),
             **{f'path_xy_{cluster}': xy.astype(np.float32) for cluster, xy in flight_xy.items()})
    print(f'{len(on_flight)} spikes on {len(flight_xy)} flight clusters: {out}')
