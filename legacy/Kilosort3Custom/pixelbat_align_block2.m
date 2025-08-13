function [imin,yblk, F0, F0m, ifirst, ilast] = pixelbat_align_block2(F, ysamp, rez)

nblocks = rez.ops.nblocks;
yc = rez.yc; % y coord of channels in channelmap
yup = rez.ops.yup; % upsampled y coord positions

% F is y bins by amp bins by batches
% ysamp are the coordinates of the y bins in um

Nbatches = size(F,3);

% look up and down this many y bins to find best alignment
n = 15;
dc = zeros(2*n+1, Nbatches);
dt = -n:n;

% we do everything on the GPU for speed, but it's probably fast enough on
% the CPU
Fg = gpuArray(single(F));

% mean subtraction to compute covariance
Fg = Fg - mean(Fg, 1);

% initialize the target "frame" with a single sample
F0 = Fg(:,:, min(300, floor(size(Fg,3)/2)));

% first we do rigid registration by integer shifts
% everything is iteratively aligned until most of the shifts become 0. 
niter = 20;
dall = zeros(niter, Nbatches);
for iter = 1:niter    
    for t = 1:length(dt)
        % for each NEW potential shift, estimate covariance
        Fs = circshift(Fg, dt(t), 1);
        dc(t, :) = gather(sq(mean(mean(Fs .* F0, 1), 2)));
    end
    
    if iter<niter
        % up until the very last iteration, estimate the best shifts
        [~, imax] = max(dc, [], 1);
        
        % align the data by these integer shifts
        for t = 1:length(dt)
            ib = imax==t;
            Fg(:, :, ib) = circshift(Fg(:, :, ib), dt(t), 1);
            dall(iter, ib) = dt(t);
        end
        
        % new target frame based on our current best alignment
        F0 = mean(Fg, 3);
    end
end


% new target frame based on our current best alignment
F0 = mean(Fg, 3);

% now we figure out how to split the probe into nblocks pieces
% if nblocks = 1, then we're doing rigid registration
%nybins = size(F,1);
%yl = floor(nybins/nblocks)-1;
%ifirst = round(linspace(1, nybins - yl, 2*nblocks-1));
%ilast  = ifirst + yl; %287;

unique_yc = unique(yc);
discontinuity_idx = find(abs(diff(unique_yc)) > abs(median(diff(unique_yc))));
discontinuity_idx = [discontinuity_idx length(unique_yc)];
yc_chunks = zeros(length(discontinuity_idx), 2);
cur = unique_yc(1);
for i = 1:length(discontinuity_idx)
    yc_chunks(i,:) = [cur unique_yc(discontinuity_idx(i))]
    if(discontinuity_idx(i) < length(unique_yc))
        cur = unique_yc(discontinuity_idx(i)+1)
    end
end

isInChMap = zeros(size(ysamp));
ysamp_chunks = zeros(size(yc_chunks));
for iChunk = 1:size(yc_chunks,1)
    isInChunk = logical( (ysamp >= yc_chunks(iChunk,1)-1) .* (ysamp <= yc_chunks(iChunk,2)-1) );
    s = find(diff(isInChunk) == 1);
    if(length(s) == 0)
        s = 1
    end
    e = find(diff(isInChunk) == -1);
    if(length(e) == 0)
        e = length(ysamp)
    end
    isInChMap( isInChunk ) = 1;
    nybinsInChunk = sum(isInChunk);

    ysamp_chunks(iChunk,:) = [s e];

    

end

nybinsInChMap = sum(isInChMap);
binSize = ceil(nybinsInChMap / (nblocks));
numBinsPerChunk = ceil((ysamp_chunks(:,2) - ysamp_chunks(:,1) ) / binSize);

ifirst = [];
ilast = [];
for iChunk = 1:length(numBinsPerChunk)
    bins = round(linspace(ysamp_chunks(iChunk,1), ysamp_chunks(iChunk,2), numBinsPerChunk(iChunk)+1))

    ifirst = [ifirst bins(1:end-1)];
    ilast = [ilast bins(2:end)];
end

nblocks = length(ifirst);
yblk = zeros(length(ifirst), 1);

% for each small block, we only look up and down this many samples to find
% nonrigid shift
n = 20;
dt = -n:n;

% this part determines the up/down covariance for each block without
% shifting anything
dcs = zeros(2*n+1, Nbatches, nblocks);
for j = 1:nblocks
    isub = ifirst(j):ilast(j);
    yblk(j) = mean(ysamp(isub));
    
    Fsub = Fg(isub, :, :);
     
    for t = 1:length(dt)
        Fs = circshift(Fsub, dt(t), 1);
        dcs(t, :, j) = gather(sq(mean(mean(Fs .* F0(isub, :, :), 1), 2)));
    end
end

% to find sub-integer shifts for each block , 
% we now use upsampling, based on kriging interpolation
dtup = linspace(-n, n, (2*n*10)+1);    
K = kernelD(dt,dtup,1); % this kernel is fixed as a variance of 1
dcs = my_conv2(dcs, .5, [1, 2, 3]); % some additional smoothing for robustness, across all dimensions

imin = zeros(Nbatches, nblocks);
for j = 1:nblocks
    % using the upsampling kernel K, get the upsampled cross-correlation
    % curves
    dcup = K' * dcs(:,:,j);
    
    % find the  max of these curves
    [~, imax] = max(dcup, [], 1);
    
    % add the value of the shift to the last row of the matrix of shifts
    % (as if it was the last iteration of the main rigid loop )
    dall(niter, :) = dtup(imax);
    
    % the sum of all the shifts equals the final shifts for this block
    imin(:,j) = sum(dall,1);
end


%%
Fg = gpuArray(single(F));
imax = sq(sum(dall(1:niter-1,:),1));
for t = 1:length(dt)
    ib = imax==dt(t);
    Fg(:, :, ib) = circshift(Fg(:, :, ib), dt(t), 1);
end
F0m = mean(Fg,3);


