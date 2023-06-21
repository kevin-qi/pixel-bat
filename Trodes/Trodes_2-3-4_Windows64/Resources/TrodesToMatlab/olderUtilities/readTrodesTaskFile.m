function [taskData, fileTimeOffsets] = readTrodesTaskFile()
%taskData = readTrodesTaskFile()
%Reads in a file which gives timing and descriptive info about a recording session. 
%Each line in the given text file is processed separately.
%You can break the recording up into separate epochs with 'TIMESTAMP epoch start' 
%and 'TIMESTAMP epoch end' 
%You can also add events like this 'TIMESTAMP event_name_no_spaces
%description' and general epoch desriptions like this 'fieldname_no_spaces value'
%
%Assumes there is at least one .trodesComments file in the current
%directory.  If multiple .trodesComments exist
% The output will be
%stiched together sorted by the time when the files were created. If a file
%needs an offset added to each timestamp, the first line of the file should
%desclare this like this: 'offset TIMESTAMP'  
%
%
%Example input file:
% time reset
% 2:00 epoch start 
% task withdrug
% 15:04 injection saline
% 30:00 epoch end
% 35:00 epoch start 
% task afterdrug
% 1:09:10 epoch end


%There may be more than one .trodesComments file in the current dir. Sort
%them by creation date.
commentsFiles = dir(['*.trodesComments']);

fileDates = [];
sortedNames = [];
firstTimestamps = [];

%We need to know the order of the comments files.  For this we find the
%first timestamp in each.
fileNames = {};
for i=1:length(commentsFiles)

    filename = commentsFiles(i).name;
    if (~isequal(filename(1),'.') )
        fileNames{end+1} = commentsFiles(i).name;
        fid = fopen(filename,'r');

        if (fid ~= -1)
            offset = 0;
            tmpTimeStamp = -1;
            while 1
                tline = fgetl(fid);
                if ~ischar(tline)
                    break
                end

                %Check if the first entry is a timestamp
                [timestampstring, remainder] = strtok(tline);
                timestamp = str2num(timestampstring);
                if isempty(timestamp)
                    timestamp = readTimeString(timestampstring);
                else
                    timestamp = timestamp/30000; %convert to seconds
                end



                if (~isempty(timestamp) && (tmpTimeStamp==-1))
                    %We have found the first timestamp in the file
                    tmpTimeStamp = timestamp;
                else
                    %check if there is an offset
                    if isequal(timestampstring,'time')
                        remainder = remainder(2:end);
                        if isequal(remainder,'reset')
                            offset = getOffset(filename);

                        end
                    end
                end

            end
            fclose(fid);

            if (tmpTimeStamp > -1)
                firstTimestamps(end+1,1) = tmpTimeStamp+offset;
            else
                firstTimestamps(end+1,1) = -1;
            end

        end
    end

end

[s, sind] = sort(firstTimestamps);
for i=1:length(sind)
    %sortedNames{i} = commentsFiles(sind(i)).name;
    sortedNames{i} = fileNames{sind(i)};
end

currentEpoch = 0;
offset = 0;
inEpoch = 0;
taskData{1} = [];
lastTimestamp = 0;
taskData = [];
fileTimeOffsets = [];

%Process each file
for fInd=1:length(sortedNames)
    filename = sortedNames{fInd};
    fileTimeOffsets(fInd).file = filename;
    fileTimeOffsets(fInd).offset = 0;
    
    fid = fopen(filename,'r');
    
    if (fid ~= -1)
        offset = 0;
        while 1
            tline = fgetl(fid);
            if ~ischar(tline)
                break
            end

            %Check if the first entry is a timestamp
            [timestampstring, remainder] = strtok(tline);
            timestamp = str2num(timestampstring);
            if isempty(timestamp)
                timestamp = readTimeString(timestampstring);
            else
                timestamp = timestamp/30000; %convert to seconds
            end


            %If no timestamp, then the first entry is the fieldname
            if (isempty(timestamp))
                fieldName = timestampstring;
            else
                timestamp = timestamp+offset;
                if (timestamp > lastTimestamp)
                    lastTimestamp = timestamp;
                else
                    error(['Error in comments read: all timestamps must occur in chronological order. File: ',filename]);
                end
                remainder = remainder(2:end);
                [fieldName, remainder] = strtok(remainder);
            end


            if (~isempty(fieldName))

                if isequal(lower(fieldName),'epoch')
                    remainder = remainder(2:end);
                    [epochDescript, remainder] = strtok(remainder);
                    if isequal(lower(epochDescript), 'start')
                        if (inEpoch == 0)
                            currentEpoch = currentEpoch+1;
                            taskData{currentEpoch} = [];
                            taskData{currentEpoch}.events = [];
                            taskData{currentEpoch}.starttime = timestamp;
                            inEpoch = 1;
                        else
                            fclose(fid);
                            error(['Error in comments read: epoch start without an end to the previous epoch. Filename: ',filename]);
                        end


                    elseif isequal(lower(epochDescript), 'end')
                        if (inEpoch == 1)

                            taskData{currentEpoch}.endtime = timestamp;
                            inEpoch = 0;
                        else
                            fclose(fid);
                            error(['Error in comments read: epoch end without a start given. Filename: ',filename]);
                        end
                    end
                elseif isempty(timestamp)
                    if isequal(fieldName,'time')
                        remainder = remainder(2:end);
                        if isequal(remainder,'reset')
                             offset = getOffset(filename);
                             fileTimeOffsets(fInd).offset = offset;
                      
                        end
                    else
                        if (inEpoch == 0)
                            currentEpoch = currentEpoch+1;
                            taskData{currentEpoch} = [];
                            taskData{currentEpoch}.events = [];
                            taskData{currentEpoch}.starttime = [];
                            inEpoch = 1;
                        end

                        remainder = remainder(2:end);
                        %[fieldValue, remainder] = strtok(remainder);
                        if ~isempty(str2num(remainder))
                            remainder = str2num(remainder);
                        end
                        
                        taskData{currentEpoch} = setfield(taskData{currentEpoch},fieldName,remainder);
                        
                    end
                else
                    if (inEpoch == 0)
                        currentEpoch = currentEpoch+1;
                        taskData{currentEpoch} = [];
                        taskData{currentEpoch}.events = [];
                        taskData{currentEpoch}.starttime = [];
                        inEpoch = 1;
                    end
                    tmpEvent.name = fieldName;
                    tmpEvent.time = timestamp;
                    remainder = remainder(2:end);
                    %[fieldValue, remainder] = strtok(remainder);
                    if ~isempty(str2num(remainder))
                        remainder = str2num(remainder);
                    end
                    tmpEvent.description = remainder;
                    taskData{currentEpoch}.events = [taskData{currentEpoch}.events tmpEvent];
                end
            end

        end
        fclose(fid);
       
    else
        error(['Error reading the file. Filename: ',filename]);
    end
end


%used to translate a time string (23:55) to seconds
function timeInSec = readTimeString(timeString)

t = [0 0 0 0 0 0];

colons = findstr(timeString,':');
if (isempty(colons))
    timeInSec = [];
    return;
end
startind = length(timeString);
count = 6;
for j = length(colons):-1:1
    t(count) = str2num(timeString((colons(j)+1):startind));
    startind = colons(j)-1;
    count = count-1;
end
t(count) = str2num(timeString(1:colons(1)-1));
timeInSec = etime(t,[0 0 0 0 0 0]);

function offset = getOffset(fName)
currDir = pwd;
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
dotLoc = strfind(fName,'.');
baseName = fName(1:(dotLoc(1)-1));
datFiles = dir([baseName,'.offset.txt']);

if (isempty(datFiles))
    cd(currDir);
    error(['No offset file found in times folder. Looking for ',baseName,'.offset.txt']);
end

oFID = fopen([baseName,'.offset.txt'],'rb','ieee-le');
headerText = fread(oFID,200,'uint8');
fclose(oFID);
headerText = char(headerText');
offsetRead = str2num(headerText);

if (isempty(offsetRead))
    cd(currDir);
    error(['Offset value could not be read in file: ',baseName,'.offset.txt']);
end
offset = double(offsetRead)/30000;
cd(currDir);

