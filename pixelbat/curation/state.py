"""Curation state of one session from its decision log, and Kilosort's duplicate-spike rule for merged units."""
import json
import os

import numpy as np
from kilosort.postprocessing import remove_duplicates

KINDS = ['merge', 'unmerge', 'label', 'flag', 'keep', 'floor', 'undo']
LABELS = ['good', 'mua', 'noise', 'unstable', 'few', None]


def read_log(log):
    """Every logged event, oldest first."""
    if not os.path.exists(log):
        return []
    return [json.loads(line) for line in open(log)]


def not_undone(logged):
    """Events left after each undo removes the latest event before it."""
    events = []
    for event in logged:
        if event['kind'] == 'undo':
            events.pop()
        else:
            events.append(event)
    return events


def current_state(unit_ids, events):
    """Members (original units) of every current unit, user labels, flagged units, member sets kept apart, and the
    amplitude floor of original units: (floor, id of the unit made of the spikes below it)."""
    members = {int(u): [int(u)] for u in unit_ids}
    labels, flagged, kept, merged_from, floors = {}, set(), [], {}, {}
    for event in events:
        if event['kind'] == 'merge':
            if len(set(event['units'])) < 2:
                raise ValueError('a merge needs two or more different units')
            merged_from[event['id']] = {u: members.pop(u) for u in event['units']}
            members[event['id']] = sorted(m for parts in merged_from[event['id']].values() for m in parts)
            # The merged unit takes its members' label when they all had the same one
            agreed = {labels.get(u) for u in event['units']}
            labels[event['id']] = agreed.pop() if len(agreed) == 1 else None
        elif event['kind'] == 'unmerge':
            del members[event['unit']]
            members.update(merged_from.pop(event['unit']))
            labels.pop(event['unit'], None)
        elif event['kind'] == 'label':
            # A label on a whole undecided group also keeps it apart, in the same decision
            if event.get('keep'):
                kept.append({m for u in event['keep'] for m in members[u]})
            for unit, label in event['labels'].items():
                if label not in LABELS:
                    raise ValueError(f'unknown label {label}')
                labels[int(unit)] = label
                members[int(unit)]
        elif event['kind'] == 'flag':
            # A flag is a toggle on each named unit
            flagged ^= {u for u in event['units'] if members[u]}
        elif event['kind'] == 'floor':
            # A floor on an original unit; None removes it
            if event['unit'] not in [int(u) for u in unit_ids]:
                raise ValueError('an amplitude floor needs an original unit')
            floors.pop(event['unit'], None)
            if event['floor'] is not None:
                floors[event['unit']] = (float(event['floor']), event['id'])
        elif event['kind'] == 'keep':
            kept.append({m for u in event['units'] for m in members[u]})
        else:
            raise ValueError(f'unknown decision {event["kind"]}')
    labels = {unit: label for unit, label in labels.items() if label is not None and unit in members}
    return members, labels, flagged & set(members), kept, floors


def duplicate_window(sort):
    """Samples within which Kilosort drops a same-unit spike as a duplicate, from the sort's settings."""
    settings = np.load(os.path.join(sort, 'ops.npy'), allow_pickle=True).item()['settings']
    if settings.get('duplicate_spike_ms') is None:
        return int(settings['duplicate_spike_bins'])
    return int(settings['duplicate_spike_ms'] * settings['fs'] / 1000)


def refractory_thresholds(sort):
    """Thresholds of Kilosort's refractory test, from the sort's settings."""
    settings = np.load(os.path.join(sort, 'ops.npy'), allow_pickle=True).item()['settings']
    return {'acg_threshold': settings['acg_threshold'], 'ccg_threshold': settings['ccg_threshold']}


def not_duplicate(samples, window):
    """Kilosort's remove_duplicates on one unit's time-sorted spike samples: True for the spikes kept."""
    return remove_duplicates(samples.astype(np.int64), np.zeros(len(samples), dtype=np.int32), np.int32(window))[2]
