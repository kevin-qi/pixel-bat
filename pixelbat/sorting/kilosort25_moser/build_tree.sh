#!/usr/bin/env bash
# Rebuilds Kilosort-2.5-moser/ from upstream Kilosort tag v2.5 and patches/, to check the vendored tree: build_tree.sh OUT_DIR
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=$1
upstream=$(mktemp -d)
git clone --quiet https://github.com/MouseLand/Kilosort "$upstream"
mkdir "$out"
git -C "$upstream" archive v2.5 | tar -x -C "$out"

# Without this, git apply inside another repository skips every file and reports success
export GIT_CEILING_DIRECTORIES=$out
cd "$out"
for patch in P0_spike_holes_v2.5.2 P1_step1_spikes_per_batch P2_step2_matching_iterations P3_step2_spikes_per_batch \
             P4_step2_similarity_limit P5_step3_similarity_limit P6_split_log P7_sign M1_merge_log I1_iteration_counts P8_split_veto_switch; do
    git apply --check --whitespace=nowarn "$here/patches/$patch.patch"
    git apply --whitespace=nowarn "$here/patches/$patch.patch"
    git apply --check --reverse --whitespace=nowarn "$here/patches/$patch.patch"
    echo "applied $patch"
done

# Patch set identity, read by run_ks25_moser.m
(cd "$here/patches" && sha256sum *.patch) > "$out/patches.sha256"
rm -rf "$upstream"
echo "$({ diff -rq "$here/Kilosort-2.5-moser" "$out" || true; } | wc -l) files differ from the vendored Kilosort-2.5-moser/"
