"""Which Trodes timestamp GridBat's processed spikes use for a Kilosort sample index: s - 1, s or s + 1 (29602/240103, GridBat sort)."""
import glob
import os
import sys

import h5py
import numpy as np

from pixelbat.curation.positions.flight_room import global_time_usec, readTrodesExtractedDataFile

REC = '/mnt/server4/users/KevinQi/datasets/GridBat/29602/flight_room/raw/240103/ephys/20240103_170535.rec'
f = h5py.File('/mnt/server4/users/KevinQi/datasets/GridBat/29602/flight_room/processed/240103/ephys/29602_240103_spikes_python.mat', 'r')
probe = f[f['spikeDataStruct'][0, 0]]
times = np.load(f'{REC}/kilosort_outdir_probe1/spike_times.npy').ravel()
clusters = np.load(f'{REC}/kilosort_outdir_probe1/spike_clusters.npy').ravel()
timestamps = readTrodesExtractedDataFile(glob.glob(f'{REC}/*_merged.kilosort/*_merged.timestamps.dat')[0])
sample_usec = np.ravel(timestamps['data']['time']).astype(float) * 1e6 / float(timestamps['clockrate'])
local_ttl_usec = np.ravel(f['local_ttl_timestamps_sec'][()]) * 1e6
for cell in [0, 100, 300]:
    cluster = int(np.squeeze(f[probe['cluster_id'][()].ravel()[cell]][()]))
    stored_index = np.ravel(f[probe['spikeTimeSampleIdx'][()].ravel()[cell]][()]).astype(np.int64)
    stored_usec = np.ravel(f[probe['spikeTimes_usec'][()].ravel()[cell]][()])
    kilosort = times[clusters == cluster].astype(np.int64)
    inside = kilosort[(kilosort > 0) & (kilosort < len(sample_usec) - 1)][:len(stored_index)]
    print(f'cluster {cluster}: {len(kilosort)} Kilosort spikes, {len(stored_index)} processed; '
          f'processed sample index - Kilosort sample: {np.unique(stored_index[:len(inside)] - inside)[:5]}')
    for offset in [-1, 0, 1]:
        local = sample_usec[inside + offset]
        shifted = global_time_usec(inside + offset + 1, sample_usec, local_ttl_usec)
        print(f'   timestamp of sample s{offset:+d}: max |global time - processed| = {np.abs(shifted - stored_usec[:len(inside)]).max():.3f} us')
