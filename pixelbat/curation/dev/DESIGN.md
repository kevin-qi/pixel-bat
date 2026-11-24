# Curation tool: design brief

What the tool must do, from Kevin's requirements (2026-11-20). Reviewers judge the page against this.

## Purpose
Replace Phy for curating Kilosort sorts of Neuropixels recordings in the lab. One page per session, in a browser,
served by a local Python server from a prepared cache. Output is a Phy-format folder the dataset loaders read.

## Hard requirements
1. **Instant.** Every unit of the session is loaded up front. Selecting, comparing or scrolling never waits on a
   per-unit load (Phy's main failing). Target: any view change under 100 ms; a decision under 300 ms.
2. **Overview first.** Maximum time looking at units, minimum time navigating. The list is ordered by how much each
   item needs the curator: merge groups, then uncertain units, then units proposed good / mua / noise that are
   confirmed in batches.
3. **Nothing disappears.** A decision never removes a row. A labelled unit stays in place, shaded by label (green
   good; grey mua or noise). A merge turns the group's rows into one row in place, clearly marked as merged, with an
   unmerge button. Merging and labelling are independent operations.
4. **Selection is obvious and single-step.** Clicking a merge group selects all its units and fills the comparison.
   Click selects; shift-click adds or removes. No decision can land on units other than the ones shown as selected
   (decisions are applied strictly in order; a key pressed while one is saving waits for it).
5. **Comparison of any set of units:** waveforms overlaid or side by side on one shared channel set; correlogram
   matrix (autocorrelograms on the diagonal, cross-correlograms off it); spikes on position per flight cluster,
   coloured by unit; the statistics of the units as if merged.
6. **Single spikes, not only means.** Show the spread of individual spike waveforms (up to 500 per unit) fast, as a
   compact density image or a small sample, never by shipping gigabytes.
7. **Metrics a spike sorter asks for,** in readable type: spike count, firing rate, amplitude (uV), signal-to-noise,
   presence ratio, percent of inter-spike intervals under 1 ms (with the count), Kilosort contamination and label,
   waveform duration, depth, Bombcell label and which test set it. For two or more selected units: the same after
   merging (duplicates removed by Kilosort's rule), plus coincident spikes between the units against chance.
8. **Merge proposals are Kilosort4's own would-be final merges** (sort run with the merge left undone), plus
   similar-waveform groups. Nothing is merged until the curator decides.
9. **Spikes on position are optional** (flight-room sessions): top-down view per flight cluster from 2 up.
10. **Output:** new Phy-format folder (never writes into the Kilosort folder); labels and merges only, no split.
11. **Lab tool:** runs on each user's machine (WSL2 or Linux), no hard-coded paths, simple, few files, no framework.
12. **Legible:** no tiny fonts; dark mode; colours consistent (unit colours in comparisons, label colours fixed).

## Known failings of the first version (to fix)
- Keys pressed during a pending save acted on stale selection (a label landed on pre-merge units).
- Rows vanished or moved on decisions; merged units jumped to another section.
- Group click did not select the group; labels inside groups did nothing.
- Numbers drawn at 11 px; too little shown per unit; no post-merge statistics.
- Each unit drawn on its own 12 largest channels, so compared units looked like they sat on different channels.
- Only mean waveforms.
- The comparison panel fetched from the server on every selection.

## Files
prepare.py (cache), server.py, index.html (page), state.py, labels.py, correlograms.py, flight_room.py, write_phy.py,
kilosort_proposals.py + sort_unmerged.py (sort recipe), checks/ (verification scripts, browser_test.py).
