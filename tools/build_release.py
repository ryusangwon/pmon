"""Build all pinned platform wheels and an sdist; all outputs stay here."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    targets=json.loads((ROOT/'tools/pueue.lock.json').read_text())['targets']
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_CACHE_DIR=str(ROOT/'.cache/pip'), TMPDIR=str(ROOT/'.tmp'))
    (ROOT/'.tmp').mkdir(exist_ok=True)
    for target in targets:
        env['PMON_BUILD_TARGET']=target
        with (ROOT/'.tmp'/f'build-{target}.log').open('w') as log:
            subprocess.run([sys.executable,'-B','-m','build','--wheel','--no-isolation'],
                env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print('Built',target,flush=True)
    env.pop('PMON_BUILD_TARGET',None)
    with (ROOT/'.tmp/build-sdist.log').open('w') as log:
        subprocess.run([sys.executable,'-B','-m','build','--sdist','--no-isolation'],
            env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Built source distribution',flush=True)


if __name__=='__main__': main()
