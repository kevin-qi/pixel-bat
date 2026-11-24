# Spike sorting for curation

Two sorters, each a plain script: set the paths at the top and run it. Both keep every unit apart and save the merges
the sorter would have made as proposals (`proposed_merges.json`), which the curator (`pixelbat/curation`) shows for a
decision by hand.

- **Kilosort 2.5, Moser patch set** (`sort_kilosort25.py`, the lab's main sorter): Kilosort 2.5 as Gardner et al. 2022
  ran it, in MATLAB. Its folder to curate is `<OUT>/curation`. See `kilosort25_moser/README.md` for the patches and the
  one-time build.
- **Kilosort 4** (`sort_kilosort4.py`): Kilosort 4.1.7 from pip with its final merge left undone. Its folder to curate
  is `OUT`.

Input: the int16 binary Trodes exports for Kilosort (`trodesexport -kilosort`, e.g. `*_merged.group0.dat`) and its
channel-coordinates file (`*.group0.coordinates.dat`). Set `TRODES_REC_FOLDER` to export a `.rec` folder first.

## Quick start (5 minutes, after installing; see `SHARING.md`)

1. Kilosort 2.5 only, once per machine: compile the mex files (`kilosort25_moser/README.md`, about 5 minutes).
2. Copy `sort_kilosort25.py` (or `sort_kilosort4.py`) next to your data notes and edit its config:
   - `BINARY`, `COORDINATES`: the exported binary and its coordinates file
   - `MASKED_CHANNELS`: dead or flat channels to leave out, counted from 0 (`[]` for none)
   - `SPIKES_POSITIVE`: whether spikes point up in the raw binary (Trodes Neuropixels exports: usually `True`; check a
     few spikes in the Trodes viewer or after a first sort: the curator's waveforms should point down)
   - `OUT`: where the sort goes
   - Kilosort 2.5: `MATLAB` (the executable), `MATLAB_CODE` (the compiled `kilosort25_moser` folder), `SCRATCH` (a
     local SSD folder with room for a copy of the binary), `GPU`
   - Kilosort 4: `SETTINGS` (changes to Kilosort's defaults), `DEVICE`
3. Run it with the repository's environment: `.venv/bin/python sort_kilosort25.py`. On an RTX 3090, Kilosort 2.5 took
   about 3 h for a 2.8 h recording (2.25 h sort, 0.6 h step 3) and 9 min for a 17 min one; Kilosort 4 takes about
   90 min for a 2 h recording.
4. Add a row for the sort to your sessions CSV and curate it (`pixelbat/curation/README.md`).

Several recordings: list them in a CSV like `recordings_example.csv` (`masked_channels` space-separated, empty for
none; `spikes_positive` exactly `True` or `False`), set `RECORDINGS` and `SORTER` in `sort_batch.py` and run it. A
recording already sorted is skipped, so a batch can be restarted.

## Windows MATLAB from WSL

`sort_kilosort25.py` runs on Linux with Linux MATLAB, or in WSL2 calling Windows MATLAB (`MATLAB` ending in `.exe`,
e.g. `/mnt/c/Program Files/MATLAB/R2026a/bin/matlab.exe`). With Windows MATLAB, every path is handed to MATLAB as a
Windows path: `MATLAB_CODE` and `SCRATCH` must be on a Windows disk (`/mnt/c/...`), and folders on network shares
mounted in WSL are best given through the share itself (`WINDOWS_SHARES = {'/mnt/server5': r'\\192.168.88.155\server_home'}`),
since `matlab -batch` sees no mapped drive letters; any other path goes through `wslpath -w`.

## Output

Kilosort 2.5 (`OUT`): `chanmap.mat`; the MATLAB logs `kilosort25.log` (and `kilosort25_step3.log` when step 3 was run
again); `rez_step2.mat` (everything after template matching), the uncut, unmerged Phy folder with every diagnostic and
`sort.json` (settings, counts, seconds per stage, patch hashes); `curation/`: the Phy folder to curate with
`proposed_merges.json`, `ops.npy`, `channel_shanks.npy`, the whitening matrices and `sort.json`. A sort that stopped
after `rez_step2.mat` was written restarts at step 3.

A Kilosort 2.5 run is void when: the largest of `n1.npy` equals 1000000 (step-1 spike cap reached); the largest entry of
`count_final.npy` or `count_learn.npy` equals 400000 (step-2 cap reached); `batches_not_converged_*` in `sort.json` is
above 0 (too few matching iterations); `max_templates_learning` equals `template_cap` (template cap reached).

Kilosort 4 (`OUT`): the Kilosort 4 folder, `proposed_merges.json` and `sort_unmerged.json` (settings, versions, time).

## Files

| file | role |
|---|---|
| `sort_kilosort25.py`, `sort_kilosort4.py` | one recording: config, then the sort |
| `sort_batch.py`, `recordings_example.csv` | several recordings from a CSV |
| `kilosort25.py` | the Kilosort 2.5 pipeline: channel map, MATLAB sort and step 3, the files the curator reads |
| `kilosort4.py`, `kilosort_proposals.py` | the Kilosort 4 sort and the patch that saves its final merge as proposals |
| `probe.py` | Kilosort probe from a Trodes coordinates file |
| `kilosort25_moser/` | patched Kilosort 2.5, npy-matlab, MATLAB drivers, build script |

The older notebooks and `pixelbat/kilosort4.py` remain for reference; these scripts are the documented way to sort.
