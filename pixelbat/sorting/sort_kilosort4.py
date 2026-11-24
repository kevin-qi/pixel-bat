"""Kilosort 4 on one recording, final merge left undone and saved as proposals: edit the config, then python sort_kilosort4.py.

Writes the Kilosort 4 folder to curate (Phy files, proposed_merges.json) in OUT.
"""
from pixelbat.utils.trodes_export import export_rec_dir
from pixelbat.sorting.kilosort4 import sort_kilosort4

## Config
# Trodes .rec folder to export with trodesexport first, or None when BINARY exists (a complete export is kept)
TRODES_REC_FOLDER = None
TRODES = '/opt/Trodes_2-8-3_Ubuntu24'  # Trodes folder holding trodesexport
# int16 binary exported by Trodes (trodesexport -kilosort) and its channel-coordinates file
BINARY = '/data/bat1/20260720_164544.rec/20260720_164544_merged.kilosort/20260720_164544_merged.group0.dat'
COORDINATES = '/data/bat1/20260720_164544.rec/20260720_164544_merged.kilosort/20260720_164544_merged.group0.coordinates.dat'
MASKED_CHANNELS = []    # channels of the binary left out (dead or flat), counted from 0
SPIKES_POSITIVE = True  # spikes point up in the raw binary
SETTINGS = {'Th_universal': 9, 'Th_learned': 8, 'nblocks': 1}  # changes to Kilosort 4's defaults
DEVICE = 'cuda:0'
OUT = '/results/bat1_260720_ks4'  # must not exist yet

## Trodes export
if TRODES_REC_FOLDER is not None:
    export_rec_dir(TRODES_REC_FOLDER, trodes=TRODES)

## Sort
sort_kilosort4(BINARY, COORDINATES, MASKED_CHANNELS, SPIKES_POSITIVE, SETTINGS, DEVICE, OUT)
