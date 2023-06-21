function scQtTimerFcn(scQtTimer,event)

global scQtHistory; %multipurpose place to store processed event history
global scQtControllerOutput; %the text output from the microcontroller
global scQtCallBackHandle; %the handle to the function called for every new event
global communicationDirectory; %the communication directory
global numBytesRead;

%stop(scQtTimer);

%currdir = pwd;
%if ~isequal(currdir,communicationDirectory)
%    cd(communicationDirectory);
%end

%pwd
%[communicationDirectory, filesep, 'qtGUIStream.txt']

fid = fopen([communicationDirectory, filesep, 'qtGUIStream.txt'],'r');

if (numBytesRead > 0)
    junk = fread(fid,numBytesRead,'char');
end
newLine = [];

while ~((length(newLine) == 1) && (newLine == -1))
    newLine = fgetl(fid);
    if ~isempty(strfind(newLine,'addScQtEvent'))
        %disp(['reading line', newLine]);
        disp(' ');
        eval(newLine);   
    elseif isequal(newLine,'quit')
        quit force
    end
end


pos = ftell(fid);
if (pos > 0)
    numBytesRead = pos;
end
if (isempty(newLine))
    readAnotherLine = 0;
end

fclose(fid);


%start(scQtTimer);







