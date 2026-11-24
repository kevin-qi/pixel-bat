"""pixelbat-curate: prepare a session's cache, serve the curation page, export the curated Phy folder."""
import argparse
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(prog='pixelbat-curate', description='Curate Kilosort sorts in a browser.')
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help="build one session's cache (once per session)")
    prepare.add_argument('sessions', help='sessions CSV')
    prepare.add_argument('name', help='session (its name column)')
    prepare.add_argument('--jobs', type=int, default=8, help='processes reading the recording (default 8)')
    serve = commands.add_parser('serve', help='serve the curation page at http://localhost:PORT')
    serve.add_argument('sessions', help='sessions CSV')
    serve.add_argument('--port', type=int, default=8780, help='port (default 8780)')
    export = commands.add_parser('export', help='write <out>/phy from the decisions so far')
    export.add_argument('sessions', help='sessions CSV')
    export.add_argument('name', help='session (its name column)')
    args = parser.parse_args()

    # Each command runs its module as a script
    if args.command == 'prepare':
        module, sys.argv = 'prepare', ['prepare', args.sessions, args.name, str(args.jobs)]
    if args.command == 'serve':
        module, sys.argv = 'server', ['server', args.sessions, str(args.port)]
    if args.command == 'export':
        module, sys.argv = 'write_phy', ['write_phy', args.sessions, args.name]
    runpy.run_module(f'pixelbat.curation.{module}', run_name='__main__', alter_sys=True)
