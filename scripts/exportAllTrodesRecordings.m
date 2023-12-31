function [] = exportAllTrodesRecordings(data_path, trodes_path, varargin)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here
%   data_path : path to directory containing .rec folders

assert(~endsWith(data_path, ".rec"), "data_path should point to parent folder of .rec directory")

recs = dir(fullfile(data_path, "*")); % list of recording directory
for i = 1:length(recs)
    path_to_recording_dir = fullfile(recs(i).folder, recs(i).name);
    if(endsWith(path_to_recording_dir, ".rec"))
        exportTrodesRecording(path_to_recording_dir, trodes_path, varargin{:});
    end
end

end