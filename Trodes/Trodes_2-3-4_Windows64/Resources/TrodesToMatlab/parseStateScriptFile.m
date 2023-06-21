function events = parseStateScriptFile(fileName, inputWatch, timeConvert)
%events = parseStateScriptFile(fileName)
%events = parseStateScriptFile(fileName, inputWatch)
%events = parseStateScriptFile(fileName, inputWatch, timeConvert)
%
%This function parses the output of a stateScript session.
%fileName -- the name of the stateScript output file
%inputWatch -- if changes in some of the 8 input ports should be ignored,
%              indicate an array of the ports to watch (i.e., 1:3)
%
%timeConvert -- optional matrix used to convert the timestamps to other
%               values. The matrix is a two column lookup table with the
%               statescript time in the first column and the converted time
%               in the second. If an exact match is not found, linear
%               interpolation is used.
%
%events is a structure array containing the parsed information for each
%line in the file.


if (nargin < 3)
    timeConvert = [];
end
if (nargin < 2)
    inputWatch = [];
end

fid=fopen(fileName);
events = [];
numEvents = 0;
lastInState = [];
lastOutState = [];
while 1
    tline = fgetl(fid);
    if ischar(tline)
        tokNum = 0;
        tokCell = [];
        while 1
            
            [tmp, tline] = strtok(tline);
            if (~isempty(tmp))
                tokNum = tokNum+1;
                tokCell{tokNum} = tmp;
            end
            if isempty(tline)
                % all tokens in the line have been counted
                
                tmpTime = str2num(tokCell{1});
                
                if (~isempty(tmpTime) && (length(tokCell)>1)&& (~isequal(tokCell{2},'RFsync'))) %only parse lines that start with the time stamp
                    
                    numEvents = numEvents+1;
                    if ~isempty(timeConvert)
                        tmpTime = interp1(timeConvert(:,1),timeConvert(:,2),tmpTime,'linear','extrap');
                    end
                    events(numEvents).time = tmpTime;
                    events(numEvents).inStateDiff = [0 0 0 0 0 0 0 0];
                    events(numEvents).outStateDiff = [0 0 0 0 0 0 0 0];
                    events(numEvents).message = [];
                    events(numEvents).inState = lastInState;
                    events(numEvents).outState = lastOutState;
                    
                                                          
                    if ((length(tokCell)==3) && (~isempty(str2num(tokCell{2}))) && (~isempty(str2num(tokCell{3}))))
                        events(numEvents).inState = bitget(str2num(tokCell{2}),1:8); %get the binary input state of all 8 ports
                        if (~isempty(lastInState));
                            events(numEvents).inStateDiff = events(numEvents).inState - lastInState;
                        else
                            events(numEvents).inStateDiff = [0 0 0 0 0 0 0 0];
                        end
                        lastInState = events(numEvents).inState;
                        events(numEvents).outState = bitget(str2num(tokCell{3}),1:8); %get the binary output state of all 8 ports
                        if (~isempty(lastOutState));
                            events(numEvents).outStateDiff = events(numEvents).outState - lastOutState;
                        else
                            events(numEvents).outStateDiff = [0 0 0 0 0 0 0 0];
                        end
                        lastOutState = events(numEvents).outState;
                    else %add the message to the event
                        events(numEvents).message = [];
                        for i = 2:length(tokCell)
                            events(numEvents).message = [events(numEvents).message, tokCell{i}];
                            if (i < length(tokCell))
                                events(numEvents).message = [events(numEvents).message, ' '];
                            end
                        end
                    end
                end
                break;
            end
        end
        
    else
        break;    
    end
   
end

%if some ports are changing but should be ignored, we only keep the
%relavent events
if (~isempty(inputWatch))
    tmpEvents = events;
    events = [];
    eventNum = 0;
    for i = 1:length(tmpEvents)
        if ((~isempty(tmpEvents(i).message)) || (sum(abs(tmpEvents(i).inStateDiff(inputWatch)))>0) || (sum(abs(tmpEvents(i).outStateDiff))>0))
            
            %tmpInStateDiff = tmpEvents(i).inStateDiff(inputWatch);
            eventNum = eventNum+1;
            events(eventNum).time = [];
            events(eventNum).inStateDiff = [];
            events(eventNum).outStateDiff = [];
            events(eventNum).message = [];
            events(eventNum).inState = [];
            events(eventNum).outState = [];
            events(eventNum) = tmpEvents(i);
            %events(eventNum).inStateDiff = tmpInStateDiff;
        end
    end
end

fclose(fid);
