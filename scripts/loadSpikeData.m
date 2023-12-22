function [out] = loadSpikeData(path_to_recording_dir, varargin)
%LOADSPIKEDATA Load kilosort / phy manually curated units
%   path_to_recording_dir : Path to directory containing kilosort_outdir.
%   [Optional] kilosort_out_folder_name : Path to kilosort outdir 
% Load sorted units

%% Parse arguments
p = inputParser;
addRequired(p, 'path_to_recording_dir');
addOptional(p, 'kilosort_out_folder_name', 'kilosort_outdir');

parse(p, path_to_recording_dir, varargin{:});
kilosort_out_folder_name = p.Results.kilosort_out_folder_name;

%% Load spike sorted data
if(exist(fullfile(path_to_recording_dir, kilosort_out_folder_name, 'cluster_info.tsv')))
    disp("Kilosort outputs found")
    phyFile = dir(fullfile(path_to_recording_dir, kilosort_out_folder_name, 'cluster_info.tsv'));
    if(length(phyFile)>0)
        disp("Manual curation found")
        phy = readtable(fullfile(phyFile.folder, phyFile.name), 'FileType', 'text', 'VariableNamingRule', 'preserve'); % import curated units
        
        % Clusters labeled 'good' after manual curation
        good_unit_idx = strcmp(phy.group, 'good'); 
        good_units = phy(good_unit_idx, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});
        
        % Clusters labeled 'mua' after manual curation
        mua_unit_idx = logical(~strcmp(phy.group, 'good') .* ~strcmp(phy.group, 'noise'));
        mua_units = phy(mua_unit_idx, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});
        
        sp_unit = double(readNPY(fullfile(phyFile.folder, 'spike_clusters.npy'))); % Unit ID
        sp_times = double(readNPY(fullfile(phyFile.folder, 'spike_times.npy'))); % Spike times in raw sample numbers
        sp_templates = double(readNPY(fullfile(phyFile.folder, 'amplitudes.npy')));
        
        % Load TTL data
        dio = loadTrodesDigital(path_to_recording_dir);
        isRising = dio{1}.state == 1;
        local_ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
        first_sample_timestamp_usec = dio{1}.first_timestamp_usec;
        
        
        % Convert raw sample numbers by dividing by clockrate
        timeData = loadTrodesTimestamps(path_to_recording_dir);
        sp_times = sp_times(sp_times <= length(timeData.sample_timestamps_usec));
        sp_unit = sp_unit(sp_times <= length(timeData.sample_timestamps_usec));
        local_spike_times_usec = timeData.sample_timestamps_usec(sp_times);

        % Synchronize timestamps using TTLs
        global_spike_times_usec = local2GlobalTime(local_ttl_timestamps_usec, local_spike_times_usec);
        
        
        num_good_units = size(good_units ,1);
        num_mua_units = size(mua_units, 1);
 
        %% Populate data structure with good units
        out.good_units = good_units;
        spikeTimes_usec = {};
        localSpikeTimes_usec = {};
        spikeTimeSampleIdx = {};
        for i = 1:num_good_units
            spikeTimes_usec{i} = global_spike_times_usec(sp_unit == good_units.cluster_id(i));
            localSpikeTimes_usec{i} = local_spike_times_usec(sp_unit == good_units.cluster_id(i));
            spikeTimeSampleIdx{i} = sp_times(sp_unit == good_units.cluster_id(i));
        end
        out.good_units.spikeTimes_usec = spikeTimes_usec.';
        out.good_units.localSpikeTimes_usec = localSpikeTimes_usec.';
        out.good_units.spikeTimeSampleIdx = spikeTimeSampleIdx.';
        
        %% Populate data structure with mua units
        out.mua_units = mua_units;
        spikeTimes_usec = {};
        localSpikeTimes_usec = {};
        for i = 1:num_mua_units
            spikeTimes_usec{i} = global_spike_times_usec(sp_unit == mua_units.cluster_id(i));
            localSpikeTimes_usec{i} = local_spike_times_usec(sp_unit == mua_units.cluster_id(i));
        end
        out.mua_units.spikeTimes_usec = spikeTimes_usec.';
        out.mua_units.localSpikeTimes_usec = localSpikeTimes_usec.';
        
        %% Populate data fields
        out.allLocalSpikeTimes_usec = local_spike_times_usec;
        out.allGlobalSpikeTimes_usec = global_spike_times_usec;
        out.numGoodUnits = height(good_units);
        out.numMuaUnits = height(mua_units);
        out.local_ttl_timestamps_usec = local_ttl_timestamps_usec;
    else
        disp("Manual Curation Missing. Please manually curate kilosort results first!")
        out.good_units = table();
        out.mua_units = table();
        out.numGoodUnits = 0;
        out.numMuaUnits = 0;
        out.local_ttl_timestamps_usec = [];
    end
else
    disp("No Kilosort outputs found")
    out.good_units = table();
    out.mua_units = table();
    out.numGoodUnits = 0;
    out.numMuaUnits = 0;
    out.local_ttl_timestamps_usec = [];
end


end

