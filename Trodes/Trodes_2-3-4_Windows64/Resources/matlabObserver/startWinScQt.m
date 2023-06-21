function startWinScQt(callBackFcn, comDirectory, initFcn)
%startScQt(callBackFcn, comDirectory)
%startScQt(callBackFcn, comDirectory, initFcn)
%This function starts the scQt agent on matlab for a windows machine. It uses files to communicate 
%to the qt based GUI instead of stdin and stdout.
%callBackFcn -- a string containing the name of the callback function to
%               be called for every new event.
%comDirectory -- the directory where temporary communication files will be
%placed
%initFcn -- <optional> a string containing the name of a function to call
%           now. Useful for setting up extra global variables or plots.

global scQtHistory; %multipurpose place to store processed event history
global scQtControllerOutput; %the text output from the microcontroller
global scQtCallBackHandle; %the handle to the function called for every new event
global communicationDirectory; %the communication directory
global numBytesRead;
global scQtInitiated; %the callback function should set this to 1 once all user variables are set


scQtCallBackHandle = str2func(callBackFcn)
scQtControllerOutput = {};
scQtHistory = [];

communicationDirectory = comDirectory;
numBytesRead = 0;
scQtInitiated = 0;

checktimer = timer('TimerFcn',@scQtTimerFcn, 'Name','scqttimer', 'Period', .1,'TasksToExecute',inf,'ExecutionMode','fixedRate','StartDelay',0);
start(checktimer);

%Run init function if given
if (nargin > 2)
scQtInitHandle = str2func(initFcn);
scQtInitHandle();
end
scQtCallBackHandle();
disp('Initiation complete.');




