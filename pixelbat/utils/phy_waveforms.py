"""Pre-extract phy Waveform View snippets so curation does not random-read group0.dat.

Calls `phy extract-waveforms` (https://github.com/cortex-lab/phy).
Install: uv tool install --python 3.12 phy

Phy defaults (also used when it auto-extracts compressed ephys):
  500 spikes per original template, 16 best channels, 20 time chunks.
The GUI then draws up to 100 waveforms per cluster from that pool.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
from pathlib import Path

from pixelbat.utils.session_paths import relativize_params_dat_path

# phy extract-waveforms positional / --nc defaults.
PHY_N_SPIKES_PER_TEMPLATE = 500
PHY_N_CHANNELS = 16

_DAT_PATH_LINE = re.compile(r'^dat_path\s*=\s*(.+)$', re.M)
SUBSET_NAME = '_phy_spikes_subset.waveforms.npy'


def phy_bin() -> str:
    candidates = [
        os.environ.get('PIXELBAT_PHY'),
        str(Path.home() / '.local' / 'bin' / 'phy'),
        shutil.which('phy'),
    ]
    checked = []
    for cand in candidates:
        if not cand:
            continue
        checked.append(cand)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    raise FileNotFoundError(
        'No phy binary. Install with: uv tool install --python 3.12 phy '
        '(then ensure ~/.local/bin is on PATH) or set PIXELBAT_PHY. '
        'Checked: ' + ', '.join(checked)
    )


def subset_exists(results_dir: str) -> bool:
    d = Path(results_dir)
    return all(
        (d / name).is_file()
        for name in (
            SUBSET_NAME,
            '_phy_spikes_subset.channels.npy',
            '_phy_spikes_subset.spikes.npy',
        )
    )


def _params_dat_readable(results_dir: str) -> bool:
    params = Path(results_dir) / 'params.py'
    if not params.is_file():
        return False
    m = _DAT_PATH_LINE.search(params.read_text(encoding='utf-8'))
    if not m:
        return False
    try:
        val = ast.literal_eval(m.group(1).strip())
    except (SyntaxError, ValueError):
        return False
    if isinstance(val, (list, tuple)):
        val = val[0] if val else None
    if not val:
        return False
    path = Path(val)
    if not path.is_absolute():
        path = Path(results_dir) / path
    return path.is_file()


def extract_phy_waveforms(
    results_dir: str,
    *,
    n_spikes: int = PHY_N_SPIKES_PER_TEMPLATE,
    n_channels: int = PHY_N_CHANNELS,
    skip_if_exists: bool = True,
) -> None:
    """Write _phy_spikes_subset.*.npy next to params.py."""
    results_dir = os.path.abspath(results_dir)
    params = os.path.join(results_dir, 'params.py')
    if not os.path.isfile(params):
        raise FileNotFoundError(f'no params.py in {results_dir}')
    if skip_if_exists and subset_exists(results_dir):
        print(f'[phy  ] skip subset exists: {results_dir}', flush=True)
        return
    if not _params_dat_readable(results_dir):
        print(
            '[phy  ] dat_path not readable; rewriting relative then extracting',
            flush=True,
        )
        relativize_params_dat_path(results_dir)
        if not _params_dat_readable(results_dir):
            raise FileNotFoundError(
                f'no readable group0.dat for {results_dir}'
            )

    cmd = [
        phy_bin(),
        'extract-waveforms',
        params,
        str(n_spikes),
        '--nc',
        str(n_channels),
    ]
    print(f'[phy  ] {" ".join(cmd)}', flush=True)
    env = os.environ.copy()
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    res = subprocess.run(cmd, cwd=results_dir, env=env)
    if res.returncode != 0:
        raise RuntimeError(
            f'phy extract-waveforms failed rc={res.returncode} for {params}'
        )
    if not subset_exists(results_dir):
        raise FileNotFoundError(
            f'extract finished but no {SUBSET_NAME} in {results_dir}'
        )
    print(f'[phy  ] wrote subset in {results_dir}', flush=True)
