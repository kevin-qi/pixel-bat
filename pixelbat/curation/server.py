"""Curation app: serves the page and each opened sort's arrays once, then only records decisions: pixelbat-curate [--port PORT].

A sort is a Kilosort output folder; everything of its curation is in its curation/ folder."""
import gc
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from pixelbat.curation.labels import HANDOFF
from pixelbat.curation.opened import footprint, load, mean_template, merged_unit, merged_waveform, missing_none, near_channels, neighbour_evidence, new_id, partners, progress, rate_maps, recorded, refractory_measures, refractory_pairs, save_caches, spikes_key, unit_table
from pixelbat.curation.state import KINDS, current_state, not_undone, read_log

HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN = os.path.expanduser('~/.pixelbat/sorts.json')  # sorts opened on this machine: when each was opened last
loaded = {}  # the 3 sorts opened last
answering = []  # requests being answered; the background work waits while there are any
lock = threading.Lock()


def known_sorts():
    """Sort folders opened on this machine, each with when it was opened last."""
    if not os.path.exists(KNOWN):
        return {}
    return json.load(open(KNOWN))


def write_known(sorts):
    """The list of sorts opened on this machine, replaced whole."""
    os.makedirs(os.path.dirname(KNOWN), exist_ok=True)
    with open(KNOWN + '.partial', 'w') as f:
        json.dump(sorts, f, indent=1)
    os.replace(KNOWN + '.partial', KNOWN)


def file_time(path):
    """When a file was last written, None without the file."""
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(path))) if os.path.exists(path) else None


def prepared(folder):
    """Whether a folder is a sort prepared for curation."""
    return os.path.exists(os.path.join(folder, 'curation', 'cache', 'display_density.npy'))


def fill_partners(data):
    """Pair evidence of every current unit with its neighbours, computed ahead of the page asking."""
    members, _, _, _, floors = current_state(data['units'].index, not_undone(read_log(data['log'])))
    # Kilosort's compiled tests run once on two units, so that the first decision does not wait for their compilation
    pair = data['units'].index[:2].tolist()
    refractory_pairs(data, [spikes_key([unit], {}) for unit in pair])
    merged_unit(data, spikes_key(pair, {}))
    for unit in members:
        while answering:
            time.sleep(0.05)
        neighbour_evidence(data, members, floors, unit)
    save_caches(data)
    # The sort's caches stay for good: the garbage collector stops scanning them
    gc.freeze()


def describe(event):
    """A decision in words, for the status line."""
    if event['kind'] == 'label':
        labels = event['labels']
        if len(labels) <= 4:
            said = ', '.join(f'{unit} → {label or "no label"}' for unit, label in labels.items())
        else:
            counts = pd.Series(list(labels.values())).fillna('no label').value_counts()
            said = f'{len(labels)} units → ' + ', '.join(f'{n} {label}' for label, n in counts.items())
        return ('kept apart ' + ' + '.join(map(str, event['keep'])) + '; ' if event.get('keep') else '') + said
    if event['kind'] == 'floor':
        return f'unit {event["unit"]}: amplitude floor removed' if event['floor'] is None else f'unit {event["unit"]}: spikes below amplitude {event["floor"]:.1f} set aside'
    if event['kind'] == 'unmerge':
        return f'unmerged unit {event["unit"]} (its own label, if any, is dropped; its parts keep theirs)'
    return {'merge': 'merged ', 'flag': 'flag toggled on ', 'keep': 'kept apart '}[event['kind']] + ' + '.join(map(str, event['units']))


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send(self, body, content_type, status=200, headers=()):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for name, value in [('Cache-Control', 'no-store'), *headers]:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, status=200):
        self.send(json.dumps(obj, allow_nan=False).encode(), 'application/json', status)

    def session(self, sort):
        with lock:
            if sort not in loaded:
                loaded[sort] = load(sort)
            # The sort asked for last is kept longest
            loaded[sort] = loaded.pop(sort)
            for old in list(loaded)[:-3]:
                loaded.pop(old)
        return loaded[sort]

    def table(self, data, logged):
        records, groups = unit_table(data, current_state(data['units'].index, not_undone(logged)))
        # Merges this tool made when the session first opened
        automatic = {e['id'] for e in not_undone(logged) if e['kind'] == 'merge' and e['user'].endswith(f'(<{data["few"]} spikes)')}
        for record in records:
            record['auto_merge'] = record['unit'] in automatic
        return {'units': records, 'groups': groups, 'n_events': len(not_undone(logged)), 'version': len(logged)}

    def get(self):
        url = urlparse(self.path)
        parts = url.path.strip('/').split('/')
        query = parse_qs(url.query)
        if url.path == '/':
            return self.send(open(os.path.join(HERE, 'index.html'), 'rb').read(), 'text/html; charset=utf-8')
        if parts[0] == 'sorts':
            # Sorts opened on this machine, each with its decisions so far
            sorts = [{'sort': sort, 'opened': opened, 'prepared': prepared(sort), 'decided': file_time(os.path.join(sort, 'curation', 'curation_log.jsonl')),
                      'decisions': len(not_undone(read_log(os.path.join(sort, 'curation', 'curation_log.jsonl'))))}
                     for sort, opened in known_sorts().items()]
            return self.send_json({'user': os.environ.get('USER', os.environ.get('USERNAME')), 'home': os.path.expanduser('~'), 'sorts': sorts})
        if parts[0] == 'folder':
            # One folder: whether it is a sort (a Kilosort output folder), whether prepared, and its subfolders
            folder = os.path.normpath(query['path'][0])
            inside = sorted(entry.name for entry in os.scandir(folder) if entry.is_dir() and not entry.name.startswith('.'))
            return self.send_json({'path': folder, 'parent': os.path.dirname(folder), 'sort': os.path.exists(os.path.join(folder, 'params.py')),
                                   'prepared': prepared(folder),
                                   'folders': [{'name': name, 'sort': os.path.exists(os.path.join(folder, name, 'params.py')),
                                                'prepared': prepared(os.path.join(folder, name))} for name in inside]})
        if parts[0] == 'progress':
            # What the app is doing to open a sort, for the page to show
            return self.send_json({'stage': progress.get(os.path.normpath(query['sort'][0]))})
        data = self.session(os.path.normpath(query['sort'][0]))
        if parts[0] == 'table':
            progress[data['sort']] = 'unit table'
            self.send_json(self.table(data, read_log(data['log'])))
            # Once the first table is out, the pair evidence of every unit is computed ahead of the page asking
            if 'filling' not in data:
                data['filling'] = threading.Thread(target=fill_partners, args=(data,), daemon=True)
                data['filling'].start()
        elif parts[0] == 'session':
            # A page opening the sort: the time is kept for the list of sorts
            with lock:
                write_known({**known_sorts(), data['sort']: time.strftime('%Y-%m-%dT%H:%M:%S')})
            self.send_json({'ids': data['units'].index.tolist(), 'rate_hz': data['rate_hz'], 'n_samples': data['n_samples'],
                            'duplicate_window': data['duplicate_window'], 'paths': data['paths'],
                            'traces_shape': list(data['traces'].shape[1:]),
                            'presence_limit': json.load(open(os.path.join(HERE, 'thresholds.json')))['mua']['presence_ratio']['greater'],
                            'handoff_limit': HANDOFF})
        elif parts[0] == 'arrays':
            # Compressed for a browser that takes it, under its own tag
            zipped = 'gzip' in self.headers.get('Accept-Encoding', '')
            tag = data['blob_tag'][:-1] + ('-gzip"' if zipped else '"')
            if self.headers.get('If-None-Match') == tag:
                self.send(b'', 'application/octet-stream', 304, [('ETag', tag), ('Vary', 'Accept-Encoding'), ('X-Arrays-Bytes', str(os.path.getsize(data['arrays'])))])
            else:
                self.send(open(data['arrays_gzip' if zipped else 'arrays'], 'rb').read(), 'application/octet-stream', 200,
                          [('ETag', tag), ('Cache-Control', 'no-cache'), ('Vary', 'Accept-Encoding'), ('X-Arrays-Bytes', str(os.path.getsize(data['arrays'])))]
                          + ([('Content-Encoding', 'gzip')] if zipped else []))
        elif parts[0] == 'traces':
            # Single-spike waveforms of original units (rows), as int16 uV: 100 spikes x samples x sites each
            rows = [int(r) for r in query['rows'][0].split(',')]
            self.send(np.ascontiguousarray(data['traces'][rows]).tobytes(), 'application/octet-stream')
        elif parts[0] == 'shared':
            # Mean waveforms of several units on the union of their display sites, so that an overlay has every unit on every site
            members = current_state(data['units'].index, not_undone(read_log(data['log'])))[0]
            chosen = [int(u) for u in query['units'][0].split(',')]
            largest = [max(members[u], key=data['spikes'].get) for u in chosen]
            sites = np.unique(data['sites'][data['units'].index.get_indexer(largest)])
            sites = sites[sites >= 0]
            self.send_json({'xy': data['channel_xy'][sites].tolist(),
                            'waveforms': {u: missing_none(np.where(recorded(data, members[u])[sites], mean_template(data, members[u])[:, sites], np.nan)) for u in chosen}})
        elif parts[0] == 'waveforms':
            # Mean waveforms of merged units, by unit
            members = current_state(data['units'].index, not_undone(read_log(data['log'])))[0]
            self.send_json({u: merged_waveform(data, members[int(u)]) for u in query['units'][0].split(',')})
        elif parts[0] == 'amplitudes':
            # Kilosort amplitude of every spike of an original unit, in time order
            self.send(data['ks_amplitude'][int(query['unit'][0])].astype(np.float32).tobytes(), 'application/octet-stream')
        elif parts[0] == 'floor':
            # What an amplitude floor would leave: the spikes above and below it, each with its contamination measures
            unit, floor = int(query['unit'][0]), float(query['floor'][0])
            above = data['ks_amplitude'][unit] >= floor
            sides = {}
            for side, chosen in [('above', above), ('below', ~above)]:
                samples = data['all_samples'][unit][chosen]
                sides[side] = {'n_spikes': int(len(samples)), **refractory_measures(data, samples)}
            self.send_json(sides)
        elif parts[0] == 'ratemaps':
            members, _, _, _, floors = current_state(data['units'].index, not_undone(read_log(data['log'])))
            bins = data['flights']['bins']
            self.send_json({'shape': [len(bins[1]) - 1, len(bins[0]) - 1], 'extent': [float(bins[0][0]), float(bins[0][-1]), float(bins[1][0]), float(bins[1][-1])],
                            'maps': {u: rate_maps(data, spikes_key(members[int(u)], floors)) for u in query['units'][0].split(',')}})
        elif parts[0] == 'partners':
            # The 5 best partners of one unit among the units with peak channels within 100 um: qualifying first, by footprint
            members, _, _, _, floors = current_state(data['units'].index, not_undone(read_log(data['log'])))
            self.send_json(partners(data, members, floors, int(query['unit'][0]))[:5])
        elif parts[0] == 'footprints':
            # Peak-to-peak amplitude of each unit on the channels within 100 um of the largest one's peak channel, and
            # its largest on any channel
            members = current_state(data['units'].index, not_undone(read_log(data['log'])))[0]
            chosen = [int(u) for u in query['units'][0].split(',')]
            footprints = [footprint(data, members[u]) for u in chosen]
            near = near_channels(data, footprints)
            self.send_json({'xy': data['channel_xy'][near].tolist(),
                            'ptp': {u: missing_none(np.where(recorded(data, members[u])[near], f[near], np.nan)) for u, f in zip(chosen, footprints)},
                            'largest': {u: float(f.max()) for u, f in zip(chosen, footprints)}})
        elif parts[0] == 'merged':
            members, _, _, _, floors = current_state(data['units'].index, not_undone(read_log(data['log'])))
            chosen = [members[int(u)] for u in query['units'][0].split(',')]
            originals = sorted(m for parts in chosen for m in parts)
            self.send_json({**{k: merged_unit(data, spikes_key(originals, floors))[k] for k in ['n_spikes', 'duplicates', 'short_isi', 'rp_label', 'rp_contamination',
                                                                                              'rp_seen', 'rp_expected', 'ks_ratio', 'short_fraction', 'presence', 'amplitude', 'bombcell']},
                            'pairs': refractory_pairs(data, [spikes_key(parts, floors) for parts in chosen])})
        else:
            self.send(b'not found', 'text/plain', 404)

    def post(self):
        event = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/forget':
            # A sort taken off this machine's list; its folder is not touched
            with lock:
                write_known({sort: opened for sort, opened in known_sorts().items() if sort != event['sort']})
            return self.send_json({})
        data = self.session(os.path.normpath(event.pop('sort')))
        with lock:
            logged = read_log(data['log'])
            if self.path == '/export':
                run = subprocess.run([sys.executable, '-m', 'pixelbat.curation.write_phy', data['sort']], capture_output=True, text=True)
                return self.send_json({'message': (run.stdout.strip().splitlines() or [run.stderr.strip()[-300:]])[-1],
                                       'folder': os.path.join(data['sort'], 'curation', 'phy')},
                                      200 if run.returncode == 0 else 500)
            # A decision is written only if it was made on the current state and the log still replays with it
            if event.pop('version') != len(logged):
                return self.send_json({'error': 'this page was out of date (the session changed elsewhere); nothing was saved',
                                       'table': self.table(data, logged)}, 409)
            event['time'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
            # A merge and a floor each make a unit with a new number
            if event['kind'] in ['merge', 'floor']:
                event['id'] = new_id(data, logged)
            undone = not_undone(logged)[-1:] if event['kind'] == 'undo' else []
            try:
                assert event['kind'] in KINDS and (event['kind'] != 'undo' or undone)
                table = self.table(data, logged + [event])
            except (KeyError, ValueError, AssertionError, IndexError) as error:
                return self.send_json({'error': f'decision refused: {error!r}', 'table': self.table(data, logged)}, 409)
            with open(data['log'], 'a') as f:
                f.write(json.dumps(event) + '\n')
        shown = undone[0] if undone else event
        named = shown.get('units', []) + [int(u) for u in shown.get('labels', {})] + [shown[k] for k in ['unit', 'id'] if k in shown]
        current = {m: u['unit'] for u in table['units'] for m in u['members']} | {u['unit']: u['unit'] for u in table['units']}
        originals = current_state(data['units'].index, not_undone(logged))[0]
        touched = [current[m] for n in named for m in originals.get(n, [n]) if m in current]
        self.send_json({**table, 'done': 'undid: ' + describe(undone[0]) if undone else describe(event),
                        'touched': list(dict.fromkeys(touched))})

    def answer(self, handle):
        """Run a request; a failure is printed in full and answered as an error, never left unanswered."""
        answering.append(self)
        try:
            handle()
        except Exception as error:
            traceback.print_exc()
            self.send_json({'error': f'server error: {error!r}', 'message': f'server error: {error!r}'}, 500)
        finally:
            answering.remove(self)

    def do_GET(self):
        self.answer(self.get)

    def do_POST(self):
        self.answer(self.post)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print(f'curation at http://localhost:{sys.argv[1]}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), Handler).serve_forever()
