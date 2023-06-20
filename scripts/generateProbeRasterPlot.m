path_to_recording_dir = "/media/batlab/BatDrive/FlyingPixels/data/29968/raw/230525/ephys/20230525_124737.rec";

spikeData = loadSpikeData(path_to_recording_dir);

depths = spikeData.good_units.depth;
num_unit = length(spikeData.spikeTimes_usec);

%mkdir('Extracted')
%save('Extracted\SingleUnits.mat','good_unit','T', sp_unit, sp_times)
s = 200*1e6;
e = 260*1e6;

dCA1 = [0 3000];
cortex = [4000 6500];
dg = [6800 10000];
colors = [[127,201,127]; [190,174,212]; [253,192,134]; [150,150,150]]/255;

fig = figure();
for i = 1:num_unit
    
    x = spikeData.spikeTimes_usec{i};
    isDuring = logical( (x < e) .* (x > s) );
    x = (x(isDuring) - s)/1e6;
    y = repmat(depths(i),size(x));
    depth = depths(i);
    if(depth > dCA1(1) && depth < dCA1(2))
        color = colors(1,:);
    elseif(depth > cortex(1) && depth < cortex(2))
        color = colors(2,:);
    elseif(depth > dg(1) && depth < dg(2))
        color = colors(3,:);
    else
        color = colors(4,:);
    end
    plot(x,y,'.k','Color', [color 1], 'MarkerSize', 1);
    hold on;
end
xlim([0 60]);
xticks([0 30 60]);
ylim([0 7780])
ylabel('Distance from Probe Tip (um)');
xlabel('time (s)');

