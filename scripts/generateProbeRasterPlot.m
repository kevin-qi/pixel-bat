dataPath = "/home/batlab/mnt/server4/users/KevinQi/datasets/GridBat/14651/flight_room/raw/240129/ephys";
dataPath = "/home/batlab/mnt/server4/users/KevinQi/datasets/GridBat/29643/signal_check";
dataPath = "/home/batlab/mnt/server4/users/KevinQi/datasets/AngeloBat/00000/signal_check";
recDirs = dir(fullfile(dataPath, "*.rec"));
recDirs(1)
path_to_recording_dir = getChildFolder(dataPath, ".*.rec");

rawSpikes = loadTrodesSpikes(path_to_recording_dir);
voltageScaling = rawSpikes.voltage_scaling;


lfpData = loadTrodesLFP(path_to_recording_dir);


s = 0;
e = 180;

iProbe = 1;

fig = figure('units','normalized','outerposition',[0 0 1 1])
t = tiledlayout(1,2);
t.TileSpacing = 'none';

ephysFs = 30000;
spikeThreshold = 70; % uV

axs(1) = nexttile
for iCh = 1:length(rawSpikes.spikes{iProbe})
    amplitude_uV = rawSpikes.spikeAmplitudes{iProbe}{iCh} * voltageScaling;
    aboveThreshold = amplitude_uV > spikeThreshold;

    chSpikes = double(rawSpikes.spikes{iProbe}{iCh})/ephysFs;
    chSpikes = chSpikes(aboveThreshold);
    chSpikes = chSpikes(logical( (chSpikes > s) .* (chSpikes < e) ));


    depth = rawSpikes.channelPositions{iProbe}(iCh,2);
    y = repmat(depth, size(chSpikes));
    plot(chSpikes,y,'.k','Color', [0 0 0 1], 'MarkerSize', 1);
    hold on
end
title(sprintf("bat %s probe %d", '00000',iProbe))

axs(2) = nexttile;
lfpFs = 1500;
numChannels = size(lfpData.lfp{iProbe},1);
for iCh = 1:4:numChannels
    chLfp = lfpData.lfp{iProbe}(iCh,:);
    t = [s*lfpFs:e*lfpFs]/lfpFs;
    depth = lfpData.channelPositions{iProbe}(iCh,2);

    plot(t,chLfp(s*lfpFs:e*lfpFs)*voltageScaling/5+depth)
    hold on
end

linkaxes(axs(:),'x')
xlim([s,s+10])




