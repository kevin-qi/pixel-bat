function generateBinaryFromTrodesFile(filename, newFileName, channels,varargin)

%generateBinaryFromTrodesFile(filename, newFileName, channels,options)
%Creates a stripped-down binary file from a Trodes recording file. There is
%no offset at the beginning of the file before data begins.  Each data
%point is an unsigned 16-bit value. To convert to uV, multiply by
%(12780/65536).
%The output file is saved in the current working directory.
%
%filename -- Trodes file name in the form of a string: 'file.rec'
%newFileName -- the name of the new binary file for Offline Sorter Import, example 'myfile.rec'
%channels -- a vector containing the channel numbers to save (example: [1:10])
%Options:
% 'bandpassLow'  (default 300)
% 'bandpassHigh' (default 6000)
%
% example:  generateBinaryFromTrodesFile('myfile.rec', 'newfile.dat', [1:32],'bandpassLow',600)


configFileName = [];
configExists = 1;

bandpassLow = 300;  % for high pass filter
bandpassHigh = 6000; % for low pass filter

for option = 1:2:length(varargin)-1   
    if isstr(varargin{option})       
        switch(varargin{option})
            case 'configFileName'
                configFileName = varargin{option+1};
            case 'bandpassLow'
                bandpassLow = varargin{option+1};
            case 'bandpassHigh'
                bandpassHigh = varargin{option+1};    
           
            otherwise
                error(['Option ',varargin{option},' unknown.']);
        end        
    else
        error('Options must be strings, followed by the variable');
    end
end

if (isempty(configFileName))
    configInfo = readTrodesFileConfig(filename);
else
    configInfo = readTrodesFileConfig(configFileName);
    configExists = 0;
end
numChannels = str2num(configInfo.numChannels);
samplingRate = str2num(configInfo.samplingRate);
headerSize = str2num(configInfo.headerSize);
numCards = numChannels/32;

hwChannels = [];
displist = [];

for trodeInd = 1:length(configInfo.nTrodes)      
        for channelInd = 1:length(configInfo.nTrodes(trodeInd).channelInfo)
            %if there are multiple headstages, the channels are interlaced in
            %the file, so we need to convert the HW channels to the interlaced
            %form.
        
            hwRead = str2num(configInfo.nTrodes(trodeInd).channelInfo(channelInd).hwChan);
            new_hw_chan =  (mod(hwRead,32)*numCards)+floor(hwRead/32)+1;  
            displist = [displist; [trodeInd hwRead new_hw_chan]];
            hwChannels = [hwChannels new_hw_chan];
        end
           
end

numWriteChannels = length(channels);
writeHeaderSize = 0; %the number of 16-bit header chennels
writeTimestampSize = 0; %the size in bytes of the timestamps

 

%Write the config info at the top of the new file
writeFID = fopen(newFileName,'w');
%fwrite(writeFID,config.configText);
%endofConfig = length(config.configText); 
endofConfig = 0; %no config
fid = fopen(filename,'r');

configsize = 0;
if (configExists)
    junk = fread(fid,30000,'char');
    configsize = strfind(junk','</Configuration>')+16;
    frewind(fid);
end


%create a precision string, including the number of channels
precisionString = [num2str(numWriteChannels),'*int16'];

[c,d] = butter(2, [bandpassLow bandpassHigh]/(samplingRate/2));
numChannelsWritten = 0;


%Read/Write the digital data
disp('Reading digital event data');

%Read file: move to the begining of digital data for this channel
fseek(fid, configsize, -1);
readString = [num2str(headerSize),'*int16=>int16'];
digitalData = fread(fid,[headerSize,inf],readString,4+(numChannels*2))';
numDigitalChannels = (headerSize*16)-8;

writeHeaderSize = numDigitalChannels/2;
numDigitalChannelsWritten = 0;
for i = 1:numDigitalChannels
    disp(['Writing digital channel ', i]);
    %Write file: move to the begining of the DIO section for this channel 
    tmpBitVals = bitget(digitalData(:,(ceil((i+8)/16))),mod(i+8,16)+1,'int16');
    fseek(writeFID, endofConfig+(2*numDigitalChannelsWritten), -1);
    
    %Write the data block to the new file
    fwrite(writeFID,tmpBitVals(1),'int16');
    fwrite(writeFID,tmpBitVals(2:end),'int16',(2*writeHeaderSize)+writeTimestampSize+(2*numWriteChannels)-2);  
    
    numDigitalChannelsWritten = numDigitalChannelsWritten+1;
end

    


%Read/Write neural data
for currentChanInd = 1:length(channels)
    disp(['Channel ' num2str(channels(currentChanInd))]);
    currentHwChan = hwChannels(channels(currentChanInd));
           
    %Write file: move to the begining channel data for this channel 
    fseek(writeFID, endofConfig+(2*writeHeaderSize)+writeTimestampSize+(2*numChannelsWritten), -1);    
    %Read file: move to the begining channel data for this channel
    fseek(fid, configsize+(2*headerSize)+4+(2*(currentHwChan-1)), -1);
    
    channelData = fread(fid,[1,inf],'1*int16=>int16',(2*headerSize)+2+(numChannels*2))';       
    channelData = double(channelData)*-1; %reverse the sign to make spike point up
    channelData = channelData * (12780/65536); %convert to uV
    channelData = filtfilt(c,d,channelData); %filter the channel 
   
    %Write the data block to the new file
    fwrite(writeFID,channelData(1)*65536/12780,'int16');  % convert it back to digitized number for OfflineSorter
    fwrite(writeFID,channelData(2:end)*65536/12780,'int16',(2*writeHeaderSize)+writeTimestampSize+(2*numWriteChannels)-2);  % convert it back to digitized number for OfflineSorter
    
    numChannelsWritten = numChannelsWritten+1;

end


fclose(fid);
fclose(writeFID);





