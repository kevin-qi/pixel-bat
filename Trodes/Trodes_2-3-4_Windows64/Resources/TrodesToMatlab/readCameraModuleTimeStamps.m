function [timestamps clockRate] = readCameraModuleTimeStamps(filename, varargin)  
%[timestamps] = readCameraModuleTimeStamps(filename)
%filename-- a string containing the name of the .videoTimeStames file
%timestamps-- a vector containing the timestamps of the camera frames (in uint32 format)

%DR added support for type double 9.5.16
forcetype = ''; %forces datatype.. This is a temp hack instead of editing the header
if (~isempty(varargin))
    assign(varargin{:});
end

if ~isempty(forcetype)
    datatype = forcetype;
else
    datatype = 'uint32';
end

clockRate = 30000;  %default clock rate
fid = fopen(filename,'r');
headerText = fread(fid,200,'uint8');
headerText = char(headerText');
endHeaderLoc = strfind(headerText,'<End settings>');

if (~isempty(endHeaderLoc))
    headersize = endHeaderLoc+14;
    clockRateLoc  = strfind(headerText,'Clock rate:');
    if (~isempty(clockRateLoc))
        clockRate = str2num(char(strtok(headerText(clockRateLoc+12:end))));
    end
    
else
    headersize = 0;
end
frewind(fid);
junk = fread(fid,headersize,'uint8');

timestamps = fread(fid,inf,'uint32=>double',0)/clockRate;
% timestamps = fread(fid,inf,sprintf('%s=>double',datatype),0)/clockRate;


fclose(fid);


