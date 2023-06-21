function [epochTimes, fileTimeOffsets] = getEpochs(maxTimeGap)
%
%epochTimes = getEpochs(maxTimeGap)
%
%This function will calculate a list of epoch start and end times based on
%the maximum allowed time gap in recording samples.  It is assumed that
%recording is paused between epochs, creating a gap in time. It also
%assumes that there is one (and only one) '*.time' folder in the current working directory
%that contains the extracted time information for the recording. Use
%'extractTimeBinaryFile.m' to create this file from the raw .rec file.


epochTimes = [];
if (nargin < 1)
    maxTimeGap = 1; %default is 1 sec
end

currDir = pwd;


[t, fileTimeOffsets] = readTrodesTaskFile();
if ~isempty(t)
    allepochsgood = 1;
    for (ep = 1:length(t))
        if ~isempty(t{ep}.starttime) && ~isempty(t{ep}.endtime)
            epochTimes = [epochTimes; [t{ep}.starttime t{ep}.endtime]];
        else
            allepochsgood = 0;
        end
    end
    if (allepochsgood)
        return
    else
        epochTimes = [];
    end
    
end



filesInDir = dir;
timeFolder = [];
for i=3:length(filesInDir)
    if filesInDir(i).isdir && ~isempty(strfind(filesInDir(i).name,'.time'))
        timeFolder = filesInDir(i).name;
        break;
    end
end

if isempty(timeFolder)
    error('Time folder not found in this directory.');
end

cd(timeFolder);

datFiles = dir('*.time.dat');

if (isempty(datFiles))
    cd(currDir);
    error('No time binary file found in spikes folder.');
elseif length(datFiles) > 1
    cd(currDir);
    error('More than one .time folder found in the current directory.');
end

t = readTrodesExtractedDataFile(datFiles(1).name);
tempPeriods = t.fields(1).data;
%Convert time to seconds
tempPeriods = double(tempPeriods) / t.clockrate;

epochTimes = [];
lastEnd = 0;
for i=1:size(tempPeriods,1)
    if (i==1)
        %first period
        epochTimes(1,1) = tempPeriods(i,1);

    else
        %check if the gap was larger then the input gap, if so add an epoch
        if (tempPeriods(i,1)-lastEnd) > maxTimeGap
            epochTimes(end,2) = lastEnd;
            epochTimes(end+1,1) = tempPeriods(i,1);
        end
    end
    lastEnd = tempPeriods(i,2);
    if (i == size(tempPeriods,1))
        %last period, so close off last epoch
        epochTimes(end,2) = lastEnd;
    end

    end


cd(currDir);