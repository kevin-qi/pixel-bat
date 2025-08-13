function [rez] = runKilosort3(path_to_recording_dir, varargin)
%RUNKILOSORT3 Summary of this function goes here
%   Detailed explanation goes here

%% Argument Parser
p = inputParser;
addRequired(p, 'path_to_recording_dir');
addOptional(p, 'probeNum', 1);
addOptional(p, 'numChannels', 384);
addOptional(p, 'nBlocks', 3);

parse(p,path_to_recording_dir,varargin{:});

probeNum = p.Results.probeNum;
numChannels = p.Results.numChannels;
nBlocks = p.Results.nBlocks;

%% System Paths
selfPath = fileparts(mfilename('fullpath')); % Path to directory containing runKilosort3.m
rootPath = fileparts(selfPath); % This should be root path of pixel-bat

addpath(genpath(fullfile(rootPath, 'Kilosort3'))) % path to kilosort folder
addpath(fullfile(rootPath, 'utils\npy-matlab')) % for converting to Phy
pathToYourConfigFile = fullfile(rootPath, 'Kilosort3Config\BatFlightConfig.m'); % Kilosort hyperparameters
pathToYourConfigFile = char(pathToYourConfigFile);

path_to_recording_dir = char(path_to_recording_dir);


%% Paths
extractedKilosortFolder = dir(fullfile(path_to_recording_dir, "*.kilosort"));
if(length(extractedKilosortFolder) == 0)
    fprintf("No .kilosort folder found in %s", path_to_recording_dir)
else
    rootZ = fullfile(path_to_recording_dir, extractedKilosortFolder(1).name); % the raw data binary file is in this folder
    rootH = fullfile(path_to_recording_dir, 'kilosort_workdir'); % path to temporary binary file (same size as data, should be on fast SSD)
    outDir = fullfile(path_to_recording_dir, sprintf('kilosort_outdir_probe%d', probeNum));
    
    rootZ = char(rootZ);
    rootH = char(rootH);
    outDir = char(outDir);

    if(~exist(rootH, 'dir'))
        mkdir(rootH)
    end

    if(~exist(outDir, 'dir'))
        mkdir(outDir)
    end

    channelMapFile = dir(fullfile(rootZ, sprintf('channelMap_probe%d_*.mat', probeNum)));
    if(length(channelMapFile) == 0)
        fprintf("No channelmap .mat file found in %s", rootZ)
    else
        pathToChannelMapFile = char(fullfile(rootZ, channelMapFile.name));
        ops.chanMap = char(pathToChannelMapFile);
    end
end


%% Kilosort3 Parameter Overrides
ops.trange    = [0 Inf]; % time range to sort
ops.NchanTOT  = numChannels; % total number of channels in your recording

run(fullfile(pathToYourConfigFile))
ops.fproc   = fullfile(rootH, sprintf('temp_wh_probe_%d.dat', probeNum)); % proc file on a fast SSD
ops.chanMap = fullfile(pathToChannelMapFile);

% main parameter changes from Kilosort2 to v2.5
ops.sig        = 20;  % spatial smoothness constant for registration
ops.fshigh     = 300; % high-pass more aggresively
ops.nblocks    = nBlocks; % blocks for registration. 0 turns it off, 1 does rigid registration. Replaces "datashift" option. 

% main parameter changes from Kilosort2.5 to v3.0
ops.Th       = [7 7];


% find the binary file
fs          = [dir(fullfile(rootZ, '*.bin')) dir(fullfile(rootZ, sprintf('*.probe%d.dat', probeNum)))];
if(isempty(fs))
    fprintf("No data .bin file found in %s", rootZ)
end
ops.fbinary = fullfile(rootZ, fs(1).name);
ops.NT = 65600*2;

%% this block runs all the steps of the algorithm
fprintf('Looking for data inside %s \n', rootZ)

% Data preprocess
rez                = preprocessDataSub(ops);

% Drift Correction
rez                = datashift2(rez, 1);

[rez, st3, tF]     = extract_spikes(rez);

rez                = template_learning(rez, tF, st3);

[rez, st3, tF]     = trackAndSort(rez);

rez                = final_clustering(rez, tF, st3);

rez                = find_merges(rez, 1);


%% Save plots
if getOr(ops, 'fig', 1)  
    fig = figure;
    set(gcf, 'Color', 'w')
    
    % plot the shift trace in um
    plot(rez.dshift) %plot(imin * dd)
    box off
    xlabel('batch number')
    ylabel('drift (um)')
    title('Estimated drift traces')
    drawnow
    savefig(fig, fullfile(outDir, 'drift_traces.fig'))
    saveas(fig, fullfile(outDir, 'drift_traces.png'))

    fig=figure;
    spkTh = 10; % same as the usual "template amplitude", but for the generic templates
    tiledlayout(1,2);
    set(gcf, 'Color', 'w')
    st3 = rez.st0;
    % No Drift Correction
    ax1 = nexttile; 
    st_shift = st3(:,2);
    for j = spkTh:100
        % for each amplitude bin, plot all the spikes of that size in the
        % same shade of gray
        ix = st3(:, 3)==j; % the amplitudes are rounded to integers
        plot(st3(ix, 1)/ops.fs, st_shift(ix), '.', 'color', [1 1 1] * max(0, 1-j/40)) % the marker color here has been carefully tuned
        hold on
    end
    title('Raw Spike Map')
    axis tight
    box off

    % With Drift Correction
    ax2 = nexttile;
    batch_id = st3(:,5);
    st_shift = st3(:,2) + rez.dshift(batch_id);% imin(batch_id) * dd;
    for j = spkTh:100
        % for each amplitude bin, plot all the spikes of that size in the
        % same shade of gray
        ix = st3(:, 3)==j; % the amplitudes are rounded to integers
        plot(st3(ix, 1)/ops.fs, st_shift(ix), '.', 'color', [1 1 1] * max(0, 1-j/40)) % the marker color here has been carefully tuned
        hold on
    end
    title('Drift Corrected Spike Map')
    axis tight
    box off
    linkaxes([ax1, ax2], 'xyz')

    xlabel('time (sec)')
    ylabel('spike position (um)')
    
    savefig(fig, fullfile(outDir, 'drift_map.fig'))
    saveas(fig, fullfile(outDir, 'drift_map.png'))

end

%% Save outputs
rez.probeNum = probeNum;
pixelbat_rezToPhy2(rez, outDir);

end

