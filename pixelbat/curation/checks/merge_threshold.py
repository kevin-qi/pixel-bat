"""Blind merge verdicts against Kilosort's template similarity: merge_threshold.py REVIEW_DIR VERDICTS_DIR.

Per similarity bin, how many reviewed pairs were judged merge, keep apart or unsure; and for each candidate threshold,
the wrong merges it would still make and the right merges it would skip.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

review, verdicts_dir = sys.argv[1:3]
similarity = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(review, 'similarity', '*.csv')))])
similarity['card'] = similarity['session'] + '_' + similarity['a'].astype(str) + '_' + similarity['b'].astype(str) + '.png'
rows = []
for path in sorted(glob.glob(os.path.join(verdicts_dir, '*.json'))):
    judge = os.path.basename(path).split('_')[-1].removesuffix('.json')
    rows += [{**verdict, 'judge': judge} for verdict in json.load(open(path))]
verdicts = pd.DataFrame(rows).merge(similarity, on='card', validate='many_to_one')
print(f'{verdicts["card"].nunique()}/{len(similarity)} pairs reviewed, {verdicts["session"].nunique()} sessions, judges {sorted(verdicts["judge"].unique())}')

## Verdicts of the first judge per similarity bin (a second judge on some sessions measures agreement only)
all_verdicts = verdicts
verdicts = verdicts[verdicts['judge'] == 'judgeA'].copy()
verdicts['bin'] = pd.cut(verdicts['ks_similarity'], [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], right=False)
print(pd.crosstab(verdicts['bin'], verdicts['verdict'], margins=True).to_string())

## Each threshold: pairs at or above it that Kilosort would merge
decided = verdicts[verdicts['ks_similarity'] >= 0.5]
for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
    above = decided[decided['ks_similarity'] >= threshold]
    below = decided[decided['ks_similarity'] < threshold]
    print(f'threshold {threshold}: merges {len(above)} pairs, of which keep_apart {(above["verdict"] == "keep_apart").sum()}, '
          f'unsure {(above["verdict"] == "unsure").sum()}; skips {(below["verdict"] == "merge").sum()} pairs judged merge')

## Agreement between judges on pairs both reviewed
wide = all_verdicts.pivot_table(index='card', columns='judge', values='verdict', aggfunc='first').dropna()
if wide.shape[1] > 1:
    first, second = wide.columns[:2]
    print(f'{len(wide)} pairs with two judges: same verdict on {(wide[first] == wide[second]).sum()}')
    print(pd.crosstab(wide[first], wide[second]).to_string())
all_verdicts.to_csv(os.path.join(review, 'verdicts_with_similarity.csv'), index=False)
