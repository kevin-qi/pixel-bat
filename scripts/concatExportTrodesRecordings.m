addpath(genpath(path_to_trodes))
isTethered = false;

ephysPaths(1) = "Z:\users\KevinQi\datasets\AlphaPixels\29968\b149f\raw\230602\ephys";
ephysPaths(2) = "Z:\users\KevinQi\datasets\AlphaPixels\29968\b149f\raw\230605\ephys";

outPath = "Z:\users\KevinQi\datasets\AlphaPixels\29968\b149f_b149f\raw\230602_230605\ephys";

if(~exist(outPath))
    mkdir(outPath)
end

%% Parse recording directory
for i = 1:length(ephysPaths)
    recs = dir(fullfile(ephysPaths(i), "*.rec")); % list of recording directory
    path_to_rec_dir{i} = fullfile(recs(1).folder, recs(1).name);
    
    [dirpath, dirname, ext] = fileparts(path_to_rec_dir{i});
    fparts = regexp([dirname ext], "(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d).rec", "tokens");
    YY = fparts{1}{1}(3:end);
    MM = fparts{1}{2};
    DD = fparts{1}{3};
    date = sprintf("%s%s%s",YY,MM,DD);
    
    time = fparts{1}{4};
    
    % Export LFP, Spikes, and Kilosort data
    lfp_flag = '-lfplowpass 600 -lfpoutputrate 1500 -uselfpfilters 1'; % LFP export parameters
    spikes_flag = '-spikehighpass 300 -spikelowpass 6000 -usespikefilters 1'; % spikes export parameters
    if(~isTethered)
        path_to_rec_file(i) = fullfile(path_to_rec_dir{i}, dirname + "_merged" + ".rec");
    else
        path_to_rec_file(i) = fullfile(path_to_rec_dir{i}, dirname + ".rec");
    end
end

original_dir = pwd;
cd(path_to_trodes)
formatted_path_to_rec_file_1 = join(['"', path_to_rec_file(1), '"'], '');
formatted_path_to_rec_file_2 = join(['"', path_to_rec_file(2), '"'], '');
output_path = join(['"', outPath, '"'], '');

cmd = join(['trodesexport -lfp -spikes -dio -analogio -kilosort -rec', formatted_path_to_rec_file_1, '-rec', formatted_path_to_rec_file_2, '-outputdirectory', output_path, '-interp 0', lfp_flag]); % command to run
[status, cmdout] = system(cmd); % Export lfp file
disp(cmdout)

chanmap_file = dir(join([outPath, '/*kilosort/*channelmap*.dat']));
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
mkdir(fullfile(outPath, 'kilosort_outdir'));
mkdir(fullfile(outPath, 'kilosort_workdir'));
    
cd(original_dir);
