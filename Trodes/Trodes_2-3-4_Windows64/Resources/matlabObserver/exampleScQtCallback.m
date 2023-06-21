function exampleScQtCallback(newLine)

%Required global variables
global scQtHistory; %multipurpose place to store processed event history
global scQtControllerOutput; %the text output from the microcontroller 
global scQtCallBackHandle; %the handle to the function called for every new event

%this is the custom callback function.  When events occur, addScQtEvent will
%call this function. 
%newLine is the last text string sent from the microcontroller

%this function keeps a record of the animal's choices and rewad history,
%and tells the microcontrooler which port to arm with reward for the next
%trial.

%the history is stored in the global variable scQtHistory for future use,
%and it is a 2-column matrix [choice reward].  In this example, the code
%assumes that choice is either 1 or 3 (2 is the initiation poke).  Reward
%is either 0 or 1.

%custom globals for this task
global scTrialcount;

if (nargin == 0)
    %Run initiation code here then return


    scTrialcount = 0;

    return;
end


%Custom parsing of the line...
atRewardPort = 0;
%now we update the action and reward history
if (~isempty(strfind(newLine,'Poke')))
    
    currentPort = str2num(newLine(strfind(newLine,'Poke')+5));
   
    if (~isempty(strfind(newLine,'not rewarded')))
        atRewardPort = 1;
        scQtHistory = [scQtHistory; [currentPort 0]];  %a 0 means no reward
    elseif (~isempty(strfind(newLine,'rewarded')))
        atRewardPort = 1;
        scQtHistory = [scQtHistory; [currentPort 1]];  %a 1 means reward
    end   
    
    if (atRewardPort == 1)
        %count the number of trials sisnce the last switch
        scTrialcount = scTrialcount+1;
        if (scTrialcount >= 2)
             %block switch
            scTrialcount = 0;
           
            tmp1 = num2str(round(rand*99));
            tmp2 = num2str(round(rand*99));

            %Now we send control messages back to change variables in the
            %stateScript environment
            sendScQtControlMessage(['rewardprob1 = ',tmp1]);
            sendScQtControlMessage(['rewardprob3 = ',tmp2]);
            sendScQtControlMessage('disp(rewardprob1)');
            sendScQtControlMessage('disp(rewardprob3)');
        end
                    
    end
end

