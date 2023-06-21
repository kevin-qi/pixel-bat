function createMatclustFile(fileName,destFolder)
%createMatclustFile(fileName,destFolder)
%saves the spike data in one nTrodes's extracted file for spikes as a file that matclust can open
%filename -- the name to give the files (i.e, 'tetrode1')
%destFolder -- the path to where the new file will be saved

maxSamplesToPeak = 17;
%maxSamplesToPeak = 40;
minSamplesToPeak = 10;


if (nargin < 2)
    destFolder = pwd;
end

data = readTrodesExtractedDataFile(fileName);
if (isempty(data))
     disp(['File read error: ',fileName]);
    return;
end
if isempty(strfind(data.description, 'Spike waveforms'))
    disp(['File does not contain spike waveforms: ',fileName]);
    return;
end

spikeTimes = double(data.fields(1).data)/data.clockrate;

%put all spikes into one 3d matrix ([spikeind spikelength channel])
spikeWaveforms = zeros(length(spikeTimes),data.fields(2).columns,length(data.fields)-1);
peakVals = [];
peakInds = [];
for fieldInd = 2:length(data.fields) 
    spikeWaveforms(:,:,fieldInd-1) = double(data.fields(fieldInd).data)*data.voltage_scaling;
    [tmpPeakVals, tmpPeakInds] = max(spikeWaveforms(:,:,fieldInd-1),[],2);
    peakVals = [peakVals tmpPeakVals];
    peakInds = [peakInds tmpPeakInds];
end

[junk, maxChannels] = max(peakVals,[],2);

keeperPeakInds = zeros(length(maxChannels),1);
for i=1:length(maxChannels)
    keeperPeakInds(i) = peakInds(i,maxChannels(i));
end
keeperPeakInds = find((keeperPeakInds <= maxSamplesToPeak)&(keeperPeakInds >= minSamplesToPeak));
spikeWaveforms = spikeWaveforms(keeperPeakInds,:,:);
spikeTimes = spikeTimes(keeperPeakInds);



windowSize = size(spikeWaveforms,2);
midpoint = round(windowSize/2);

if (size(spikeWaveforms,1) > 100)
    
    scores = [];
    haveStatsToolbox = which('pca');
       
    %if the user has access to the 'pca' function, calculate the 1st and
    %2nd priciple components
    if ~isempty(haveStatsToolbox)
        for ch = 1:size(spikeWaveforms,3)
            pcaWaves = spikeWaveforms(:,:,ch);
            for i = 1:size(pcaWaves,2)
                pcaWaves(:,i) = pcaWaves(:,i)-mean(pcaWaves(:,i));
            end
            
            coef = pca(pcaWaves);
            %coef = princomp(pcaWaves);
            coef = coef(:,1:2); %first two components
            %coef = coef(:,1); %just keep the 1st component
            scores = [scores (pcaWaves*coef)];
           
        end
    end
    
    
    filedata.paramnames = {'Time'};
    filedata.params = [spikeTimes];
    for i = 1:size(spikeWaveforms,3)
        filedata.paramnames = [filedata.paramnames,['Peak ',num2str(i),' (uV)']];
        filedata.params = [filedata.params max(spikeWaveforms(:,:,i),[],2)];
    end
    for i = 1:size(spikeWaveforms,3)
        filedata.paramnames = [filedata.paramnames,['Trough ',num2str(i),' (uV)']];
        filedata.params = [filedata.params min(spikeWaveforms(:,:,i),[],2)];
    end
    for i = 1:size(spikeWaveforms,3)
        filedata.paramnames = [filedata.paramnames,['Peak to trough ',num2str(i),' (uV)']];
        filedata.params = [filedata.params max(spikeWaveforms(:,:,i),[],2)-min(spikeWaveforms(:,:,i),[],2)];
    end
    
    if ~isempty(haveStatsToolbox)
        for i = 1:size(spikeWaveforms,3)
            filedata.paramnames = [filedata.paramnames,['1stPCA ',num2str(i)]];
            filedata.paramnames = [filedata.paramnames,['2ndPCA ',num2str(i)]];
        end
    end
    filedata.params = [filedata.params scores];
       
    waves = permute(spikeWaveforms,[2 3 1]);
else
    disp('Not enough spike events in file');
    filedata = [];
    waves = [];
    
end


%-----------------------------------
if (~isempty(filedata))
    saveName = fullfile(destFolder,['param_nt',num2str(data.ntrode_id)]);
    waveName = fullfile(destFolder,['waves_nt',num2str(data.ntrode_id)]);
    filedata.filename = waveName;
    save(saveName, '-v7.3', 'filedata');
    save(waveName, '-v7.3', 'waves');
end
