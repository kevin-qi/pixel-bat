from kilosort import run_kilosort, DEFAULT_SETTINGS
from kilosort.io import save_probe, load_ops

import os
import numpy as np
import pandas as pd
import glob
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import gridspec, rcParams
rcParams['axes.spines.top'] = False
rcParams['axes.spines.right'] = False

import spikeinterface.core as sc
from probeinterface import Probe
from probeinterface.plotting import plot_probe

from pixelbat.utils import parse_file_structure, readTrodesExtractedDataFile

def run(dataset_path: str, bat_id: str, experiment: str, date: str, settings: dict = DEFAULT_SETTINGS, device: int = 0, invert_sign: bool = True):
    recording_paths = parse_file_structure(dataset_path, bat_id, experiment, date)

    # Create channel maps for each probe
    create_channel_map(dataset_path, bat_id, experiment, date)

    for iProbe in range(recording_paths['num_probes']):
        print(settings)

        res = run_kilosort(settings=settings,
                        filename=recording_paths['kilosort_binary_paths'][iProbe],
                        probe_name=recording_paths['channelmap_json_paths'][iProbe],
                        device=device,
                        data_dtype='int16',
                        invert_sign=True, # True for Trodes exported data. Check that waveforms have positive peaks.
                        results_dir=recording_paths['kilosort_out_paths'][iProbe],
                        save_preprocessed_copy=True) # Lets phy use the drift corrected data.
        
        plot_results(dataset_path, bat_id, experiment, date, iProbe)

    
def plot_results(dataset_path: str, bat_id: str, experiment: str, date: str, iProbe: int):
    recording_paths = parse_file_structure(dataset_path, bat_id, experiment, date, verbose=False)
    
    # outputs saved to results_dir
    results_dir = recording_paths['kilosort_out_paths'][iProbe]
    ops = load_ops(os.path.join(results_dir, 'ops.npy'))
    camps = pd.read_csv(os.path.join(results_dir, 'cluster_Amplitude.tsv'), sep='\t')['Amplitude'].values
    contam_pct = pd.read_csv(os.path.join(results_dir, 'cluster_ContamPct.tsv'), sep='\t')['ContamPct'].values
    chan_map = np.load(os.path.join(results_dir, 'channel_map.npy'))
    templates = np.load(os.path.join(results_dir, 'templates.npy'))
    chan_best = (templates**2).sum(axis=1).argmax(axis=-1)
    chan_best = chan_map[chan_best]
    amplitudes = np.load(os.path.join(results_dir, 'amplitudes.npy'))
    st = np.load(os.path.join(results_dir, 'spike_times.npy'))
    clu = np.load(os.path.join(results_dir, 'spike_clusters.npy'))
    firing_rates = np.unique(clu, return_counts=True)[1] * 30000 / st.max()
    dshift = ops['dshift']

    gray = .5 * np.ones(3)

    # Summary figure
    fig = plt.figure(figsize=(10,10), dpi=100)
    grid = gridspec.GridSpec(3, 3, figure=fig, hspace=0.5, wspace=0.5)

    ax = fig.add_subplot(grid[0,0])
    ax.plot(np.arange(0, ops['Nbatches'])*2, dshift);
    ax.set_xlabel('time (sec.)')
    ax.set_ylabel('drift (um)')

    ax = fig.add_subplot(grid[0,1:])
    t0 = 0
    t1 = np.nonzero(st > ops['fs']*5)[0][0]
    ax.scatter(st[t0:t1]/30000., chan_best[clu[t0:t1]], s=0.5, color='k', alpha=0.25)
    ax.set_xlim([0, 5])
    ax.set_ylim([chan_map.max(), 0])
    ax.set_xlabel('time (sec.)')
    ax.set_ylabel('channel')
    ax.set_title('spikes from units')

    ax = fig.add_subplot(grid[1,0])
    nb=ax.hist(firing_rates, 20, color=gray)
    ax.set_xlabel('firing rate (Hz)')
    ax.set_ylabel('# of units')

    ax = fig.add_subplot(grid[1,1])
    nb=ax.hist(camps, 20, color=gray)
    ax.set_xlabel('amplitude')
    ax.set_ylabel('# of units')

    ax = fig.add_subplot(grid[1,2])
    nb=ax.hist(np.minimum(100, contam_pct), np.arange(0,105,5), color=gray)
    ax.plot([10, 10], [0, nb[0].max()], 'k--')
    ax.set_xlabel('% contamination')
    ax.set_ylabel('# of units')
    ax.set_title('< 10% = good units')

    for k in range(2):
        ax = fig.add_subplot(grid[2,k])
        is_ref = contam_pct<10.
        ax.scatter(firing_rates[~is_ref], camps[~is_ref], s=3, color='r', label='mua', alpha=0.25)
        ax.scatter(firing_rates[is_ref], camps[is_ref], s=3, color='b', label='good', alpha=0.25)
        ax.set_ylabel('amplitude (a.u.)')
        ax.set_xlabel('firing rate (Hz)')
        ax.legend()
        if k==1:
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_title('loglog')

    plt.savefig(os.path.join(results_dir, 'summary_plots.png'))
    plt.close()

    probe = ops['probe']
    # x and y position of probe sites
    xc, yc = probe['xc'], probe['yc']
    nc = 16 # number of channels to show
    good_units = np.nonzero(contam_pct <= 0.1)[0]
    mua_units = np.nonzero(contam_pct > 0.1)[0]

    gstr = ['good', 'mua']
    for j in range(2):
        print(f'~~~~~~~~~~~~~~ {gstr[j]} units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        print('title = number of spikes from each unit')
        units = good_units if j==0 else mua_units
        fig = plt.figure(figsize=(12,3), dpi=150)
        grid = gridspec.GridSpec(2,20, figure=fig, hspace=0.25, wspace=0.5)

        for k in range(40):
            wi = units[np.random.randint(len(units))]
            wv = templates[wi].copy()
            cb = chan_best[wi]
            nsp = (clu==wi).sum()

            ax = fig.add_subplot(grid[k//20, k%20])
            n_chan = wv.shape[-1]
            ic0 = max(0, cb-nc//2)
            ic1 = min(n_chan, cb+nc//2)
            wv = wv[:, ic0:ic1]
            x0, y0 = xc[ic0:ic1], yc[ic0:ic1]

            amp = 4
            for ii, (xi,yi) in enumerate(zip(x0,y0)):
                t = np.arange(-wv.shape[0]//2,wv.shape[0]//2,1,'float32')
                t /= wv.shape[0] / 20
                ax.plot(xi + t, yi + wv[:,ii]*amp, lw=0.5, color='k')

            ax.set_title(f'{nsp}', fontsize='small')
            ax.axis('off')
        
        plt.savefig(os.path.join(results_dir, f'unit_waveforms_{gstr[j]}.png'))
        plt.close()

def create_channel_map(dataset_path: str, bat_id: str, experiment: str, date: str):
    recording_paths = parse_file_structure(dataset_path, bat_id, experiment, date, verbose=False)

    num_probes = recording_paths['num_probes']
    channelmap_paths = recording_paths['channelmap_paths']
    binary_paths = recording_paths['binary_paths']
    kilosort_folder = recording_paths['kilosort_folder']
    
    # Create channel maps for each probe
    recordings = []
    for iProbe in range(num_probes):
        channel_map_data = readTrodesExtractedDataFile(channelmap_paths[iProbe])
        channel_map = np.column_stack([
            channel_map_data['data']['ml'].ravel(),
            channel_map_data['data']['dv'].ravel()
        ]).astype(float)

        n_chan = len(channel_map)
        chanMap = np.arange(n_chan)
        kcoords = np.zeros(n_chan)
        xcoords = channel_map[:,0]
        ycoords = channel_map[:,1]

        probe = {
            'chanMap': chanMap,
            'xc': xcoords,
            'yc': ycoords,
            'kcoords': kcoords,
            'n_chan': n_chan
        }

        recording = sc.read_binary(
            file_paths=binary_paths[iProbe],
            sampling_frequency=30000,
            num_channels=n_chan, 
            dtype='<i2',
            time_axis=0,
            is_filtered=False,
        )
        

        recording.set_dummy_probe_from_locations(
            channel_map,
            shape_params=dict(radius=2.5)
        )

        print(f"\nChannel map for probe {iProbe+1}:")
        print(probe)
        

        fig, ax = plt.subplots(figsize=(8, 16))
        plot_probe(recording.get_probe(), ax=ax, with_device_index=True)
        ax.set_title(f'Probe {iProbe+1} (Note, Device Index is reversed from Trodes Index)')
        ax.set_aspect('auto')
        plt.show()

        recordings.append(recording)
        print(recordings)

        save_probe(probe, os.path.join(kilosort_folder, f'{bat_id}_{date}_{experiment}_channelmap_probe{iProbe+1}.json'))