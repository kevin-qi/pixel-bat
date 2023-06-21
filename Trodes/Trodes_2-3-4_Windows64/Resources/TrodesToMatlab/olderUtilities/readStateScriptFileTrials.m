function trials = readStateScriptFileTrials(fileName,varargin)

%readStateScriptFileTrials(fileName,varargin)
%readStateScriptFileTrials('an123_121214_scLog.txt','inputWatch',[1:3],'trialStartTerms',{'initiate'},'trialEndTerms',{'initiate'},'checkMessageTerms',myMessageTerms)
%
%'trialStartTerms' flag requires a cell array containing search strings that trigger a new trial in the output
%
%'trialEndTerms' flag requires a cell array containing search strings that trigger the end of a trial in the output
%
%'inputWatch' flag requires a vector of input ports that require
%                   monitoring. If these ports change, the events are
%                   logged in the output.
%'checkMessageTerms' flag is used to create custom fields in the output. The algorithms searches for strings to match conditions. 
%                    There are the following 'types' allowed: boolean, number, persistent, and event. It requires an input array with the following
%                    structure:
%                    BOOLEAN TYPE CAN HAVE TRUE AND FALSE STRING CONDITIONS
%                    myMessageTerms(1).fieldname = 'rewarded'
%                    myMessageTerms(1).type = 'boolean'  
%                    myMessageTerms(1).truestring = {'rewarded'}
%                    myMEssageTerms(1).falsestring = {'not rewarded'}
%  
%                   SOME VARIABLES CHANGES OUTSIDE OF TRIALS. USE
%                   PERSISTENT TYPE TO LOG THE LAST RECORDED VALUE
%                   messageterms(2).fieldname = 'rewardProb1';
%                   messageterms(2).type = 'persistent';
%                   messageterms(2).string = 'leftRewardProbability';
%
%                   MULTIPLE STRINGS CAN TRIGGER BOOLEAN TRUE OR FALSE 
%                   messageterms(4).fieldname = 'error';
%                   messageterms(4).type = 'boolean';
%                   messageterms(4).truestring = {'Error right side' 'Error left side'};
%                   messageterms(4).falsestring = [];
%
%                   LOG ALL DEFINED EVENT TIMES 
%                   messageterms(5).fieldname = 'inittypes';
%                   messageterms(5).type = 'events';
%                   messageterms(5).events = {'Played left' 'Played right'};
%
%'timeConvert'  flag for optional matrix used to convert the timestamps to other
%               values. The matrix is a two column lookup table with the
%               statescript time in the first column and the converted time
%               in the second. If an exact match is not found, linear
%               interpolation is used.
%

trialStartTerms = []; %a cell array of strings that indicate the start of a trial
trialEndTerms = []; %a cell array of strings that indicate the end of a trial
checkMessageTerms = [];
inputWatch = []; %a vector declaring which input ports to pay attention to (empty = all)
timeConvert = [];
trials = {[]};

for option = 1:2:length(varargin)-1
    switch varargin{option}
       
        case 'trialStartTerms'
            trialStartTerms = varargin{option+1};
        case 'trialEndTerms'
            trialEndTerms = varargin{option+1};            
        case 'inputWatch'
            inputWatch = varargin{option+1};
        case 'timeConvert'
            timeConvert = varargin{option+1};
        case 'checkMessageTerms'
            checkMessageTerms = varargin{option+1};
        otherwise
            error(['Option ''', varargin{option}, ''' not defined']);
    end
end


events = parseStateScriptFile(fileName,inputWatch,timeConvert);

inTrial = 0;
trialEventInds = [0 0];
currentTrial = 0;

%find the start and end events associated with each trial,
%based on the given strings.  Search the 'message' field for
%the strings. If the start and end terms contain the same string,
%that works too, as trials will first end, then begin on the
%same event.
persistantVals = zeros(length(checkMessageTerms),1); %keep track of state variables
for i = 1:length(events)
    if ~isempty(events(i).message)
        foundStartTerm = 0;
        foundEndTerm = 0;
        %search for end terms
        for j = 1:length(trialEndTerms)
            if ~isempty(strfind(events(i).message,trialEndTerms{j}))
                foundEndTerm = 1;               
            end
        end
        %if an end term was found, mark the event index
        if (foundEndTerm)
            if (inTrial)
                trialEventInds(currentTrial,2) = i;
            end
            inTrial = 0;           
        end
        %search for start terms
        for j = 1:length(trialStartTerms)
            if ~isempty(strfind(events(i).message,trialStartTerms{j}))
                foundStartTerm = 1;               
            end
        end
        
        %now we look to see if the event contains a variable name that we
        %need to keep track of on a PERSISTENT level (see above)
        for k = 1:length(checkMessageTerms)
            if (isequal(checkMessageTerms(k).type,'persistent'))
                if ~isempty(checkMessageTerms(k).string) && ~isempty(strfind(events(i).message,checkMessageTerms(k).string))
                    equalLoc = strfind(events(i).message,'='); %find where the equal sign is.  The number to store is after that
                    if ~isempty(equalLoc)
                        try
                            persistantVals(k) = str2num(events(i).message(equalLoc+1:end));
                        catch
                            keyboard;
                        end
                    end
                    break;
                end
            end
            
           
        end
            %if a start term was found, mark the event index
        if (foundStartTerm)            
            inTrial = 1;
            currentTrial = currentTrial+1;
            trialEventInds(currentTrial,1) = i;
            if (currentTrial > 1)
                trials(length(trials)+1) = parseTrial(events,trialEventInds(currentTrial-1,:),checkMessageTerms);
                for k = 1:length(checkMessageTerms)
                    if (isequal(checkMessageTerms(k).type,'persistent'))
                        %append all persistent values (the last known
                        %value)
                        trials{end} = setfield(trials{end},checkMessageTerms(k).fieldname,persistantVals(k));
                    end
                end
            end
        end
    end
end


function trials = parseTrial(events,trialEventInds,checkMessageTerms)
%This function will parse all events associated with one trial

for i = 1:size(trialEventInds,1)
    
    currentActiveInput = 0;
    inputChangeFirstOfEach = [];
    inputChange = [];      
    outputChange = [];
    if (trialEventInds(i,2) > 0) %make sure the trial is completed
       
        for j = trialEventInds(i,1):trialEventInds(i,2)
            changes = find(abs(events(j).inStateDiff));
            if ((length(changes) == 1) && (changes ~= currentActiveInput))
                currentActiveInput = changes;
                %Log only the first change time of each input change
                inputChangeFirstOfEach = [inputChangeFirstOfEach; [events(j).time currentActiveInput]];
            elseif (length(changes) > 1)
                disp(['Warning-- more than one input changed at the same time!  Ignoring event ', num2str(i)]);
            end 
            if ~isempty(changes)
                inputChange = [inputChange;[events(j).time events(j).inStateDiff]];
            end
        end
       
       
        for j = trialEventInds(i,1):trialEventInds(i,2)
            changes = find(abs(events(j).outStateDiff));
            if ~isempty(changes)
                %Log all output changes
                outputChange = [outputChange;[events(j).time events(j).outStateDiff]];
            end
        end
        
        
       
        
        trials{i}.timeRange = [events(trialEventInds(i,1)).time events(trialEventInds(i,2)).time];
        trials{i}.initialInputState = events(trialEventInds(i,1)).inState;
        trials{i}.initialOutputState = events(trialEventInds(i,1)).outState;
        trials{i}.inputChangeFirstOfEach = inputChangeFirstOfEach;
        trials{i}.inputChange = inputChange;
        trials{i}.outputChange = outputChange;
        %save a list of any outputs that either went high or low during the trial
        trials{i}.inputSequence = inputChangeFirstOfEach(:,2)';
        trials{i}.outputsThatChanged = find(sum(abs(outputChange(:,2:end))))';
       
        
        %check if any of the messageTerms were included in the trial
        for k = 1:length(checkMessageTerms)
            tmpVal = [];
            
            %Check for boolean types (ie., myState = 1)
            if (isequal(checkMessageTerms(k).type,'boolean'))
                tmpVal = 0;
                
                valueDetermined = 0;
                for j = trialEventInds(i,1):trialEventInds(i,2)
                    if ~isempty(events(j).message)
                        %Determine if either the true or false condition
                        %was set
                        for ff = 1:length(checkMessageTerms(k).falsestring)
                            if ~isempty(checkMessageTerms(k).falsestring{ff}) && ~isempty(strfind(events(j).message,checkMessageTerms(k).falsestring{ff}))
                                tmpVal = 0;
                                valueDetermined = 1;
                                break;
                            end
                        end
                        if (valueDetermined == 1)
                            break;
                        end
                        for ff = 1:length(checkMessageTerms(k).truestring)
                            if ~isempty(checkMessageTerms(k).truestring{ff}) && ~isempty(strfind(events(j).message,checkMessageTerms(k).truestring{ff}))
                                tmpVal = 1;
                                valueDetermined = 1;
                                break;
                            end
                        end
                        if (valueDetermined == 1)
                            break;
                        end
                                                 
                    end
                end
                
            %check for number types (ie., myVar = 77) 
            elseif (isequal(checkMessageTerms(k).type,'number'))
                tmpVal = [];
                
                for j = trialEventInds(i,1):trialEventInds(i,2)
                    if ~isempty(events(j).message)
                        if ~isempty(checkMessageTerms(k).string) && ~isempty(strfind(events(j).message,checkMessageTerms(k).string))
                            equalLoc = strfind(events(j).message,'='); %find where the equal sign is.  The number to store is after that 
                            if ~isempty(equalLoc)
                                try
                                    tmpVal = str2num(events(j).message(equalLoc+1:end));
                                end
                            end
                            break;
                        end
                    end
                end
            %Log all event types in a two column matrix with the first column as time and the second being the event index    
            elseif (isequal(checkMessageTerms(k).type,'events'))
                tmpVal = [];
                
                for j = trialEventInds(i,1):trialEventInds(i,2)
                    if ~isempty(events(j).message)
                        for ff = 1:length(checkMessageTerms(k).events)
                            if ~isempty(checkMessageTerms(k).events{ff}) && ~isempty(strfind(events(j).message,checkMessageTerms(k).events{ff}))
                                tmpVal = [tmpVal; [events(j).time ff]];
                            end
                        end                        
                    end
                end
                
            end  
            
            
            trials{i} = setfield(trials{i},checkMessageTerms(k).fieldname,tmpVal);
            
           
        end
    end    
end




