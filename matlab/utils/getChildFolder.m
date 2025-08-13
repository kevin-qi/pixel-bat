function [folderPaths] = getChildFolder(parentFolder,folderRegex)
%GETRECFOLDERNAME Summary of this function goes here
%   Detailed explanation goes here
dirs = dir(parentFolder);

f = regexpi({dirs.name},folderRegex,'match');
folderPaths = [f{:}];
folderPaths = fullfile(parentFolder ,folderPaths{1});
end

