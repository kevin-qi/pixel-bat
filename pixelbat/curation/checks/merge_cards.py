"""One review card per pair of units Kilosort4 would have merged, without its similarity score: merge_cards.py SESSIONS_CSV NAME OUT.

Writes OUT/cards/NAME_A_B.png (waveforms, correlograms, amplitude over time, spikes on flight paths, counts) and
OUT/similarity/NAME.csv (the pair's Kilosort template similarity, kept away from the cards).
"""
import itertools
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sessions = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False).set_index('name')
name, out = sys.argv[2], sys.argv[3]
session = sessions.loc[name]
cache = os.path.join(session['out'], 'cache')
os.makedirs(os.path.join(out, 'cards'), exist_ok=True)
os.makedirs(os.path.join(out, 'similarity'), exist_ok=True)

## Data
units = pd.read_csv(os.path.join(cache, 'units.csv'), index_col='cluster_id')
row_of = {unit: row for row, unit in enumerate(units.index)}
templates = np.load(os.path.join(cache, 'templates.npy'), mmap_mode='r')
amplitude_sample = np.load(os.path.join(cache, 'amplitude_sample.npy'))
channel_xy = np.load(os.path.join(cache, 'channel_positions.npy'))
recording = json.load(open(os.path.join(cache, 'recording.json')))
rate_hz = recording['rate_hz']
duration = recording['n_samples'] / rate_hz
spike_times = np.load(os.path.join(session['sort'], 'spike_times.npy')).ravel()
spike_clusters = np.load(os.path.join(session['sort'], 'spike_clusters.npy')).ravel()
ks_similarity = np.load(os.path.join(session['sort'], 'similar_templates.npy'))
groups = json.load(open(os.path.join(session['sort'], 'proposed_merges.json')))['groups']
has_position = os.path.exists(os.path.join(cache, 'position.npz'))
if has_position:
    position = np.load(os.path.join(cache, 'position.npz'))
    flight_clusters = sorted(int(key.split('_')[-1]) for key in position.files if key.startswith('flight_xy_'))[:4]
    position_unit = spike_clusters[position['spike_index']]


def correlogram(a, b, half_window, bin_size):
    """Counts of spikes of b around each spike of a (samples), in bins of bin_size up to half_window."""
    edges = np.arange(-half_window, half_window + bin_size, bin_size)
    first = np.searchsorted(b, a - half_window)
    last = np.searchsorted(b, a + half_window)
    lags = np.concatenate([b[i:j] - t for t, i, j in zip(a, first, last)])
    return np.histogram(lags, edges)[0], edges


pairs = [(a, b, group) for group in groups for a, b in itertools.combinations(sorted(group), 2)]
records = []
for a, b, group in pairs:
    # The larger unit first, blue
    a, b = sorted([a, b], key=lambda unit: -units.loc[unit, 'num_spikes'])
    trains = [spike_times[spike_clusters == unit].astype(np.int64) for unit in (a, b)]
    colors = ['#0072B2', '#D55E00']
    fig = plt.figure(figsize=(17, 10 if has_position else 7.4), facecolor='white')
    grid = fig.add_gridspec(4 if has_position else 2, 6, height_ratios=[1.5, 1, 1, 1][:4 if has_position else 2])

    ## Mean waveforms on the 12 sites nearest the larger unit's peak
    mean = [np.asarray(templates[row_of[unit]]) for unit in (a, b)]
    peak_site = np.ptp(mean[0], axis=0).argmax()
    near = np.argsort(np.hypot(*(channel_xy - channel_xy[peak_site]).T))[:12]
    ax = fig.add_subplot(grid[0, 0:2])
    xs = np.unique(channel_xy[near, 0])
    ys = np.unique(channel_xy[near, 1])
    top = max(np.abs(m[:, near]).max() for m in mean)
    time = np.linspace(0, 0.8, mean[0].shape[0])
    for m, color in zip(mean, colors):
        for site in near:
            col = np.searchsorted(xs, channel_xy[site, 0])
            line = np.searchsorted(ys, channel_xy[site, 1])
            ax.plot(col + time, line + 0.45 * m[:, site] / top, color=color, linewidth=1.0)
    ax.plot([-0.08, -0.08], [0, 0.45 * 100 / top], color='black', linewidth=2)
    ax.text(-0.12, 0, '100 µV', rotation=90, va='bottom', ha='right', fontsize=9)
    ax.set_title('Mean waveforms, same scale, sites nearest the peak of the blue unit', fontsize=10)
    ax.axis('off')
    ## Shape on the blue unit's peak site, each scaled to its own peak
    ax = fig.add_subplot(grid[0, 2])
    for m, color in zip(mean, colors):
        ax.plot(m[:, peak_site] / np.abs(m[:, peak_site]).max(), color=color, linewidth=1.3)
    ax.set_title('Peak site, each scaled to 1', fontsize=10)
    ax.set_xticks([])

    ## Correlograms, 1 ms bins to 50 ms
    for k, (x, y, title, color) in enumerate([(trains[0], trains[0], f'ACG {a}', colors[0]), (trains[1], trains[1], f'ACG {b}', colors[1]),
                                              (trains[0], trains[1], f'CCG {b} around {a}', '#555555')]):
        counts, edges = correlogram(x, y, int(0.05 * rate_hz), int(0.001 * rate_hz))
        if x is y:
            counts[len(counts) // 2] -= len(x)
        ax = fig.add_subplot(grid[0, 3 + k])
        ax.bar(edges[:-1] / rate_hz * 1000, counts, width=1.0, align='edge', color=color, linewidth=0)
        ax.axvspan(-1, 1, color='red', alpha=0.12, linewidth=0)
        ax.set_title(f'{title} (tallest bin {counts.max()})', fontsize=10)
        ax.set_xlabel('ms')
    cross, _ = correlogram(trains[0], trains[1], int(0.05 * rate_hz), int(0.001 * rate_hz))
    centre = cross[49:51].sum()
    shoulder = (cross[:40].sum() + cross[60:].sum()) / 40

    ## Amplitude over the session
    ax = fig.add_subplot(grid[1, 0:4])
    for unit, color in zip((a, b), colors):
        sample = amplitude_sample[row_of[unit]]
        ax.scatter(sample[:, 0] / 60, np.abs(sample[:, 1]), s=4, color=color, linewidths=0)
    ax.set_xlim(0, duration / 60)
    ax.set_ylim(0, None)
    ax.set_xlabel('min')
    ax.set_ylabel('spike amplitude (µV)')
    ax.set_title('Amplitude of up to 400 spikes per unit over the session', fontsize=10)

    ## Numbers
    ax = fig.add_subplot(grid[1, 4:6])
    ax.axis('off')
    lines = [f'{name}   group of {len(group)} units']
    for unit, train, color in zip((a, b), trains, ['blue', 'orange']):
        u = units.loc[unit]
        short = (np.diff(train) <= 0.001 * rate_hz).sum()
        lines.append(f'{color} {unit}: {len(train):,} spikes, {len(train) / duration:.2f} Hz, {abs(u["amplitude_median"]):.0f} µV,\n'
                     f'   intervals ≤1 ms {short} ({100 * short / max(len(train) - 1, 1):.2f}%), presence {u["presence_ratio"]:.2f},\n'
                     f'   Kilosort {u["KSLabel"]}, depth {u["depth"]:.0f} µm')
    lines.append(f'CCG within ±1 ms: {centre} spikes; expected from 10-50 ms: {shoulder:.1f}')
    ax.text(0, 1, '\n'.join(lines), va='top', fontsize=10.5, family='monospace')

    ## Spikes on flight paths, one row per unit
    if has_position:
        for r, (unit, color) in enumerate(zip((a, b), colors)):
            for k, cluster in enumerate(flight_clusters):
                ax = fig.add_subplot(grid[2 + r, k])
                path = position[f'flight_xy_{cluster}']
                ax.plot(path[:, 0], path[:, 1], '.', color='#cccccc', markersize=1)
                on = (position_unit == unit) & (position['spike_flight_cluster'] == cluster)
                ax.plot(position['spike_xy'][on, 0], position['spike_xy'][on, 1], '.', color=color, markersize=3)
                ax.set_title(f'unit {unit}, flight cluster {cluster}: {on.sum()} spikes', fontsize=9)
                ax.set_aspect('equal')
                ax.set_xticks([])
                ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'cards', f'{name}_{a}_{b}.png'), dpi=70)
    plt.close(fig)
    records.append({'session': name, 'a': a, 'b': b, 'group_size': len(group), 'ks_similarity': ks_similarity[a, b]})

pd.DataFrame(records).to_csv(os.path.join(out, 'similarity', f'{name}.csv'), index=False)
print(f'{len(records)} pairs from {len(groups)} proposed groups')
