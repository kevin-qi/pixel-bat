"""Do the pre-merge units of a recorded Kilosort4 final merge match the units of a separate final-merge-off sort? map_merge_record.py RECORD_NPZ SORT."""
import sys

import numpy as np
import pandas as pd

record = np.load(sys.argv[1])
times = np.load(f'{sys.argv[2]}/spike_times.npy').ravel()
clusters = np.load(f'{sys.argv[2]}/spike_clusters.npy').ravel()
print(f'record: {len(record["samples_before"])} spikes, {len(np.unique(record["clu_before"]))} units before, '
      f'{len(np.unique(record["clu_after"]))} after; sort: {len(times)} spikes, {len(np.unique(clusters))} units')

## Spikes at the same sample in both
pairs = pd.merge(pd.DataFrame({'sample': record['samples_before'], 'before': record['clu_before']}),
                 pd.DataFrame({'sample': times, 'unit': clusters}), on='sample')
overlap = pairs.groupby(['before', 'unit']).size().rename('shared').reset_index()
overlap['share_of_before'] = overlap['shared'] / overlap['before'].map(pd.Series(record['clu_before']).value_counts())
overlap['share_of_unit'] = overlap['shared'] / overlap['unit'].map(pd.Series(clusters).value_counts())
best = overlap.sort_values('shared', ascending=False).drop_duplicates('before')
both = np.minimum(best['share_of_before'], best['share_of_unit'])
print('best-match share (min of both directions) per pre-merge unit, quantiles 0.05/0.25/0.5/0.75:',
      both.quantile([0.05, 0.25, 0.5, 0.75]).round(3).tolist())
print(f'pre-merge units matched one-to-one at >= 0.95: {(both >= 0.95).sum()}/{len(best)}; at >= 0.8: {(both >= 0.8).sum()}')

## Recorded merge groups whose members all match
merged_units = pd.DataFrame({'before': record['clu_before'], 'after': record['clu_after']}).drop_duplicates()
groups = merged_units.groupby('after')['before'].apply(list)
groups = groups[groups.map(len) > 1]
good = best.set_index('before').assign(both=both.to_numpy())['both']
print(f'{len(groups)} recorded merge groups; every member matched at >= 0.95 in {sum(all(good.get(b, 0) >= 0.95 for b in g) for g in groups)}')
