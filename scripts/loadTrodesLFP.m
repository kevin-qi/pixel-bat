function [out] = loadTrodesLFP(path_to_recording_dir, varargin)
%LOADTRODESLFP Summary of this function goes here
%   Detailed explanation goes here

p = inputParser;
addRequired(p, 'path_to_recording_dir');
addOptional(p, 'kilosort_out_folder_name', 'kilosort_outdir');

parse(p, path_to_recording_dir, varargin{:});
kilosort_out_folder_name = p.Results.kilosort_out_folder_name;

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedLFP_dirname = dirname + "_merged.LFP";
mergedTime_filename = dirname + "_merged.timestamps.dat";

%% Channel Map
xPos = repmat([8 -24 24 -8].', [240 1]);
yPos = reshape( repmat( [0:960/2], 2,1 ), 1, [] )*20+100;

%% Load LFP sample timestamps
timestamps = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, ...
                                                  mergedLFP_dirname, ...
                                                  mergedTime_filename));
local_sample_timestamps_usec = 1e6 * double(timestamps.fields.data) / double(timestamps.clockrate);
timestamp_at_creation_usec = 1e6 * double(timestamps.timestamp_at_creation) / double(timestamps.clockrate);
first_timestamp_usec = 1e6 * double(timestamps.first_timestamp) / double(timestamps.clockrate);

dio = loadTrodesDigital(path_to_recording_dir);
ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
first_sample_timestamp_usec = dio{1}.first_timestamp_usec;

%% Synchronize lfp sample timestamps with TTLs
global_sample_timestamps = local2GlobalTime(ttl_timestamps_usec, local_sample_timestamps_usec);
%global_sample_timestamps = local_sample_timestamps_usec;

datFiles = dir(fullfile(path_to_recording_dir, mergedLFP_dirname, '*_*.LFP_nt*ch*.dat'));
nChannels = length(datFiles);

fnames = {datFiles.name};
parsedTokens = regexp(fnames, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.LFP_nt(\d)(\d\d\d)ch\d.dat', 'tokens');

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
lfpData = {};
channelIDs = {};
channelPositions = {};
for probeIdx = 1:nProbes
    % Get lfp files for probeIdx
    datFiles = dir(fullfile(path_to_recording_dir, mergedLFP_dirname, sprintf('*_*.LFP_nt%d*ch*.dat', probeIdx)));
    parsedTokens = regexp({datFiles.name}, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.LFP_nt(\d)(\d\d\d)ch\d.dat', 'tokens');
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

    % Load LFP data
    chPositions_x = xPos(chNums(probeNums == probeIdx));
    chPositions_y = yPos(chNums(probeNums == probeIdx));
    channelPositions{probeIdx} = [chPositions_x.'; chPositions_y].';
    lfp = zeros([numChannels(probeIdx),length(local_sample_timestamps_usec)],"int16");
    for idx = 1:numChannels(probeIdx)
        file = sortedDatFiles(idx);
        tokens = regexp(file.name, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.LFP_nt(\d)(\d\d\d)ch(\d).dat', 'tokens');
        tokens = tokens{1};
        yyyy = tokens{1};
        mm = tokens{2};
        dd = tokens{3};
        date = [yyyy mm dd];
        hhmmss = tokens{4};
        chNum = str2num(tokens{6});
        probeNum = str2num(tokens{7});
        disp(sprintf("Loading ch %d ...", chNum));
    
        chData = readTrodesExtractedDataFile(fullfile(file.folder, file.name));
    
        lfp(idx, :) = chData.fields.data;  
        channelMap{probeIdx}(idx) = chNum;
    end
    lfpData{probeIdx} = lfp;
end

out = struct();
out.timestamps = timestamps;
out.lfp = lfpData;
out.channelMap = channelMap;
out.channelID = channelIDs;
out.channelPositions = channelPositions;
out.voltage_scaling = chData.voltage_scaling;
out.local_sample_timestamps_usec = local_sample_timestamps_usec;
out.timestamp_at_creation_usec = timestamp_at_creation_usec;
out.first_timestamp_usec = first_timestamp_usec;
out.global_sample_timestamps_usec = global_sample_timestamps;
out.ttl_timestamps_usec = ttl_timestamps_usec;
out.first_sample_timestamps_usec = first_sample_timestamp_usec;

end

