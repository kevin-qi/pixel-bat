function [] = exportTrodesRecording(path_to_rec_dir, path_to_trodes, isTethered)
%EXPORTTRODESRECORDING Summary of this function goes here
%   Detailed explanation goes here
%   Recording directory must have default name generated by trodes: 
%   (YYYYMMDD_HHMMSS.rec)


%% Parse recording directory
[dirpath, dirname, ext] = fileparts(path_to_rec_dir);
fparts = regexp([dirname ext], "(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).rec", "tokens");
YY = fparts{1}{1}(3:end);
MM = fparts{1}{2};
DD = fparts{1}{3};
date = sprintf("%s%s%s",YY,MM,DD);

time = fparts{1}{4};

% Types of export (0 or 1)
% Not used
export_spikes = 0;
export_lfp = 1;
export_ks = 1;

% Export LFP, Spikes, and Kilosort data
lfp_flag = '-lfplowpass 600 -lfpoutputrate 1500 -uselfpfilters 1'; % LFP export parameters
spikes_flag = '-spikehighpass 300 -spikelowpass 6000 -usespikefilters 1'; % spikes export parameters
if(~isTethered)
    path_to_rec_file = fullfile(path_to_rec_dir, dirname + "_merged" + ".rec");
else
    path_to_rec_file = fullfile(path_to_rec_dir, dirname + ".rec");
end

cd(path_to_trodes)
if(exist(path_to_rec_file))
    formatted_path_to_rec_file = join(['"', path_to_rec_file, '"'], '');
    output_path = join(['"', path_to_rec_dir, '"'], '');
    
    if export_lfp == 1
        cmd = join(['trodesexport -lfp -rec', formatted_path_to_rec_file, '-outputdirectory', output_path, '-interp 0', lfp_flag]); % command to run
        [status, cmdout] = system(cmd); % Export lfp file
    end
    if export_spikes == 1
        cmd = join(['trodesexport -spikes -rec', formatted_path_to_rec_file, '-outputdirectory', output_path, '-interp 0', spikes_flag]); % command to run
        [status, cmdout] = system(cmd); % Export spike file
    end
    if export_ks == 1
        cmd = join(['trodesexport -kilosort -rec', formatted_path_to_rec_file,  '-outputdirectory', output_path, '-interp 0']); % command to run
        [status, cmdout] = system(cmd); % Export kilosort .dat file
    
        % Export channel map
        % Modified from getChanMap.m by V. A. Normand 2020. 
        chanmap_file = dir(join([path_to_rec_dir, '\*kilosort\*channelmap*.dat']));
        ks_struct = readTrodesExtractedDataFile(fullfile(chanmap_file(1).folder,chanmap_file(1).name));
        nchan = length(ks_struct.fields(1).data);
        chanMap = (1:1:nchan);
        chanMap0ind = chanMap-1;
        connected = logical(ones(nchan, 1));
        kcoords = ones(nchan, 1);
        xcoords = double(ks_struct.fields(1).data);
        ycoords = double(ks_struct.fields(2).data);
        fs = 30000; % sampling rate
        name = sprintf('Channel map from recording on %s_%s',date, time);
        save(fullfile(chanmap_file.folder, sprintf('channelMap_%s_%s.mat', date, time)), 'chanMap', 'chanMap0ind', 'connected','fs','kcoords','name','xcoords', 'ycoords')
        mkdir(fullfile(path_to_rec_dir, 'kilosort_outdir'));
        mkdir(fullfile(path_to_rec_dir, 'kilosort_workdir'));
    end
end
cd(pwd);

end

