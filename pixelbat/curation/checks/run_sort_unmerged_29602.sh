#!/bin/bash
# Unmerged Kilosort4 sort of 29602/240103 with proposed merges, on the workstation GPU once the running sort has left it
set -euo pipefail
D=/mnt/pool2/scratch/KevinQi/TwinBat/curation
exec > $D/logs/sort_unmerged_29602_240103.out 2>&1
while kill -0 3347435 2>/dev/null; do sleep 20; done
cd /home/kevin/main/pixel-bat/curation
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMBA_NUM_THREADS=8 /home/kevin/main/TwinBat/.venv/bin/python sort_unmerged.py \
  /home/kevin/.cache/pixelbat/stage/f656e07555c6eabd/20240103_170535_merged.probe1.dat \
  /mnt/server4/users/KevinQi/datasets/GridBat/29602/flight_room/raw/240103/ephys/20240103_170535.rec/20240103_170535_merged.kilosort/20240103_170535_merged.channelmap_probe1.dat \
  $D/sorts/29602_240103_unmerged '{"Th_universal": 9, "Th_learned": 8, "nblocks": 1}'
