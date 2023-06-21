function out = readTrodesFileDigitalChannels(filename)
%out = readTrodesFileDigitalChannels(filename)
%Reads in all of the digital channels from a Trodes .rec file
%filename -- the name of the .rec file, i.e., 'myrecording.rec'
%out -- a structure containing the data from the channels,time range info, and the channal ID's



configInfo = readTrodesFileConfig(filename); %get the configuration from the file
numChannels = str2num(configInfo.numChannels);
samplingRate = str2num(configInfo.samplingRate);
headerSize = str2num(configInfo.headerSize);

channels = [];
channelCount = 0;
channelIDs = {};

for channelInd = 1:length(configInfo.headerChannels)
                  
    if isequal(configInfo.headerChannels(channelInd).dataType,'digital') %if this is a digital channel, we will read it
        channelCount = channelCount+1;
        channels(channelCount,1) = str2num(configInfo.headerChannels(channelInd).startByte)+1;  %the byte (1-based) where the digital bit is stored
        channels(channelCount,2) = str2num(configInfo.headerChannels(channelInd).bit)+1; %the bit (1-based, 1-8)
        channelIDs{channelCount} = configInfo.headerChannels(channelInd).id; %the channel ID
    end
end  

%Now, we read in the channels from the file
[out.channelData, out.timestamps] = importDigitalChannels(filename,numChannels,channels,samplingRate,headerSize, 1);

%and add the ID for each channel
for i = 1:length(out.channelData)
    out.channelData(i).id = channelIDs{i};
end


