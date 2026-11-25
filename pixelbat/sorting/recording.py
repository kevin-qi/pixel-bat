"""What a sort folder records about the binary it was sorted from: <sort>/curation/recording.json."""
import json
import os
import re

import numpy as np
import spikeinterface.full as si
from spikeinterface.sortingcomponents.peak_detection import detect_peaks


def trodes_gain_uv(binary):
    """Microvolts per bit of a binary exported by Trodes: spikeScalingToUv in the header of its .rec file."""
    export = os.path.dirname(binary)
    rec = os.path.join(os.path.dirname(export), os.path.basename(export).removesuffix('.kilosort') + '.rec')
    with open(rec, 'rb') as f:
        header = f.read(4_000_000).decode('latin-1')
    [gain] = set(re.findall(r'spikeScalingToUv="([^"]*)"', header))
    return float(gain)


def peak_signs(binary, n_channels, sample_rate):
    """Positive and negative peaks beyond 5 x noise in three 20 s stretches of an int16 binary, high-passed at 300 Hz
    with the median over channels subtracted."""
    recording = si.read_binary(binary, sampling_frequency=sample_rate, dtype='int16', num_channels=n_channels)
    n_samples = recording.get_num_samples()
    starts = [int(fraction * n_samples) for fraction in (0.25, 0.5, 0.75)]
    stretches = [recording.frame_slice(start, start + 20 * int(sample_rate)) for start in starts]
    recording = si.concatenate_recordings(stretches)
    recording = si.highpass_filter(recording, freq_min=300.0)
    recording = si.common_reference(recording, reference='global', operator='median')
    peaks = detect_peaks(recording, method='by_channel', method_kwargs={'peak_sign': 'both', 'detect_threshold': 5,
                                                                        'random_slices_kwargs': {'seed': 0}},
                         job_kwargs={'n_jobs': 1, 'progress_bar': False})
    return int(np.sum(peaks['amplitude'] > 0)), int(np.sum(peaks['amplitude'] < 0))


def write_recording(sort, binary, gain_uv, spikes_positive):
    """recording.json of a sort folder."""
    os.makedirs(os.path.join(sort, 'curation'), exist_ok=True)
    with open(os.path.join(sort, 'curation', 'recording.json'), 'w') as f:
        json.dump({'binary': binary, 'gain_uV': gain_uv, 'spikes_positive': spikes_positive}, f, indent=1)
