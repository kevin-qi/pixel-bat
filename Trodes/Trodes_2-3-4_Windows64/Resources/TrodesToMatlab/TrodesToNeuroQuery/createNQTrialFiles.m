function createNQTrialFiles(dest,animalID,sessionNum, varargin)
%
%createNQTrialFiles('an123_121214_scLog.txt',[],[],'inputWatch',[1:3],'trialStartTerms',{'initiate'},'trialEndTerms',{'initiate'},'checkMessageTerms',{'LEDStim'})

trialStartTerms = []; %a cell array of strings that indicate the start of a trial
trialEndTerms = []; %a cell array of strings that indicate the end of a trial
checkMessageTerms = [];
inputWatch = []; %a vector declaring which input ports to pay attention to (empty = all)
trials = [];

for option = 1:2:length(varargin)-1
    switch varargin{option}
        case 'trialStartTerms'
            trialStartTerms = varargin{option+1};
        case 'trialEndTerms'
            trialEndTerms = varargin{option+1};            
        case 'inputWatch'
            inputWatch = varargin{option+1};
        case 'checkMessageTerms'
            checkMessageTerms = varargin{option+1};
        otherwise
            error(['Option ''', varargin{option}, ''' not defined']);
    end
end

currDir = pwd;


stateScriptFiles = dir(['*_scLog.txt']);
if (length(stateScriptFiles) == 1)
    filename = stateScriptFiles(1).name;
elseif (length(stateScriptFiles) == 0)
    error(['No stateScript log file found in folder ', pwd]);
elseif (length(stateScriptFiles) > 1)
    error(['More than one stateScript log file found in folder ', pwd]);
end
taskData = [];
taskData{1} = [];
taskFiles = dir(['*_task.txt']);

if ~isempty(taskFiles)
    taskData = readTrodesTaskFile(taskFiles(1).name);
end

tmpTrials = readStateScriptFileTrials(filename,'inputWatch',inputWatch,'trialStartTerms',trialStartTerms,'trialEndTerms',trialEndTerms,'checkMessageTerms',checkMessageTerms);

%we need to separate into epochs somehow here...

