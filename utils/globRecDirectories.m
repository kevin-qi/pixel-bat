function [out] = globRecDirectories(folder_path)
%GLOBRECDIRECTORIES Globs all *.rec directories in folder_path/
%   Detailed explanation goes here

files = dir(folder_path);

idx = 1;
for iFile = 1:length(files)
    if(endsWith(files(iFile).name, '.rec') && files(iFile).isdir)
        out(idx).name = files(iFile).name;
        out(idx).path = fullfile(folder_path, files(iFile).name);
    end
end

end

