function [lfpData] = loadTrodesLFP(path_to_recording_dir)
%LOADTRODESLFP Summary of this function goes here
%   Detailed explanation goes here

%timestampData = loadTrodesTimestamps(path_to_recording_dir);



[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedLFP_dirname = dirname + "_merged.LFP";
mergedTime_filename = dirname + "_merged.timestamps.dat";

timestamps = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, ...
                                                  mergedLFP_dirname, ...
                                                  mergedTime_filename));
sample_timestamps_usec = 1e6 * double(timestamps.fields.data) / double(timestamps.clockrate);
timestamp_at_creation_usec = 1e6 * double(timestamps.timestamp_at_creation) / double(timestamps.clockrate);
first_timestamp_usec = 1e6 * double(timestamps.first_timestamp) / double(timestamps.clockrate);


datFiles = dir(fullfile(path_to_recording_dir, mergedLFP_dirname));

lfp = zeros(384,length(sample_timestamps_usec));
for i = 1:length(datFiles)
    file = datFiles(i);
    if(regexp(file.name, ".*nt\d(\d\d\d)ch\d\.dat"))
        chNumToken = regexp(file.name, ".*nt\d(\d\d\d)ch\d\.dat", "tokens");
        chNum = str2num(chNumToken{1}{1});
        disp(sprintf("Loading ch %d ...", chNum));

        chData = readTrodesExtractedDataFile(fullfile(file.folder, file.name));

        lfp(chNum,:) = chData.fields.data;
        
    end
end
lfpData = struct();
lfpData.lfp = lfp;
lfpData.voltage_scaling = chData.voltage_scaling;
lfpData.sample_timestamps_usec = sample_timestamps_usec;
lfpData.timestamp_at_creation_usec = timestamp_at_creation_usec;
lfpData.first_timestamp_usec = first_timestamp_usec;

%lfpData.sample_timestamps_usec = timestampData.sample_timestamps_usec;

end

