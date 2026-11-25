"""pixelbat-curate: the curation app; prepare sort folders for it; export a curated Phy folder."""
import argparse
import os
import runpy
import subprocess
import sys

from pixelbat.sorting.recording import peak_signs, write_recording


def main():
    parser = argparse.ArgumentParser(prog='pixelbat-curate', description='Curate Kilosort sorts in a browser. Without a command: '
                                     'start the app and open sort folders in the page.')
    parser.add_argument('--port', type=int, default=8780, help='port of the app (default 8780)')
    commands = parser.add_subparsers(dest='command')
    prepare = commands.add_parser('prepare', help='prepare sort folders for curation (once per sort; prepared ones are skipped)')
    prepare.add_argument('sorts', nargs='+', help='Kilosort output folders')
    prepare.add_argument('--jobs', type=int, default=8, help='processes reading the recording (default 8)')
    prepare.add_argument('--binary', help='for one sort made without pixelbat/sorting: the int16 binary it was sorted from')
    prepare.add_argument('--gain-uv', type=float, help='with --binary: microvolts per bit of the binary')
    export = commands.add_parser('export', help='write <SORT>/curation/phy from the decisions so far')
    export.add_argument('sort', help='the sort folder')
    args = parser.parse_args()

    if args.command is None:
        sys.argv = ['server', str(args.port)]
        runpy.run_module('pixelbat.curation.server', run_name='__main__', alter_sys=True)
    if args.command == 'prepare':
        # A sort made elsewhere: its recording details, the spike sign measured
        if args.binary:
            [sort] = args.sorts
            params = {}
            exec(open(os.path.join(sort, 'params.py')).read(), params)
            n_positive, n_negative = peak_signs(args.binary, params['n_channels_dat'], params['sample_rate'])
            print(f'spike sign: {n_positive} positive, {n_negative} negative peaks')
            write_recording(sort, args.binary, args.gain_uv, n_positive > n_negative)
        # One process per sort
        todo = [sort for sort in args.sorts if not os.path.exists(os.path.join(sort, 'curation', 'cache'))]
        print(f'{len(todo)} of {len(args.sorts)} sorts to prepare')
        for sort in todo:
            subprocess.run([sys.executable, '-m', 'pixelbat.curation.prepare', sort, str(args.jobs)], check=True)
        # Each sort opened ahead of the app, which then only reads it
        for sort in args.sorts:
            subprocess.run([sys.executable, '-m', 'pixelbat.curation.open_ahead', sort], check=True)
    if args.command == 'export':
        sys.argv = ['write_phy', args.sort]
        runpy.run_module('pixelbat.curation.write_phy', run_name='__main__', alter_sys=True)
