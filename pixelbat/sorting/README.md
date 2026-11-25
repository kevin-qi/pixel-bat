# Spike sorting for curation

One script sorts a list of recordings with Kilosort 2.5 (Moser patch set) or Kilosort 4. Every unit is kept apart and
the merges the sorter would have made are saved as proposals (`proposed_merges.json`), which the curator
(`pixelbat/curation`) shows for a decision by hand.

- **Kilosort 2.5, Moser patch set** (the lab's main sorter): Kilosort 2.5 as Gardner et al. 2022 ran it, in MATLAB.
  See `kilosort25_moser/README.md` for the patches and the one-time build.
- **Kilosort 4**: Kilosort 4.1.7 from pip with its final merge left undone.

Input: the int16 binary Trodes exports for Kilosort (`trodesexport -kilosort`, e.g. `*_merged.group0.dat`) and its
channel-coordinates file (`*.group0.coordinates.dat`).

## Quick start (after installing; see `SHARING.md`)

1. Kilosort 2.5 only, once per machine: compile the mex files (`kilosort25_moser/README.md`, about 5 minutes).
2. List the recordings in a CSV like `recordings_example.csv`, one row each:
   - `binary`, `coordinates`: the exported binary and its coordinates file
   - `masked_channels`: dead or flat channels to leave out, counted from 0, space-separated (empty for none)
   - `out`: the sort folder, by convention `<recording>.rec/kilosort_outdir_probe1`. Kilosort 4 needs it not to exist.
3. Copy `sort.py` and edit its config:
   - `RECORDINGS`, `SORTER` (`'kilosort25'` or `'kilosort4'`), `TRODES` (a Trodes folder, to export each `.rec` folder
     first; `None` when the binaries exist)
   - Kilosort 2.5: `MATLAB` (the executable), `MATLAB_CODE` (the compiled `kilosort25_moser` folder), `SCRATCH` (a
     local SSD folder with room for a copy of the binary), `GPU`, `NBLOCKS`
   - Kilosort 4: `SETTINGS` (changes to Kilosort's defaults), `DEVICE`
4. Run it with the repository's environment: `.venv/bin/python my_sort.py`. On an RTX 3090, Kilosort 2.5 took about
   3 h for a 2.8 h recording (2.25 h sort, 0.6 h step 3) and 9 min for a 17 min one; Kilosort 4 takes about 90 min for
   a 2 h recording.
5. Prepare and curate the sort folders (`pixelbat/curation/README.md`).

A recording whose sort folder has `curation/recording.json` (written last) is skipped, so the list can be run again
after a failure.

Per recording, before sorting, the script measures the spike sign: peaks beyond 5 x noise of each sign in three 20 s
stretches of the binary (high-passed at 300 Hz, median over channels subtracted; about 1 min). The commoner sign is the
spikes' and is printed with both counts; both sorters are then run on negative-going spikes. The gain is
`spikeScalingToUv` in the header of the `.rec` file beside the export.

## Windows MATLAB from WSL

Kilosort 2.5 runs on Linux with Linux MATLAB, or in WSL2 calling Windows MATLAB (`MATLAB` ending in `.exe`,
e.g. `/mnt/c/Program Files/MATLAB/R2026a/bin/matlab.exe`). With Windows MATLAB, every path is handed to MATLAB as a
Windows path: `MATLAB_CODE` and `SCRATCH` must be on a Windows disk (`/mnt/c/...`), and folders on network shares
mounted in WSL are best given through the share itself (`WINDOWS_SHARES = {'/mnt/server5': r'\\192.168.88.155\server_home'}`),
since `matlab -batch` sees no mapped drive letters; any other path goes through `wslpath -w`.

## Output

Both sorters: the sort folder `out` holds the Phy files to curate, `proposed_merges.json` and
`curation/recording.json` (`binary`, `gain_uV`, `spikes_positive`).

Kilosort 2.5 adds `ops.npy`, `channel_shanks.npy`, the whitening matrices and `sort.json` (settings, counts, seconds
per stage, patch hashes) to `out`, and keeps in `out/uncut` what step 3 started from: `chanmap.mat`, the MATLAB logs
`kilosort25.log` (and `kilosort25_step3.log` when step 3 was run again), `rez_step2.mat` (everything after template
matching) and the uncut, unmerged Phy folder with every diagnostic. A sort that stopped after `rez_step2.mat` was
written restarts at step 3.

A Kilosort 2.5 run is void when, in `out/uncut`: the largest of `n1.npy` equals 1000000 (step-1 spike cap reached); the
largest entry of `count_final.npy` or `count_learn.npy` equals 400000 (step-2 cap reached); `batches_not_converged_*`
in `sort.json` is above 0 (too few matching iterations); `max_templates_learning` equals `template_cap` (template cap
reached).

Kilosort 4 adds `sort_unmerged.json` (settings, versions, time) to `out`.

## Files

| file | role |
|---|---|
| `sort.py`, `recordings_example.csv` | a list of recordings: config, then the sorts |
| `recording.py` | gain and spike sign of a binary; `curation/recording.json` |
| `kilosort25.py` | the Kilosort 2.5 pipeline: channel map, MATLAB sort and step 3, the files the curator reads |
| `kilosort4.py`, `kilosort_proposals.py` | the Kilosort 4 sort and the patch that saves its final merge as proposals |
| `probe.py` | Kilosort probe from a Trodes coordinates file |
| `kilosort25_moser/` | patched Kilosort 2.5, npy-matlab, MATLAB drivers, build script |

The older notebooks and `pixelbat/kilosort4.py` remain for reference; these scripts are the documented way to sort.
