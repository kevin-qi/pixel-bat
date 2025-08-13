function rez = spliced_datashift2(rez, do_correction)

NrankPC = 6;
[wTEMP, wPCA]    = extractTemplatesfromSnippets(rez, NrankPC);
rez.wTEMP = gather(wTEMP);
rez.wPCA  = gather(wPCA);

ops = rez.ops;

% The min and max of the y and x ranges of the channels
ymin = min(rez.yc);
ymax = max(rez.yc);
xmin = min(rez.xc);
xmax = max(rez.xc);

dmin = median(diff(unique(rez.yc)));
fprintf('vertical pitch size is %d \n', dmin)
rez.ops.dmin = dmin;
rez.ops.yup = ymin:dmin/2:ymax; % centers of the upsampled y positions

% dminx = median(diff(unique(rez.xc)));
% yunq = unique(rez.yc);
% mxc = zeros(numel(yunq), 1);
% for j = 1:numel(yunq)
%     xc = rez.xc(rez.yc==yunq(j));
%     if numel(xc)>1
%        mxc(j) = median(diff(sort(xc))); 
%     end
% end
% dminx = max(5, median(mxc));

dminx = median(diff(unique(rez.xc)));
fprintf('horizontal pitch size is %d \n', dminx)

rez.ops.dminx = dminx;
nx = round((xmax-xmin) / (dminx/2)) + 1;
rez.ops.xup = linspace(xmin, xmax, nx); % centers of the upsampled x positions
disp(rez.ops.xup) 

if  getOr(rez.ops, 'nblocks', 1)==0
    rez.iorig = 1:rez.temp.Nbatch;
    return;
end

% binning width across Y (um)
dd = 5;
% min and max for the range of depths
dmin = ymin - 1;
dmax  = 1 + ceil((ymax-dmin)/dd);
disp(dmax)


spkTh = 8; % same as the usual "template amplitude", but for the generic templates

% Extract all the spikes across the recording that are captured by the
% generic templates. Very few real spikes are missed in this way. 
[st3, rez] = standalone_detector(rez, spkTh);
%%

% detected depths
% dep = st3(:,2);
% dep = dep - dmin;

Nbatches      = rez.temp.Nbatch;
% which batch each spike is coming from
batch_id = st3(:,5); %ceil(st3(:,1)/dt);

% preallocate matrix of counts with 20 bins, spaced logarithmically
F = zeros(dmax, 20, Nbatches);
for t = 1:Nbatches
    % find spikes in this batch
    ix = find(batch_id==t);
    
    % subtract offset
    dep = st3(ix,2) - dmin;
    
    % amplitude bin relative to the minimum possible value
    amp = log10(min(99, st3(ix,3))) - log10(spkTh);
    
    % normalization by maximum possible value
    amp = amp / (log10(100) - log10(spkTh));
    
    % multiply by 20 to distribute a [0,1] variable into 20 bins
    % sparse is very useful here to do this binning quickly
    M = sparse(ceil(dep/dd), ceil(1e-5 + amp * 20), ones(numel(ix), 1), dmax, 20);    
    
    % the counts themselves are taken on a logarithmic scale (some neurons
    % fire too much!)
    F(:, :, t) = log2(1+M);
end

%% Original single recording offset calculations
%{
% determine registration offsets
ysamp = dmin + dd * [1:dmax] - dd/2;
[imin,yblk, F0, F0m] = align_block2(F, ysamp, ops.nblocks);

if isfield(rez, 'F0')
    d0 = align_pairs(rez.F0, F0);
    % concatenate the shifts
    imin = imin - d0;
end
%}

%% Additional Drift Correction at splice point between recordings
% the 'midpoint' branch is for chronic recordings that have been
% concatenated in the binary file
if isfield(ops, 'midpoint')
    % register the first block as usual
    ysamp = dmin + dd * [1:dmax] - dd;

    %[imin1, F1] = align_block(F(:, :, 1:ops.midpoint));
    [imin1,yblk1, F1, F1m, ifirst, ilast] = pixelbat_align_block2(F(:, :, 1:ops.midpoint), ysamp, rez);
    % register the second block as usual
    %[imin2, F2] = align_block(F(:, :, ops.midpoint+1:end));
    [imin2,yblk2, F2, F2m, ifirst, ilast] = pixelbat_align_block2(F(:, :, ops.midpoint:end), ysamp, rez);
    % now register the average first block to the average second block
    %d0 = pixelbat_align_pairs(F1, F2)*5;
    
    % Non rigid splice correction

    figure;
    plot(mean(F1,2));
    hold on
    plot(mean(F2,2));
    
    % To fit chunks, the actual nblocks may not be the same as specified
    % num blocks
    nblocks = length(ifirst);
    
    figure;
    d0 = [];
    for j = 1:nblocks
        isub = ifirst(j):ilast(j);
        d0 = [d0 pixelbat_align_pairs(F1(isub,:), F2(isub,:))];
        plot(isub, mean(mean(F1(isub,:),3),2));
        hold on
        
    end
    
    %[imin1, F1] = align_block(F(:, :, 1:ops.midpoint));
    [imin1,yblk1, F1, F1m, ifirst, ilast] = pixelbat_align_block2(F(:, :, 1:ops.midpoint), ysamp, rez);
    % register the second block as usual
    %[imin2, F2] = align_block(F(:, :, ops.midpoint+1:end));
    [imin2,yblk2, F2, F2m, ifirst, ilast] = pixelbat_align_block2(F(:, :, ops.midpoint:end), ysamp, rez);
    % now register the average first block to the average second block

    % concatenate the shifts
    imin = [imin1' imin2' + d0']';
    
    %imin = imin - mean(imin);
    %ops.datashift = 1;
else
    % determine registration offsets 
    ysamp = dmin + dd * [1:dmax] - dd/2;
    %[imin,yblk, F0, F0m] = align_block2(F, ysamp, ops.nblocks)
    [imin,yblk, F0, F0m] = pixelbat_align_block2(F, ysamp, rez);
    %imin(ops.midpoint+1:end,:) = imin(ops.midpoint+1:end,:) + d0;
end

%% Get which block each spike belongs to
block_bins = [];
spk_dep = st3(:,2);
spk_block_idx = zeros(size(spk_dep));
for iChunk = 1:length(ifirst)  % spk_block_idx tells us which block each spike in st3 belongs to
    s = ysamp(ifirst(iChunk));
    e = ysamp(ilast(iChunk));

    isInChunk = logical( (spk_dep > s) .* (spk_dep <e) );

    spk_block_idx(isInChunk) = iChunk;
end


%%
if getOr(ops, 'fig', 1)  
    figure;
    set(gcf, 'Color', 'w')
    
    % plot the shift trace in um
    plot(imin * dd)
    box off
    xlabel('batch number')
    ylabel('drift (um)')
    title('Estimated drift traces')
    drawnow
    
    
    figure;
    tiledlayout(1,2);
    
    set(gcf, 'Color', 'w')
    % raster plot of all spikes at their original depths
    spk_shifts = zeros(size(batch_id));
    for k = 1:length(batch_id)
        iChunk = spk_block_idx(k);
        if(iChunk > 0)
            spk_shifts(k) = imin(batch_id(k), iChunk) * dd;
        else
            spk_shifts(k) = 0;
        end
    end
    ax1 = nexttile;
    st_shift = st3(:,2);% + spk_shifts;% imin(batch_id) * dd;
    for j = spkTh:100
        % for each amplitude bin, plot all the spikes of that size in the
        % same shade of gray
        ix = st3(:, 3)==j; % the amplitudes are rounded to integers
        plot(st3(ix, 1)/ops.fs, st_shift(ix), '.', 'color', [1 1 1] * max(0, 1-j/40)) % the marker color here has been carefully tuned
        hold on
    end
    axis tight
    box off
    xline([ops.midpoint*ops.NTbuff/ops.fs], 'Alpha', 0.3);
    yline(ysamp(ilast));
    yline(ysamp(ifirst));

    ax2 = nexttile;
    st_shift = st3(:,2) + spk_shifts;% imin(batch_id) * dd;
    for j = spkTh:100
        % for each amplitude bin, plot all the spikes of that size in the
        % same shade of gray
        ix = st3(:, 3)==j; % the amplitudes are rounded to integers
        plot(st3(ix, 1)/ops.fs, st_shift(ix), '.', 'color', [1 1 1] * max(0, 1-j/40)) % the marker color here has been carefully tuned
        hold on
    end
    axis tight
    box off
    xline([ops.midpoint*ops.NTbuff/ops.fs], 'Alpha', 0.3);
    yline(ysamp(ilast));
    yline(ysamp(ifirst));
    linkaxes([ax1, ax2], 'xyz')


    %xlim([ops.midpoint*ops.NTbuff/ops.fs - 500, ops.midpoint*ops.NTbuff/ops.fs + 500]);
   
    %ylim([1000 1500])
    xlabel('time (sec)')
    ylabel('spike position (um)')
    title('Drift map')
end
%%
% convert to um 
dshift = imin * dd * -1;

% this is not really used any more, should get taken out eventually
[~, rez.iorig] = sort(mean(dshift, 2));

if do_correction
    % sigma for the Gaussian process smoothing
    sig = rez.ops.sig;
    % register the data batch by batch
    dprev = gpuArray.zeros(ops.ntbuff,ops.Nchan, 'single');
    for ibatch = 1:Nbatches
        dprev = shift_batch_on_disk2(rez, ibatch, dshift(ibatch, :), yblk1, sig, dprev);
    end
    fprintf('time %2.2f, Shifted up/down %d batches. \n', toc, Nbatches)
else
    fprintf('time %2.2f, Skipped shifting %d batches. \n', toc, Nbatches)
end
% keep track of dshift 
rez.dshift = dshift;
% keep track of original spikes
rez.st0 = st3;

rez.F = F1;
rez.F0 = F1;
rez.F0m = F1m;
rez.custom.spk_shifts = spk_shifts; % Drift correction amount per spike 
rez.custom.spk_block_idx = spk_block_idx; % Block each spike belongs to
rez.custom.ifirst = ifirst; % Start ysamp idx of blocking
rez.custom.ilast = ilast; % End ysamp idx of blocking
rez.custom.F1 = F1; % Amplitude x Spike Rate map of first session 
rez.custom.F2 = F2; % Amplitude x Spike Rate map of second session
rez.custom.yblk1 = yblk1; % Centers of blocks
rez.custom.yblk2 = yblk2; % Block centers
rez.custom.ysamp = ysamp; % Sampling positions in y. Upsampled from actual channel map.
rez.custom.nblocks = nblocks; % Number of blocks, may be different from sppecified number of nblocks

% next, we can just run a normal spike sorter, like Kilosort1, and forget about the transformation that has happened in here 

%%



