function createNQSpikesFiles(dest,animalID,sessionNum)
%createNQSpikesFiles(dest,animalID,sessionNum)
%
%This function extracts sorted spike information from matclust files 
%and saves data in the NeuroQuery format. It is assumed that there is
%one (and only one) folder named '*.matclust' in the current working
%directory that contains matclust ('matclust_*.mat') files (result of createAllMatclustFiles.m and saving clustered
%data in matclust). 
%
%The function also assumes that there is a '*.time' folder in the current directory
%conaining time information about the session (from extractTimeBinaryFile.m).
%
%dest -- the directory where the processed files should be saved for the
%animal
%animalID -- a string identifying the animal's id (appended to the
%beginning of the files).
%sessionNum -- the session number (in chronological order for the animal)


currDir = pwd;
filesInDir = dir;
targetFolder = [];
for i=3:length(filesInDir)
    if filesInDir(i).isdir && ~isempty(strfind(filesInDir(i).name,'.matclust'))
        targetFolder = filesInDir(i).name;
        break;
    end
end

if isempty(targetFolder)
    error('Time folder not found in this directory.');
end

epochList = getEpochs(1);  %assumes that there is at least a 1-second gap in data between epochs if no .trodesComments file is found
cd(targetFolder);


spikes = [];
matclustfiles = dir('matclust_*');
disp('Processing MatClust files...');
for matclustfileInd = 1:length(matclustfiles)
    
    [filePath,prefixName,ext] = fileparts(matclustfiles(matclustfileInd).name);
    nt = strfind(prefixName,'nt');
    nTrodeNum = str2num(prefixName(nt(end)+2:end));
    channelString = getTwoDigitNumber(nTrodeNum);
    
    for e = 1:size(epochList,1)
        epochString = getTwoDigitNumber(e);
        currentSession = sessionNum;
        sessionString = getTwoDigitNumber(sessionNum);
        currentTimeRange = epochList(e,:);
        
        
        %we change the start and end times to match the actual first and last data points in the recording
        
        %epochDataInd = find((timeData.timestamps >= currentTimeRange(1))&(timeData.timestamps < currentTimeRange(2)));
        %starttime = timeData.timestamps(epochDataInd(1));
        %endtime = timeData.timestamps(epochDataInd(end));
        
        starttime = currentTimeRange(1,1);
        endtime = currentTimeRange(1,2);
        
        clear clustattrib clustdata
        load(matclustfiles(matclustfileInd).name);
        
        if ~isempty(clustattrib.clusters)
            for clustnum = 1:length(clustattrib.clusters)
                if (~isempty(clustattrib.clusters{clustnum}))
                    spikes{currentSession}{e}{nTrodeNum}{clustnum} = [];
                    %make sure that the cluster was defined for the current time epoch.  If not, make the cell empty.
                    %if (is_cluster_defined_in_epoch(clustnum,epoch+1))
                    timepoints = clustdata.params(clustattrib.clusters{clustnum}.index,1);
                    timepoints = timepoints(find((timepoints >= starttime) & (timepoints <= endtime)));
                    
                    spikes{currentSession}{e}{nTrodeNum}{clustnum}.time = timepoints;
                    spikes{currentSession}{e}{nTrodeNum}{clustnum}.timerange = currentTimeRange;
                    %spikes{currentSession}{e}{nTrodeNum}{clustnum}.includeperiods = currentIncludePeriods;
                    spikes{currentSession}{e}{nTrodeNum}{clustnum}.meanrate = length(timepoints)/(endtime-starttime);
                    %TODO-- add location and other searchable info
                end
            end
        end
        
        
    end
    
end
cd(dest)
save([animalID,'spikes',sessionString], 'spikes');
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
    

