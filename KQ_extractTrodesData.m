%% Parameters
batID = "29968";
dates = ["230525", "230526", "230527", "230531", "230601", "230602"];
data_path = '/media/batlab/BatDrive/FlyingPixels/data';
trodes_path = '';


%% Process Cortex
for iDate = 1:length(dates)
    date = dates(iDate);
    raw_path = fullfile(data_path, batID, 'raw', date);

    processed_path = strrep(raw_path, 'raw', 'processed');
    existingTrackingFile = dir(fullfile(processed_path, 'ephys', '*ephys.mat'));
    
    rec_dir_list = dir(fullfile(raw_path,'ephys','*.rec'));
    if(length(rec_dir_list) > 0)
        path_to_recording_dir = fullfile(rec_dir_list(1).folder, rec_dir_list(1).name);
        
        containsAnalog = length(dir(fullfile(path_to_recording_dir, '*.analog'))) > 0;
        containsDIO = length(dir(fullfile(path_to_recording_dir, '*.kilosort'))) > 0;
        containsKilosort = length(dir(fullfile(path_to_recording_dir, '*.DIO'))) > 0;
        containsLFP = length(dir(fullfile(path_to_recording_dir, '*.LFP'))) > 0;
        containsTime = length(dir(fullfile(path_to_recording_dir, '*.time'))) > 0;

        exportAllTrodesRecordings(path_to_recording_dir, ...
                                  trodes_path, ...
                                  "extractAnalog", containsAnalog, ...
                                  "extractDIO", containsDIO, ...
                                  "extractKilosort", containsKilosort, ...
                                  "extractTime", containsTime, ...
                                  "extractLFP", containsLFP )

        
    end
end