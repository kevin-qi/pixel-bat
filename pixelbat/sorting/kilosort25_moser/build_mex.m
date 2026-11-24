function build_mex()
% Compiles the CUDA mex files of the patched Kilosort 2.5 in this folder, once per machine:
% matlab -batch "cd('<this folder>'); build_mex"
% Needs the Parallel Computing Toolbox, a CUDA GPU and a C++ compiler MATLAB supports (mex -setup C++).

here = fileparts(mfilename('fullpath'));
cd(fullfile(here, 'Kilosort-2.5-moser', 'CUDA'));
mex -setup C++
gpu = gpuDevice;
fprintf('%s, CUDA toolkit %g\n', gpu.Name, gpu.ToolkitVersion)
mexGPUall
built = dir(['*.' mexext]);
fprintf('%d of 9 mex files built in %s\n', numel(built), pwd)
