"""Thin wrapper around SpikeGadgets `trodesexport`.

Does not read extracted files — that is readTrodesExtractedDataFile.

Linux (serverx) uses `Trodes_2-8-3_Ubuntu24/trodesexport` with native
`/mnt/server5/...` paths. WSL still uses the Windows `.exe` via Y:\\.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from pixelbat.utils.session_paths import (
    extraction_binary,
    find_rec_dir,
    rec_file,
)

# Streams needed to sort (kilosort) plus the usual companions. Matches
# bat-spike-sort-v5-pipeline/run_v5_session.py plus MATLAB's -interp 0.
DEFAULT_FLAGS = ('-kilosort', '-lfp', '-dio', '-time', '-analogio', '-interp', '0')

# Y: on Windows == //192.168.88.155/server_home, mounted here at /mnt/server5
NAS_LINUX = '/mnt/server5'
NAS_WINDOWS = 'Y:'
DEFAULT_TRODES_WINDOWS = f'{NAS_LINUX}/users/KevinQi/Trodes_2-8-3_Windows11'
DEFAULT_TRODES_LINUX = f'{NAS_LINUX}/users/KevinQi/Trodes_2-8-3_Ubuntu24'
LOCAL_TRODES_LINUX = str(Path.home() / 'Trodes_2-8-3_Ubuntu24')
# Complete extracts are ~97% of the .rec; anything under this is a killed run.
INCOMPLETE_DAT_FRAC = 0.5
EXTRACT_SIDECARS = (
    '.kilosort', '.LFP', '.DIO', '.analog', '.time', '.timestampoffset',
)


def _is_wsl() -> bool:
    try:
        return 'microsoft' in Path('/proc/version').read_text().lower()
    except OSError:
        return False


def linux_path(path: str) -> str:
    """Turn Y:\\users\\... into /mnt/server5/users/... so we can stat files."""
    p = path.strip().replace('/', '\\')
    if len(p) >= 2 and p[1] == ':' and p[0].upper() == 'Y':
        rest = p[2:].lstrip('\\').replace('\\', '/')
        return f'{NAS_LINUX}/{rest}'
    return path


def windows_nas_path(path: str) -> str:
    """Turn /mnt/server5/... into Y:\\... for Windows trodesexport.exe.

    Do not use wslpath -w: that yields \\\\wsl.localhost\\... and reads the
    NAS through 9p instead of the Y: share.
    """
    p = os.path.abspath(linux_path(path))
    prefix = NAS_LINUX.rstrip('/')
    if p == prefix or p.startswith(prefix + '/'):
        rest = p[len(prefix):].replace('/', '\\')
        return NAS_WINDOWS + rest
    return p


def _is_windows_exe(path: Path) -> bool:
    return path.suffix.lower() == '.exe' or path.name.lower().endswith('.exe')


def default_trodes_dir() -> str:
    if _is_wsl() or os.name == 'nt':
        return DEFAULT_TRODES_WINDOWS
    local = Path(LOCAL_TRODES_LINUX) / 'trodesexport'
    if local.is_file():
        return LOCAL_TRODES_LINUX
    return DEFAULT_TRODES_LINUX


def extraction_is_complete(rec_dir: str) -> bool:
    """True if group0.dat exists and is not a killed partial write."""
    existing = extraction_binary(rec_dir)
    if not existing:
        return False
    rec_path = rec_file(rec_dir)
    rec_sz = os.path.getsize(rec_path)
    dat_sz = os.path.getsize(existing)
    if rec_sz > 10_000_000 and dat_sz < INCOMPLETE_DAT_FRAC * rec_sz:
        return False
    return True


def _remove_extract_products(rec_dir: str) -> None:
    rec_path = Path(rec_dir)
    for child in rec_path.iterdir():
        if any(child.name.endswith(sfx) for sfx in EXTRACT_SIDECARS):
            print(f'[extract] removing incomplete {child}', flush=True)
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def trodesexport_bin(explicit: str | None = None) -> str:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    for env_name in ('PIXELBAT_TRODES', 'TRODES_PATH'):
        val = os.environ.get(env_name)
        if val:
            candidates.append(val)
    candidates.append(default_trodes_dir())

    wsl = _is_wsl()
    checked: list[str] = []
    for cand in candidates:
        path = Path(linux_path(os.path.expanduser(cand)))
        if path.is_dir():
            names = ['trodesexport.exe', 'trodesexport']
            if not (wsl or os.name == 'nt'):
                names = ['trodesexport', 'trodesexport.exe']
            exes = [path / n for n in names]
        else:
            exes = [path]
        for exe in exes:
            checked.append(str(exe))
            if not exe.is_file():
                continue
            if _is_windows_exe(exe) and not (wsl or os.name == 'nt'):
                raise FileNotFoundError(
                    f'{exe} is a Windows binary; serverx cannot run it. '
                    f'Set PIXELBAT_TRODES to Trodes_2-8-3_Ubuntu24.'
                )
            return str(exe)
    raise FileNotFoundError(
        'No trodesexport found. Default is '
        f'{default_trodes_dir()}. Checked: ' + ', '.join(checked)
    )


def export_rec_dir(
    rec_dir: str,
    *,
    trodes: str | None = None,
    skip_if_exists: bool = True,
    flags: tuple[str, ...] = DEFAULT_FLAGS,
) -> str:
    """Run trodesexport into rec_dir. Returns the group0.dat path."""
    rec_path = rec_file(rec_dir)
    existing = extraction_binary(rec_dir)
    complete = extraction_is_complete(rec_dir)
    if skip_if_exists and complete:
        print(f'[extract] skip (already have {existing})', flush=True)
        return existing
    if existing and not complete:
        rec_sz = os.path.getsize(rec_path)
        dat_sz = os.path.getsize(existing)
        print(
            f'[extract] incomplete {existing} '
            f'({dat_sz / 1e9:.1f} GB dat vs {rec_sz / 1e9:.1f} GB rec); re-extracting',
            flush=True,
        )

    if existing is not None or any(
        Path(rec_dir).glob(f'*{sfx}') for sfx in EXTRACT_SIDECARS
    ):
        if not skip_if_exists or not complete:
            _remove_extract_products(rec_dir)

    exe = trodesexport_bin(trodes)
    rec_arg, out_arg = rec_path, rec_dir
    if _is_windows_exe(Path(exe)):
        rec_arg = windows_nas_path(rec_path)
        out_arg = windows_nas_path(rec_dir)
    cmd = [exe, '-rec', rec_arg, '-outputdirectory', out_arg, *flags]
    print(f'[extract] {" ".join(cmd)}', flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=rec_dir)
    if res.returncode != 0:
        raise RuntimeError(f'trodesexport failed rc={res.returncode} for {rec_path}')
    print(f'[extract] done in {(time.time() - t0) / 60:.1f} min', flush=True)

    binary = extraction_binary(rec_dir)
    if not binary:
        raise FileNotFoundError(
            f'trodesexport finished but no group0.dat under {rec_dir}'
        )
    return binary


def export_session(
    bat_id: str,
    date: str,
    *,
    rec_dir: str | None = None,
    trodes: str | None = None,
    skip_if_exists: bool = True,
) -> str:
    folder = find_rec_dir(bat_id, date, rec_dir=rec_dir)
    print(f'[extract] {bat_id} {date} rec_dir={folder}', flush=True)
    return export_rec_dir(
        folder, trodes=trodes, skip_if_exists=skip_if_exists
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract a GridBat session with trodesexport.'
    )
    parser.add_argument('--bat', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument(
        '--rec-dir',
        default=None,
        help='Rec folder name or absolute path if the date has more than one .rec',
    )
    parser.add_argument(
        '--trodes',
        default=None,
        help='Trodes install dir or trodesexport binary (else PIXELBAT_TRODES)',
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Run even if group0.dat already exists',
    )
    args = parser.parse_args()
    export_session(
        args.bat,
        args.date,
        rec_dir=args.rec_dir,
        trodes=args.trodes,
        skip_if_exists=not args.force,
    )
    print('[extract] COMPLETED ok', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print(f'[fail] {sys.argv}', flush=True)
        raise
