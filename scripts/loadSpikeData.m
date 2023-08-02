function [out] = loadSpikeData(path_to_recording_dir)
%LOADSPIKEDATA Load kilosort / phy manually curated units
%   path_to_recording_dir: Path to directory containing kilosort_outdir.
% Load sorted units
phyFile = dir(fullfile(path_to_recording_dir, 'kilosort_outdir', 'cluster_info.tsv'));
phy = readtable(fullfile(phyFile.folder, phyFile.name), 'FileType', 'text', 'VariableNamingRule', 'preserve'); % import curated units
%phy.depth = 3940-phy.depth; % Correct the channel map setting for the 1st and 2nd recording

rows = strcmp(phy.group, 'good'); % Extract the neurons labeled 'good' after manual curation
good_unit = phy(rows, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});

noise_rows = strcmp(phy.group, 'noise');
mua_unit = phy(~noise_rows, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});

sp_unit = double(readNPY(fullfile(phyFile.folder, 'spike_clusters.npy'))); % Unit ID
sp_times = double(readNPY(fullfile(phyFile.folder, 'spike_times.npy'))); % Spike times in raw sample numbers
sp_templates = double(readNPY(fullfile(phyFile.folder, 'amplitudes.npy')));

dio = loadTrodesDigital(path_to_recording_dir);
isRising = dio{1}.state == 1;
local_ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
first_sample_timestamp_usec = dio{1}.first_timestamp_usec;

out.local_ttl_timestamps_usec = local_ttl_timestamps_usec;
out.first_sample_timestamps_usec = first_sample_timestamp_usec;

analogData = loadTrodesAnalog(path_to_recording_dir);
sp_times_usec = analogData.local_sample_timestamps_usec(sp_times);
%lfp = loadTrodesLFP(path_to_recording_dir);

% Convert raw sample numbers by dividing by clockrate and adding to first
% sample timestamp
local_spike_times_usec = sp_times_usec;

global_spike_times_usec = local2GlobalTime(local_ttl_timestamps_usec, local_spike_times_usec);

%kilosort_dirname = dir(fullfile(path_to_recording_dir, "*.kilosort")).name;
%timestamp_filename = dir(fullfile(path_to_recording_dir, kilosort_dirname, "*.timestamps.dat")).name;
%timeFile = dir(fullfile(path_to_recording_dir, kilosort_dirname, timestamp_filename));
%timestamp = readTrodesExtractedDataFile(fullfile(timeFile.folder,timeFile.name));
%T = double(timestamp.fields.data(end) - timestamp.fields.data(1)); % length of recording
%start_time = timestamp.fields.data(1);
%end_time = timestamp.fields.data(end);
%sampling_times = timestamp.fields.data;

out.good_units = good_unit;
num_unit = size(good_unit ,1);
%% FIGURE: raster plot of good units

for i = 1:num_unit
    out.spikeTimes_usec{i} = global_spike_times_usec(sp_unit == good_unit.cluster_id(i));
    out.localSpikeTimes_usec{i} = local_spike_times_usec(sp_unit == good_unit.cluster_id(i));
end


end

