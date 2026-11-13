"""Upload verified release files using project-local credentials, without printing them."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def published(version):
    try:
        with urllib.request.urlopen(f'https://pypi.org/pypi/pueue-pmon/{version}/json',timeout=30) as response:
            return {f['filename']:f['digests']['sha256'] for f in json.load(response)['urls']}
    except urllib.error.HTTPError as exc:
        if exc.code==404: return {}
        raise


def main():
    os.chdir(ROOT)
    manifest=json.loads((ROOT/'release-validation.json').read_text())
    remote=published(manifest['version'])
    pending=[]
    for item in manifest['artifacts']:
        path=ROOT/item['file']
        if path.resolve().parent != ROOT/'dist': raise SystemExit('Artifact outside dist directory')
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum!=item['sha256']: raise SystemExit('Validated artifact changed: '+path.name)
        if path.name in remote:
            if remote[path.name]!=checksum: raise SystemExit('Published artifact differs: '+path.name)
        else: pending.append(str(path))
    token_path=ROOT/'.pypi-token'
    if not pending:
        print('All validated release files are already published and match.')
        return
    token=os.environ.get('TWINE_PASSWORD') or os.environ.get('PYPI_TOKEN')
    if not token and token_path.is_file(): token=token_path.read_text().strip()
    if not token: raise SystemExit('No authentication available. Run .venv/bin/python -B tools/pypi_auth.py locally.')
    env=dict(os.environ,TWINE_USERNAME='__token__',TWINE_PASSWORD=token,
        PYTHON_KEYRING_BACKEND='keyring.backends.null.Keyring',PYTHONDONTWRITEBYTECODE='1',
        PIP_CACHE_DIR=str(ROOT/'.cache/pip'),TMPDIR=str(ROOT/'.tmp'))
    config=ROOT/'.tmp/upload.pypirc'
    config.parent.mkdir(exist_ok=True)
    config.write_text('[distutils]\nindex-servers = pypi\n[pypi]\nrepository = https://upload.pypi.org/legacy/\n')
    subprocess.run([sys.executable,'-B','-m','twine','upload','--non-interactive',
        '--config-file',str(config),'--repository-url','https://upload.pypi.org/legacy/',*pending],env=env,check=True)
    remote=published(manifest['version'])
    if any(remote.get(Path(item['file']).name)!=item['sha256'] for item in manifest['artifacts']):
        raise SystemExit('Upload command finished; PyPI file verification is pending. Keep the token for verification/retry.')
    manifest['published']=True
    manifest['project_url']='https://pypi.org/project/pueue-pmon/'
    (ROOT/'release-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if token_path.exists(): token_path.unlink()
    print('Published and hash-verified: https://pypi.org/project/pueue-pmon/')
    print('Project-local token file removed.')


if __name__=='__main__': main()
