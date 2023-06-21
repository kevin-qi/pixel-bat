function addScQtEvent(eventString)
%addScQtEvent(eventString)
%This function is called by the qt-based gui every time a new even occurs.
%The event string is passed in the input, and the designated callBack
%function is called.

global scQtHistory; %multipurpose place to store processed event history
global scQtControllerOutput; %the text output from the microcontroller 
global scQtCallBackHandle; %the handle to the function called for every new event

%add the event output string to the memory log
l = length(scQtControllerOutput);
if (l==0)
    scQtControllerOutput = {[]};
end
scQtControllerOutput{l+1} = eventString;

%call the callback
scQtCallBackHandle(eventString);
