function [timestampData] = loadTrodesTimestamps(path_to_recording_dir)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedTime_dirname = dirname + "_merged.time";

mergedTime_filename = dirname + "_merged.timestamps.dat";

data = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, ...
                                                  mergedTime_dirname, ...
                                                  mergedTime_filename));


timestampData.raw = data;
timestampData.first_timestamp = data.first_timestamp;
timestampData.timestamps = data.fields(:,1);
timestampData.clockrate = data.clockrate;
timestampData.sample_timestamps_usec = double(data.fields(:,1).data)*1e6/data.clockrate;
timestampData.first_timestamp_usec = double(data.first_timestamp)*1e6/data.clockrate;

end