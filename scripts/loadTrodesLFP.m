function [lfpData] = loadTrodesLFP(path_to_recording_dir)
%LOADTRODESLFP Summary of this function goes here
%   Detailed explanation goes here

timestampData = loadTrodesTimestamps(path_to_recording_dir);

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedLFP_dirname = dirname + "_merged.LFP";

datFiles = dir(fullfile(path_to_recording_dir, mergedLFP_dirname));

lfpData = struct();
for i = 1:length(datFiles)
    file = datFiles(i);
    if(regexp(file.name, ".*nt\d(\d\d\d)ch\d\.dat"))
        chNumToken = regexp(file.name, ".*nt\d(\d\d\d)ch\d\.dat", "tokens");
        chNum = str2num(chNumToken{1}{1})-2;
        disp(sprintf("Loading ch %d ...", chNum));

        chData = readTrodesExtractedDataFile(fullfile(file.folder, file.name));

        lfpData.lfp(chNum,:) = chData.fields.data;
        
    end
end
lfpData.voltage_scaling = chData.voltage_scaling;
lfpData.first_timestamp = chData.first_timestamp;
lfpData.sample_timestamps_usec = timestampData.sample_timestamps_usec;

end

