"""Compare two preparations of a session: units_table_compare.py CACHE_A CACHE_B.

Prints how many units differ in each saved metric, in the Bombcell label of each spike draw and in being uncertain.
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
from pixelbat.curation.labels import DRAWS, bombcell_labels

thresholds = json.load(open(os.path.join(HERE, '..', 'thresholds.json')))
labels = []
for cache in sys.argv[1:3]:
    units = pd.read_csv(os.path.join(cache, 'units.csv'), index_col='cluster_id')
    units['ks_good'] = (units['KSLabel'] == 'good').astype(int)
    draws = pd.DataFrame({draw: bombcell_labels(units, pd.read_csv(os.path.join(cache, f'shape_draw{draw}.csv'), index_col=0), thresholds)
                          for draw in range(DRAWS)}, index=units.index)
    labels.append((units, draws))
(units_a, draws_a), (units_b, draws_b) = labels
print(f'{len(units_a)}/{len(units_b)} units')
for column in units_a.columns:
    same = (units_a[column] == units_b[column]) | (units_a[column].isna() & units_b[column].isna())
    print(f'{column}: {(~same).sum()} units differ')
snr_ratio = units_b['snr'] / units_a['snr']
print(f'snr ratio B/A: {snr_ratio.min():.4f} to {snr_ratio.max():.4f}')
for draw in range(DRAWS):
    print(f'label of draw {draw}: {(draws_a[draw] != draws_b[draw]).sum()} units differ')
flips_a, flips_b = draws_a.nunique(axis=1) > 1, draws_b.nunique(axis=1) > 1
print(f'uncertain: {flips_a.sum()} and {flips_b.sum()} units, {(flips_a & flips_b).sum()} in both')
print(pd.crosstab(draws_a[0], draws_b[0]))
