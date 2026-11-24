"""Several recordings, one after another: edit the config and recordings.csv, then python sort_batch.py.

A recording already sorted is skipped, so the batch can be restarted after a failure.
"""
import pandas as pd

from pixelbat.sorting.kilosort4 import sort_kilosort4
from pixelbat.sorting.kilosort25 import KILOSORT25_DIR, sort_kilosort25

## Config
RECORDINGS = 'recordings.csv'  # columns as in recordings_example.csv
SORTER = 'kilosort25'          # or 'kilosort4'
# Kilosort 2.5, as in sort_kilosort25.py
NBLOCKS = 1
MATLAB = '/usr/local/MATLAB/R2026a/bin/matlab'
MATLAB_CODE = KILOSORT25_DIR
SCRATCH = '/scratch/ks25'
GPU = 1
WINDOWS_SHARES = {}
# Kilosort 4, as in sort_kilosort4.py
SETTINGS = {'Th_universal': 9, 'Th_learned': 8, 'nblocks': 1}
DEVICE = 'cuda:0'

## Recordings
recordings = pd.read_csv(RECORDINGS, dtype=str, keep_default_na=False)
print(f'{len(recordings)} recordings, {SORTER}')
for recording in recordings.itertuples():
    masked = [int(channel) for channel in recording.masked_channels.split()]
    spikes_positive = {'True': True, 'False': False}[recording.spikes_positive]
    print(f'== {recording.name}', flush=True)
    if SORTER == 'kilosort25':
        sort_kilosort25(recording.binary, recording.coordinates, masked, spikes_positive, NBLOCKS, recording.out, SCRATCH,
                        MATLAB, MATLAB_CODE, GPU, WINDOWS_SHARES)
    if SORTER == 'kilosort4':
        sort_kilosort4(recording.binary, recording.coordinates, masked, spikes_positive, SETTINGS, DEVICE, recording.out)
