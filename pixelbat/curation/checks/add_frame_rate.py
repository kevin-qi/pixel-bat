"""Add the tracking frame rate to caches prepared before rate maps existed: add_frame_rate.py SESSIONS_CSV."""
import os
import sys

import numpy as np
import pandas as pd

from pixelbat.curation.positions.flight_room import frame_rate_hz

sessions = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
for _, session in sessions.iterrows():
    path = os.path.join(session['out'], 'cache', 'position.npz')
    if os.path.exists(path):
        position = dict(np.load(path))
        if 'frame_rate_hz' not in position:
            position['frame_rate_hz'] = frame_rate_hz(session['flight_paths'])
            np.savez(path + '.tmp.npz', **position)
            os.replace(path + '.tmp.npz', path)
            print(session['name'], float(position['frame_rate_hz']))
