# Sorting and curating Neuropixels recordings: lab quick start

Two separate tools in this repository:

- **Sorter** (`pixelbat/sorting/`): plain Python scripts, no GUI. Set the paths at the top of `sort_kilosort25.py` (the
  main sorter: Kilosort 2.5 with the Moser lab's changes, run in MATLAB) or `sort_kilosort4.py` (Kilosort 4 from pip)
  and run it. Both keep every unit apart and save the merges the sorter would have made as proposals.
  `sort_batch.py` sorts a list of recordings from a CSV. Details: `pixelbat/sorting/README.md`.
- **Curator** (`pixelbat/curation/`): a browser page for curating one sort at a time: all units on one page, merge
  proposals decided by hand, labels in batches, a Phy-format folder as output. Command line: `pixelbat-curate
  prepare | serve | export`. Spikes on positions are an optional plug-in (a positions file per session). Details:
  `pixelbat/curation/README.md`.

## Requirements

- Linux or Windows with WSL2, an NVIDIA GPU with a current driver, and `uv` (https://docs.astral.sh/uv/:
  `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Kilosort 2.5: MATLAB with the Parallel Computing Toolbox and a C++ compiler MATLAB supports (Windows: Visual Studio
  2022 Build Tools); Linux MATLAB or, from WSL2, Windows MATLAB.
- Curator: about 1.5 GB of memory per open session; preparing a 2 h, 1,000-unit session peaks at about 45 GB with 32
  processes (less with fewer).
- Recordings exported by Trodes for Kilosort: an int16 binary (`*.group0.dat`) and its channel-coordinates file.

## Quick start

    git clone <pixel-bat repository> && cd pixel-bat
    uv sync --all-extras                      # Python environment in .venv, exactly as in uv.lock

Sort (Kilosort 2.5; compile once per machine first, see `pixelbat/sorting/kilosort25_moser/README.md`):

    cp pixelbat/sorting/sort_kilosort25.py my_sort.py     # edit BINARY, COORDINATES, OUT, MATLAB, SCRATCH ...
    .venv/bin/python my_sort.py

Curate: one row per sort in a sessions CSV (`pixelbat/curation/sessions_example.csv`; for Kilosort 2.5 the `sort`
column is `<OUT>/curation`), then

    .venv/bin/pixelbat-curate prepare sessions.csv NAME --jobs 8   # once per session
    .venv/bin/pixelbat-curate serve sessions.csv --port 8780       # open http://localhost:8780, press ? for help
    .venv/bin/pixelbat-curate export sessions.csv NAME             # or the Export button: <out>/phy

## Not yet generic

- Trodes only: the sorters read a Trodes coordinates file, and the shank of each site comes from a table of the Trodes
  layouts we use (Neuropixels 1.0, 2.0 four-shank, UHD; `pixelbat/sorting/probe.py`). Another probe or acquisition
  system needs a row there or its own probe reader.
- The sign of the spikes (`SPIKES_POSITIVE`) and dead channels (`MASKED_CHANNELS`) are set by hand per recording; no
  check is built in.
- Kilosort 2.5 was built and run only with Windows MATLAB R2026a from WSL2 on an RTX 3090. Linux MATLAB is supported
  by the code (paths are passed as they are) but untested, as is compiling on Linux.
- Kilosort 4 is pinned to 4.1.7: its final merge is patched by function name.
- The curator's displayed waveform window is fixed in samples for 30 kHz (`pixelbat/curation/waveforms.py`), its
  neighbour radius (100 µm) and sites shown (16) suit Neuropixels, and its Bombcell thresholds were chosen on our data
  (`pixelbat/curation/thresholds.json`).
- The page calls paths "flight paths"; the only positions converter is our flight room's
  (`pixelbat/curation/positions/flight_room.py`). Other set-ups write the positions file themselves (format in the
  curator README).
- `pixelbat/utils/trodes_export.py`, `session_paths.py` and the older notebooks default to our NAS layout; the new
  scripts use only `export_rec_dir` from them, with the Trodes folder given explicitly.
- `pixelbat/curation/checks/` are verification scripts written for our data; only `browser_test.py` is general (it
  needs `playwright` and a Chromium path set at its top).
