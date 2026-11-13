"""Locate bundled pueue; official commands are exposed without global installs."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def resolve_binary(name):
    """Prefer this release's tested binary; fall back to PATH in source checkouts."""
    suffix = '.exe' if sys.platform == 'win32' else ''
    bundled = Path(__file__).resolve().parent/'_bin'/(name+suffix)
    if bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def _upstream(name):
    executable = resolve_binary(name)
    if not executable:
        print(f'{name} binary missing; install a platform wheel of pueue-pmon.', file=sys.stderr)
        return 1
    args = sys.argv[1:]
    informational = any(arg in ('--help','-h','--version','-V') for arg in args)
    explicit = any(arg in ('--config','-c') or arg.startswith('--config=') for arg in args)
    if not informational and not explicit and not os.environ.get('PUEUE_CONFIG_PATH'):
        print('Specify --config /path/to/pueue.yml (home defaults are disabled).', file=sys.stderr)
        return 2
    # These are explicit upstream passthrough tools, separate from the read-only monitor.
    return subprocess.call([executable, *args])


def pueue_main():
    return _upstream('pueue')


def pueued_main():
    return _upstream('pueued')
