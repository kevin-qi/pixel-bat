"""Can the waveform metrics of several spike draws come from one waveform extraction? Test on 3 minutes of a session.

Sets the templates extension's average to the mean of a subset of the extracted waveforms and recomputes template_metrics;
checks that (a) the full set reproduces SpikeInterface's own metrics exactly, (b) a subset gives different numbers.
"""
import os
import sys

import numpy as np
import pandas as pd
import spikeinterface.full as si

sessions = pd.read_csv(sys.argv[1], dtype=str).set_index('name')
session = sessions.loc[sys.argv[2]]
params = {}
exec(open(os.path.join(session['sort'], 'params.py')).read(), params)
si.set_global_job_kwargs(n_jobs=8, chunk_duration='1s', progress_bar=False, mp_context='fork', max_threads_per_worker=1)
channel_xy = np.load(os.path.join(session['sort'], 'channel_positions.npy'))
recording = si.read_binary(session['recording'], sampling_frequency=params['sample_rate'], dtype=params['dtype'],
                           num_channels=params['n_channels_dat'])
recording.set_channel_locations(channel_xy)
recording = si.scale(recording, gain=-float(session['gain_uV']), dtype='float32')
recording.set_channel_gains(1.0)
recording.set_channel_offsets(0.0)
recording = si.common_reference(si.highpass_filter(recording, freq_min=300.0), reference='global', operator='median')
recording = recording.frame_slice(0, 180 * 30000)
sorting = si.read_kilosort(session['sort'], keep_good_only=False).frame_slice(0, 180 * 30000)
counts = sorting.count_num_spikes_per_unit()
sorting = sorting.select_units([u for u in sorting.unit_ids if counts[u] >= 200][:40])
analyzer = si.create_sorting_analyzer(sorting, recording, sparse=True, format='memory')
analyzer.compute('random_spikes', method='uniform', max_spikes_per_unit=200, seed=0)
analyzer.compute('waveforms', ms_before=3.0, ms_after=3.0)
analyzer.compute('templates', operators=['average'])
analyzer.compute('template_metrics', include_multi_channel_metrics=True)
own = analyzer.get_extension('template_metrics').get_data().copy()

templates = analyzer.get_extension('templates')
print('templates extension data:', {k: v.shape for k, v in templates.data.items()})
waveforms = analyzer.get_extension('waveforms')


def subset_templates(step, offset):
    """Dense templates from every `step`-th extracted waveform of each unit, starting at `offset`."""
    out = np.zeros_like(templates.data['average'])
    for i, unit in enumerate(analyzer.unit_ids):
        sites = analyzer.sparsity.unit_id_to_channel_indices[unit]
        out[i][:, sites] = waveforms.get_waveforms_one_unit(unit)[offset::step].mean(axis=0)
    return out


full = subset_templates(1, 0)
print('mean of all extracted waveforms vs the extension: max |difference|', np.abs(full - templates.data['average']).max())
templates.data['average'] = full
analyzer.compute('template_metrics', include_multi_channel_metrics=True)
again = analyzer.get_extension('template_metrics').get_data()
print('metrics from injected full templates equal SpikeInterface\'s own:', bool(np.allclose(again.to_numpy(float), own.to_numpy(float), equal_nan=True, rtol=1e-5, atol=0)))
templates.data['average'] = subset_templates(2, 0)
analyzer.compute('template_metrics', include_multi_channel_metrics=True)
half = analyzer.get_extension('template_metrics').get_data()
changed = ~np.isclose(half.to_numpy(float), own.to_numpy(float), equal_nan=True, rtol=1e-5, atol=0)
print(f'metrics from every second waveform differ in {changed.sum()} of {changed.size} values (they must: the injection is used)')
