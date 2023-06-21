function createNQLFPFiles(dest,animalID,sessionNum)
%createNQLFPFiles(dest,animalID,sessionNum)
%
%This function extracts LFP information and saves data in the NeuroQuery format.
%It is assumed that there is
%one (and only one) folder named '*.LFP' in the current working
%directory that contains binary files for each LFP channel (result of extractLFPBinaryFiles.m)  
%
%The function also assumes that there is a '*.time' folder in the current directory
%conaining time information about the session (from
%extractTimeBinaryFile.m).
%
%
%dest -- the directory where the processed files should be saved for the
%animal
%animalID -- a string identifying the animal's id (appended to the
%beginning of the files).
%sessionNum -- the session number (in chronological order for the animal)


currDir = pwd;
filesInDir = dir;
targetFolder = [];
for i=3:length(filesInDir)
    if filesInDir(i).isdir && ~isempty(strfind(filesInDir(i).name,'.LFP'))
        targetFolder = filesInDir(i).name;
        break;
    end
end

if isempty(targetFolder)
    error('LFP folder not found in this directory.');
end

epochList = getEpochs(1);  %assumes that there is at least a 1-second gap in data between epochs

cd(targetFolder);
datFiles = dir('*.LFP_*.dat');

if (isempty(datFiles))
    cd(currDir);
    error('No LFP binary files found in LFP folder.');
end

timeDatFiles = dir('*.timestamps.dat');

if (isempty(datFiles))
    cd(currDir);
    error('No timestamps file found in LFP folder.');
end
timeData = readTrodesExtractedDataFile(timeDatFiles(1).name);
timeData = double(timeData.fields(1).data) / timeData.clockrate;

for datFileInd = 1:length(datFiles)
    disp(datFiles(datFileInd).name);
    data = readTrodesExtractedDataFile(datFiles(datFileInd).name);
    
    nTrodeNum = data.ntrode_id;
    channelNum = data.ntrode_channel_1based;
    nTrodeString = getTwoDigitNumber(nTrodeNum);
    channelString = getTwoDigitNumber(channelNum);
        
    for e = 1:size(epochList,1)
        epochString = getTwoDigitNumber(e);
        currentSession = sessionNum;
        sessionString = getTwoDigitNumber(sessionNum);
        currentTimeRange = epochList(e,:);
        
        lfp = []; 
        epochDataInd = find((timeData >= currentTimeRange(1))&(timeData < currentTimeRange(2)));
        
        lfp{currentSession}{e}{nTrodeNum}.timerange = [timeData(epochDataInd(1)) timeData(epochDataInd(end))]; 
        %redundant notation
        lfp{currentSession}{e}{nTrodeNum}.starttime = timeData(epochDataInd(1));
        lfp{currentSession}{e}{nTrodeNum}.endtime = timeData(epochDataInd(end));       
        lfp{currentSession}{e}{nTrodeNum}.samprate = data.clockrate/data.decimation;
        lfp{currentSession}{e}{nTrodeNum}.nTrode = nTrodeNum;
        lfp{currentSession}{e}{nTrodeNum}.nTrodeChannel = channelNum;
        lfp{currentSession}{e}{nTrodeNum}.data = double(data.fields(1).data(epochDataInd,1)) * data.voltage_scaling;
        
        lfpdir = pwd;
        cd(dest);
        save([animalID,'lfp',sessionString,'-',epochString,'-',nTrodeString,'.mat'],'lfp');
        cd(lfpdir);
    end
end
cd(currDir);    

function numString = getTwoDigitNumber(input)
    
if (input < 10)
    numString = ['0',num2str(input)];
else
    numString = num2str(input);
end
    
