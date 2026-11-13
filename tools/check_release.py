"""Check wheel payloads, hashes, tags, and absence of local/private config."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def check_public_text(name, data):
    private=ROOT/'.tmp/release-private-markers.json'
    if not private.exists(): return
    if name.endswith(('.py','.md','.toml','.json','.txt','PKG-INFO','METADATA')):
        for marker in json.loads(private.read_text()):
            assert marker.encode() not in data, f'Private project text in release: {name}'


def main():
    version=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['version']
    lock=json.loads((ROOT/'tools/pueue.lock.json').read_text())
    targets=set()
    for wheel in sorted((ROOT/'dist').glob(f'pueue_pmon-{version}-*.whl')):
        with zipfile.ZipFile(wheel) as archive:
            names=archive.namelist()
            assert not any(name.endswith('/pmon.toml') or '/.venv/' in name or '/.tmp/' in name for name in names)
            manifest_name=next(n for n in names if n.endswith('/_bin/manifest.json'))
            manifest=json.loads(archive.read(manifest_name))
            targets.add(manifest['target'])
            prefix=manifest_name.rsplit('/',1)[0]+'/'
            for filename,asset in manifest['assets'].items():
                assert hashlib.sha256(archive.read(prefix+filename)).hexdigest()==asset['sha256']
                assert filename.removesuffix('.exe') in ('pueue','pueued')
            assert prefix+'LICENSE.MIT' in names and prefix+'LICENSE.APACHE' in names
            metadata=archive.read(next(n for n in names if n.endswith('.dist-info/METADATA')))
            assert b'Name: pueue-pmon' in metadata
            assert str(ROOT).encode() not in metadata
            for name in names:
                if not name.endswith('/'):
                    check_public_text(name,archive.read(name))
        print('Verified',wheel.name)
    assert targets==set(lock['targets']),targets
    source=ROOT/'dist'/f'pueue_pmon-{version}.tar.gz'
    with tarfile.open(source) as archive:
        names=archive.getnames()
        assert not any(name.endswith('/pmon.toml') for name in names)
        assert any(name.endswith('/tools/pueue.lock.json') for name in names)
        assert not any('/_bin/' in name for name in names)
        for member in archive.getmembers():
            if member.isfile(): check_public_text(member.name,archive.extractfile(member).read())
    print('Verified source archive and all platform payloads')


if __name__=='__main__': main()
