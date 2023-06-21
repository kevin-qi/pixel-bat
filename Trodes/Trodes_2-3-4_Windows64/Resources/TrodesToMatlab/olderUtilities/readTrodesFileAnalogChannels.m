function out = readTrodesFileAnalogChannels(filename, channels)
%out = readTrodesFileAnalogChannels(filename)
%out = readTrodesFileAnalogChannels(filename,channels)
%Reads in all of the auxilliary analog channels from a Trodes .rec file
%filename -- the name of the .rec file, i.e., 'myrecording.rec'
%channels -- the list of analog channels, which is a cell array of strings containing the channel names. If omitted, all analog channels are read. 
%out -- a structure containing the data from the channels,time range info, and the channal ID's


if (nargin < 2)
    channels = [];
end

configInfo = readTrodesFileConfig(filename); %get the configuration from the file
numChannels = str2num(configInfo.numChannels);
samplingRate = str2num(configInfo.samplingRate);
headerSize = str2num(configInfo.headerSize);

channelbytes = [];
channelCount = 0;
channelIDs = {};

for channelInd = 1:length(configInfo.headerChannels)
                  
    if isequal(configInfo.headerChannels(channelInd).dataType,'analog') %if this is an analog channel, we will read it
        usechannel = 0;
        if (~isempty(channels))
           %we are only reading a subset of the channels, so we need to
           %know if this channel is one of them
           for chSearch = 1:length(channels) 
                if (isequal(configInfo.headerChannels(channelInd).id,channels{chSearch}))
                   %This channel is a keeper
                   usechannel = 1;
                   break;
                end
           end
        else
            %we are reading all analog channels available
            usechannel = 1;
        end
        
        if (usechannel)
            channelCount = channelCount+1;
            channelbytes(channelCount,1) = str2num(configInfo.headerChannels(channelInd).startByte)+1;  %the byte (1-based) where the digital bit is stored
            channelIDs{channelCount} = configInfo.headerChannels(channelInd).id; %the channel ID
        end
    end
end  


%Now, we read in the channels from the file
[out.channelData, out.timestamps] = importAnalogChannels(filename,numChannels,channelbytes,samplingRate,headerSize, 1);

%and add the ID for each channel
for i = 1:length(out.channelData)
    out.channelData(i).id = channelIDs{i};
end

