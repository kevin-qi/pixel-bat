"""Kilosort 4 sort of one recording for curation: units left unmerged, the final merge saved as proposals."""
import json
import os
import time

import kilosort
import numpy as np
import torch
from kilosort import DEFAULT_SETTINGS, run_kilosort

from pixelbat.sorting.kilosort_proposals import propose_final_merges
from pixelbat.sorting.probe import trodes_probe


def sort_kilosort4(binary, coordinates, masked_channels, spikes_positive, settings, device, out):
    """Kilosort 4 folder in out, plus proposed_merges.json and sort_unmerged.json; skipped when sort_unmerged.json exists."""
    if os.path.exists(os.path.join(out, 'sort_unmerged.json')):
        print(f'{out}: already sorted')
        return
    t0 = time.time()
    os.makedirs(out)
    propose_final_merges(out)

    ## Probe: every channel of the binary but the masked ones
    sites = trodes_probe(coordinates)
    kept = ~np.isin(sites['chanMap'], masked_channels)
    probe = {name: sites[name][kept] for name in ['chanMap', 'xc', 'yc', 'kcoords']}
    probe['n_chan'] = int(kept.sum())

    ## Sort; Kilosort expects negative-going spikes
    settings = {**DEFAULT_SETTINGS, **settings, 'n_chan_bin': sites['n_chan']}
    run_kilosort(settings=settings, probe=probe, filename=binary, results_dir=out, data_dtype='int16',
                 invert_sign=spikes_positive, save_preprocessed_copy=False, device=torch.device(device))
    with open(os.path.join(out, 'sort_unmerged.json'), 'w') as f:
        json.dump({'binary': binary, 'coordinates': coordinates, 'masked_channels': list(masked_channels),
                   'spikes_positive': spikes_positive, 'settings': settings, 'final_merge': 'proposed, not applied',
                   'kilosort': kilosort.__version__, 'torch': torch.__version__, 'elapsed_s': time.time() - t0},
                  f, indent=1, default=str)
    print(f'SORT_DONE {out} in {time.time() - t0:.0f} s')
