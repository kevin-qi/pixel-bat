%% Parameters
batID = "29968";
dates = ["230525", "230526", "230527", "230531", "230601", "230602"];
data_path = '/media/batlab/BatDrive/FlyingPixels/data';


%% Process Cortex
clear ephys
for iDate = 1:length(dates)
    date = dates(iDate);
    raw_path = fullfile(data_path, batID, 'raw', date);
    processed_path = strrep(raw_path, 'raw', 'processed');
    existingTrackingFile = dir(fullfile(processed_path, 'ephys', '*ephys.mat'));
    
    rec_dir_list = dir(fullfile(raw_path,'ephys','*.rec'));
    if(length(rec_dir_list) > 0)
        if(length(existingTrackingFile) == 0)
            path_to_recording_dir = fullfile(rec_dir_list(1).folder, rec_dir_list(1).name);

            spikeData = loadSpikeData(path_to_recording_dir);
    
            analogData = loadTrodesAnalog(path_to_recording_dir);
            
            lfpData = loadTrodesLFP(path_to_recording_dir);

            ephys(iDate).spikeData = spikeData;
            ephys(iDate).analogData = analogData;
            ephys(iDate).lfpData = lfpData;

            data = ephys(iDate);

            if ~isdir(fullfile(processed_path, 'ephys'))
                mkdir(fullfile(processed_path, 'ephys'));
            end
            save(fullfile(processed_path, 'ephys', sprintf('%s_%s_ephys.mat', batID, date)), 'data', '-v7.3', '-nocompression');
        else
            disp(sprintf("%s already exists!", existingTrackingFile(1).name)) 
        end
    else
        fprintf("No rec directory found in %s\n", fullfile(raw_path,'ephys'));
    end
end

save(fullfile(data_path, batID, 'processed', sprintf('%s_ephys.mat', batID)), 'ephys');