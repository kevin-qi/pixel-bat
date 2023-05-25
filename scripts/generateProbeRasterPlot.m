path_to_recording_dir = "C:/Users/YartsevPixels1/Desktop/pixel-bat/data/29968/raw/230525/ephys/20230525_124737.rec";

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

% Load sorted units
phyFile = dir(fullfile(path_to_recording_dir, 'kilosort_outdir', 'cluster_info.tsv'));
phy = readtable(fullfile(phyFile.folder, phyFile.name), 'FileType', 'text', 'VariableNamingRule', 'preserve'); % import curated units
%phy.depth = 3940-phy.depth; % Correct the channel map setting for the 1st and 2nd recording

rows = strcmp(phy.group, 'good'); % Extract the neurons labeled 'good' after manual curation
good_unit = phy(rows, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});

noise_rows = strcmp(phy.group, 'noise');
mua_unit = phy(~noise_rows, {'cluster_id', 'Amplitude', 'ch', 'depth', 'fr', 'n_spikes', 'KSLabel', 'group'});

sp_unit = double(readNPY(fullfile(phyFile.folder, 'spike_clusters.npy'))); % Unit ID
sp_times = double(readNPY(fullfile(phyFile.folder, 'spike_times.npy'))); % Spike times
sp_templates = double(readNPY(fullfile(phyFile.folder, 'amplitudes.npy')));

kilosort_dirname = dir(fullfile(path_to_recording_dir, "*.kilosort")).name;
timestamp_filename = dir(fullfile(path_to_recording_dir, kilosort_dirname, "*.timestamps.dat")).name;
timeFile = dir(fullfile(path_to_recording_dir, kilosort_dirname, timestamp_filename));
timestamp = readTrodesExtractedDataFile(fullfile(timeFile.folder,timeFile.name));
T = double(timestamp.fields.data(end) - timestamp.fields.data(1)); % length of recording
start_time = timestamp.fields.data(1);
end_time = timestamp.fields.data(end);
sampling_times = timestamp.fields.data;


units = good_unit;
num_unit = size(units,1);

%mkdir('Extracted')
%save('Extracted\SingleUnits.mat','good_unit','T', sp_unit, sp_times)

%% FIGURE: raster plot of good units
for i = 1:num_unit
    units.sp{i} = sp_times(sp_unit == units.cluster_id(i))'/30000;
end

dCA1 = [0 2500];
cortex = [4000 8000];
dg = [3400 4000];
colors = [[127,201,127]; [190,174,212]; [253,192,134]; [150,150,150]]/255;

fig = figure();
for i = 1:num_unit
    x = units.sp{i};
    y = repmat(units.depth(i),size(x));
    depth = units.depth(i);
    if(depth > dCA1(1) && depth < dCA1(2))
        color = colors(1,:);
    elseif(depth > cortex(1) && depth < cortex(2))
        color = colors(2,:);
    elseif(depth > dg(1) && depth < dg(2))
        color = colors(3,:);
    else
        color = colors(4,:);
    end
    plot(x,y,'.k','Color', [color 1], 'MarkerSize', 1);
    hold on;
end
xlim([0 600]);
xticks([0 300 600]);
ylim([0 10000])
ylabel('Distance from Probe Tip (um)');
xlabel('time (s)');

