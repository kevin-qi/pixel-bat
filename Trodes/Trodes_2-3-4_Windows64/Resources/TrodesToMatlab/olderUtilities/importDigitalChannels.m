function [recData, timestamps] = importDigitalChannels(filename,NumChannels, channels, samplingRate,headerSize, configExists)  

%[recData, timestamps] = importDigitalChannels(filename,NumChannels, channels, samplingRate,headerSize, configExists) )  

%Imports digital channel data in matlab from the raw data file
%
%INPUTS
%filename-- a string containing the name of the .dat file (raw file from SD card)
%NumChannels-- the number of channels in the recording (i.e., 32,64,96...)
%channels-- the digital channels you want to extract, designated as an N by 2 matrix [byte(1-based) bit(1-based)] 
%samplingRate-- the sampling rate of the recording, i.e 30000
%headerSize--the size, in int16's, of the header block of the data
%(contains DIO channels and aux analog channels).
%
%OUTPUTS
%timestamps--the system clock when each sample was taken
%recData-- a structure continaing the digital state of the channels

configsize = 0;
if (nargin < 6)
    configExists = 1;   
end

fid = fopen(filename,'r');

if (configExists)
    junk = fread(fid,1000000,'uint8');
    configsize = strfind(junk','</Configuration>')+16;
    frewind(fid);
end

%get the timestamps
junk = fread(fid,configsize,'uint8');
junk = fread(fid,headerSize,'int16');
timestamps = fread(fid,[1,inf],'1*uint32=>uint32',(2*headerSize)+(NumChannels*2))';
timestamps = double(timestamps)/samplingRate;
frewind(fid);


bytesToRead = unique(channels(:,1)); %find the list of unique bytes to read in
recData = [];


for i = 1:length(bytesToRead)  
    junk = fread(fid,configsize,'uint8'); %skip config
    junk = fread(fid,bytesToRead(i)-1,'uint8'); %skip byes in header block up to the correct byte
    tmpData = fread(fid,[1,inf],'1*char=>uint8',(2*headerSize)+3+(NumChannels*2))';
    frewind(fid);
    
    currentDigitalChannels = find(channels(:,1)==bytesToRead(i));  %all the channels that use the current byte (up to 8)
    for j = 1:length(currentDigitalChannels)
        recData(currentDigitalChannels(j)).data = logical(bitget(tmpData,channels(currentDigitalChannels(j),2)));
        recData(currentDigitalChannels(j)).timeRange = [timestamps(1) timestamps(end)];
        recData(currentDigitalChannels(j)).samplingRate = samplingRate;
    end
             
end

fclose(fid);




