# Unit curation

Curate a Kilosort 4 or Kilosort 2.5 sort in a browser: every unit of a session on one page, merge proposals decided by
hand, labels in batches. Writes a Phy-format folder; never modifies the sort.

Runs on Linux or WSL2. Install once from the repository folder (see `SHARING.md` at its root):

    uv sync --all-extras

Then `pixelbat-curate` is in `.venv/bin` (or run `uv run pixelbat-curate ...`).

## Steps

### 1. Sort

With `pixelbat/sorting/` (`sort_kilosort25.py` or `sort_kilosort4.py`): the sort to curate keeps every unit apart and
saves the merges the sorter would have made in `proposed_merges.json`. For Kilosort 2.5 the folder to curate is
`<OUT>/curation`; for Kilosort 4 it is `OUT`. Any other Kilosort 4 output folder also works; its merge groups then come
from waveform similarity only. The curator reads the Phy files plus `ops.npy`, `channel_shanks.npy`,
`whitening_mat_inv.npy` and the `cluster_*.tsv` files; the Kilosort 2.5 script writes the ones Kilosort 2.5 lacks.

### 2. Session table

One CSV row per session (`sessions_example.csv`):

| column | meaning |
|---|---|
| name | label shown in the page |
| sort | the sort folder to curate |
| recording | the binary the sort was made from |
| gain_uV | microvolts per bit of the binary: `spikeScalingToUv` in the header of the Trodes `.rec` file |
| spikes_positive | exactly `True` or `False`: whether spikes point up in the raw binary (Trodes Neuropixels exports: usually `True`) |
| out | folder for this session's cache, decision log and export |
| positions | optional: the session's positions file (below); leave the cell empty for none |

### 3. Prepare, once per session

    pixelbat-curate prepare SESSIONS.csv NAME --jobs 8

About 23 min with 32 processes for a 2 h recording with 1,005 units, with a memory peak of 45 GB (one pass for the
first draw of waveforms, one for the other four draws, one for spike amplitudes); a 17 min recording with 300 units
takes a few minutes with 8. `prepare_array.sbatch` runs several sessions as a Slurm array.
The cache is built in `<out>/cache.partial` and replaces `<out>/cache` only when complete; a rerun starts over.

### 4. Curate

    pixelbat-curate serve SESSIONS.csv --port 8780

Open http://localhost:8780. From another machine, tunnel first: `ssh -L 8780:localhost:8780 HOST` (the server
listens on the machine itself only). The server holds about 1.5 GB of memory per open session, and the page loads
50 to 95 MB (compressed) once per session; after the first table, the server works out every unit's possible partners
in the background (10-20 s). Press `?` in the page for the keys and every term.

- Every decision is appended to `<out>/curation_log.jsonl` at once. Close the tab or stop the server (Ctrl+C) any
  time; reopening continues where you were. To start over, delete that file.
- After re-sorting or re-preparing a session, delete the log: it refers to the unit numbers of the old sort.
- One curator per session at a time. A second open page is refused once ("this page was out of date") and then
  continues on the new state. Undo removes the last decision of the session, whoever made it.

### 5. Export

The "Export Phy folder" button, or `pixelbat-curate export SESSIONS.csv NAME`. It writes `<out>/phy`, overwriting the
previous export:

- `spike_times.npy`, `spike_clusters.npy`, `spike_templates.npy`, `amplitudes.npy`
- `cluster_group.tsv` (labelled units only, as Phy writes it), `cluster_info.tsv` (`cluster_id`, `Amplitude`,
  `ContamPct`, `KSLabel`, `ch`, `depth`, `fr`, `group`, `n_spikes`, `sh`; an empty `group` for a unit without a label)
- `cluster_KSLabel.tsv`, `cluster_ContamPct.tsv`, `cluster_Amplitude.tsv`, `curation_quality.tsv` (continuous
  contamination numbers of every unit), the templates and channel files Phy opens a sort with, `params.py` pointing at
  the recording, and a copy of the decision log

A merged unit gets a new cluster id above the sort's largest. Flags and keep-apart decisions are not exported.
`pc_features` and `spike_positions` are not written (they stop matching once a merge drops duplicate spikes), so Phy
opens the folder without its feature view. A loader that reads `cluster_info.tsv`, `spike_clusters.npy`,
`spike_times.npy` and `amplitudes.npy` works on `<out>/phy` as on a Phy-curated folder.

## Spikes on positions (optional)

A session with a `positions` file gets spikes on paths and rate maps in the comparison panel (`r`); without one, the
panel has no position section. The file is an `.npz` made for one sort (spike indices refer to its `spike_times.npy`):

| array | content |
|---|---|
| `spike_index` | int, (n,): index in the sort's `spike_times.npy` of each spike fired on a path |
| `spike_xy` | float, (n, 2): its x, y in metres |
| `spike_path` | int 0-255, (n,): label of the path it was fired on |
| `path_xy_<label>` | float, (frames, 2): the animal's x, y on every tracking frame spent on path `<label>` |
| `frame_rate_hz` | float: tracking frames per second (occupancy is frames / rate) |

Rate maps use 0.1 m bins smoothed by 1.2 bins, bins occupied under 0.03 s left empty; a path is drawn broken where
consecutive frames are over 1 m apart. Any tracking system works: write the arrays with `np.savez`. The page calls
paths "flight paths".

Flight room (Trodes and our flight-path `.mat`): `positions/flight_room.py` writes the file,

    python -m pixelbat.curation.positions.flight_room SORT REC FLIGHT_PATHS OUT.npz

where `REC` is the Trodes `.rec` folder holding `*_merged.kilosort/*_merged.timestamps.dat` and
`*_merged.DIO/*_merged.dio_Controller_Din1.dat` (the 3 s sync TTL) and `FLIGHT_PATHS` is the `.mat` with `flightPaths`
(`id`, `flight_starts_idx`, `flight_ends_idx`, `trajectoriesContinous`) and `cortexData.global_sample_ts_usec`.
Flight clusters 2 and up are the paths.

## What the page shows

- **Merge groups**: the sorter's would-be merges from `proposed_merges.json` (Kilosort 4's final merge; for Kilosort 2.5,
  `group_sources` says whether its template match would merge a group and whether it split the group despite its own
  refractory check), and groups of units not proposed noise in which every pair has waveform similarity above 0.95
  (shifts up to 0.5 ms allowed) and Kilosort's refractory test does not argue against the merge. Ordered: every pair
  refractory, then pairs too sparse to test, then Kilosort proposals whose merged unit is over 20% contamination. Each
  header says in words who proposed the group and why, then the curator's decision ("you: merged", "you: kept apart");
  the section header counts the sorter's proposals by decision. Rows of a group share one µV scale and one amplitude
  axis. `shift+M` merges (the rows become one, with an Unmerge button; plain `m` is the mua label); a label on
  the whole group also keeps it apart. Groups under 500 spikes in all are merged when the server first loads the
  session (logged as merges by "kilosort (<500 spikes)", only for groups no logged decision names) and not listed. Digits `1`-`9` add or remove a row of the group from the selection, for a partial merge.
- **Possible merges**: pairs the sorter did not propose, peak channels within 100 µm, neither labelled (or, unlabelled,
  proposed) noise nor in an open merge group, not kept apart (older logs), with footprint correlation at least 0.85 and a notch
  at most 0.5 (2–10 ms flanks, from 5 centre pairs expected) or a hand-off over 0.4 (rates in 5-minute blocks:
  (1 − overlap of the two time courses) × (1 − CV of their sum ÷ the larger own CV)); each unit in its best pair,
  searched again after every decision; decided by merging or labelling either unit. Nothing is merged automatically. `p` adds a
  unit's best partner within 100 µm for reference.
- **Merge evidence** (two or more units selected): whether they fire within 1 ms of each other (cross-correlogram
  ±20 ms as a multiple of chance, centre 0.25–1 ms shaded and compared with the busier 2–10 ms flank; each pair, up to
  3), whether they have one shape across channels (peak-to-peak amplitude per channel against depth, with the
  footprint correlation), and whether they take turns over the session (spikes per 5 minutes, with the hand-off when
  over 0.4).
- **Comparison panel**: the selected units on shared axes: numbers, waveforms (`w`: mean, 100 single spikes per unit,
  or the density of 500), correlogram matrix, autocorrelogram if merged, amplitude over the session, spikes on flight
  paths together and per unit.
- **Uncertain units**: the Bombcell label differs between five independent draws of 500 spikes.
- **Proposed good / mua / noise**: Bombcell's label (thresholds in `thresholds.json`; its mua test is
  foreign spikes at most 20% (pairs 0.25 to 1.25 ms apart against the unit's own rate 10 to 50 ms away),
  at least 500 spikes, presence at least 0.5). `a` accepts a screen of tiles.
  A `non-somatic` tag marks axonal-looking waveforms (Bombcell's shape tests); it does not change the proposal.
- **Few spikes**: units (and merged units) under 500 spikes, proposed `few` unless proposed noise; label `f`. Flag is `shift+F`.
- Labels (`g`, `m`, `n`, `u` unstable, `f` few) apply to every selected unit with one press and shade it in place; nothing leaves the list or changes section, except a possible-merge pair once merged or labelled noise. `z` undoes the last
  decision, repeatedly; there is no redo. There is no split: label such a unit mua, or split it in Phy.
- The session is finished when "unlabelled" in the top bar reads 0.

A merged unit loses duplicate spikes by Kilosort's own rule (a spike within `duplicate_spike_ms` of the previous kept
spike), in the page and in the export. Its spike times stay as detected, as in Phy (Kilosort's own merge would also
shift the absorbed unit by the lag between the templates).

## Conventions

- Peak channel and depth follow Phy: the largest channel of the unwhitened Kilosort template that gave the unit most
  of its spikes.
- Waveforms, amplitude and signal-to-noise come from the recording high-passed at 300 Hz, with bad channels
  interpolated and the median over channels subtracted; amplitude is taken at the waveform's largest extremum.
- `<=1 ms` counts inter-spike intervals of 30 samples or less at 30 kHz; rates use the length of the recording.
- The pair verdict is Kilosort's own cross-refractory test with the sort's thresholds (`kilosort.CCG.compute_CCG` and
  `CCG_metrics`, the larger unit first, as in Kilosort's merge): "refractory together" when the centre/shoulder ratio
  of the cross-correlogram is below `ccg_threshold` and the dip is significant (p < 0.05), "too few spikes to test"
  when the ratio is below the limit but not significant, "not refractory together" otherwise. The ratio is printed.
- "Shared spikes" are counted in the page: the excess within 1 ms over the rate at 10-50 ms, when significant
  (Poisson, p < 0.01) and at least 5% of the smaller unit. Two units are noted as rarely active in the same minutes
  when the sum over minutes of the product of their per-minute spike shares, times the number of minutes, is below
  0.5 (1 for two units whose activity is unrelated).
- Positions: whatever the positions file gives (the flight-room converter gives a spike the Trodes timestamp of its own
  sample and the nearest tracking frame).

## Files

| file | role |
|---|---|
| `cli.py` | `pixelbat-curate prepare / serve / export` |
| `prepare.py` | cache of one session: metrics, waveforms, similarity |
| `server.py`, `index.html` | the page; the server only stores decisions (`<out>/curation_log.jsonl`) |
| `state.py` | curation state from the decision log |
| `labels.py`, `thresholds.json` | Bombcell labels |
| `waveforms.py` | display waveforms (mean and single-spike density) |
| `ratemaps.py` | rate maps of spikes on positions |
| `positions/flight_room.py` | positions file of a flight-room session |
| `write_phy.py` | export |
| `prepare_array.sbatch` | Slurm array of `prepare` |
| `checks/` | verification scripts (written for our data) and the browser test |
| `dev/` | requirements (`DESIGN.md`), review findings and progress notes |
