"""One sort opened ahead of the app, so that the app only reads it: python -m pixelbat.curation.open_ahead SORT.

Saves <SORT>/curation/opened with the evidence of every merge group, possible pair and neighbour computed.
"""
import sys
import time

from pixelbat.curation.opened import load, neighbour_evidence, save_caches, unit_table
from pixelbat.curation.state import current_state, not_undone, read_log

t0 = time.time()
sort = sys.argv[1]
data = load(sort)
state = current_state(data['units'].index, not_undone(read_log(data['log'])))
unit_table(data, state)
members, _, _, _, floors = state
for unit in members:
    neighbour_evidence(data, members, floors, unit)
save_caches(data)
print(f'{sort}: {len(data["units"])} units opened ahead; {time.time() - t0:.0f} s')
