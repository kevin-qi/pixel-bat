"""cluster_table against the cluster_info.tsv Phy wrote for a Phy-curated sort: phy_table_check.py PHY_FOLDER."""
import os
import sys

import numpy as np
import pandas as pd

from pixelbat.curation.write_phy import cluster_table

sort = sys.argv[1]
params = {}
exec(open(os.path.join(sort, 'params.py')).read(), params)
ours = cluster_table(np.load(f'{sort}/spike_times.npy').ravel(), np.load(f'{sort}/spike_clusters.npy').ravel(),
                     np.load(f'{sort}/spike_templates.npy').ravel(), np.load(f'{sort}/templates.npy'), np.load(f'{sort}/whitening_mat_inv.npy'),
                     np.load(f'{sort}/channel_map.npy').ravel(), np.load(f'{sort}/channel_positions.npy'),
                     np.zeros(len(np.load(f'{sort}/channel_map.npy').ravel()), dtype=int),  # this sort has one shank
                     np.load(f'{sort}/spike_times.npy').ravel()[-1] / params['sample_rate'])
phy = pd.read_csv(f'{sort}/cluster_info.tsv', sep='\t').set_index('cluster_id')
both = ours.join(phy, lsuffix='_ours', rsuffix='_phy', how='outer')
print(f'{len(ours)} clusters ours, {len(phy)} Phy, {len(both)} in the union')
for column in ['n_spikes', 'ch', 'depth', 'sh']:
    same = both[f'{column}_ours'] == both[f'{column}_phy']
    print(f'{column}: identical for {same.sum()}/{len(both)}')
print(f'fr: max relative difference {np.max(np.abs(both["fr_ours"] / both["fr_phy"] - 1)):.2e}')
off = both[both['ch_ours'] != both['ch_phy']]
print('channel differences (ours - Phy):', (off['ch_ours'] - off['ch_phy']).value_counts().head(8).to_dict())
