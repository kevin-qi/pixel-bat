function run_ks25_moser(binary, coordinates_mat, n_chan, sign, nblocks, fproc_dir, out_dir)
% Kilosort 2.5 with the Moser patch set on one recording: the uncut, unmerged sort as a Phy folder, with the merges
% and splits of step 3 computed on copies and saved as proposals; then redo_step3 writes the split, cut sort into
% curation/. Needs Kilosort-2.5-moser and npy-matlab on the path.

mkdir(out_dir);

%% Config
ops.fbinary = binary;
ops.fproc = fullfile(fproc_dir, 'temp_wh.dat');
ops.chanMap = coordinates_mat;
ops.NchanTOT = n_chan;
ops.sign = sign;
ops.nblocks = nblocks;
ops.fs = 30000;
ops.fshigh = 300;
ops.CAR = 1;
ops.Th = [10 4];
ops.lam = 10;
ops.AUCsplit = 0.9;
ops.split_ccg_veto = 1;
ops.minFR = 1/50;
ops.momentum = [20 400];
ops.sigmaMask = 30;
ops.spkTh = -6;
ops.sig = 20;
ops.ntbuff = 64;
ops.NT = 64*1024 - ops.ntbuff;
ops.nt0 = 61;
ops.nfilt_factor = 8;
ops.whiteningRange = 32;
ops.nSkipCov = 25;
ops.nskip = 25;
ops.scaleproc = 200;
ops.useStableMode = 1;
ops.trange = [0 Inf];
ops.fig = 0;
info.config = ops;

%% Preprocessing
t = tic;
rez = preprocessDataSub(ops);
info.stage_s.preprocess = toc(t);
n_batches = rez.ops.Nbatch;
whitened = dir(ops.fproc);
fprintf('preprocess: %.0f s, temp_wh.dat %d of %d bytes\n', info.stage_s.preprocess, whitened.bytes, 2 * n_batches * ops.NT * rez.ops.Nchan)

%% Drift correction
t = tic;
rez = datashift2(rez, 1);
info.stage_s.drift = toc(t);
n1 = accumarray(rez.st0(:,5), 1, [n_batches 1]);
info.max_n1 = max(n1);
fprintf('drift correction: %.0f s, at most %d step-1 spikes in a batch\n', info.stage_s.drift, info.max_n1)

%% Template learning and extraction
t = tic;
rez = learnAndSolve8b(rez, 1);
info.stage_s.templates = toc(t);
n_spikes = size(rez.st3, 1);
n_units = size(rez.W, 2);
rez.st3(:,6) = (1:n_spikes)';
n_final = accumarray(rez.st3(:,5), 1, [n_batches 1]);
spikes_per_unit = accumarray(rez.st3(:,2), 1, [n_units 1]);
info.n_spikes = n_spikes;
info.n_units = n_units;
info.nInnerIter = rez.nInnerIter;
info.max_templates_learning = max(rez.Nfilt_learn);
info.template_cap = rez.ops.Nfilt;
% Spikes added by the last iteration
last_learn = rez.count_learn(rez.nInnerIter + 1, :) - rez.count_learn(rez.nInnerIter, :);
last_final = rez.count_final(rez.nInnerIter + 1, :) - rez.count_final(rez.nInnerIter, :);
info.batches_not_converged_learning = nnz(last_learn);
info.batches_not_converged_final = nnz(last_final);
info.max_kernel_spikes_learning = max(rez.count_learn(rez.nInnerIter + 1, :));
info.max_kernel_spikes_final = max(rez.count_final(rez.nInnerIter + 1, :));
fprintf('templates: %.0f s, %d spikes, %d units, at most %d of %d templates while learning\n', ...
    info.stage_s.templates, n_spikes, n_units, info.max_templates_learning, info.template_cap)
fprintf('matching pursuit, %d iterations: not converged in %d learning and %d final batches of %d, at most %d spikes in a batch\n', ...
    rez.nInnerIter, info.batches_not_converged_learning, info.batches_not_converged_final, n_batches, info.max_kernel_spikes_final)

%% Step 2 result in full
t = tic;
saved.rez = rez;
% Stock loop of main_kilosort.m
rez_fields = fieldnames(saved.rez);
for i = 1:numel(rez_fields)
    field_name = rez_fields{i};
    if(isa(saved.rez.(field_name), 'gpuArray'))
        saved.rez.(field_name) = gather(saved.rez.(field_name));
    end
end
save(fullfile(out_dir, 'rez_step2.mat'), '-struct', 'saved', '-v7.3', '-nocompression');
clear saved
info.stage_s.save_step2 = toc(t);
fprintf('rez_step2.mat: %.0f s\n', info.stage_s.save_step2)

%% Merge proposals
t = tic;
rez_m = find_merges(rez, 1);
rez_p = find_merges(rez, 0);
merge_label = accumarray(rez.st3(:,2), rez_m.st3(:,2), [n_units 1], @max);
[pair_i, pair_j] = find(triu(~cellfun(@isempty, rez_p.K_CCG), 1));
pair = sub2ind([n_units n_units], pair_i, pair_j);
merge_pairs = [pair_i, pair_j, rez.simScore(pair), rez_p.Q_CCG(pair), rez_p.R_CCG(pair)];
info.n_merges = size(rez_m.merge_log, 1);
info.n_merge_pairs_tested = numel(pair);
info.stage_s.merges = toc(t);
fprintf('merge proposals: %.0f s, %d merges of %d pairs tested\n', info.stage_s.merges, info.n_merges, info.n_merge_pairs_tested)

%% Split proposals
t = tic;
rez_s = splitAllClusters(rez, 1);
split_spikes = rez_s.split_log(:,2);
split_n_low = cellfun(@numel, rez_s.split_low)';
split_Q12 = rez_s.split_log(:,3);
split_R = rez_s.split_log(:,4);
split_nremove = rez_s.split_log(:,5);
split_confidence = min(rez_s.split_log(:,6), rez_s.split_log(:,7));
% Criteria of splitAllClusters.m
split_vetoed = split_Q12 < .25 & split_R < .05;
split_accepted = ~split_vetoed & split_nremove > .05 & split_confidence > ops.AUCsplit & min(split_n_low, split_spikes - split_n_low) > 300;
split_child = zeros(size(split_accepted));
split_child(split_accepted) = n_units + (1:nnz(split_accepted))';
info.n_split_candidates = numel(split_accepted);
info.n_splits_vetoed = nnz(split_vetoed);
info.n_splits_accepted = nnz(split_accepted);
info.n_splits_made = size(rez_s.W, 2) - n_units;
info.stage_s.splits = toc(t);
fprintf('split proposals: %.0f s, %d candidates, %d vetoed by the correlogram, %d accepted (%d made by Kilosort)\n', ...
    info.stage_s.splits, info.n_split_candidates, info.n_splits_vetoed, info.n_splits_accepted, info.n_splits_made)

%% Stock automatic result
t = tic;
rez_auto = splitAllClusters(rez_m, 1);
% set_cutoff without spike features
rez_auto.cProj = [];
rez_auto.cProjPC = [];
rez_auto = set_cutoff(rez_auto);
auto_labels = zeros(n_spikes, 1);
auto_labels(rez_auto.st3(:,6)) = rez_auto.st3(:,2);
info.n_units_automatic = numel(unique(rez_auto.st3(:,2)));
info.n_spikes_automatic = size(rez_auto.st3, 1);
info.stage_s.automatic = toc(t);
fprintf('automatic result: %.0f s, %d units, %d of %d spikes above cutoff\n', info.stage_s.automatic, info.n_units_automatic, info.n_spikes_automatic, n_spikes)

%% Cutoff of each unmerged unit
t = tic;
rez_c = rez;
rez_c.cProj = [];
rez_c.cProjPC = [];
rez_c = set_cutoff(rez_c);
above_cutoff = zeros(n_spikes, 1, 'uint8');
above_cutoff(rez_c.st3(:,6)) = 1;
cutoff_Th = nan(n_units, 1);
cutoff_Th(1:numel(rez_c.Ths)) = rez_c.Ths;
cutoff_Th(spikes_per_unit == 0) = nan;
info.n_spikes_above_cutoff = size(rez_c.st3, 1);
info.stage_s.cutoff = toc(t);
fprintf('cutoff of unmerged units: %.0f s, %d of %d spikes above cutoff\n', info.stage_s.cutoff, info.n_spikes_above_cutoff, n_spikes)

%% Uncut, unmerged Phy folder
t = tic;
rez.ops.AUCsplit = Inf;
rez_out = splitAllClusters(rez, 1);
rez_out.good = rez_c.good;
rez_out.est_contam_rate = rez_c.est_contam_rate;
rez_out.good = get_good_units(rez_out);
rezToPhy(rez_out, out_dir);
info.n_good = sum(rez_out.good);

%% Proposals and diagnostics, spikes in the order of spike_times.npy
[~, isort] = sort(rez.st3(:,1), 'ascend');
place = zeros(n_spikes, 1);
place(isort) = 1:n_spikes;
split_low = cat(1, rez_s.split_low{:});
% Unit ids and spike places start at 0; -1 is no unit
writeNPY(int32(auto_labels(isort) - 1), fullfile(out_dir, 'auto_labels.npy'));
writeNPY(int32(rez_s.st3(isort,2) - 1), fullfile(out_dir, 'split_labels.npy'));
writeNPY(single(rez.st3(isort,4)), fullfile(out_dir, 'spike_vexp.npy'));
writeNPY(above_cutoff(isort), fullfile(out_dir, 'above_cutoff_unmerged.npy'));
writeNPY(cutoff_Th, fullfile(out_dir, 'cutoff_Th.npy'));
writeNPY(int32(merge_label - 1), fullfile(out_dir, 'merge_label.npy'));
writeNPY([rez_m.merge_log(:,1:2) - 1, rez_m.merge_log(:,3:4)], fullfile(out_dir, 'merge_log.npy'));
writeNPY([merge_pairs(:,1:2) - 1, merge_pairs(:,3:5)], fullfile(out_dir, 'merge_pairs.npy'));
writeNPY([rez_s.split_log(:,1) - 1, split_spikes, split_n_low, split_Q12, split_R, split_nremove, rez_s.split_log(:,6:7), ...
    split_vetoed, split_accepted, split_child - 1], fullfile(out_dir, 'split_log.npy'));
writeNPY(uint32(place(split_low) - 1), fullfile(out_dir, 'split_low.npy'));
writeNPY(n1, fullfile(out_dir, 'n1.npy'));
writeNPY(n_final, fullfile(out_dir, 'n_final.npy'));
writeNPY(rez.count_learn, fullfile(out_dir, 'count_learn.npy'));
writeNPY(rez.count_final, fullfile(out_dir, 'count_final.npy'));
writeNPY(rez.Nfilt_learn, fullfile(out_dir, 'Nfilt_learn.npy'));
writeNPY(rez.iorig, fullfile(out_dir, 'iorig.npy'));
writeNPY(rez.dshift, fullfile(out_dir, 'dshift.npy'));
writeNPY(rez.Wrot, fullfile(out_dir, 'Wrot.npy'));
info.stage_s.output = toc(t);
fprintf('output: %.0f s, %d good of %d units\n', info.stage_s.output, info.n_good, n_units)

%% Run record
gpu = gpuDevice;
info.gpu = gpu.Name;
info.cuda_toolkit = gpu.ToolkitVersion;
info.matlab = version;
info.patches = fileread(fullfile(fileparts(fileparts(which('find_merges'))), 'patches.sha256'));
fid = fopen(fullfile(out_dir, 'sort.json'), 'w');
fprintf(fid, '%s', jsonencode(info));
fclose(fid);

%% Split, cut sort for curation
redo_step3(out_dir);
