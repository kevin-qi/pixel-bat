function [sensors] = loadTrodesAnalog(path_to_recording_dir)
%loadTrodesAnalog Load analog data (accelerometer, gyroscope)
%   path_to_recording_dir : Path to directory containing .analog directory.

[dirpath, dirname, ext] = fileparts(path_to_recording_dir);
assert(strcmp(ext, ".rec"), "Trodes recording directory must end in .rec");

mergedAnalog_dirname = dirname + "_merged.analog";

mergedAnalog_filename = dirname + "_merged.timestamps.dat";

%% Analog data sample timestamps
timestampData = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, mergedAnalog_dirname, mergedAnalog_filename));

first_sample_timestamp_usec = double(timestampData.first_timestamp)*1e6/timestampData.clockrate;
sample_timestamps = timestampData.fields.data;
sample_timestamps_usec = 1e6 * double(sample_timestamps) / double(timestampData.clockrate);

%% TTL data
dio = loadTrodesDigital(path_to_recording_dir);
isRising = dio{1}.state == 1;
ttl_timestamps_usec = dio{1}.ttl_timestamp_usec;
global_sample_timestamps_usec = local2GlobalTime(ttl_timestamps_usec, sample_timestamps_usec);
close all;

%% Read and organize Acceleromer and Gyroscope data structure
sensorNames = ["Accel", "Gyro"];
euclideanAxes = ["X", "Y", "Z"];
sensors = struct();
for i = 1:length(sensorNames)
    for j = 1:length(euclideanAxes)
        fname = join([mergedAnalog_dirname, "_Headstage_", sensorNames(i), euclideanAxes(j), ".dat"],"");
        data = readTrodesExtractedDataFile(fullfile(path_to_recording_dir, mergedAnalog_dirname, fname));
        sensorVoltage = data.fields.data;
        sensors.(lower(sensorNames(i)))(j,:) = sensorVoltage;
        sensors.raw.(lower(sensorNames(i)))(j,:)  = data;
    end
end
sensors.global_sample_timestamps_usec = global_sample_timestamps_usec;
sensors.local_sample_timestamps_usec = sample_timestamps_usec;
