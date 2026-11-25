# Sorting and curating Neuropixels recordings: lab quick start

Sort a list of recordings, prepare the sorts, curate them in a browser. Everything about one sort lives in its sort
folder.

## The sort folder

One folder per recording and probe, by convention beside the Trodes export:

    20260720_164544.rec/
        20260720_164544_merged.kilosort/     Trodes export: the int16 binary and its channel coordinates
        kilosort_outdir_probe1/              the sort folder: Kilosort's output (Phy files), never modified afterwards
            curation/                        everything added to it
                recording.json               the binary sorted, its gain (µV per bit) and spike sign; written by the sorter
                cache/                       written by prepare
                opened/                      written by prepare: what the app reads to open the sort in about a second
                positions.npz                optional: spikes on positions
                curation_log.jsonl           every decision made in the curator
                phy/                         the curated sort, exported

The sort folder is what you give each step. It can be anywhere; moving it keeps its curation.

## Install (Linux or WSL2, NVIDIA GPU)

    curl -LsSf https://astral.sh/uv/install.sh | sh
    git clone <pixel-bat repository> && cd pixel-bat
    uv sync                                    # the environment in .venv, exactly as in uv.lock

Kilosort 2.5 also needs MATLAB and a one-time build: `pixelbat/sorting/kilosort25_moser/README.md`.

## 1. Sort

    cp pixelbat/sorting/sort.py my_sort.py     # edit its config: the recordings list, the sorter, this machine
    .venv/bin/python my_sort.py

The list is a CSV with one row per recording: `binary`, `coordinates`, `masked_channels`, `out` (the sort folder);
`pixelbat/sorting/recordings_example.csv`. Kilosort 2.5 with the Moser lab's changes is the main sorter, Kilosort 4 the
second. Gain is read from the `.rec` header and the spike sign is measured. Sorted recordings are skipped when the
script is run again. Details: `pixelbat/sorting/README.md`.

## 2. Prepare

    .venv/bin/pixelbat-curate prepare /data/bat1/*.rec/kilosort_outdir_probe1 --jobs 8

Once per sort; prepared sorts are skipped. About 23 min and 45 GB with 32 processes for a 2 h, 1,000-unit recording;
a few minutes with 8 for a 17 min one.

## 3. Curate

    .venv/bin/pixelbat-curate                  # one app per machine: http://localhost:8780

The app starts on its picker: browse to a sort folder or choose one of the recent sorts (filter by words, order by any
column), then curate; `?` lists the keys and every term. Decisions are saved as they are made.
Export (the button, or `pixelbat-curate export SORT`) writes `curation/phy`, which loads like a Phy-curated folder.
From another machine: `ssh -L 8780:localhost:8780 HOST`, then the same address. Details:
`pixelbat/curation/README.md`.

## Not yet generic

- Trodes only: the sorters read a Trodes coordinates file and the `.rec` header, and the shank of each site comes from
  a table of the Trodes layouts we use (Neuropixels 1.0, 2.0 four-shank, UHD; `pixelbat/sorting/probe.py`). A sort
  made by other code is prepared with `pixelbat-curate prepare SORT --binary BINARY --gain-uv GAIN`.
- Dead channels (`masked_channels`) are listed by hand per recording.
- Kilosort 2.5 was built and run only with Windows MATLAB R2026a from WSL2 on an RTX 3090. Linux MATLAB is supported
  by the code (paths are passed as they are) but untested, as is compiling on Linux.
- Kilosort 4 is pinned to 4.1.7: its final merge is patched by function name.
- The curator's displayed waveform window is fixed in samples for 30 kHz (`pixelbat/curation/waveforms.py`), its
  neighbour radius (100 µm) and sites shown (16) suit Neuropixels, and its Bombcell thresholds were chosen on our data
  (`pixelbat/curation/thresholds.json`).
- The page calls paths "flight paths"; the only positions converter is our flight room's
  (`pixelbat/curation/positions/flight_room.py`). Other set-ups write the positions file themselves (format in the
  curator README).
- `pixelbat/utils/trodes_export.py`, `session_paths.py` and the older notebooks default to our NAS layout; the sort
  script uses only `export_rec_dir` from them, with the Trodes folder given explicitly.
- `pixelbat/curation/checks/` are verification scripts written for our data; only `browser_test.py` is general (it
  needs `playwright` and a Chromium path set at its top).
