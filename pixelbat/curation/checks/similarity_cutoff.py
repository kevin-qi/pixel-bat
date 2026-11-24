"""Merge-group sizes by waveform-similarity cutoff for one prepared session: similarity_cutoff.py CACHE."""
import sys

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components

similarity = np.load(f'{sys.argv[1]}/similarity.npy')
units = pd.read_csv(f'{sys.argv[1]}/units.csv', index_col='cluster_id')
neuron = ~units['bombcell_draw0'].isin(['noise', 'non_soma']).to_numpy()
print(f'{len(units)} units, {neuron.sum()} not proposed noise or non-somatic')
pairs = similarity[np.triu_indices(len(units), 1)]
both = np.outer(neuron, neuron)[np.triu_indices(len(units), 1)]
for cutoff in [0.8, 0.85, 0.9, 0.95, 0.97, 0.99]:
    linked = (similarity > cutoff) & np.outer(neuron, neuron)
    n_groups, group_of = connected_components(linked, directed=False)
    sizes = np.bincount(group_of)
    sizes = sizes[sizes > 1]
    print(f'cutoff {cutoff}: {int((pairs > cutoff).sum())} pairs among all units, {int(((pairs > cutoff) & both).sum())} among neurons; '
          f'groups of neurons: {len(sizes)}, units in them {sizes.sum()}, largest {sizes.max() if len(sizes) else 0}')
