function [lfpData] = loadTrodesLFP(path_to_recording_dir)
%LOADTRODESLFP Summary of this function goes here
%   Detailed explanation goes here

%timestampData = loadTrodesTimestamps(path_to_recording_dir);

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedLFP_dirname = dirname + "_merged.LFP";
mergedTime_filename = dirname + "_merged.timestamps.dat";

chPositionsFile = fullfile(path_to_recording_dir, 'kilosort_outdir', 'channel_positions.npy');
chPositions = readNPY(chPositionsFile);

timestamps = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, ...
                                                  mergedLFP_dirname, ...
                                                  mergedTime_filename));
local_sample_timestamps_usec = 1e6 * double(timestamps.fields.data) / double(timestamps.clockrate);
timestamp_at_creation_usec = 1e6 * double(timestamps.timestamp_at_creation) / double(timestamps.clockrate);
first_timestamp_usec = 1e6 * double(timestamps.first_timestamp) / double(timestamps.clockrate);

dio = loadTrodesDigital(path_to_recording_dir);
ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
first_sample_timestamp_usec = dio{1}.first_timestamp_usec;


global_sample_timestamps = local2GlobalTime(ttl_timestamps_usec, local_sample_timestamps_usec);

datFiles = dir(fullfile(path_to_recording_dir, mergedLFP_dirname, '*_*.LFP_nt*ch*.dat'));
nChannels = length(datFiles);

fnames = {datFiles.name};
parsedTokens = regexp(fnames, '(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).*\.LFP_nt(\d\d\d\d)ch(\d).dat', 'tokens');

chNums = [];
probeNums = [];
for i = 1:nChannels
    probeNums = [probeNums str2num(parsedTokens{i}{1}{end})];
    chNums = [chNums str2num(parsedTokens{i}{1}{end-1})];
end

[a, sortedIdx] = sort(chNums);

nProbes = length(unique(probeNums));

sortedDatFiles = datFiles(sortedIdx);
sortedParsedTokens = parsedTokens{sortedIdx};

lfp = zeros(nProbes, nChannels,length(local_sample_timestamps_usec));
channelMap = zeros(nProbes, nChannels);
for probeIdx = 1:nProbes
    for idx = 1:nChannels
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
    
        lfp(probeNum, idx, :) = chData.fields.data;  
        channelMap(probeNum, idx) = chNum;
    end
end

lfpData = struct();
lfpData.timestamps = timestamps;
lfpData.lfp = lfp;
lfpData.channelMap = channelMap;
lfpData.channelPositions = chPositions;
lfpData.voltage_scaling = chData.voltage_scaling;
lfpData.local_sample_timestamps_usec = local_sample_timestamps_usec;
lfpData.timestamp_at_creation_usec = timestamp_at_creation_usec;
lfpData.first_timestamp_usec = first_timestamp_usec;
lfpData.global_sample_timestamps_usec = global_sample_timestamps;
lfpData.ttl_timestamps_usec = ttl_timestamps_usec;
lfpData.first_sample_timestamps_usec = first_sample_timestamp_usec;
%lfpData.sample_timestamps_usec = timestampData.sample_timestamps_usec;

end

