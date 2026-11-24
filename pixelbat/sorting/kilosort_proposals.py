"""Kilosort 4 without its final merge, with the merges it would have made saved as proposals."""
import json
import os

import numpy as np
from kilosort import template_matching

original_merging_function = template_matching.merging_function


def propose_final_merges(results_dir):
    """Patch Kilosort 4.1.7 so its final merge only writes proposed_merges.json (groups of unit ids) to results_dir."""

    def merging_function(ops, Wall, clu, st, tF, r_thresh=0.5, mode='ccg', check_dt=True, **kwargs):
        if mode != 'ccg':
            return original_merging_function(ops, Wall, clu, st, tF, r_thresh=r_thresh, mode=mode, check_dt=check_dt, **kwargs)
        # The default merge on copies; it returns spikes re-sorted, so a last column carries each spike's place
        indexed = np.c_[st, np.arange(len(st))]
        result = original_merging_function(ops, Wall.clone(), clu.copy(), indexed, tF.clone(), r_thresh=r_thresh,
                                           mode=mode, check_dt=check_dt, **kwargs)
        merged = np.empty_like(result[1])
        merged[result[3][:, -1].astype(np.int64)] = result[1]
        pairs = np.unique(np.c_[merged, clu], axis=0)
        groups = [pairs[pairs[:, 0] == after, 1].tolist() for after in np.unique(merged)]
        units, counts = np.unique(clu, return_counts=True)
        with open(os.path.join(results_dir, 'proposed_merges.json'), 'w') as f:
            json.dump({'groups': [g for g in groups if len(g) > 1], 'r_thresh': r_thresh,
                       'spikes_per_unit': dict(zip(units.tolist(), counts.tolist()))}, f)
        # No merge
        return original_merging_function(ops, Wall, clu, st, tF, r_thresh=float('inf'), mode=mode, check_dt=check_dt, **kwargs)

    template_matching.merging_function = merging_function
