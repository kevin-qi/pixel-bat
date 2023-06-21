function generateTrodesFileFromSDFile(recordingFile, newFileName, configFileName, offsettime)

%generateTrodesFileFromSDFiles(recordingFile, newFileName, configFileName, offsettime)
%Converts an SD card recording into a .rec file that Trodes can open.
%The file is saved in the current working directory.
%
%newFileName -- the name of the new .rec file, example 'myfile.rec'
%
%configFileName -- an xml-based config file used by Trodes.
%
%recordingFile -- file name in the form of a string: 'file.dat'
%
%offsettime (default = [0 1]) -- the (1) offset and (2) multiplicative
%scaling the new timestamps realtive to the timestamps in the read file.
%Useful if you are sticking together multiple files for one session and/or if 
%there is drift between the headstage clock and the behavioral system clock


%
%Example:
%generateTrodesFileFromSDFiles({'ephysRecording.dat','recording.rec', 'Config64.trodesconf')


configsize = 0;

if (nargin < 4)
    offsettime = [0 1];  %the (1) offset and (2) multiplicative scaling of the timestamps
end

config = readTrodesFileConfig(configFileName);
NumChannels = str2num(config.numChannels);
samplingRate = str2num(config.samplingRate);
headerSize = str2num(config.headerSize); %the size of the digital header

 

%Write the config info at the top of the new file
writeFID = fopen(newFileName,'w');
fwrite(writeFID,config.configText);
endofConfig = length(config.configText); 

fid = fopen(recordingFile,'r');


%Calculate the total number of packets in the read file
fseek(fid,0,1);  %go to the end of the read file
totalBytesinReadFile = ftell(fid);
packetsToWrite = totalBytesinReadFile/((2*headerSize)+4+(2*NumChannels));
totalPackets = packetsToWrite;

disp(['Writing to new file...']);

%now, we transfer the channel data from one file to the other

packetsPerLoop = 100000; %the maximum number of packets to store in memory during transfer

%create a precision string, including the number of channels
precisionString = [num2str(NumChannels),'*int16'];
numPacketsProcessed = 0;

while (packetsToWrite > 0)
    %transfer channel data from one file to the other
    if (packetsToWrite > packetsPerLoop)
        tmpTransfer = packetsPerLoop;
    else
        tmpTransfer = packetsToWrite;
    end
    
    
    %Write file: move to the begining of this transfer section 
    fseek(writeFID, endofConfig+numPacketsProcessed*((2*headerSize)+4+(2*NumChannels)), -1);    
    %Read file: move to the begining of this transfer section 
    fseek(fid, numPacketsProcessed*((2*headerSize)+4+(2*NumChannels)), -1);
    
    %Read the auxilliary data block from the SD card file
    tmpDIO = fread(fid,headerSize*tmpTransfer,[num2str(headerSize),'*int16=>int16'],4+(NumChannels*2))'; 
    %Write the auxilliary data block to the new file
    count = fwrite(writeFID,tmpDIO(1:headerSize),[num2str(headerSize),'*int16']);
    count = fwrite(writeFID,tmpDIO(headerSize+1:end),[num2str(headerSize),'*int16'],4+(NumChannels*2));
    
    %Write file: move to the begining timestamp of the this transfer section 
    fseek(writeFID, endofConfig+numPacketsProcessed*((2*headerSize)+4+(2*NumChannels))+(2*headerSize), -1);    
    %Read file: move to the begining timestamp of the this transfer section 
    fseek(fid, numPacketsProcessed*((2*headerSize)+4+(2*NumChannels))+(2*headerSize), -1);
    
    %Read the timestamp block from the SD card file
    tmpTimestamps = fread(fid,tmpTransfer,'1*uint32=>uint32',(2*headerSize)+(NumChannels*2))';
    tmpTimestamps = (tmpTimestamps*offsettime(2))+offsettime(1); %add the desired offset and scaling
    
    %Write the timestamp data block to the new file
    count = fwrite(writeFID,tmpTimestamps(1),'1*uint32');
    count = fwrite(writeFID,tmpTimestamps(2:end),'1*uint32',(2*headerSize)+(NumChannels*2));
    
    
    %Write file: move to the begining channel data of the this transfer section 
    fseek(writeFID, endofConfig+numPacketsProcessed*((2*headerSize)+4+(2*NumChannels))+(2*headerSize)+4, -1);    
    %Read file: move to the begining channel data of the this transfer section 
    fseek(fid, numPacketsProcessed*((2*headerSize)+4+(2*NumChannels))+(2*headerSize)+4, -1);
    
    %Read the data block from the SD card file
    tmpChannelData = fread(fid,(NumChannels)*tmpTransfer,[precisionString,'=>int16'],(2*headerSize)+4);
    
    %Write the data block to the new file
    count = fwrite(writeFID,tmpChannelData(1:NumChannels),precisionString);
    count = fwrite(writeFID,tmpChannelData(NumChannels+1:end),precisionString,(2*headerSize)+4);
        
    %Display the percentage done
    disp([num2str((100*(totalPackets-packetsToWrite))/totalPackets),'%']);
    numPacketsProcessed = numPacketsProcessed+tmpTransfer;
    packetsToWrite = packetsToWrite-tmpTransfer;
    
end


fclose(fid);


fclose(writeFID);

