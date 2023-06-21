function dataIndices = splitVideoInfoFile(filename,timegap,fieldname)
%dataIndices = splitVideoInfoFile(filename,timegap,fieldname)
%dataIndices = splitVideoInfoFile(filename,dataIndices)
%This function is used to split the files associated with video timestamps
%and position tracking data. Files are created with _splitX appended to the
%base name.
%
%filename -- a string containing the name of the file to split, for example
%            'myFile.1.videoTimeStamps'
%
%timgap -- the maximum number of clock ticks (usually sampled at 30 kHz) allowed before a split occurs
%
%fieldname -- a string containing the field name where the system clock
%             values are stored.  For .videoPositionTracking and .videoTimeStamps files this is 'time'
%             and for .videoTimeStamps.cameraHWSync file it is
%             'PosTimestamp'
%
%dataIndices -- used for files that do not have a time based field, such as
%.cameraHWFrameCount files.  You can piggyback off of the same call to an
%associated file with time.  Like this:
%
%ind = splitVideoInfoFile('gapTest.1.videoTimeStamps',100000,'time');
%ind2 = splitVideoInfoFile('gapTest.1.videoTimeStamps.cameraHWFrameCount',ind);


fid = fopen(filename,'rb','ieee-le');

headerText = fread(fid,10000,'uint8');
headerText = char(headerText');
endHeaderLoc = strfind(headerText,'<End settings>')+14;

dotLoc = strfind(filename,'.');
newPreName = filename(1:dotLoc(1)-1);
newPostName = filename(dotLoc:end);


headerText = headerText(1:endHeaderLoc);
fclose(fid);

fileData = readTrodesExtractedDataFile(filename);

usetimefield = 1;
if (nargin < 3)
    usetimefield = 0;
end

dataIndices = [];

if (usetimefield)
    timeField = [];
    %look for the designated time field
    for i = 1:length(fileData.fields)
        if (isequal(fileData.fields(i).name,fieldname))
            timeField = i; %this is the field containing time
        end
    end
    
    if (isempty(timeField))
        error('No field found matching the fieldname');
    end
    
    %find the gaps
    splitGaps = find(diff(fileData.fields(timeField).data)>=timegap);
    
    %for each gap, create a new file with the binary data preceding the gap
    if (~isempty(splitGaps))
        splitGaps = [0;splitGaps];
        
        for i=1:length(splitGaps)
            %create the new file
            splitfid = fopen([newPreName,'_split',num2str(i),newPostName],'w','ieee-le');
            %write the header to the file
            fwrite(splitfid,headerText);
            if (i < length(splitGaps))
                dataSet = [splitGaps(i)+1:splitGaps(i+1)];
            else
                dataSet = [splitGaps(i)+1:length(fileData.fields(timeField).data)];
            end
            dataIndices{i} = dataSet;
            %write the binary data to the file
            for currentDataInd = dataSet
                for currentField = 1:length(fileData.fields)
                    fwrite(splitfid, fileData.fields(currentField).data(currentDataInd),fileData.fields(currentField).type);
                end
            end
            %close the file
            fclose(splitfid);
        end
        
    end
else
    dataIndices = timegap;
    if (~isempty(dataIndices))
        
        
        for i=1:length(dataIndices)
            %create the new file
            splitfid = fopen([newPreName,'_split',num2str(i),newPostName],'w','ieee-le');
            %write the header to the file
            fwrite(splitfid,headerText);
            
            %write the binary data to the file
            for currentDataInd = dataIndices{i}
                for currentField = 1:length(fileData.fields)
                    fwrite(splitfid, fileData.fields(currentField).data(currentDataInd),fileData.fields(currentField).type);
                end
            end
            %close the file
            fclose(splitfid);
        end
        
    end
end

