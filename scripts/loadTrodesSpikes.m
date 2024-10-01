function [out] = loadTrodesSpikes(path_to_recording_dir, varargin)
%LOADTRODESLFP Summary of this function goes here
%   Detailed explanation goes here

p = inputParser;
addRequired(p, 'path_to_recording_dir');

parse(p, path_to_recording_dir, varargin{:});

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

%mergedSpikes_dirname = dirname + "_merged.spikes";
mergedSpikes_dirname = getChildFolder(path_to_recording_dir, ".*.spikes");

%% Channel Map
xPos = repmat([8 -24 24 -8].', [240 1]);
yPos = reshape( repmat( [0:959/2], 2,1 ), 1, [] )*20+100;

%% Load LFP sample timestamps
%dio = loadTrodesDigital(path_to_recording_dir);
%ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
%first_sample_timestamp_usec = dio{1}.first_timestamp_usec;

%% Synchronize lfp sample timestamps with TTLs
%global_sample_timestamps = local2GlobalTime(ttl_timestamps_usec, local_sample_timestamps_usec);
%global_sample_timestamps = local_sample_timestamps_usec;

datFiles = dir(fullfile(mergedSpikes_dirname, '*.spikes_nt*.dat'));
nChannels = length(datFiles);

fnames = {datFiles.name};
parsedTokens = regexp(fnames, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.spikes_nt(\d)(\d\d\d).dat', 'tokens');

% Restructure parsed LFP files to match channel numbers with probe number
chNums = [];
probeNums = [];
for i = 1:nChannels
    probeNums = [probeNums str2num(parsedTokens{i}{1}{end-1})];
    chNums = [chNums str2num(parsedTokens{i}{1}{end})];
end

nProbes = length(unique(probeNums));

channelMap = {};
numChannels = nan([1, nProbes]);
spikeData = {};
spikeAmplitudes = {};
channelIDs = {};
channelPositions = {};
for probeIdx = 1:nProbes
    % Get lfp files for probeIdx
    datFiles = dir(fullfile(mergedSpikes_dirname, sprintf('*_*.spikes_nt%d*.dat', probeIdx)));
    parsedTokens = regexp({datFiles.name}, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.spikes_nt(\d)(\d\d\d).dat', 'tokens');
    numChannels(probeIdx) = length(parsedTokens);
    channelIDs{probeIdx} = nan([1, numChannels(probeIdx)]);
    channelMap{probeIdx} = nan([1, numChannels(probeIdx)]);
    for i = 1:numChannels(probeIdx)
        % Parse Trodes channel number from file name. Smaller ID is towards
        % the tip of the probe
        channelIDs{probeIdx}(i) = str2num(parsedTokens{i}{1}{end});
        
    end
    [a, sortIdx] = sort(channelIDs{probeIdx}); % Sort in case filesystem is not in order
    sortedDatFiles = datFiles(sortIdx);

    % Load Spikes data
    chPositions_x = xPos(chNums(probeNums == probeIdx));
    chPositions_y = yPos(chNums(probeNums == probeIdx));
    channelPositions{probeIdx} = [chPositions_x.'; chPositions_y].';
    %spikes = zeros([numChannels(probeIdx),length(local_sample_timestamps_usec)],"int16");
    for idx = 1:numChannels(probeIdx)
        file = sortedDatFiles(idx);
        tokens = regexp(file.name, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.spikes_nt(\d)(\d\d\d).dat', 'tokens');
        tokens = tokens{1};
        yyyy = tokens{1};
        mm = tokens{2};
        dd = tokens{3};
        date = [yyyy mm dd];
        hhmmss = tokens{4};
        probeNum = str2num(tokens{5});
        chNum = str2num(tokens{6});
        disp(sprintf("Loading ch %d ...", chNum));
    
        chData = readTrodesExtractedDataFile(fullfile(file.folder, file.name));

        probe_ntrode_id = num2str(chData.ntrode_id);
        ntrode_id = str2num(probe_ntrode_id(2:end));
    
        spikes{idx} = chData.fields(1).data;  
        channelMap{probeIdx}(idx) = chNum;
        ampl{idx} = max(chData.fields(2).data(:,:).');
        disp(sprintf("%d_%d", chNum, ntrode_id))
    end
    spikeData{probeIdx} = spikes;
    spikeAmplitudes{probeIdx} = ampl;
end

out = struct();
%out.timestamps = timestamps;
out.spikes = spikeData;
out.spikeAmplitudes = spikeAmplitudes;
out.channelMap = channelMap;
out.channelID = channelIDs;
out.channelPositions = channelPositions;
out.voltage_scaling = chData.voltage_scaling;
%out.local_sample_timestamps_usec = local_sample_timestamps_usec;
%out.timestamp_at_creation_usec = timestamp_at_creation_usec;
%out.first_timestamp_usec = first_timestamp_usec;
%out.global_sample_timestamps_usec = global_sample_timestamps;
%out.ttl_timestamps_usec = ttl_timestamps_usec;
%out.first_sample_timestamps_usec = first_sample_timestamp_usec;

end

