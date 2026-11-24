# Curation tool: progress log (autonomous work, started 2026-11-20 evening)

Kevin's mandate: 12 hours autonomous; complete review and redesign; at least 5 rounds of adversarial review; polished,
fast, superior to Phy. Brief: DESIGN.md. Do not ask questions; record decisions here.

## Working setup
- Real session server: port 8780, sessions /mnt/pool2/scratch/KevinQi/TwinBat/curation/sessions.csv (Kevin's log; never test on it).
- Test server: port 8790, /tmp/claude-1000/uitest/sessions.csv (out -> /tmp/claude-1000/uitest/out, cache symlinked, own log).
  Start: cd pixel-bat/curation && setsid nohup <TwinBat venv python> server.py /tmp/claude-1000/uitest/sessions.csv 8790 &
- Browser test: cd /tmp/claude-1000 && LD_LIBRARY_PATH=/tmp/claude-1000/libs/root/usr/lib/x86_64-linux-gnu \
  uv run --quiet --with playwright python pixel-bat/curation/checks/browser_test.py http://localhost:8790/ /tmp/claude-1000/uitest/shots
  (libs from `apt-get download libnspr4 libnss3 libasound2t64` + dpkg -x; headless shell in ~/.cache/ms-playwright).
- Python: /home/kevin/main/TwinBat/.venv/bin/python; serverx copy ~/main/pixel-bat/curation (rsync), venv ~/main/BatGPT/.venv.

## Log
- v1 page judged unusable by Kevin (stale-selection race, rows vanishing, tiny fonts, no post-merge stats).
- v2 written (server.py, index.html): all arrays loaded once (incl. spike times; correlograms computed in the page),
  decisions queued, labels shade in place, merge in place with Unmerge, metrics in 13-17 px, group header shows
  if-merged numbers, spike-density view (w). Needs display_* cache arrays: from single_waveforms via
  checks/display_from_singles.py for 29602_240103 (prepare.py now writes them directly).
- NEXT: test v2 in browser; fix; then review rounds 1-5 (workflow, speed, legibility, correctness, new user).
- v2 tested in headless browser (checks/browser_test.py): page usable 0.5 s (5.5 s first open after server start),
  select 25-30 ms, merge/label ~85 ms, accept screen 90 ms; stale-selection race fixed (decisions queued, server
  rejects decisions naming units that no longer exist). Live on 8780 with Kevin's 5 decisions intact.
- Review round 1 (two reviewers in parallel, isolated servers 8791 / 8792, out dirs /tmp/claude-1000/review1|2):
  A = curation workflow (electrophysiologist), B = speed + robustness + numeric correctness. Do not edit index.html
  / server.py while they run (their servers serve the files from disk).
- Pending: display_density from single_waveforms (job 58466) via checks/display_from_singles.py, then restart servers.
- Remaining rounds planned: 3 legibility/visual design, 4 numbers/correctness vs Phy/SpikeInterface, 5 first-time lab user (README).
- Round 1 reviews done (REVIEWS.md: 1A workflow 20 findings, 1B speed/robustness 20 findings). display_density real (from singles).
- NOW: v3 = fixes for all of round 1 (server validation + versioning + 409s, merge ids stored in events, kept by members,
  overlapping groups united, non-somatic section, one symmetric correlogram in the page (drop acg.npy from page),
  focus/selection by unit id, selection captured at keydown, colours per unit, amplitude-vs-time in panel, tiles redesign,
  partial redraw + path cache, unlabel key, undo message, export confirm). Then round 2 reviews (legibility; numbers vs SI/Phy).
- Kevin's rule kept over reviewer 1A#16: clicking a merge group selects the whole group (second click on a row narrows to that unit).
- v3 done and live on 8780 (Kevin's log migrated: merge event given id 1005). browser_test.py: 24 checks pass; j 30 ms,
  tile click 25 ms, accept 99 ms, 5 largest units 205 ms. Similarity recomputed with +-0.5 ms lags (one-off
  checks/similarity_with_lag.py; prepare.py now does it); groups now united components: 102 groups (largest 10).
- Round 2 reviewers next: C = legibility/visual design, D = numbers vs SpikeInterface/Phy + export correctness. Servers 8791/8792 restarted clean.
- Round 2 reviews done (REVIEWS.md 2C legibility 25 findings, 2D numbers/export 18 findings).
- v4: prepare.py interpolates bad channels before the median reference (found ch 124 dead), amplitude with peak_sign both,
  ch/depth by Phy's rule (write_phy.cluster_table, shared), similarity = max(S, S.T), density clamps and normalises per unit,
  recording.json (n_samples, rate, bad channels), cache built in cache.partial then swapped; flight_room uses the spike's own
  sample and the nearest frame; server: Kilosort groups kept as they are + similarity cliques + "also similar", merged presence
  on 60 s bins, merged mean weighted per site, check_CCG with the sort's thresholds, <=1 ms counts; page rewritten to the 2C spec
  (Okabe-Ito colours, text-colour selection, label stripes, verdict chip by Poisson test, metric grid, two-row action bar,
  status line in panel, tiles without position, transposed table for many units, zoom). Job 58467 re-prepares 29602_240103.
- For Kevin to decide (not changed): merges keep spike times as detected (Phy) rather than Kilosort's lag shift;
  spike-to-position timing now 33 us later than GridBat's processed files (the spike's own sample).
- NEXT: when 58467 is done -> restart 8780/8790, browser_test, export + phylib load check, then round 3 reviewers
  (E first-time lab user incl. README; F full adversarial re-review of everything), then rounds 4-5.
- v4 live on 8780 on the re-prepared cache (job 58467; ch 124 interpolated; 6 units at depth 5640 instead of 50).
  amplitude_median came out empty in that job (wrong metric_params; SpikeInterface only warns) -> prepare.py now makes a
  failed metric fatal; job 58468 re-prepares (about 36 min). Restart 8780/8790/8791/8792 after it.
- Export check: phylib load_model opens <out>/phy; peak channel equals cluster_info ch for 1004/1004 clusters.
- Round 3 reviewers running: E first-time lab user (8791), F full adversarial re-review against KEVIN_SAID.md (8792).
- Round 3 reviews done (3E first-time user; 3F full re-review: "close, one more fix round, not a redesign").
- v5 live on 8780: full redraw after every table change; fresh focus at top; undo/merge/unmerge select what they touched;
  units never change section (merged unit sits where its largest member was; flag is a toggle chip); unlabelled-unit counters
  that jump, finished state, e = next undecided, / = go to unit; x selects the first member and labels step through the group;
  a label on a whole undecided group = keep apart + label; held keys do not repeat decisions; verdict = Kilosort's
  cross-refractory test per pair (server, cached) + duplicate excess + "B follows A"; matrix up to 8 units; group rows share
  sites and scale; README rewritten; sort_unmerged.py no longer imports from TwinBat scratch. browser_test.py: 35 checks pass.
- Waiting: job 58468 (amplitude). Then restart 8780/8790/8791/8792 and run rounds 4 and 5:
  G = regression + "would Kevin still reject" on v5; H = polish at 3 viewport sizes + decisions per minute.
- Job 58468 done: amplitude present for 1005/1005 units (median 110 uV). All servers restarted on the complete cache;
  browser_test.py 35 checks pass; live 8780 has Kevin's 5 decisions.
- Rounds 4 and 5 running: G (8791) = verify round-3 fixes + attack the Kilosort-test verdict + would Kevin still reject;
  H (8792) = polish at 4 viewport sizes / dark / zoom + throughput (decisions per minute, total session time).
- While they run: do not edit index.html / server.py. Candidate work after: preparation time (36 min vs 15 min target):
  profile; fewer draws; skip bad-channel interpolation cost.
- Rounds 4 (G) and 5 (H) done, recorded in REVIEWS.md. Mechanics hold; remaining: verdict honesty, evidence (per-unit flight maps,
  row waveform scale, real single-spike traces), narrow layouts, navigation after corrections / partial merges, slips (label key on
  a whole undecided group), one event for keep+label.
- prepare.py: draws 1-4 now from one accumulator pass (checks/draws_from_one_pass.py verified the template injection exactly);
  job 58469 timing run in progress; old five-pass draw csvs saved in /tmp/claude-1000/uitest/draws_five_pass for comparison.
- NOW: v6 = fixes for 4G + 5H. Then final verification round (round 6) if time allows.
- v6 done (REVIEWS.md "Status after v6"); 42 browser checks pass on the real cache. Single-spike traces: display_spikes.npy
  (100 per unit, int16 uV), fetched per unit by /traces.
- Preparation: 24 min (job 58470; was 36 min; target 15 not met; peak memory 45 GB). checks/units_table_compare.py: the one-pass
  draws give the same Bombcell label on every draw for all 1,005 units as the five passes (45 uncertain units in both).
  Found there: signal-to-noise differed by up to 10% between runs (noise chunks unseeded); seeded, rerun as job 58471.
- Round 6 review running on port 8791.
- Round 6 done and fixed (REVIEWS.md). Seeded preparation (job 58471): 22 min; labels identical to the unseeded run. Live server
  on 8780 restarted on the final page and cache.
