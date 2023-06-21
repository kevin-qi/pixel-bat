function out = readTrodesFileContinuous(filename,channels,skipTime,varargin)
%out = readTrodesFileChannels(filename,channels)
%out = readTrodesFileChannels(filename,channels,skipTime)
%out = readTrodesFileChannels(filename,channels,skipTime,OPTIONS)
%Reads in the designated channels from a Trodes .rec file
%filename -- the name of the .rec file, i.e., 'myrecording.rec'
%channels -- a list of channels to extract from the file, where each entry
%row lists the nTrode ID, follwed by the channel number (1-based)
%skipTime (default 0) -- skips reading in the time of each sample
%out -- a structure containing the broadband traces of the channels,timestamps, and some configuration info
%OPTIONS
%configFileName -- if the configuration settings at not at the top of the
%file, you can designate another file which has the config settings.

out = [];

if (nargin < 3)
    skipTime = 0;
end

if (size(channels,2) ~= 2)
    error('The "channels" input must have two columns for nTrode and channel');
end

configFileName = [];
configExists = 1;

for option = 1:2:length(varargin)-1   
    if isstr(varargin{option})       
        switch(varargin{option})
            case 'configFileName'
                configFileName = varargin{option+1};
           
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


%Compile a list of the actual packet offsets for the desired channels
hwChannels = [];
displist = [];
for chInd = 1:size(channels,1) 
    foundCh = 0;
    for trodeInd = 1:length(configInfo.nTrodes)
        if (str2num(configInfo.nTrodes(trodeInd).id) == channels(chInd,1))
            %This is the correct nTrode, based on the id field
            foundCh = 1;
            if (length(configInfo.nTrodes(trodeInd).channelInfo) >= channels(chInd,2))
                hwChannels = [hwChannels configInfo.nTrodes(trodeInd).channelInfo(channels(chInd,2)).packetLocation+1];
            else
                error(['nTrode ', num2str(channels(chInd,1)), ' does not have enough channels.']);
            end                     
            break;
        end
    end
    if (~foundCh)
       error(['nTrode ID ',num2str(channels(chInd,1)), ' not found.']);
    end
end

%Read in the data
if (skipTime)
    [out.channelData] = importChannels(filename,numChannels,hwChannels,samplingRate,headerSize, configExists);
    out.timestamps = [];
else    
    [out.channelData, out.timestamps] = importChannels(filename,numChannels,hwChannels,samplingRate,headerSize, configExists);
    %timeDir = diff(out.timestamps);
    %out.timestamps(find(timeDir < 0)) = out.timestamps(find(timeDir < 0))*-1;
end
out.headerSize = headerSize;
out.samplingRate = samplingRate;
out.numChannels = numChannels;



