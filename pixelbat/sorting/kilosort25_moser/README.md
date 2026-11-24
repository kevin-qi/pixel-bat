# Kilosort 2.5 with the Moser patch set

Kilosort 2.5 as Gardner et al. 2022 (Nature 602:123, "Toroidal topology of population activity in grid cells") ran it,
with its step-3 merges left to the curator. Run it through `pixelbat/sorting/sort_kilosort25.py`.

## Credit and licence

- `Kilosort-2.5-moser/`: Kilosort by Marius Pachitariu and colleagues (MouseLand, https://github.com/MouseLand/Kilosort),
  tag v2.5 (commit 80d0062), GPL-2 (`Kilosort-2.5-moser/licence.txt`), with the patches in `patches/` applied. Cite
  Pachitariu et al. 2024 (Nature Methods 21:914) and Steinmetz et al. 2021 (Science 372:eabf4588) for Kilosort 2.5.
- `npy-matlab/`: npy-matlab (kwikteam, https://github.com/kwikteam/npy-matlab, commit 7e61a88), BSD-2 (`npy-matlab/LICENSE`).
- `run_ks25_moser.m`, `redo_step3.m`, `build_mex.m`, `patches/`: ours; as changes to and drivers of Kilosort they are
  distributed under GPL-2 as well.

`build_tree.sh OUT_DIR` rebuilds the patched tree from upstream and the patches and reports how many files differ from
the vendored one (0 when checked on 2026-11-24).

## Patches

| Patch | Change |
|---|---|
| `P0_spike_holes_v2.5.2` | upstream v2.5 → v2.5.2 diff, minus the hunk that sets `useStableMode = 0` |
| `P1_step1_spikes_per_batch` | `spikedetector3.cu:20` `maxFR` 10000 → 1000000 |
| `P2_step2_matching_iterations` | `learnTemplates.m:57`, `trackAndSort.m:62` `nInnerIter` 60 → 499 |
| `P3_step2_spikes_per_batch` | `mexMPnu8.cu:25` `maxFR` 100000 → 400000 |
| `P4_step2_similarity_limit` | `triageTemplates2.m:32` 0.9 → 0.975 |
| `P5_step3_similarity_limit` | `splitAllClusters.m:139` 0.9 → 1.0 |
| `P6_split_log` | `rez.split_log`, `rez.split_low`: every candidate split |
| `P7_sign` | `gpufilter.m:18` multiplies the raw data by `ops.sign` |
| `M1_merge_log` | `rez.merge_log`: merges in the order made |
| `P8_split_veto_switch` | `splitAllClusters.m:126` the correlogram veto on splits applies only if `rez.ops.split_ccg_veto` is 1 |
| `I1_iteration_counts` | 11th output of `mexMPnu8` (spikes after each iteration); `rez.count_learn`, `rez.count_final`, `rez.Nfilt_learn`, `rez.nInnerIter` |

P1-P5 are the paper's changes (more spikes per batch in step 1, more template-matching iterations in step 2, template
similarity limits 0.975 in step 2 and 1.0 in step 3); the others record what Kilosort did or let step 3 make every
split. The text above each diff states file, line, old and new value.

## What a sort does

`run_ks25_moser.m` sorts one recording (preprocessing, drift correction, template learning and matching) and writes the
uncut, unmerged sort with every diagnostic into the output folder; it ends with `redo_step3.m`, which writes the folder
to curate into `curation/`: every split made (also those stock Kilosort withholds for a correlogram dip), the stock
amplitude cutoff, no merge. The merges `find_merges` would make and the splits made despite a dip become merge
proposals (`proposed_merges.json`, written by `kilosort25.py`). Settings are those of `run_ks25_moser.m` (`Th = [10 4]`,
`lam = 10`, `AUCsplit = 0.9`, `minFR = 1/50`, `sigmaMask = 30`, `NT = 64*1024 - 64`, stable mode).

## Requirements and build (once per machine)

- MATLAB with the Parallel Computing Toolbox (used: R2026a, which brings its own CUDA 12.8 compiler) and an NVIDIA GPU.
- A C++ compiler MATLAB supports: Windows, Visual Studio 2022 Build Tools with the C++ workload
  (`winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`);
  Linux, the gcc version MATLAB's release lists as supported.
- Windows: the regional format must be English (US) while compiling (decimal commas break the `mexcuda` command line).
- Used on an RTX 3090 (24 GB) with 2 h, 384-channel recordings. A local SSD with room for a copy of the binary (the
  whitened `temp_wh.dat`).

Compile the nine CUDA mex files where MATLAB will run them. Windows MATLAB needs this folder on a Windows disk, so from
WSL copy it first:

    cp -r pixelbat/sorting/kilosort25_moser /mnt/c/kilosort25_moser
    "/mnt/c/Program Files/MATLAB/R2026a/bin/matlab.exe" -batch "cd('C:\kilosort25_moser'); build_mex"

Linux MATLAB, in place:

    matlab -batch "cd('pixelbat/sorting/kilosort25_moser'); build_mex"

It prints the GPU and CUDA version and `9 of 9 mex files built`. Then set `MATLAB_CODE` in `sort_kilosort25.py` to the
folder compiled in.
