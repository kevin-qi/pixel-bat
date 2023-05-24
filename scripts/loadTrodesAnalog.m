function [analogData] = loadTrodesAnalog(path_to_recording_dir)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedAnalog_dirname = dirname + "_merged.analog";

mergedAnalog_filename = dirname + "_merged.timestamps.dat";

analogData = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, mergedAnalog_dirname, mergedAnalog_filename));

end