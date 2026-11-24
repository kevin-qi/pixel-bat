"""One-off for a cache prepared with zero-lag similarity: waveform similarity allowing +-0.5 ms shifts, as prepare.py now computes: similarity_with_lag.py CACHE."""
import sys
import time

import numpy as np
from spikeinterface.postprocessing.template_similarity import compute_similarity_with_templates_array

cache = sys.argv[1]
t0 = time.time()
templates = np.load(f'{cache}/templates.npy')
mask = np.ptp(templates, axis=1) > 0
similarity, _ = compute_similarity_with_templates_array(templates, templates, method='cosine', support='union', num_shifts=15,
                                                        sparsity=mask, other_sparsity=mask)
old = np.load(f'{cache}/similarity.npy')
np.save(f'{cache}/similarity_zero_lag.npy', old)
np.save(f'{cache}/similarity.npy', similarity.astype(np.float32))
pairs = np.triu_indices(len(old), 1)
print(f'{len(old)} units, {time.time() - t0:.0f} s; pairs above 0.95: {int((old[pairs] > 0.95).sum())} at zero lag, '
      f'{int((similarity[pairs] > 0.95).sum())} with lags; above 0.9: {int((old[pairs] > 0.9).sum())} -> {int((similarity[pairs] > 0.9).sum())}')
