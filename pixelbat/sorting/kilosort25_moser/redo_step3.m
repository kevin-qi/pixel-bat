function redo_step3(run_dir)
% Step 3 of Kilosort 2.5 on rez_step2.mat of one run, into <run_dir>/curation: every split made (also those the
% correlogram dip vetoes in stock), no merge, stock cutoff. Merges of find_merges and the vetoed splits are saved as proposals.

t_all = tic;
out_dir = fullfile(run_dir, 'curation');
mkdir(out_dir);

%% Step 2 result
t = tic;
saved = load(fullfile(run_dir, 'rez_step2.mat'));
rez = saved.rez;
clear saved
n_spikes = size(rez.st3, 1);
info.config.fs = rez.ops.fs;
info.config.NchanTOT = rez.ops.NchanTOT;
info.config.scaleproc = rez.ops.scaleproc;
info.config.Th = rez.ops.Th;
info.config.AUCsplit = rez.ops.AUCsplit;
info.n_spikes_step2 = n_spikes;
info.n_units_step2 = size(rez.W, 2);
info.stage_s.load = toc(t);
fprintf('rez_step2.mat: %.0f s, %d spikes, %d units\n', info.stage_s.load, n_spikes, info.n_units_step2)

%% Splits without the correlogram veto
t = tic;
rez.ops.split_ccg_veto = 0;
info.config.split_ccg_veto = rez.ops.split_ccg_veto;
rez = splitAllClusters(rez, 1);
n_units = size(rez.W, 2);
[~, isort] = sort(rez.st3(:,1), 'ascend');
precut = rez.st3(isort, :);
spikes_per_unit = accumarray(rez.st3(:,2), 1, [n_units 1]);
split_made = rez.split_log(:,9) > 0;
info.n_split_candidates = size(rez.split_log, 1);
info.n_splits_made = nnz(split_made);
info.n_splits_made_despite_dip = nnz(split_made & rez.split_log(:,8) == 1);
info.n_units = n_units;
info.stage_s.splits = toc(t);
fprintf('splits: %.0f s, %d candidates, %d made, %d of them with a correlogram dip, %d units\n', ...
    info.stage_s.splits, info.n_split_candidates, info.n_splits_made, info.n_splits_made_despite_dip, n_units)

%% Merge proposals on the split units
t = tic;
rez_m = find_merges(rez, 1);
rez_p = find_merges(rez, 0);
[pair_i, pair_j] = find(triu(~cellfun(@isempty, rez_p.K_CCG), 1));
pair = sub2ind([n_units n_units], pair_i, pair_j);
merge_pairs = [pair_i, pair_j, rez.simScore(pair), rez_p.Q_CCG(pair), rez_p.R_CCG(pair)];
merge_log = rez_m.merge_log;
info.n_merges = size(merge_log, 1);
info.n_merge_pairs_tested = numel(pair);
info.stage_s.merges = toc(t);
fprintf('merge proposals: %.0f s, %d merges of %d pairs tested\n', info.stage_s.merges, info.n_merges, info.n_merge_pairs_tested)

%% Cutoff and Phy folder, as main_kilosort.m
t = tic;
rez = set_cutoff(rez);
rez.good = get_good_units(rez);
rezToPhy(rez, out_dir);
kept = zeros(n_spikes, 1, 'uint8');
kept(rez.st3(:,6)) = 1;
cutoff_Th = nan(n_units, 1);
cutoff_Th(1:numel(rez.Ths)) = rez.Ths;
cutoff_Th(spikes_per_unit == 0) = nan;
info.n_spikes = size(rez.st3, 1);
info.n_units_with_spikes = numel(unique(rez.st3(:,2)));
info.n_good = sum(rez.good);
info.stage_s.cutoff_output = toc(t);
fprintf('cutoff and output: %.0f s, %d of %d spikes above cutoff, %d units with spikes, %d good\n', ...
    info.stage_s.cutoff_output, info.n_spikes, n_spikes, info.n_units_with_spikes, info.n_good)

%% Spikes before the cutoff, proposals; unit ids start at 0, -1 is no unit
writeNPY(uint64(precut(:,1)), fullfile(out_dir, 'precut_spike_times.npy'));
writeNPY(int32(precut(:,2) - 1), fullfile(out_dir, 'precut_units.npy'));
writeNPY(single(precut(:,4)), fullfile(out_dir, 'precut_vexp.npy'));
writeNPY(kept(isort), fullfile(out_dir, 'precut_kept.npy'));
writeNPY(cutoff_Th, fullfile(out_dir, 'cutoff_Th.npy'));
writeNPY([merge_log(:,1:2) - 1, merge_log(:,3:4)], fullfile(out_dir, 'merge_log.npy'));
writeNPY([merge_pairs(:,1:2) - 1, merge_pairs(:,3:5)], fullfile(out_dir, 'merge_pairs.npy'));
writeNPY([rez.split_log(:,1) - 1, rez.split_log(:,2:8), rez.split_log(:,9) - 1], fullfile(out_dir, 'split_log.npy'));
writeNPY(rez.Wrot, fullfile(out_dir, 'Wrot.npy'));

%% Run record
info.stage_s.total = toc(t_all);
info.matlab = version;
info.patches = fileread(fullfile(fileparts(fileparts(which('find_merges'))), 'patches.sha256'));
fid = fopen(fullfile(out_dir, 'sort.json'), 'w');
fprintf(fid, '%s', jsonencode(info));
fclose(fid);
fprintf('step 3: %.0f s\n', info.stage_s.total)
