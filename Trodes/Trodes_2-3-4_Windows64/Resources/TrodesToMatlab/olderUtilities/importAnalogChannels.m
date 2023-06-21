function [recData, timestamps] = importAnalogChannels(filename,NumChannels, channels, samplingRate,headerSize, configExists)  

%[recData, timestamps] = importAnalogChannels(filename,NumChannels, channels, samplingRate,headerSize, configExists) )  

%Imports digital channel data in matlab from the raw data file
%
%INPUTS
%filename-- a string containing the name of the .dat file (raw file from SD card)
%NumChannels-- the number of channels in the recording (i.e., 32,64,96...)
%channels-- the analog channels you want to extract, designated by the byte location (1-based), i.e., [3 5 7]
%samplingRate-- the sampling rate of the recording, i.e 30000
%headerSize--the size, in int16's, of the header block of the data
%(contains DIO channels and aux analog channels).
%
%OUTPUTS
%timestamps--the system clock when each sample was taken
%recData-- an N by M matrix with N data points and M channels (M is equal to the number of channels in the input)

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


bytesToRead = channels; %find the list of unique bytes to read in
recData = [];
for i = 1:length(bytesToRead)  
    junk = fread(fid,configsize,'uint8'); %skip config
    junk = fread(fid,bytesToRead(i)-1,'char'); %skip byes in header block up to the correct byte
    tmpData = fread(fid,[1,inf],'1*int16=>int16',(2*headerSize)+2+(NumChannels*2))';
    frewind(fid);
    
    recData(i).data = tmpData;
    recData(i).timeRange = [timestamps(1) timestamps(end)];
    recData(i).samplingRate = samplingRate;
             
end

fclose(fid);




