"""Sort a list of recordings with Kilosort 2.5 (Moser patch set) or Kilosort 4: copy, edit the config, then python sort.py.

Each recording's `out` becomes its sort folder: the Kilosort output, every unit kept apart, the merges the sorter would
have made in proposed_merges.json, and curation/recording.json. A recording whose sort folder is complete is skipped, so
the list can be run again after a failure.
"""
import os

import pandas as pd

from pixelbat.sorting.kilosort4 import sort_kilosort4
from pixelbat.sorting.kilosort25 import KILOSORT25_DIR, sort_kilosort25
from pixelbat.sorting.probe import trodes_probe
from pixelbat.sorting.recording import peak_signs, trodes_gain_uv, write_recording
from pixelbat.utils.trodes_export import export_rec_dir

## Config: what to sort
RECORDINGS = 'recordings.csv'  # one row per recording, columns as in recordings_example.csv
SORTER = 'kilosort25'          # or 'kilosort4'
TRODES = None                  # Trodes folder holding trodesexport, to export each .rec folder first; None when exported

## Config: Kilosort 2.5
NBLOCKS = 1                # drift correction blocks (1 rigid, 0 none)
# MATLAB with the Parallel Computing Toolbox; on WSL, Windows MATLAB works too
MATLAB = '/usr/local/MATLAB/R2026a/bin/matlab'
# Folder holding Kilosort-2.5-moser with its mex files compiled (build_mex.m); Windows MATLAB needs it on a Windows disk
MATLAB_CODE = KILOSORT25_DIR
SCRATCH = '/scratch/ks25'  # local SSD for the whitened copy of the binary (as large as the binary), removed afterwards
GPU = 1                    # MATLAB GPU index, from 1
# Windows MATLAB only: WSL mounts of network shares and the share MATLAB reads them through
WINDOWS_SHARES = {}        # e.g. {'/mnt/server5': r'\\192.168.88.155\server_home'}

## Config: Kilosort 4
SETTINGS = {'Th_universal': 9, 'Th_learned': 8, 'nblocks': 1}  # changes to Kilosort 4's defaults
DEVICE = 'cuda:0'

## Recordings not yet sorted
recordings = pd.read_csv(RECORDINGS, dtype=str, keep_default_na=False)
todo = recordings[[not os.path.exists(os.path.join(out, 'curation', 'recording.json')) for out in recordings['out']]]
print(f'{len(todo)} of {len(recordings)} recordings to sort, {SORTER}')
for recording in todo.itertuples():
    print(f'== {recording.out}', flush=True)
    if TRODES is not None:
        export_rec_dir(os.path.dirname(os.path.dirname(recording.binary)), trodes=TRODES)
    masked_channels = [int(channel) for channel in recording.masked_channels.split()]

    ## Spike sign, measured
    n_channels = trodes_probe(recording.coordinates)['n_chan']
    n_positive, n_negative = peak_signs(recording.binary, n_channels, 30000)
    spikes_positive = n_positive > n_negative
    print(f'spike sign: {n_positive} positive, {n_negative} negative peaks', flush=True)

    ## Sort
    if SORTER == 'kilosort25':
        sort_kilosort25(recording.binary, recording.coordinates, masked_channels, spikes_positive, NBLOCKS, recording.out, SCRATCH,
                        MATLAB, MATLAB_CODE, GPU, WINDOWS_SHARES)
    if SORTER == 'kilosort4':
        sort_kilosort4(recording.binary, recording.coordinates, masked_channels, spikes_positive, SETTINGS, DEVICE, recording.out)
    write_recording(recording.out, recording.binary, trodes_gain_uv(recording.binary), spikes_positive)
