function createNQDioFiles(dest,animalID,sessionNum)
%createNQDioFiles(dest,animalID,sessionNum)
%
%This function saves DIO data in the NeuroQuery format. It is assumed that there is
%one (and only one) folder named '*DIO' in the current working
%directory that contains .dat files (result of extractDioBinaryFiles.m).
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
    if filesInDir(i).isdir && ~isempty(strfind(filesInDir(i).name,'.DIO'))
        targetFolder = filesInDir(i).name;
        break;
    end
end

if isempty(targetFolder)
    error('DIO folder not found in this directory.');
end

epochList = getEpochs(1);  %assumes that there is at least a 1-second gap in data between epochs if no .trodesComments file is found
cd(targetFolder);

dio = [];
dio{sessionNum} = [];
dioFiles = dir('*.dat');

if isempty(dioFiles)
  warning('No DIO files found.');
  cd(currDir);
  return
end

disp('Processing DIO files...');

displayOrder = [];
for diofileInd = 1:length(dioFiles)
    
    [filePath,prefixName,ext] = fileparts(dioFiles(diofileInd).name);
    tmpData = readTrodesExtractedDataFile(dioFiles(diofileInd).name);
    displayOrder(end+1,1) = tmpData.display_order; %1-based value for the displayed channel order
end
[junk, displayOrder] = sort(displayOrder);

for diofileInd = 1:length(displayOrder)
    
   
    tmpData = readTrodesExtractedDataFile(dioFiles(displayOrder(diofileInd)).name);
    %nt = strfind(prefixName,'nt');
    %channelID = str2num(prefixName(nt(end)+2:end));
    %channelString = getTwoDigitNumber(nTrodeNum);
    channelID = tmpData.id;
    
    for e = 1:size(epochList,1)
        
        epochString = getTwoDigitNumber(e);
        currentSession = sessionNum;
        sessionString = getTwoDigitNumber(sessionNum);       
        currentTimeRange = epochList(e,:);
        if (length(dio{currentSession}) < e)
             dio{currentSession}{e} = [];
        end
        
        %we change the start and end times to match the actual first and last data points in the recording
        
        %epochDataInd = find((timeData.timestamps >= currentTimeRange(1))&(timeData.timestamps < currentTimeRange(2)));
        %starttime = timeData.timestamps(epochDataInd(1));
        %endtime = timeData.timestamps(epochDataInd(end));
        
        starttime = currentTimeRange(1,1);
        endtime = currentTimeRange(1,2);
        
        t = double(tmpData.fields(1).data)/tmpData.clockrate;
        includedTimes = find((t >= starttime) & (t <= endtime));
        if (length(dio{currentSession}{e}) < diofileInd)
             dio{currentSession}{e}{diofileInd} = [];
        end
        dio{currentSession}{e}{diofileInd} = setfield(dio{currentSession}{e}{diofileInd},'time',t(includedTimes));
        dio{currentSession}{e}{diofileInd} = setfield(dio{currentSession}{e}{diofileInd},'state',tmpData.fields(2).data(includedTimes));
        dio{currentSession}{e}{diofileInd} = setfield(dio{currentSession}{e}{diofileInd},'id',channelID);
        dio{currentSession}{e}{diofileInd} = setfield(dio{currentSession}{e}{diofileInd},'direction',tmpData.direction);
       
     
    end
    
end
cd(dest)
save([animalID,'dio',sessionString], 'dio');
cd(currDir);





%----------------------------------------------------------
%Helper functions
%-----------------------------------------------------------


function numString = getTwoDigitNumber(input)
    
if (input < 10)
    numString = ['0',num2str(input)];
else
    numString = num2str(input);
end
    

