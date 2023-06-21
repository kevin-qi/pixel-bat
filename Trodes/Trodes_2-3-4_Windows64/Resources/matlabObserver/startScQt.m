function startScQt(callBackFcn, initFcn)
%startScQt(callBackFcn)
%startScQt(callBackFcn, initFcn)
%This function starts the scQt agent on matlab.  
%callBackFcn -- a string containing the name of the callback function to 
%               be called for every new event.
%initFcn -- <optional> a string containing the name of a function to call
%           now. Useful for setting up extra global variables or plots.

global scQtHistory; %multipurpose place to store processed event history
global scQtControllerOutput; %the text output from the microcontroller 
global scQtCallBackHandle; %the handle to the function called for every new event
global scQtInitiated; %the callback function should set this to 1 once all user variables are set

scQtCallBackHandle = str2func(callBackFcn)
scQtControllerOutput = {};
scQtHistory = [];
scQtInitiated = 0;

%Run init function if given
if (nargin > 1) 
    scQtInitHandle = str2func(initFcn);
    scQtInitHandle();
end

scQtCallBackHandle();
disp('Initiation complete.');










