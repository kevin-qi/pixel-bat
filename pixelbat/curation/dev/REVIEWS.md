# Review findings and their status

## Round 1A: curation workflow (electrophysiologist), 2026-11-20
B = bug, D = design. Status in brackets.
1. B keep-apart (x) acts on focused group, not the selection. [fixed in v3]
2. B group header "if merged" ignores merges of its members made in an overlapping group (15 units sit in two groups); show overlapping groups as one. [fixed in v3]
3. B merging units outside a proposed group: rows vanish, merged unit far away without Unmerge, focus jumps. Track focus by unit id; Unmerge on every merged row. [fixed in v3]
4. B Caps Lock: 'M' without shift merges. Test shift explicitly. [fixed in v3]
5. B key that closes help is also executed. [fixed in v3]
6. B keep-apart after a partial merge saves but changes nothing (kept matched on original ids); flag inside a group draws nothing. [fixed in v3]
7. B a failed save poisons the key queue until reload; server sends no response on its KeyError. Return 409 + reason; page reloads table, resets queue. [fixed in v3]
8. B unit colours differ between list and panel. One colour map per unit. [fixed in v3]
9. B panel unreadable at 4+ units: table columns collide, CCG captions overlap, merged-ACG caption over bars, low-amplitude waveforms overflow rows. [fixed in v3]
10. B depth-order toggle loses place (selection jumps to top, list not scrolled); no group/kept/unmerge marks in depth order. [fixed in v3]
11. B correlogram conventions: page ACG asymmetric (bin edges), cached vs page versions differ, "together" drops same-sample coincidences. One function, symmetric bins. [fixed in v3]
12. D no amplitude-over-time comparison for a candidate merge (drift splits); row amplitude axis set by outliers. Shared-axis amplitude vs time by unit in panel. [fixed in v3]
13. D waveform similarity (SpikeInterface, no lag tolerance) is negative for many Kilosort-proposed pairs. Max over small lags, or drop. [fixed in v3]
14. D accept-screen too blunt: silently maps non_soma to noise, works across sections, no summary, does not advance. Own non-somatic section; summary; advance. [fixed in v3]
15. D tiles: waveforms unreadable, no spike count/KS label, id collides with label, selected tile barely marked. [fixed in v3]
16. D label keys act on whole selection (group click selects all; g labels all; after s labels off-screen units). Row click selects the unit, header click the group; s for comparison only. [fixed in v3]
17. D "together within ±1 ms N (independent X)" unreadable; print ratio in words and duplicates dropped; per pair. [fixed in v3]
18. D selection can be off-screen and still take decisions; header should warn when a group mixes noise and good proposals. [fixed in v3]
19. D merged-unit statistics incomplete (amplitude, SNR, duration, presence in the if-merged column; KS needs a fetch). [fixed in v3]
20. D undo is blind (say what was undone; unlabel key); uncertain rows do not say which labels the draws gave; "KS cont. 345%" unexplained; export does not warn about undecided units. [fixed in v3]
Keep: speed; merge arithmetic (verified on all 114 groups); in-place merged row; CCG matrix + merged ACG; key ordering.

## Round 1B: speed, robustness, numbers, 2026-11-20
Measured (headless, software raster): load 0.43-0.62 s; j through groups 36 ms median / 62 worst to frame; tile click 97 ms;
2 largest units (254k spikes each) 70 ms; 5 largest 265 ms; 8 largest 579 ms; decisions 62-99 ms; export 6.8 s;
payload 151 MB (112 MB spike times); page 308-441 MB; server 1.25 GB.
1. BUG failed request poisons the key queue; server gives no HTTP response on error. [fixed in v3]
2. BUG (data loss) a bad event (undo on empty, unmerge of an original, merge [14,14], missing kind) makes the session unloadable. Validate by replaying events+[event] before writing. [fixed in v3]
3. BUG stale tab: label overwrite and merged-id reuse after undo. Version check (409 + fresh table); merge ids never reused. [fixed in v3]
4. BUG a key queued behind a save acts on a later click's selection. Capture selection at keydown. [fixed in v3]
5. BUG panel table can show another selection's numbers (panelKey not set for single/empty selections). [fixed in v3]
6. BUG no Unmerge for partial merges or "other merged"; keep-apart ignored after partial merge. [fixed in v3]
7. BUG merging outside a group moves rows and focus (focus is a line index). Focus by unit id; undo should refocus the affected units. [fixed in v3]
8. BUG two correlogram implementations disagree; page version asymmetric bins. One integer rule: d>0 -> 50+floor((d-1)/bin), d<0 -> 49-floor((-d-1)/bin). [fixed in v3]
9. BUG "together" omits exactly coincident spikes (6,631 vs 7,013 over all groups). Count |lag| <= 30 incl. 0 across units. [fixed in v3]
10. PERF comparing 5-8 large units 250-560 ms: pair correlograms computed 3x, sort of sorted trains, together() recomputed per redraw. Cache per pair, mirror, k-way merge. [fixed in v3]
11. PERF every selection change redraws all visible canvases (tile click 97 ms; flight paths re-stroked per tile). Redraw changed lines only; cache paths offscreen. [fixed in v3]
12. PERF fast scroll / HiDPI long frames. Draw in requestAnimationFrame + path cache. [fixed in v3]
13. PERF /merged fetched on every multi-selection; use group's if_merged, cache others. [fixed in v3]
14. FRAGILE unknown paths (favicon) never answered. 404. [fixed in v3]
15. FRAGILE label values and kinds not validated ('banana' exported). [fixed in v3]
16. BUG export not serialised with decisions; copied log may differ from arrays. [fixed in v3]
17. PERF 151 MB re-sent on every reload; two transient copies per request. Build blob once, ETag. [fixed in v3]
18. FRAGILE reload loses focus/scroll/depth/density. localStorage. [fixed in v3]
19. FRAGILE session switch keeps old derived trains; keys during load post to the new session. [fixed in v3]
20. FRAGILE Math.min(...spread) on long paths; NaN in table JSON fails the whole table; g with dropdown focused; Caps Lock. [fixed in v3]
Verified correct: merged counts and short-interval counts (114 groups); duplicate window 7 samples and JS rule = Kilosort's;
chance counts; no uint32 underflow; ids; nested merge/unmerge label restore; rapid keys run in order.

Round 1 status: all 40 findings addressed in v3 except, deliberately: 1A#16 (group click still selects the whole group, per Kevin;
a second click on a row narrows to that unit; s-added units are reference-only), 1A#19 (merged-unit SNR and duration not
computed; amplitude is a spike-weighted mean marked with ~), 1B#18 (scroll position not restored, focus unit is).
checks/browser_test.py: 24 assertions, all pass.

## Round 2C: legibility and visual design, 2026-11-20 (headless font DejaVu is ~10% wider than Segoe UI)
1. Top bar overflows at 1440 px: status and help invisible. Status gets its own line in the panel; shorten progress text. [fixed in v4]
2. Stats table clips at 8-10 units. Transpose (units as rows) when columns < 100 px. [fixed in v4]
3. Panel does not fit (1000 px canvas in 952/752 px box); ~190 px blank (reserved lines at n=1; position boxes square for a flat room). Position at data aspect; tighter rows. [fixed in v4]
4. Unit colour changes with selection; 10-unit groups reuse colours. Reference units neutral dashed grey; palette of 10. [fixed in v4]
5. COLORS not colour-blind safe; fails contrast as text. Okabe-Ito based palette; ids in text colour with a colour swatch. [fixed in v4]
6. Selection (amber) / focus (blue) / warning (red) collide with unit and label colours. Selection and focus in text colour (solid / dashed outline); no green/orange/red in the unit palette. [fixed in v4]
7. White chip text and coloured label text under 4.5:1. Darker chip fills (#1e7b2c good, #a85f00 mua, #5f5f5f noise, #6d3fc4 non-somatic); KS chips outline only; tile label as a chip. [fixed in v4]
8. Good vs other shading nearly equal lightness; mua and noise share a grey. Add an 8 px label stripe at the right edge in the label colour. [fixed in v4]
9. Group header line 2 is one 150-character sentence, clipped at 1440. Verdict chip first, then fixed columns. [fixed in v4]
10. Row metrics unranked, abbreviations differ from the panel. Label/value grid, values bold tabular right-aligned, interval and contamination first, same words as panel. [fixed in v4]
11. Text/plot overflows: long "fails" notes into the waveform; 1-spike units' waveforms overflow; amplitude label under dots; captions overprint in density view. [fixed in v4]
12. Tiles: flight plot saturates to a blob; per-tile waveform gain hides amplitude; ACG slabs. Drop position from tiles; shared gain + scale tick. [fixed in v4]
13. Tile metric line clips; "0.0 Hz"; "1 spikes"; contamination >100% unmarked. TILE_MIN 300; 2 significant digits; ">100%". [fixed in v4]
14. Density view too small beyond 2 units; mean invisible at n=1; gain/3 changes scale silently. 4 peak sites per unit, same gain as the mean view, mean line with halo. [fixed in v4]
15. Correlogram matrix unreadable from 5 units; no time ticks or counts anywhere. From 5 units: only the focused unit's row; ticks -50/0/50; peak count per cell. [fixed in v4]
16. Merged ACG is a heavy black block. Mid-grey, lower; visible +-1 ms band (pale red). [fixed in v4]
17. Verdict line is plain text under the table and clips. A band at the top of the panel with a verdict chip. [fixed in v4]
18. Row flight panels tiny with 60% of the band empty. Stack the flight clusters vertically at data aspect in a 120 px column. [fixed in v4]
19. Action bar: 13 same-weight buttons in three rows. Two rows: decisions (Merge filled primary, labels with colour stripe, undo right) and view (segmented toggles showing state); disable what cannot apply. [fixed in v4]
20. Reference marker and Unmerge easy to miss. "ref" chip, dashed bar, hollow dots. [fixed in v4]
21. 11-12 px text carries content. Minimum 13 px. [fixed in v4]
22. Wasted space at 2560 and at n=1. n=1 layout: label/value pairs beside a bigger waveform; zoom control. [fixed in v4]
23. Plots lack minimum scale: amplitude zero and session minutes; shared waveform gain within a group with one scale bar. [fixed in v4]
24. Section vs group header too close in weight; kept-apart looks like labelled-noise. Section header 18 px, sticky; kept-apart header with a left bar. [fixed in v4]
25. Minor: help has no close hint; merged row repeats "= a + b"; omit SNR/dur cells for merged; scale label hit by traces. [fixed in v4]
Keep: shared site grid and gain with scale bar; in-place merged row and shading; group-position colours; red KS contamination and the draws note; crisp at device pixel ratio 2.

## Round 2D: numbers and export, 2026-11-20
1. WRONG 50 units get peak channel/depth/amplitude/SNR on dead channel 124 (global median reference writes the inverted probe-wide artifact there). Interpolate bad channels before referencing; peak channel and depth from Kilosort's template. [fixed in v4]
2. WRONG similarity.npy covers one sign of lag only (SpikeInterface max_lag_ms, same-array shortcut). Use max(S, S.T). [fixed in v4]
3. Reviewer claimed spikes on position were indexed one sample early vs the owner's pipeline. Checked (checks/sample_index_check.py): the tool matched GridBat's processed spike times exactly (0 us); GridBat itself uses the timestamp of sample s - 1. Changed to the spike's own sample (33 us later than GridBat; no wrap at sample 0). [changed in v4]
4. A merge is not Kilosort's merge: Kilosort shifts the absorbed unit's spike times by the template lag (8 proposed pairs have 7-9 samples). NOT CHANGED: merges keep spike times as detected, as Phy does; stated in the help and README. For Kevin to decide.
5. RISK united groups chain unrelated units (10-unit group: 35 of 45 pairs unlinked). Keep Kilosort groups as they are; similarity groups must be cliques; a similarity link never joins two Kilosort groups. [fixed in v4]
6. WRONG export ch/depth not Phy's (Phy: unwhitened template with most spikes); page depth differs from export. One function for both. [fixed in v4]
7. MISLEADING "they avoid each other" printed without power (0 seen vs 0.09 expected). Poisson test; "too few spikes to tell". [fixed in v4]
8. MISLEADING density drops samples outside +-1.5 x peak; per-site normalisation; "500 spikes" untrue for small units. Clamp to edge bins, normalise per unit, caption real n. [fixed in v4]
9. MISLEADING "amp." is the trough-channel median: understates positive-going units. peak_sign both. [fixed in v4]
10. WRONG (small) merged presence uses different bins from single units. 60 s bins over the recording. [fixed in v4]
11. MISLEADING merged mean waveform averages zeros where members' channel sets differ. Weight per site by units that have it. [fixed in v4]
12. RISK exported params.py dat_path points at a staging cache. Write the session's recording path. [fixed in v4]
13. WRONG (small) chance level uses 60 samples for a 61-sample window. [fixed in v4]
14. WRONG (small) panel "if merged" for an already merged unit dedupes sequentially. Build from original members. [fixed in v4]
15. MISLEADING failure reasons incomplete (NaN counts as a noise failure in SpikeInterface; non-somatic units that also fail mua tests). [fixed in v4]
16. Small: rate denominators differ (use recording length); "<1 ms" strict vs correlogram bin inclusive; zero-lag breaks exact mirror; percentage over spikes not intervals; merged similarity uses first member; position frame = next not nearest. [fixed in v4]
17. RISK kilosort_proposals r_thresh 1.0 not strictly no-merge (use inf); check_CCG called with default thresholds not the sort's. [fixed in v4]
18. RISK cache not built by the current prepare.py; stale files (acg.npy, single_*.npy, similarity_zero_lag.npy). Rebuild from empty. [fixed in v4]
Verified correct: spike counts, rate, short intervals, presence, Kilosort label/contamination, Bombcell labels on 5 draws (all 1005 units);
merged units for all 102 groups (dedupe = Kilosort's, KS label, amplitude); correlograms exact; export arrays exact (6 merges incl. nested),
loads with phylib and SpikeInterface; unmerge/undo/unlabel right.

Round 2 status: v4 addresses all of 2C and 2D except: 2C#14 partly (density shows the 4 largest sites, up to 4 units side by side),
2C#22 partly (zoom control added; n=1 layout unchanged), 2C#24 (section header not sticky), 2D#4 (no time shift on merge, as Phy),
2D#9 (amplitude now uses the largest extremum of either sign), 2D#16 (percentage over intervals; rate over recording length; nearest frame).

## Round 3E: first-time lab user, 2026-11-20
README: (1) says `M` merges without saying shift (plain m = mua); (2) sort recipe imports probe() from a hard-coded TwinBat scratch path, needs GPU + Kilosort 4.1.7, OUT must not exist; (3) "any Phy-format folder works" is false (needs ops.npy, channel_shanks.npy, cluster_*.tsv, whitening_mat_inv.npy: Kilosort4 only); (4) gain_uV source; (5) spikes_positive must be exactly True/False (anything else silently False); (6) rec/flight_paths columns must exist, their requirements unstated; (7) prepare time/RAM, not resumable; (8) tunnel command, RAM, 150 MB load; (9) resuming, stale log after re-sort; (10) two people; (11) export contents and consequences, how to load it; (12) non-somatic section policy; (13) flag and ad-hoc merges do move units; (14) undo is multi-level, no redo; (15) similarity rule; (16) versions; (17) files table.
Page:
1. g/m/n on a selected undecided group labels every member and marks the group decided. [fixed in v5]
2. "To decide" at zero does not mean done: unlabelled units inside decided groups are counted nowhere; no done state. [fixed in v5]
3. A fresh browser opens mid-list (missing focus value becomes unit 0). [fixed in v5]
4. Second click toggles group <-> unit; a double-click then labels the wrong set. Header selects the group, a row selects the unit. [fixed in v5]
5. After shift+M the list is drawn wrong (blank gap, stale header count, no Unmerge until scrolled): applyTable must always redraw all. [fixed in v5]
6. No way to find a unit (canvas text is not searchable). Go-to-unit box; clickable "also similar". [fixed in v5]
7. No section navigation (groups section is 33 screens). Counters jump to sections; a key for next undecided. [fixed in v5]
8. Flag and ad-hoc merge teleport the unit and then the view; no un-flag. Flag as a toggle, in place. [fixed in v5]
9. Help cannot be closed with the mouse; clicks pass through. [fixed in v5]
10. Labelled tiles show the label twice. [fixed in v5]
11. Unmerge silently discards the merged unit's label. Say so. [fixed in v5]
12. Text collisions at 100% ("<=1 ms0.97% (289)", "100,297 spk14.8 Hz"). [fixed in v5]
13. Merged unit: SNR/duration blank, no proposal, no explanation. [fixed in v5]
14. Accept screen opaque: acts on scroll position, first section only, scrolls on before the result is seen, "labelled 5: 1 mua" reads as a count. [fixed in v5]
15. Selection after a decision inconsistent (labels advance; keep/merge/backspace stay); undo may act off screen. [fixed in v5]
16. Vocabulary never defined (verdict chips, mixes, also similar, kept apart, flagged, fails, draws, >100%, ~, ref, plot corner numbers); no hover text. [fixed in v5]
17. Help wrong/incomplete (a = first section only; s adds 3 more each press; Delete; depth, dark, zoom, export; partial merges). [fixed in v5]
18. Panel with reference units unreadable (all refs one grey, drawn over the selection). [fixed in v5]
19. "waveform similarity 0.00" for 20+33, which Kilosort proposes. To trace. [fixed in v5]
20. Smaller: export status does not say where; backspace on an unlabelled unit saved as a decision; buttons wrap to four rows at 1440; two-line status shifts the panel; PageDown needs a click first; Unmerge overlaps the flight plot.
Missing, ranked: go to unit; section / next-undecided jumps and an undecided filter; true remaining count and finished state; review list of decisions with per-item revert; un-flag / un-keep; notes per unit; non-somatic policy; who is curating; redo; split (say so); trace/feature view (say so).
Keep: layout; group header with verdict and if-merged numbers; comparison panel; status after each decision; merged / kept headers; shading + stripe; off-screen guard and stale-page refusal; two-click export; navigation keys; dark mode.

## Round 3F: full adversarial re-review against KEVIN_SAID.md, 2026-11-20
Verdict: "Kevin would still reject it, though it is close": one more fix round, not a redesign.
1. BUG stale list after every merge (hole, no Unmerge, stale count): applyTable takes the partial-redraw branch. Always drawAll. [fixed in v5]
2. BUG unmerging the selected merged unit leaves it drawn as merged; focus falls to the first line. [fixed in v5]
3. BUG verdict underflow: poissonAtMost returns 0 above ~745 expected -> always "avoid each other". [fixed in v5]
4. DESIGN verdict uses the wrong null (session-mean independence ignores co-modulated firing): 47 of 164 pairs flip with the correlogram's shoulders as baseline; groups of 3+ sum pairs. Per pair, centre vs shoulders. [fixed in v5]
5. BUG fresh browser opens at the bottom (+null = 0, unit 0 exists). [fixed in v5]
6. BUG undo loses the place. Server returns the undone units; select and scroll to them. [fixed in v5]
7. DESIGN tile merges and Flag make units disappear / jump sections. Keep merged units at their first member's place; flag in place. [fixed in v5]
8. DESIGN kept-apart groups slow and uncounted: x does not advance; labelling a member jumps to the next group; unlabelled members counted nowhere. [fixed in v5]
9. MISSING no fast path: next undecided, go to unit, one-key accept. [fixed in v5]
10. BUG key auto-repeat on `a` labelled 110 unseen units. Ignore repeats for decisions. [fixed in v5]
11. BUG labelled tiles print the chip twice. [fixed in v5]
12. BUG side-by-side and density silently drop units beyond 4. [fixed in v5]
13. MISSING no pair matrix for 5+ units; small cells with blank space beside. [fixed in v5]
14. POLISH text collisions in rows and tiles. [fixed in v5]
15. POLISH 1440 and zoomed layouts break (4-row action bar, clipped captions, warning overprint). [fixed in v5]
16. DESIGN group rows not on a shared site grid. [fixed in v5]
17. MISSING evidence: correlogram window/bin control, amplitude histogram / all spikes, feature scatter, ISI log axis, rate over time, raw trace, more sites, cross-correlogram asymmetry (Kevin asked). [fixed in v5]
18. DESIGN "+ similar": refs share a grey, drop the matrix, are discarded by shift-click. [fixed in v5]
19. DESIGN all-noise groups listed first-class in the top section. Demote. [fixed in v5]
20. TRUST merged-unit depth differs between page (weighted mean) and export (Phy's rule), up to 19 um. [fixed in v5]
21. DESIGN density scale differs from the mean view; blocky; no count choice. [fixed in v5]
22. DESIGN a merge drops labels. Inherit when all members agree. [fixed in v5]
23. POLISH decided groups still say "Same neuron?". [fixed in v5]
24. DESIGN accept-screen scrolls away at once. [fixed in v5]
25. POLISH cross-group merge shows the merged unit twice; counter mismatch. [fixed in v5]
26. POLISH section headers not sticky; single-unit panel half blank; export 8.8 s with only "exporting...". [fixed in v5]
Verified holding: key ordering, stale-tab refusal, zoom click mapping, depth toggle keeps place, nested merge/undo, export labels and arrays (144 labels, 962 clusters exact).
Top 5 for decisions per minute: full redraw + reselect; one key accept and x advances; j/k through rows inside groups, label advances to the next unlabelled row, nothing changes section; per-pair shoulder-based test + asymmetry note; bigger matrix up to 8x8 and go-to-unit.

Round 3 status (v5). Fixed: all README items; 3E 1-5, 7-12, 14-17, 20 and go-to-unit, section jumps, next-undecided, true remaining
count and finished state, flag toggle; 3F 1-3, 5-8, 10-14, 16, 19, 20, 22, 23, 24 and the cross-correlogram asymmetry note.
Changed approach: 3F#4 verdict is now Kilosort's own cross-refractory test per pair (check_CCG, server side), plus a duplicate-spike
excess test and an asymmetry note in the page. On this session: 117 of 135 Kilosort-proposed pairs are refractory together,
1 of 30 similarity-only pairs is.
Not done: review list of decisions with per-item revert, notes per unit, redo, who-is-curating per browser, sticky section
headers, correlogram window/bin control, amplitude histogram, feature scatter, raw trace, more than 16 sites, 100/1000 spike
counts for the density, one-key "accept verdict", 1440 px action-bar wrapping (3F#15), reference units in distinct colours (3E#18).

## Round 5H: polish at all sizes + throughput, 2026-11-20 (v5)
Verdict: polished at 1900x1100 and 2560x1400; broken at 1440x900 and below or at 130% zoom (also with Windows fonts). Speed is not the limit; reading tiles and groups of 3+ are.
Polish (Windows fonts too): 1 "mixes" warning overprints the verdict chip at narrow widths; 2 top-bar progress loses its links below 1700 px; 3 header line 2 drops different cells per group; 4 header line 1 clipped mid-word; 5-6 table columns collide (transposed scaling; across at 4-5 columns); 7 verdict band overflows; 8 band lists first 6 pairs in index order (sort worst first, "+N more"); 9 correlogram cells tiny beside blank space (make cells rectangular); 10 "similar" refs set the waveform scale; 11 "if merged" row under the ref rows; 12 colour reuse at 10 units, two near-identical greens; 13 wine colour invisible in dark; 14 white on grey chips; 15 row plots unreadable at 1440 (TEXT_W 452 is half the list; drop "KS cont." (in the chip) and the flight column when narrow); 16 action bars 4 rows at 1440; 17 status line changes height; 18 accept scroll wastes a tile row; 19 TILE_MIN at 1280; 20 merged tile clips its chip, `a` sends null label for merged tiles; 21 matrix ticks collide; 22 captions clipped at 1280; 23 "-" vs "n/a"; 24 "1 decisions", "labelled 1005: 1 good", "no unit NaN", "2 Hz" vs "2.2 Hz"; 25 amplitude axis set by one outlier; 26 single-unit panel blank space; 27 help needs two columns.
Throughput (estimates): merge+label 4-6 s; keep+label 5-7 s; partial merge in a 3-5 unit group 18-30 s; uncertain 3-4 s; tiles ~1 s each; session total ~38 min at 1900x1100 (tiles 12-14 min, groups of 3+ 7-8 min, pairs 7 min).
Changes ranked: 1 sort tiles by risk and mark outliers in red; 2 keyboard partial merge (digits toggle rows; stay in the group on the leftover); 3 more compact confirm tiles; 4 one `a` accepts and pages; 5 one key "accept verdict"; 6 order groups by decisiveness; 7 bigger pair correlograms; 8 panel fits at 1440; 9 composite decisions undo in one step; 10 `s` should not rescale; 11 a label inside an open group advances within the group; 12 narrower row text.
Slips: forgetting shift on merge labels a whole group mua + keeps apart (two undos); a repeated label key after merge+label labels the whole next group; stray label after `a`; partial merge leaves leftovers unlabelled; shift-click on the only selected tile empties the selection.

## Round 4G: verification of round 3 + the new verdict + would Kevin still reject, 2026-11-20 (v5)
Verification: round-3 fixes hold (merge redraw, unmerge, undo refocus, fresh start, in-place tile merges and flags, kept-apart flow,
counters and finished state, go-to, e, auto-repeat, chips, matrix 5-8, shared grid, merged depth = export, label inheritance);
no regressions; export exact (965 units, 32 merges, 371 labels). Not fixed: side-by-side/density beyond 4 units; similarity "0.00"
(matrix is zero outside a neighbourhood); cross-group merge shown under two headers; 1440 px layout.
Verdict test: server matches Kilosort's check_CCG on all 165 pairs. But:
1. DESIGN red on untestable pairs and drift splits: 17 of 37 red pairs have centre/shoulder below 0.25 and fail only the significance term; 781+782 is a drift split shown red. Add "too few spikes to test"; show when two units are active at different times. [ ]
2. DESIGN amber ("same spikes") overrides and hides Kilosort's verdict, on as few as 7 spikes. Require an effect size; show as a second chip. [ ]
3. BUG panel lists only 6 pairs. List all, worst first. [ ]
4. DESIGN group chip takes the worst pair; header sums seen/expected. "k of n refractory", no summed numbers. [ ]
5. DESIGN green while the merged unit becomes mua (4 groups). Red text and a chip. [ ]
6. DESIGN chip contradicts the "seen / expected" beside it. Print Kilosort's centre/shoulder ratio. [ ]
7. BUG 1440x900 still broken (links cut, 4-row action bar, warning over chip, table collisions). [ ]
8. DESIGN spikes on flight paths overplot. One small map per unit. [ ]
9. BUG side-by-side and spikes view drop units beyond 4. [ ]
10. POLISH header line 1 clipped without ellipsis. [ ]
11. BUG "B follows A" counts the duplicate bin and tiny asymmetries. Use 1-10 ms and a ratio of at least 1.5. [ ]
12. DESIGN shared scale flattens small members in group rows. Own scale per row. [ ]
13. DESIGN single-spike view coarse; Kevin asked to see spikes. Draw 100 real traces per unit. [ ]
14. DESIGN correcting a label teleports the view. Stay put when the unit already had a label. [ ]
15. BUG partial merge strands the leftover unit. Stay on the group while it holds unlabelled units. [ ]
16. MISSING add a distant unit to a comparison (shift+Enter in go-to). [ ]
17. DESIGN after `a` the selection stays behind. [ ]
18. DESIGN tiles show no stability evidence. [ ]
19. POLISH merged tile chip clipped. [ ]
20. DESIGN one key writes two decisions. One event. [ ]
21. BUG similarity "0.00" printed for far-apart pairs. [ ]
22. POLISH cross-group merge under two headers. Fuse the groups. [ ]
23. POLISH 5-8 unit layout wastes space. [ ]
24. POLISH status wording ("flagged" on un-flag, "1 decisions", "labelled 27: 1 no label", "no unit NaN"). [ ]
25. MISSING j/k through rows inside a group, correlogram window control, amplitude histogram, more sites, review list, sticky headers.
Reviewer's summary: "Closer, but I would still expect a rejection, this time on trust rather than mechanics": make the verdict honest;
make the discriminating evidence usable (flight maps per unit, readable row waveforms, a single-spike view that shows spikes);
fix the 1440 px layout and the two navigation jumps.

## Status after v6, 2026-11-20
Round 4G: fixed 1 (three verdicts; time overlap shown), 2 (shared spikes need 5% of the smaller unit; second chip), 3 (all pairs,
worst first, 8 printed), 4 ("k of n pairs refractory"), 5 (red chip when the merged unit is Kilosort mua), 6 (centre/shoulder ratio
and limit printed), 7 (wrapping top bar, narrower row text, table fits the panel), 8 (one map per unit under the overlay), 9 (side by
side up to 8), 11 (1-10 ms, ratio 1.5), 12 (own scale and scale bar per row), 13 (100 real traces per unit on 16 sites), 14, 15, 16,
17 (`a` moves on to the next unlabelled unit), 20 (one event with `keep`, asked twice), 21, 22 (groups fused by a merge), 24.
Not done: 10 (header line 1 is clipped, no ellipsis), 18 (no stability evidence in tiles), 19, 23, 25.
Round 5H: fixed polish 1-2, 5-11, 12-13 (ten colours, no wine), 15-17, 19, 20 (`a` skips merged tiles without a proposal), 21-22, 24;
changes 2, 4 (in part), 9, 10, 11, 12; slips: whole-group label asked twice, shift-click and digits cannot empty the selection.
Not done: 3-4 (header cells drop by width), 14, 18, 23, 25 (the amplitude axis keeps every spike in range on purpose), 26, 27;
changes 1, 3, 5, 6, 7 (tiles stay in depth order, as asked).

## Round 6: verification of v6, 2026-11-20
Verified working: three verdicts, "k of n" chips, worst-first pair list, shared-spike rule, Kilosort-mua chip, per-unit flight maps,
side by side up to 8, real single-spike traces, digit partial merge, relabel stays put, go-to Shift+Enter, fused groups, accept and
undo chains, stale tab refused, export; no JS errors.
1. MISLEADING "active at different times" wrong for 15 of 33 flagged pairs (a brief unit inside the other's activity). [x] replaced by co-activity (sum over minutes of the product of the per-minute spike shares, times the number of minutes; noted below 0.5)
2. BUG pair lines and header chips clipped. [x] pair lines wrap; header clips at the Unmerge button only when merged
3. MISLEADING "not refractory" from a handful of spikes. [x] seen and expected counts within 1 ms printed for every pair; the colour rule is unchanged
4. BUG density of a merged unit drawn off the grid. [x]
5. BUG twice-press guard fails against key mashing and survives navigation. [x] cleared by every key and click; a second press within 0.6 s of a saved decision does not count
6. BUG captions overprint. [x]
7. Action bars 4 rows at 1440 (smaller buttons below 1500 px [x]); table collisions at 1280 (smaller type in narrow columns [x]); long status prompt (shortened [x]).
8. BUG shift-click leaves the focus behind. [x]
9. POLISH wording (similarity, plural, n/a). [x] Not done: tile scale label over the lower-left trace; small waveforms in 4-unit groups at 1280.
