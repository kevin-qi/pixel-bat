"""Resolve GridBat rec folders and Trodes/Kilosort paths for one session."""
from __future__ import annotations

import glob
import os
import re

DATA_PATH = os.environ.get(
    'PIXELBAT_DATA', '/mnt/server5/users/KevinQi/datasets/GridBat'
)
EXPERIMENT = 'flight_room'


def _raw_path(bat_id: str, date: str) -> str:
    return os.path.join(DATA_PATH, bat_id, EXPERIMENT, 'raw', date)


def rec_dirs(bat_id: str, date: str) -> list[str]:
    raw_path = _raw_path(bat_id, date)
    if not os.path.isdir(raw_path):
        raise FileNotFoundError(f'No raw folder: {raw_path}')
    folders = (
        glob.glob(os.path.join(raw_path, 'ephys', '*.rec'))
        or glob.glob(os.path.join(raw_path, '*.rec'))
    )
    return sorted(folders)


def rec_file(rec_dir: str) -> str:
    """Prefer wireless *_merged.rec; else the folder-named .rec file."""
    merged = sorted(glob.glob(os.path.join(rec_dir, '*_merged.rec')))
    if len(merged) == 1:
        return merged[0]
    if len(merged) > 1:
        raise FileNotFoundError(
            f'Expected 1 *_merged.rec in {rec_dir}, found {merged}'
        )
    named = os.path.join(rec_dir, os.path.basename(rec_dir))
    if os.path.isfile(named):
        return named
    raise FileNotFoundError(
        f'No *_merged.rec or {os.path.basename(rec_dir)} in {rec_dir}'
    )


def find_rec_dir(bat_id: str, date: str, rec_dir: str | None = None) -> str:
    if rec_dir:
        path = rec_dir if os.path.isabs(rec_dir) else os.path.join(
            _raw_path(bat_id, date), 'ephys', rec_dir
        )
        if not os.path.isdir(path):
            raise FileNotFoundError(f'rec dir not found: {path}')
        return os.path.abspath(path)

    folders = rec_dirs(bat_id, date)
    with_merged = [
        d for d in folders
        if glob.glob(os.path.join(d, '*_merged.rec'))
    ]
    chosen = with_merged if with_merged else folders
    if len(chosen) != 1:
        raise FileNotFoundError(
            f'Expected exactly 1 .rec folder under {_raw_path(bat_id, date)}, '
            f'found {len(folders)}: {folders}. Pass --rec-dir.'
        )
    return chosen[0]


def extraction_binary(rec_dir: str) -> str | None:
    kilosort_folders = glob.glob(os.path.join(rec_dir, '*.kilosort'))
    if len(kilosort_folders) != 1:
        return None
    folder = kilosort_folders[0]
    fname = os.path.splitext(os.path.basename(folder))[0]
    binary = os.path.join(folder, f'{fname}.group0.dat')
    return binary if os.path.isfile(binary) else None


def resolve_sort_paths(
    bat_id: str,
    date: str,
    rec_dir: str | None = None,
    results_subdir: str = 'kilosort4',
) -> dict:
    rec_folder = find_rec_dir(bat_id, date, rec_dir=rec_dir)
    kilosort_folders = glob.glob(os.path.join(rec_folder, '*.kilosort'))
    if len(kilosort_folders) != 1:
        raise FileNotFoundError(
            f'Expected exactly 1 .kilosort extraction in {rec_folder}, '
            f'found {len(kilosort_folders)}. Cannot sort without '
            f'Trodes-extracted group0.dat.'
        )
    kilosort_folder = kilosort_folders[0]
    fname = os.path.splitext(os.path.basename(kilosort_folder))[0]
    binary_file = os.path.join(kilosort_folder, f'{fname}.group0.dat')
    channelmap_dat_file = os.path.join(
        kilosort_folder, f'{fname}.group0.coordinates.dat'
    )
    channelmap_mat_file = os.path.join(
        kilosort_folder, f'{fname}.group0.coordinates.mat'
    )
    results_dir = os.path.join(rec_folder, results_subdir)
    for path, label in [
        (binary_file, 'binary'),
        (channelmap_dat_file, 'channelmap .dat'),
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(f'Missing {label}: {path}')
    return {
        'rec_folder': rec_folder,
        'rec_file': rec_file(rec_folder),
        'kilosort_folder': kilosort_folder,
        'binary_file': binary_file,
        'channelmap_dat_file': channelmap_dat_file,
        'channelmap_mat_file': channelmap_mat_file,
        'results_dir': results_dir,
    }


_DAT_PATH_LINE = re.compile(r'^(\s*)dat_path\s*=\s*.*$', re.M)


def relativize_params_dat_path(
    results_dir: str,
    binary_file: str | None = None,
) -> str:
    """Point params.py dat_path at group0.dat relative to the results folder.

    Kilosort4 writes an absolute path (often the NVMe staging copy). Phy then
    breaks if that folder is opened on another machine or after the cache is
    evicted. The .dat lives next to the results dir, so a relative path moves
    with the rec folder.
    """
    results_dir = os.path.abspath(results_dir)
    params = os.path.join(results_dir, 'params.py')
    if not os.path.isfile(params):
        raise FileNotFoundError(f'no params.py in {results_dir}')
    if binary_file is None:
        binary_file = extraction_binary(os.path.dirname(results_dir))
        if not binary_file:
            raise FileNotFoundError(
                f'no group0.dat next to {results_dir}; pass binary_file='
            )
    binary_file = os.path.abspath(binary_file)
    rel = os.path.relpath(binary_file, results_dir).replace('\\', '/')
    new_line = f'dat_path = [{rel!r}]'
    with open(params, encoding='utf-8') as fh:
        text = fh.read()
    if not _DAT_PATH_LINE.search(text):
        raise ValueError(f'no dat_path line in {params}')
    new_text, n = _DAT_PATH_LINE.subn(
        lambda m: f'{m.group(1)}{new_line}', text, count=1
    )
    if n != 1:
        raise ValueError(f'expected 1 dat_path line in {params}, got {n}')
    if new_text != text:
        with open(params, 'w', encoding='utf-8') as fh:
            fh.write(new_text)
        print(f'[params] {params}: dat_path -> {rel}', flush=True)
    else:
        print(f'[params] {params}: already {rel}', flush=True)
    return rel
