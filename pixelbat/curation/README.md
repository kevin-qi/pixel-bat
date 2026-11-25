# Unit curation

Curate a Kilosort 2.5 or Kilosort 4 sort in a browser: every unit of a sort on one page, merge proposals decided by
hand, labels in batches. Writes a Phy-format folder; never modifies Kilosort's files.

Runs on Linux or WSL2. Install once from the repository folder with `uv sync` (see `SHARING.md` at its root); then
`pixelbat-curate` is in `.venv/bin`.

## The sort folder

A sort is its Kilosort output folder, and everything of its curation is in its `curation/` subfolder:

| file | written by | content |
|---|---|---|
| `curation/recording.json` | the sorter | `binary` (the int16 binary sorted), `gain_uV` (microvolts per bit), `spikes_positive` (whether spikes point up in the binary) |
| `curation/cache/` | `prepare` | waveforms, metrics, similarity |
| `curation/opened/` | `prepare`, or the app on first opening | everything the app holds of the sort (about 0.7 GB), so that opening only reads it |
| `curation/positions.npz` | optional, a converter | spikes on positions (below) |
| `curation/curation_log.jsonl` | the app | every decision, appended as it is made |
| `curation/phy/` | export | the curated sort |

The curator reads the Phy files plus `ops.npy`, `channel_shanks.npy`, `whitening_mat_inv.npy`, the `cluster_*.tsv`
files and, if present, `proposed_merges.json`. Sorts made with `pixelbat/sorting/` have all of them; any other
Kilosort 4 folder also works, its merge groups then coming from waveform similarity only.

## Steps

### 1. Sort

With `pixelbat/sorting/sort.py`: the sort keeps every unit apart and saves the merges the sorter would have made in
`proposed_merges.json`.

### 2. Prepare, once per sort

    pixelbat-curate prepare SORT [SORT ...] --jobs 8

Prepared sorts are skipped; each sort runs in its own process, and is then opened ahead of the app (`curation/opened`:
contamination of every unit, merge groups, the evidence of every pair of neighbours; about 1 min). About 23 min with 32 processes for a 2 h recording with
1,005 units, with a memory peak of 45 GB (one pass for the first draw of waveforms, one for the other four draws, one
for spike amplitudes); a 17 min recording with 300 units takes a few minutes with 8. `prepare_array.sbatch` runs a
list of sorts as a Slurm array. The cache is built in `curation/cache.partial` and becomes `curation/cache` only when
complete. To prepare again, delete `curation/cache`.

Prepare checks the spike sign in `recording.json` against the mean raw waveforms of the largest good units and stops
if they disagree: the sort was then made on sign-flipped data.

A sort made without `pixelbat/sorting/` has no `recording.json`: give its binary and gain once, and the sign is
measured from the binary:

    pixelbat-curate prepare SORT --binary BINARY --gain-uv GAIN

### 3. Curate

    pixelbat-curate                  # one app per machine, http://localhost:8780 (--port for another)

The app starts on its picker (later: **Open…**). Pick a sort folder: type or paste its path, or click through the
folders (prepared sorts are marked; a sort not yet prepared shows the command that prepares it). Below are the recent
sorts on the machine, with when each was opened and last decided on and its number of decisions: type words to filter
them, click a column to order by it. The address bar holds the open sort (`?sort=/path`), so a link or bookmark
reopens it. Opening shows what is being waited for: the app, the unit data arriving, the unit table, drawing. A sort
with `curation/opened` opens in about 2 s; without it, or after its files or the app's code changed, the app builds it
first (10 to 30 s, each step named on the loading card). From another machine, tunnel first: `ssh -L 8780:localhost:8780 HOST` (the app listens on the
machine itself only). The app keeps the three sorts opened last, reading their large arrays from disk as they are used, and the page loads
50 to 120 MB (compressed) once per sort. Press `?` in the page for the keys and every term.

- Every decision is appended to `curation/curation_log.jsonl` at once, with the curator's name (set in the Open
  dialog; at first the user the app runs as). Close the tab or stop the app (Ctrl+C) any time; reopening continues
  where you were. To start over, delete that file.
- A new sort is a new folder, so a log never meets another sort's unit numbers.
- One curator per sort at a time. A second open page is refused once ("this page was out of date") and then
  continues on the new state. Undo removes the last decision of the sort, whoever made it.

### 4. Export

The "Export" button, or `pixelbat-curate export SORT`. It writes `curation/phy`, overwriting the previous export:

- `spike_times.npy`, `spike_clusters.npy`, `spike_templates.npy`, `amplitudes.npy`
- `cluster_group.tsv` (labelled units only, as Phy writes it), `cluster_info.tsv` (`cluster_id`, `Amplitude`,
  `ContamPct`, `KSLabel`, `ch`, `depth`, `fr`, `group`, `n_spikes`, `sh`; an empty `group` for a unit without a label)
- `cluster_KSLabel.tsv`, `cluster_ContamPct.tsv`, `cluster_Amplitude.tsv`, `curation_quality.tsv` (continuous
  contamination numbers of every unit), the templates and channel files Phy opens a sort with, `params.py` pointing at
  the recording, and a copy of the decision log
- `cluster_members.tsv` (`cluster_id`, `original_cluster_id`): the Kilosort clusters each exported unit is made of, one
  row per original cluster; the spikes below an amplitude floor list the cluster they were taken from

From Python, `pixelbat.curation.write_phy.export(sort, log, out)` writes the same folder to `out` from the decision log
`log` and returns the summary line.

A merged unit gets a new cluster id above the sort's largest. Flags and keep-apart decisions are not exported.
`pc_features` and `spike_positions` are not written (they stop matching once a merge drops duplicate spikes), so Phy
opens the folder without its feature view. A loader that reads `cluster_info.tsv`, `spike_clusters.npy`,
`spike_times.npy` and `amplitudes.npy` works on `curation/phy` as on a Phy-curated folder.

## Spikes on positions (optional)

A sort with `curation/positions.npz` gets spikes on paths and rate maps in the comparison panel (`r`); without one, the
panel has no position section. The file is made for one sort (spike indices refer to its `spike_times.npy`):

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

    python -m pixelbat.curation.positions.flight_room SORT REC FLIGHT_PATHS

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
  the whole group also keeps it apart. Groups under 500 spikes in all are not listed (nothing is merged
  automatically). Digits `1`-`9` add or remove a row of the group from the selection, for a partial merge.
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
- The sort is finished when "unlabelled" in the top bar reads 0.

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
| `cli.py` | `pixelbat-curate` (the app), `pixelbat-curate prepare`, `pixelbat-curate export` |
| `prepare.py` | cache of one sort: metrics, waveforms, similarity |
| `server.py`, `index.html` | the app and its page; the app only stores decisions (`curation/curation_log.jsonl`) |
| `opened.py`, `open_ahead.py` | everything the app holds of a sort, computed once and saved in `curation/opened` |
| `state.py` | curation state from the decision log |
| `labels.py`, `thresholds.json` | Bombcell labels |
| `waveforms.py` | display waveforms (mean and single-spike density) |
| `ratemaps.py` | rate maps of spikes on positions |
| `positions/flight_room.py` | positions file of a flight-room sort |
| `write_phy.py` | export |
| `prepare_array.sbatch` | Slurm array of `prepare` |
| `checks/` | verification scripts (written for our data) and the browser test |
| `dev/` | requirements (`DESIGN.md`), review findings and progress notes |
