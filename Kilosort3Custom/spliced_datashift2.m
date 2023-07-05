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


spkTh = 10; % same as the usual "template amplitude", but for the generic templates

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
    ysamp = dmin + dd * [1:dmax] - dd/2;

    %[imin1, F1] = align_block(F(:, :, 1:ops.midpoint));
    [imin1,yblk1, F1, F1m] = pixelbat_align_block2(F(:, :, 1:ops.midpoint), ysamp, ops.nblocks);
    % register the second block as usual
    %[imin2, F2] = align_block(F(:, :, ops.midpoint+1:end));
    [imin2,yblk2, F2, F2m] = pixelbat_align_block2(F(:, :, ops.midpoint+1:end), ysamp, ops.nblocks);
    % now register the average first block to the average second block
    d0 = pixelbat_align_pairs(F1, F2)*5;
    
    % Non rigid splice correction
    nybins = size(F,1);
    yl = floor(nybins/ops.nblocks)-1;
    bins = round(linspace(1, nybins , 2*ops.nblocks-1));
    ifirst = bins(1:end-1);
    ilast  =  bins(2:end);
    figure;
    d0 = [];
    for j = 1:2*ops.nblocks-1
        isub = ifirst(j):ilast(j);
        d0 = [d0 align_pairs(F1(isub,:), F2(isub,:))];
        plot(isub, mean(mean(F1(isub,:),3),2));
        hold on
    end
    

    % concatenate the shifts
    imin = [imin1' imin2' + d0']';
    
    %imin = imin - mean(imin);
    %ops.datashift = 1;
else
    % determine registration offsets 
    ysamp = dmin + dd * [1:dmax] - dd/2;
    [imin,yblk, F0, F0m] = align_block2(F, ysamp, ops.nblocks);
    imin(ops.midpoint+1:end,:) = imin(ops.midpoint+1:end,:) + d0;
end

%% Get which block each spike belongs to
nybins = size(F,1);
block_bins = ysamp(round(linspace(1, nybins, 2*ops.nblocks-1)));
% spk_block_idx tells us which block each spike in st3 belongs to
[counts, bin_edges, spk_block_idx] = histcounts(st3(:,2), block_bins);


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
    set(gcf, 'Color', 'w')
    % raster plot of all spikes at their original depths
    st_shift = st3(:,2);% - imin(batch_id)' * dd;
    for j = spkTh:100
        % for each amplitude bin, plot all the spikes of that size in the
        % same shade of gray
        ix = st3(:, 3)==j; % the amplitudes are rounded to integers
        plot(st3(ix, 1)/ops.fs, st_shift(ix), '.', 'color', [1 1 1] * max(0, 1-j/40)) % the marker color here has been carefully tuned
        hold on
    end
    axis tight
    box off

    figure;
    tiledlayout(1,2);
    
    set(gcf, 'Color', 'w')
    % raster plot of all spikes at their original depths
    spk_shifts = zeros(size(batch_id));
    for k = 1:length(batch_id)
        spk_shifts(k) = imin(batch_id(k), spk_block_idx(k)) * dd;
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

    ax2 = nexttile;
    st_shift = st3(:,2) - spk_shifts;% imin(batch_id) * dd;
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
    
    linkaxes([ax1, ax2], 'xyz')
    %xlim([ops.midpoint*ops.NTbuff/ops.fs - 500, ops.midpoint*ops.NTbuff/ops.fs + 500]);
   
    %ylim([1000 1500])
    xlabel('time (sec)')
    ylabel('spike position (um)')
    title('Drift map')
end
%%
% convert to um 
dshift = imin * dd;

% this is not really used any more, should get taken out eventually
[~, rez.iorig] = sort(mean(dshift, 2));

if do_correction
    % sigma for the Gaussian process smoothing
    sig = rez.ops.sig;
    % register the data batch by batch
    dprev = gpuArray.zeros(ops.ntbuff,ops.Nchan, 'single');
    for ibatch = 1:Nbatches
        dprev = shift_batch_on_disk2(rez, ibatch, dshift(ibatch, :), yblk, sig, dprev);
    end
    fprintf('time %2.2f, Shifted up/down %d batches. \n', toc, Nbatches)
else
    fprintf('time %2.2f, Skipped shifting %d batches. \n', toc, Nbatches)
end
% keep track of dshift 
rez.dshift = dshift;
% keep track of original spikes
rez.st0 = st3;

rez.F = F;
rez.F0 = F0;
rez.F0m = F0m;

% next, we can just run a normal spike sorter, like Kilosort1, and forget about the transformation that has happened in here 

%%



