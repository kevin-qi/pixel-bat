"""Kilosort 2.5 (Moser patch set) on one recording: edit the config, then python sort_kilosort25.py.

Writes <OUT>/curation, the folder to curate (Phy files, proposed_merges.json); <OUT> keeps the uncut sort and diagnostics.
"""
from pixelbat.utils.trodes_export import export_rec_dir
from pixelbat.sorting.kilosort25 import KILOSORT25_DIR, sort_kilosort25

## Config: recording
# Trodes .rec folder to export with trodesexport first, or None when BINARY exists (a complete export is kept)
TRODES_REC_FOLDER = None
TRODES = '/opt/Trodes_2-8-3_Ubuntu24'  # Trodes folder holding trodesexport
# int16 binary exported by Trodes (trodesexport -kilosort) and its channel-coordinates file
BINARY = '/data/bat1/20260720_164544.rec/20260720_164544_merged.kilosort/20260720_164544_merged.group0.dat'
COORDINATES = '/data/bat1/20260720_164544.rec/20260720_164544_merged.kilosort/20260720_164544_merged.group0.coordinates.dat'
MASKED_CHANNELS = []    # channels of the binary left out (dead or flat), counted from 0
SPIKES_POSITIVE = True  # spikes point up in the raw binary
NBLOCKS = 1             # drift correction blocks (1 rigid, 0 none)
OUT = '/results/bat1_260720_ks25'

## Config: machine
# MATLAB with the Parallel Computing Toolbox; on WSL, Windows MATLAB works too
MATLAB = '/usr/local/MATLAB/R2026a/bin/matlab'
# Folder holding Kilosort-2.5-moser with its mex files compiled (build_mex.m); Windows MATLAB needs it on a Windows disk
MATLAB_CODE = KILOSORT25_DIR
SCRATCH = '/scratch/ks25'  # local SSD for the whitened copy of the binary (as large as the binary), removed afterwards
GPU = 1                    # MATLAB GPU index, from 1
# Windows MATLAB only: WSL mounts of network shares and the share MATLAB reads them through
WINDOWS_SHARES = {}        # e.g. {'/mnt/server5': r'\\192.168.88.155\server_home'}

## Trodes export
if TRODES_REC_FOLDER is not None:
    export_rec_dir(TRODES_REC_FOLDER, trodes=TRODES)

## Sort
sort_kilosort25(BINARY, COORDINATES, MASKED_CHANNELS, SPIKES_POSITIVE, NBLOCKS, OUT, SCRATCH, MATLAB, MATLAB_CODE, GPU,
                WINDOWS_SHARES)
