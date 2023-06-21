function createNQTaskFile(dest,animalID,sessionNum)
%createNQTaskFile(dest,animalID,sessionNum)
%
%This function extracts task information from a recording session 
%and saves data in the NeuroQuery format. It is assumed there is at
%least one *.trodesComments file in the current working directory, and that
%if there is more than one they all are part of the same session.
%
%dest -- the directory where the processed files should be saved for the
%animal
%animalID -- a string identifying the animal's id (appended to the
%beginning of the files).
%sessionNum -- the session number (in chronological order for the animal)

currDir = pwd;
sessionString = getTwoDigitNumber(sessionNum);
t = readTrodesTaskFile();

task{sessionNum} = t;

cd(dest)
save([animalID,'task',sessionString], 'task');
cd(currDir);




%----------------------------------------------------------
%Helper functions
%-----------------------------------------------------------


function numString = getTwoDigitNumber(input)
    
if (input < 10)
    numString = ['0',num2str(input)];
else
    numString = num2str(input);
end
    
