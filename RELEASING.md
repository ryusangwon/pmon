# pueue-pmon release procedure

Distribution name: `pueue-pmon`; monitor command/import: `pmon`.
The PyPI name returned HTTP 404 on 2026-11-14; this does not reserve the name.
No PyPI credentials were present when preparing this release.

## Local-only tooling

Keep tooling, caches, temporary files and install tests inside this checkout:

```bash
mkdir -p .tmp .cache/pip
python3.13 -B -m venv .venv
PIP_CACHE_DIR="$PWD/.cache/pip" TMPDIR="$PWD/.tmp" PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -m pip install build twine 'setuptools>=77' wheel
```

## Build and validate

```bash
.venv/bin/python -B tools/build_release.py
.venv/bin/python -B tools/check_release.py
.venv/bin/python -B -m twine check --strict dist/*
PYTHONPATH=src .venv/bin/python -B -m unittest discover -s tests
```

The build downloads only release-pinned pueue 4.0.4 executables and verifies
SHA-256 against `tools/pueue.lock.json`. Platform wheels include both executables
and upstream licenses. Wheel installation does not execute download/install
hooks or start services. A source installation downloads the same pinned files
during its wheel build, so it requires network access.

The Linux build rejects an ELF interpreter or shared-library dependencies before
using manylinux/musllinux tags. Mac deployment tags come from Mach-O headers.
Cross-built wheels still require runtime validation on their target OS. Locally,
the macOS ARM64 wheel is install-tested without a pueue executable on PATH.

The source archive intentionally excludes `pmon.toml`, credentials, virtual
environments, build caches and local paths. Do not upload files manually from
the project root; upload only checked distribution files.

## Publish (authentication required)

Authenticate using PyPI's supported API token or Trusted Publishing. Never put
tokens in command arguments, Git, build logs, or chat. With credentials supplied
securely to the process, upload the checked files:

```bash
.venv/bin/python -B -m twine upload --non-interactive dist/*
```

For TestPyPI use `--repository-url https://test.pypi.org/legacy/` and credentials
specifically issued by TestPyPI. Do not send a production token to TestPyPI.
PyPI does not allow replacing a file for an already published version; increment
the version for subsequent releases.

## Executable updates

Review a new upstream release before changing the lock. Record official asset
URLs and SHA-256 values; do not replace pinned binaries through an unverified
"latest" URL. Rebuild and run platform tests after any upstream update.
