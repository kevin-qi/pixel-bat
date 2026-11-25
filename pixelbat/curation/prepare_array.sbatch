#!/bin/bash
#SBATCH --job-name=curation_prepare
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=logs/prepare_%A_%a.out
# Curation caches of several sorts on a Slurm cluster, from the repository folder (mkdir logs first):
# sbatch --array=1-N%4 pixelbat/curation/prepare_array.sbatch SORTS_TXT (one sort folder per line)
set -euo pipefail
export OMP_NUM_THREADS=1
SORT=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$1")
/usr/bin/time -v .venv/bin/pixelbat-curate prepare "$SORT" --jobs 32
echo "PREPARE_DONE $SORT"
