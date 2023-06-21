function createNQPosFiles(dest,animalID,sessionNum, dioFramePulseChannelName)
%createNQPosFiles(dest,animalID,sessionNum)
%createNQPosFiles(dest,animalID,sessionNum, dioFramePulseChannelName)
%
%This function extracts position tracking information and saves data in the NeuroQuery format.
%It is assumed that there is at least one *.videoPositionTracking file in the current directory. 

%
%The function also tries to separate the data by epochs.  This 
%information is acquired from any .trodesComments files found in the 
%current directory, or by lookinbg for gaps in recording data if there is a '*.time' folder in the current directory
%conaining time information about the session (from
%extractTimeBinaryFile.m).
%
%
%dest -- the directory where the processed files should be saved for the
%animal
%animalID -- a string identifying the animal's id (appended to the
%beginning of the files).
%sessionNum -- the session number (in chronological order for the animal)
%dioFramePulseChannelName (optional) -- the name (ID string) of the digital input channel pulses 
%when each frame occured.  Frame times are recalulated from these pulses.NOT WORKING YET.


tFiles = dir(['*.videoPositionTracking']);
currDir = pwd;
sessionString = getTwoDigitNumber(sessionNum);

if isempty(tFiles)
  warning('No position tracking files found.');
  cd(currDir);
  return
end

    

%Get the epoch boundaries.  This assumes that there is at least one
%*.trodesComments file in the current directory with "epoch start" and "epoch end" indicators 
[epochList, fileOffsets] = getEpochs(1);  %assumes that there is at least a 1-second gap in data between epochs if no .trodesComments file is found
%epochs = readTrodesTaskFile();


posMatrix = [];
allTimeStamps = [];
%There may be more than one file in the current directory.  If so, process
%them all, then sort by time.
for fileInd = 1:length(tFiles)
    disp(['Reading file: ',tFiles(fileInd).name]);
    offset = 0;
    tmpFileName = tFiles(fileInd).name;
    dotLoc = strfind(tmpFileName,'.');
    baseName = tmpFileName(1:dotLoc-1);
    tmpPosData = readTrodesExtractedDataFile(tmpFileName);
    
    tmpTimeStamps = readCameraModuleTimeStamps([baseName,'.videoTimeStamps']);
    if isfield(tmpPosData,'clockrate')
        clockrate = tmpPosData.clockrate;
    else
        clockrate = 30000;
    end

    
    for offsetCheck = 1:length(fileOffsets)
        
        if isequal(fileOffsets(offsetCheck).file, [baseName,'.trodesComments']);           
            offset = fileOffsets(offsetCheck).offset;
            disp(['Using offset: ', num2str(offset)]);
        end
    end
    
    tmpTimeStamps = tmpTimeStamps + offset;
    allTimeStamps = [allTimeStamps; tmpTimeStamps];
    
    %Create a matrix to hold the position data from the file
    tmpPosMatrix = zeros(length(tmpPosData.fields(1).data),5);
    tmpPosMatrix(:,1) = double(tmpPosData.fields(1).data + (offset*clockrate))/clockrate;
    for f = 2:length(tmpPosData.fields)
        tmpPosMatrix(:,f) = double(tmpPosData.fields(f).data);
    end
    posMatrix = [posMatrix; tmpPosMatrix];
    
end

%Sort the values by the timestamps.
posMatrix = sortrows(posMatrix,1);

%sort the timestamps
allTimeStamps = sort(allTimeStamps);
disp([num2str(length(allTimeStamps)), ' total frames found.']);

if (nargin > 3)
    %A digital channel was given containing frame pulses
    DIOdir = dir('*.DIO');
    if  (length(DIOdir) ~= 1)
        error('One and only one .DIO directory must exist in this folder. Run extractDioBinaryFiles.m');
    end
    [p,n,e,v] = fileparts(DIOdir(1).name);
    cd(DIOdir(1).name);
    targetFile = [n,'.dio_', dioFramePulseChannelName,'.dat'];
    targetFileCheck = dir(targetFile);
    if (isempty(targetFileCheck))
        cd(currDir);
        error([targetFileCheck, ' does not exist in ', p]);
    end
    pulseData = readTrodesExtractedDataFile(targetFile);
    pulseTimes = pulseData.fields(1).data(find(pulseData.fields(2).data == 1));
    
    %if ((length(pulseTimes)>1)&& (pulseData.fields(2).data(1) == 1)) 
    %    pulseTimes = pulseTimes(2:end);
    %end
    pulseTimes = double(pulseTimes)/pulseData.clockrate;
    disp([num2str(length(pulseTimes)), ' pulses found.']);
    
    
    %Trodes will plut a 0.5 sec gap in frame acquisition when recording 
    %starts to make it easier to align the first pulse with the right
    %frame.  Here, we look for this gap in both the frame time record and
    %the pulse record.
    pulseGapFound = 0;
    firstPulseInd = 1;
    if (length(pulseTimes) > 100)
        findPulseGap = find(diff(pulseTimes(1:100))>.3);
        if (length(findPulseGap) > 0)
            firstPulseAfterGap = pulseTimes(findPulseGap(1)+1);
            pulseGapFound = 1;
            firstPulseInd = findPulseGap(1)+1;
        else
            firstPulseAfterGap = pulseTimes(1);
        end
    else
         firstPulseAfterGap = pulseTimes(1);
    end
    if ((length(allTimeStamps) > 100) && (pulseGapFound == 1))
        findFrameGap = find(diff(allTimeStamps(1:100))>.3);
        if (length(findFrameGap) > 0)
            disp(['First frame', num2str(findFrameGap(1)+1)]);
            firstFrameAfterGap = allTimeStamps(findFrameGap(1)+1);
        else
            firstFrameAfterGap = allTimeStamps(1);
            firstPulseAfterGap = pulseTimes(1);
            firstPulseInd = 1;
        end
    else
         firstFrameAfterGap = allTimeStamps(1);
         firstPulseAfterGap = pulseTimes(1);
         firstPulseInd = 1;
    end
    
    
    
    newTimeStamps = zeros(size(posMatrix,1),1);
    frameCaptureLag = firstFrameAfterGap-firstPulseAfterGap; %Calculate the expected lag between the pulse times and the frame time
        
    %Now we try to match up each frame time (timestamped with trodes
    %software) with the pulse time that most likely corresponded to that
    %frame.
    [lagMin, pulseInd] = min(abs(posMatrix(1,1)-pulseTimes-frameCaptureLag));
    currentPulseInd = pulseInd;
    for frameInd = 1:size(posMatrix,1)
        if (length(pulseTimes) > currentPulseInd+100)
            tmpPulseTimes = pulseTimes(currentPulseInd:(currentPulseInd+100));
        else 
            tmpPulseTimes = pulseTimes(currentPulseInd:end);
        end

        %find the pulse that occured nearest the expected lag time in the
        %past
        lags = posMatrix(frameInd,1)-tmpPulseTimes;
        lags(find(lags < 0)) = inf; %no future pulses are considered
        lags = lags-frameCaptureLag;
        [lagMin, pulseInd] = min(abs(lags));
        
        %keep the pulse index for the frames' new timestamp
        newTimeStamps(frameInd) = currentPulseInd+pulseInd-1;
        
        currentPulseInd = currentPulseInd+pulseInd-1; %only pulses at or after the chosen pulse will be considered for the next loop
        
    end

    %Sometimes, frames piled up and
    %were processed all at once a bit later,
    %which gives them the same nearest pulse.  These need to 
    %distrubuted back to the correct pulses.  
    %We look for times when two frames were given the same pulse, and at
    %least one pulse was skipped right before.
    newTimeStamps(find(diff(newTimeStamps(2:end)) == 0 & diff(newTimeStamps(1:end-1)) > 1)+1) = newTimeStamps(find(diff(newTimeStamps(2:end)) == 0 & diff(newTimeStamps(1:end-1)) > 1)+1)-1;
    
    posMatrix(:,1) = pulseTimes(newTimeStamps);
       
    cd(currDir);
end 


fieldNames = {'time','x1','y1','x2','y2'};

rawpos{sessionNum} = [];
%check if epochs are defined, if so separate by epoch
if (~isempty(epochList))
    for e = 1:size(epochList,1)
        rawpos{sessionNum} = [];
        rawpos{sessionNum}{e} = [];
        epochPosMatrix = posMatrix(find((posMatrix(:,1) >= epochList(e,1)) & (posMatrix(:,1) < epochList(e,2))),:);
        
        for i=1:5
            rawpos{sessionNum}{e} = setfield(rawpos{sessionNum}{e},fieldNames{i},epochPosMatrix(:,i));
        end
        epochString = getTwoDigitNumber(e);
        cd(dest)
        save([animalID,'rawpos',sessionString,'-',epochString], 'rawpos');
        cd(currDir);
    end    
else
    for i=1:5
        rawpos{sessionNum} = setfield(rawpos{sessionNum},fieldNames{i},posMatrix(:,i));
    end
    cd(dest)
    save([animalID,'rawpos',sessionString], 'rawpos');
    cd(currDir);
end


%---------------------------------------------------

function numString = getTwoDigitNumber(input)
    
if (input < 10)
    numString = ['0',num2str(input)];
else
    numString = num2str(input);
end


    
