"""Curation cache of one sort folder: pixelbat-curate prepare SORT --jobs N_JOBS.

Reads the Kilosort output and the binary named in <SORT>/curation/recording.json; writes waveforms, waveform metrics
over repeated spike draws, spike metrics, amplitudes and waveform similarity to <SORT>/curation/cache.
"""
import json
import os
import shutil
import sys
import time
import warnings

import numpy as np
import pandas as pd
import spikeinterface.full as si
from scipy.signal import butter, sosfiltfilt
from spikeinterface.core.sorting_tools import random_spikes_selection
from spikeinterface.core.waveform_tools import estimate_templates_with_accumulator
from spikeinterface.postprocessing.template_similarity import compute_similarity_with_templates_array

from pixelbat.curation.labels import DRAWS
from pixelbat.curation.write_phy import cluster_table
from pixelbat.curation.waveforms import AMPLITUDE_BINS, SITES, TIME_BINS, WINDOW, nearest_sites, waveform_density

t0 = time.time()

## Sort
sort = os.path.normpath(sys.argv[1])
si.set_global_job_kwargs(n_jobs=int(sys.argv[2]), chunk_duration='1s', progress_bar=False, mp_context='fork',
                          max_threads_per_worker=1)
details = json.load(open(os.path.join(sort, 'curation', 'recording.json')))
# Built in a new folder that replaces the cache when complete
cache = os.path.join(sort, 'curation', 'cache.partial')
shutil.rmtree(cache, ignore_errors=True)
os.makedirs(cache)
params = {}
exec(open(os.path.join(sort, 'params.py')).read(), params)

## Spike sign of the largest good units' mean raw waveforms, against the recorded one
spike_times = np.load(os.path.join(sort, 'spike_times.npy')).ravel()
spike_samples = spike_times.astype(np.int64)
spike_clusters = np.load(os.path.join(sort, 'spike_clusters.npy')).ravel()
raw = np.memmap(details['binary'], dtype=params['dtype'], mode='r').reshape(-1, params['n_channels_dat'])
# Three 20 s windows
starts = (len(raw) * np.array([0.25, 0.5, 0.75])).astype(np.int64)
length = 20 * int(params['sample_rate'])
offsets = np.arange(-20, 41)
kilosort_label = pd.read_csv(os.path.join(sort, 'cluster_KSLabel.tsv'), sep='\t').set_index('cluster_id')['KSLabel']
kilosort_amplitude = pd.read_csv(os.path.join(sort, 'cluster_Amplitude.tsv'), sep='\t').set_index('cluster_id')['Amplitude']
window = np.searchsorted(starts, spike_samples, side='right') - 1
in_window = (window >= 0) & (spike_samples + offsets[0] >= starts[window]) & (spike_samples + offsets[-1] < starts[window] + length)
count = pd.Series(spike_clusters[in_window]).value_counts()
eligible = count.index[(count >= 50) & (kilosort_label.reindex(count.index) == 'good').to_numpy()]
voters = np.sort(kilosort_amplitude.loc[eligible].nlargest(12).index.to_numpy())
of_voters = in_window & np.isin(spike_clusters, voters)
sos = butter(3, 300, btype='highpass', fs=params['sample_rate'], output='sos')
waveform_sum = np.zeros((len(voters), len(offsets), params['n_channels_dat']))
for w, start in enumerate(starts):
    highpassed = sosfiltfilt(sos, np.array(raw[start:start + length]).astype(np.float32), axis=0).astype(np.float32)
    here = of_voters & (window == w)
    np.add.at(waveform_sum, np.searchsorted(voters, spike_clusters[here]), highpassed[(spike_samples[here] - start)[:, None] + offsets])
waveform = waveform_sum / count.loc[voters].to_numpy()[:, None, None]
on_peak = waveform[np.arange(len(voters)), :, np.ptp(waveform, axis=1).argmax(axis=1)]
deflection = on_peak[np.arange(len(voters)), np.abs(on_peak).argmax(axis=1)]
n_positive = int(np.sum(deflection > 0))
print(f'spike sign: {n_positive} of {len(voters)} largest good units positive-going in the raw binary', flush=True)
assert (n_positive > len(voters) / 2) == details['spikes_positive'], 'spike sign of the sorted units disagrees with recording.json'

## Recording with negative-going spikes, in uV, high-passed, bad channels interpolated, median-referenced
channel_map = np.load(os.path.join(sort, 'channel_map.npy')).ravel()
channel_xy = np.load(os.path.join(sort, 'channel_positions.npy'))
channel_shank = np.load(os.path.join(sort, 'channel_shanks.npy')).ravel()
recording = si.read_binary(details['binary'], sampling_frequency=params['sample_rate'], dtype=params['dtype'],
                           num_channels=params['n_channels_dat'])
recording = recording.select_channels(recording.channel_ids[channel_map])
recording.set_channel_locations(channel_xy)
recording = si.scale(recording, gain=details['gain_uV'] * (-1 if details['spikes_positive'] else 1), dtype='float32')
recording.set_channel_gains(1.0)
recording.set_channel_offsets(0.0)
recording = si.highpass_filter(recording, freq_min=300.0)
bad_channels, _ = si.detect_bad_channels(recording, seed=0)
recording = si.interpolate_bad_channels(recording, bad_channels)
recording = si.common_reference(recording, reference='global', operator='median')
print(f'{len(bad_channels)} bad channels interpolated: {list(bad_channels)}', flush=True)
sorting = si.read_kilosort(sort, keep_good_only=False)
analyzer = si.create_sorting_analyzer(sorting, recording, sparse=True, format='memory')

## Waveform metrics on each spike draw
# First draw: SpikeInterface's own extraction; its waveforms are also the ones displayed
analyzer.compute('random_spikes', method='uniform', max_spikes_per_unit=500, seed=0)
analyzer.compute('waveforms', ms_before=3.0, ms_after=3.0)
analyzer.compute('templates', operators=['average'])
# The waveform as recorded, for the non-somatic tag (positive-going spikes are what it detects)
analyzer.compute('template_metrics', include_multi_channel_metrics=True)
analyzer.get_extension('template_metrics').get_data().to_csv(os.path.join(cache, 'shape_as_recorded.csv'))
# Positive-going units (largest deflection on their peak channel positive): every draw's shape metrics on the
# sign-flipped waveform, since Bombcell's trough-to-peak and peak counts assume a negative-going spike
templates_extension = analyzer.get_extension('templates')
first_draw_means = templates_extension.data['average']
peak_trace = first_draw_means[np.arange(len(first_draw_means)), :, np.abs(first_draw_means).max(axis=1).argmax(axis=1)]
positive = peak_trace.max(axis=1) > -peak_trace.min(axis=1)
flip = np.where(positive, -1.0, 1.0)[:, None, None].astype(first_draw_means.dtype)
print(f'{int(positive.sum())} of {len(positive)} units positive-going: shape metrics on the flipped waveform', flush=True)
templates_extension.data['average'] = first_draw_means * flip
analyzer.compute('template_metrics', include_multi_channel_metrics=True)
analyzer.get_extension('template_metrics').get_data().to_csv(os.path.join(cache, 'shape_draw0.csv'))
print(f'draw 0: {time.time() - t0:.0f} s', flush=True)
# Other draws: their mean waveforms in one more pass over the recording (each unit and draw as one unit), then each
# draw's means set as the templates the metrics are computed from
n_units = len(sorting.unit_ids)
spike_vector = sorting.to_spike_vector()
drawn = []
for draw in range(1, DRAWS):
    chosen = spike_vector[random_spikes_selection(sorting, [recording.get_num_samples()], method='uniform',
                                                  max_spikes_per_unit=500, seed=draw)]
    chosen['unit_index'] += (draw - 1) * n_units
    drawn.append(chosen)
drawn = np.concatenate(drawn)
drawn = drawn[np.argsort(drawn['sample_index'], kind='stable')]
waveforms_extension = analyzer.get_extension('waveforms')
draw_means = estimate_templates_with_accumulator(recording, drawn, np.arange(n_units * (DRAWS - 1)), waveforms_extension.nbefore,
                                                 waveforms_extension.nafter, return_in_uV=True)
for draw in range(1, DRAWS):
    templates_extension.data['average'] = draw_means[(draw - 1) * n_units:draw * n_units] * analyzer.sparsity.mask[:, None, :] * flip
    analyzer.compute('template_metrics', include_multi_channel_metrics=True)
    analyzer.get_extension('template_metrics').get_data().to_csv(os.path.join(cache, f'shape_draw{draw}.csv'))
templates_extension.data['average'] = first_draw_means
print(f'draws 1-{DRAWS - 1}: {time.time() - t0:.0f} s', flush=True)

## Display waveforms of the first draw: mean and single-spike density on the sites nearest the peak site
display_sites = np.full((n_units, SITES), -1)
display_mean = np.zeros((n_units, WINDOW.stop - WINDOW.start, SITES), dtype=np.float32)
display_density = np.zeros((n_units, SITES, TIME_BINS, AMPLITUDE_BINS), dtype=np.uint8)
display_range = np.zeros(n_units, dtype=np.float32)
display_count = np.zeros(n_units, dtype=np.int32)
display_spikes = np.zeros((n_units, 100, WINDOW.stop - WINDOW.start, SITES), dtype=np.int16)
for i, unit in enumerate(sorting.unit_ids):
    waveforms = analyzer.get_extension('waveforms').get_waveforms_one_unit(unit)[:, WINDOW]
    sites = analyzer.sparsity.unit_id_to_channel_indices[unit]
    mean = waveforms.mean(axis=0)
    shown = nearest_sites(channel_xy, np.arange(len(sites)), np.ptp(mean, axis=0).argmax())
    display_sites[i, :len(shown)] = sites[shown]
    display_mean[i, :, :len(shown)] = mean[:, shown]
    display_range[i] = 1.5 * np.abs(mean).max()
    display_density[i, :len(shown)] = waveform_density(waveforms[:, :, shown], display_range[i])
    display_count[i] = len(waveforms)
    # Every fifth spike of the draw, up to 100, as single traces
    single = waveforms[::5][:100][:, :, shown]
    display_spikes[i, :len(single), :, :len(shown)] = np.round(single)
np.save(os.path.join(cache, 'display_sites.npy'), display_sites)
np.save(os.path.join(cache, 'display_mean.npy'), display_mean)
np.save(os.path.join(cache, 'display_density.npy'), display_density)
np.save(os.path.join(cache, 'display_range.npy'), display_range)
np.save(os.path.join(cache, 'display_count.npy'), display_count)
np.save(os.path.join(cache, 'display_spikes.npy'), display_spikes)

## Spike metrics
analyzer.compute('noise_levels', random_slices_kwargs={'seed': 0})
analyzer.compute('spike_amplitudes', peak_sign='both')
# SpikeInterface reports a failed metric as a warning and leaves it empty: make that fatal
warnings.filterwarnings('error', message='Error computing metric')
analyzer.compute('quality_metrics', metric_names=['amplitude_median', 'snr', 'num_spikes', 'presence_ratio', 'firing_rate'],
                 metric_params={'presence_ratio': {'bin_duration_s': 60}})
units = analyzer.get_extension('quality_metrics').get_data()

## Kilosort's labels; peak channel, depth and shank as Phy gives them
place = cluster_table(spike_times, spike_clusters, np.load(os.path.join(sort, 'spike_templates.npy')).ravel(),
                      np.load(os.path.join(sort, 'templates.npy')), np.load(os.path.join(sort, 'whitening_mat_inv.npy')),
                      channel_map, channel_xy, channel_shank, recording.get_num_samples() / params['sample_rate'])
units[['ch', 'depth', 'sh']] = place.loc[units.index, ['ch', 'depth', 'sh']]
templates = analyzer.get_extension('templates').get_data()
for column, file in [('KSLabel', 'cluster_KSLabel.tsv'), ('ContamPct', 'cluster_ContamPct.tsv'),
                     ('Amplitude', 'cluster_Amplitude.tsv')]:
    table = pd.read_csv(os.path.join(sort, file), sep='\t').set_index('cluster_id')
    units[column] = table.iloc[:, 0].reindex(units.index).to_numpy()
units.index.name = 'cluster_id'
units.to_csv(os.path.join(cache, 'units.csv'))

## Per-unit arrays: mean waveform on every channel, amplitude sample
amplitudes = analyzer.get_extension('spike_amplitudes').get_data(outputs='by_unit')[0]
amplitude_sample = np.full((len(units), 400, 2), np.nan, dtype=np.float32)
for i, unit in enumerate(units.index):
    in_unit = np.flatnonzero(spike_clusters == unit)
    seconds = spike_times[in_unit] / params['sample_rate']
    shown = np.sort(np.random.default_rng([unit, 0]).choice(len(in_unit), min(400, len(in_unit)), replace=False))
    amplitude_sample[i, :len(shown), 0] = seconds[shown]
    amplitude_sample[i, :len(shown), 1] = amplitudes[unit][shown]
np.save(os.path.join(cache, 'templates.npy'), templates.astype(np.float32))
np.save(os.path.join(cache, 'amplitude_sample.npy'), amplitude_sample)
# Waveform similarity: cosine over shifts up to 0.5 ms. SpikeInterface searches each pair at shifts of one sign only
# (it copies each shift's value to the transposed pair), so the units in reverse order give the other sign.
mask, shifts = analyzer.sparsity.mask, int(0.5e-3 * params['sample_rate'])
forward, _ = compute_similarity_with_templates_array(templates, templates, 'cosine', 'union', shifts, mask, mask)
backward, _ = compute_similarity_with_templates_array(templates[::-1], templates[::-1], 'cosine', 'union', shifts, mask[::-1], mask[::-1])
np.save(os.path.join(cache, 'similarity.npy'), np.maximum(forward, backward[::-1, ::-1]).astype(np.float32))
with open(os.path.join(cache, 'recording.json'), 'w') as f:
    json.dump({'n_samples': recording.get_num_samples(), 'rate_hz': params['sample_rate'],
               'bad_channels': [int(c) for c in bad_channels]}, f)
np.save(os.path.join(cache, 'channel_positions.npy'), channel_xy)

shutil.rmtree(os.path.join(sort, 'curation', 'cache'), ignore_errors=True)
os.replace(cache, os.path.join(sort, 'curation', 'cache'))
print(f'{sort}: {len(units)} units; {time.time() - t0:.0f} s')
