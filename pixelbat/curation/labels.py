"""Bombcell label per unit from saved metrics and thresholds.json, Llobet refractory contamination, and the notch and
hand-off of two spike trains."""
import numpy as np
import pandas as pd
from bombcell.default_parameters import get_default_parameters
from bombcell.quality_metrics import sliding_rp_violations
from spikeinterface.curation import bombcell_label_units

DRAWS = 5  # independent draws of 500 spikes for the waveform metrics
MAX_CONTAMINATION = 0.2  # foreign spikes of a good unit
HANDOFF = 0.4  # hand-off of a possible drift split


def llobet_parameters(sort):
    """Bombcell's Kilosort 4 parameters with Llobet's method: refractory period swept 1-10 ms, duplicate window censored."""
    return dict(get_default_parameters(sort, kilosort_version=4), rpv_method='llobet')


def llobet_contamination(seconds, duration, parameters):
    """Llobet contamination of one spike train and the refractory period that gives it (the lowest over the sweep)."""
    contamination, tau_r, _ = sliding_rp_violations(seconds, np.array([0, duration]), parameters)
    return contamination, tau_r


def foreign_spikes(samples, rate_hz):
    """Spike pairs of one train 0.25 to 1.25 ms apart, the number predicted there by the larger of its own rates 10 to 50 ms
    and 250 to 500 ms away (Kilosort 4's baseline), and the share of the unit's spikes from other cells that implies:
    seen / expected = 1 - (1 - foreign)^2."""
    samples = samples.astype(np.int64)
    within = [np.searchsorted(samples, samples + int(lag * rate_hz), side='right').sum() for lag in (0.00025, 0.00125, 0.01, 0.05, 0.25, 0.5)]
    seen = within[1] - within[0]
    window = int(0.00125 * rate_hz) - int(0.00025 * rate_hz)
    near = (within[3] - within[2]) * window / (int(0.05 * rate_hz) - int(0.01 * rate_hz))
    far = (within[5] - within[4]) * window / (int(0.5 * rate_hz) - int(0.25 * rate_hz))
    expected = max(near, far)
    return int(seen), float(expected), 1 - np.sqrt(1 - min(seen / expected, 1)) if expected > 0 else np.nan


def short_interval_share(samples, rate_hz):
    """Share of inter-spike intervals over 0.25 ms and under 1.25 ms."""
    intervals = np.diff(samples)
    return np.mean((intervals > 0.00025 * rate_hz) & (intervals < 0.00125 * rate_hz))


def notch_rates(a, b, rate_hz):
    """Spike pairs of two trains per ms of lag: at the centre (0.25-1 ms either way, mean of the two sides) and on the
    busier flank (2-10 ms); the notch is their ratio."""
    ms = rate_hz / 1000
    windows = [(int(np.ceil(start * ms)), int(np.floor(end * ms))) for start, end in [(-1, -0.25), (0.25, 1), (-10, -2), (2, 10)]]
    lags = pair_lags(a.astype(np.int64), b.astype(np.int64), max(max(-lo, hi) for lo, hi in windows))
    rates = [np.count_nonzero((lags >= lo) & (lags <= hi)) / ((hi - lo + 1) / ms) for lo, hi in windows]
    return (rates[0] + rates[1]) / 2, max(rates[2], rates[3])


def pair_lags(a, b, reach):
    """Lag b - a of every spike pair of two sorted trains up to `reach` samples apart, looked up from the smaller train."""
    small, large, sign = (a, b, 1) if len(a) <= len(b) else (b, a, -1)
    start = np.searchsorted(large, small - reach, side='left')
    n = np.searchsorted(large, small + reach, side='right') - start
    index = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n - start, n)
    return sign * (large[index] - np.repeat(small, n))


def block_rates(train, n_samples, rate_hz):
    """Spikes per sample of one train in each 5-minute block."""
    edges = np.r_[np.arange(0, n_samples, 300 * rate_hz), n_samples]
    return np.histogram(train, edges)[0] / np.diff(edges)


def handoff(rate_a, rate_b):
    """Hand-off of two spike trains from their block rates: (1 - overlap of their time courses) x steadiness of their sum."""
    # Overlap
    overlap = np.minimum(rate_a / rate_a.sum(), rate_b / rate_b.sum()).sum()
    # Steadiness
    cv = [np.std(r) / np.mean(r) for r in (rate_a, rate_b, rate_a + rate_b)]
    steadiness = 1 - cv[2] / max(cv[0], cv[1])
    return (1 - overlap) * steadiness


def bombcell_labels(spike_metrics, shape_metrics, thresholds, label_non_somatic):
    """good, mua or noise per unit; with label_non_somatic, units of non-somatic waveform shape are non_soma instead."""
    labels = bombcell_label_units(thresholds=thresholds, external_metrics=spike_metrics.join(shape_metrics),
                                  label_non_somatic=label_non_somatic, split_non_somatic_good_mua=False)
    return labels.iloc[:, 0].to_numpy()


def failed_tests(metrics, thresholds):
    """Per unit, the noise tests it fails (a missing value fails, as in SpikeInterface), or else the mua tests it fails."""
    failed = {}
    for section in ['noise', 'mua']:
        outside = pd.DataFrame({name: ~((metrics[name] >= (-np.inf if limit['greater'] is None else limit['greater']))
                                        & (metrics[name] <= (np.inf if limit['less'] is None else limit['less'])))
                                for name, limit in thresholds[section].items()})
        failed[section] = outside.apply(lambda row: row.index[row].tolist(), axis=1)
    return [noise or mua for noise, mua in zip(failed['noise'], failed['mua'])]
