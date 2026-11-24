"""Proposed merges of an unmerged sort: group sizes, and whether proposal unit ids are the sort's final unit ids: proposals_check.py SORT."""
import json
import sys

import numpy as np

proposals = json.load(open(f'{sys.argv[1]}/proposed_merges.json'))
clusters = np.load(f'{sys.argv[1]}/spike_clusters.npy').ravel()
units, counts = np.unique(clusters, return_counts=True)
before = {int(u): n for u, n in proposals['spikes_per_unit'].items()}
sizes = np.bincount([len(g) for g in proposals['groups']])
print(f'{len(proposals["groups"])} proposed groups joining {sum(len(g) for g in proposals["groups"])} units; '
      f'groups by size: {dict((s, int(n)) for s, n in enumerate(sizes) if n)}')
print(f'units at the merge step {len(before)}, in the final sort {len(units)}; same ids: {set(before) == set(units.tolist())}')
ratio = np.array([counts[units == u][0] / before[int(u)] for u in units if int(u) in before])
print(f'final / merge-step spike count per unit: min {ratio.min():.3f}, median {np.median(ratio):.3f}, max {ratio.max():.3f}')
