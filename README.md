# pmon

A read-only, live terminal monitor for [pueue](https://github.com/Nukesor/pueue).

[PyPI](https://pypi.org/project/pueue-pmon/) · [한국어 사용 설명](README.ko.md)

View running, queued, paused, completed and failed commands in one auto-refreshing
screen. Inspect task groups, elapsed time, dependencies and recent output without
changing the programs being monitored.

## Install

```bash
pip install pueue-pmon
```

Python 3.11 or newer is required. Platform wheels include the official **pueue
and pueued 4.0.4 executables**, so a separate Homebrew or Cargo installation is
not required. Installation does not start a daemon or change an existing queue.

Wheels are provided for macOS ARM64/x86_64, Linux ARM64/x86_64 and Windows x86_64.
The macOS ARM64 wheel has been runtime-tested; other platform payloads are
checksum-verified but need additional runtime testing on those operating systems.

## Quick start

Connect to an existing pueue daemon using its configuration:

```bash
pmon --config /path/to/pueue.yml
```

The screen refreshes every two seconds. Press **q** or **Ctrl+C** to exit the
monitor; queued and running commands continue normally. Press **r** to refresh
immediately. Connection failures are retried while the last successful snapshot
remains visible.

```bash
pmon --config /path/to/pueue.yml --group gpu
pmon --config /path/to/pueue.yml --log
pmon --config /path/to/pueue.yml --log 2
pmon --config /path/to/pueue.yml --interval 5
pmon --config /path/to/pueue.yml --once
pmon --config /path/to/pueue.yml --json
```

`--log` displays recent output from the first running task; `--log ID` selects a
specific task. Each refresh requests at most 12 recent lines and displays up to
six. The monitor does not show task environment variables. Logs contain whatever
the monitored command printed.

Pmon reports the state known to pueue. It does not infer application-level
progress percentages, require instrumentation, or read application status files.

## Connection settings

Save a `pmon.toml` in the directory where you run the monitor:

```toml
[connection]
config = "/path/to/pueue.yml"
# Optional filters:
group = "gpu"
# profile = "local"
```

Then run `pmon`. Relative configuration paths are resolved against the TOML file.
Use `--settings /path/to/pmon.toml` to choose another file. Explicit command-line
options take precedence. Without settings, pmon checks `.pueue/config.yml` in the
current directory. It never creates a default configuration in the home directory.

The connection configuration is private to the user and is not included in the
package. The daemon controls where its queue state, socket and logs are stored.

### Is a `.pueue` folder required?

No. That is only an optional local directory convention. Pmon connects to a
**pueue daemon**, not to an application or a particular project. The configuration
file can have any name and live at any location you choose. Pass its path using
`--config`.

Multiple projects can share the same daemon. Use task groups to filter the view;
you do not need a separate `.pueue` directory for each project. Separate daemons
can also be monitored by selecting their respective configuration files.

If `pmon` is not found after installation, use the same Python environment that
installed the package:

```bash
python -m pmon --config /path/to/pueue.yml
```

## Included pueue tools

```bash
pmon-pueue --version
pmon-pueued --version
pmon-pueue --config /path/to/pueue.yml status
```

These commands expose the bundled upstream executables without replacing an
existing `pueue` command. Except for help and version information, an explicit
`--config` or `PUEUE_CONFIG_PATH` is required. The passthrough tools support the
upstream features; the **pmon monitor itself only performs status/log queries**.

## Python API

```python
from pmon import Client

client = Client("/path/to/pueue.yml")
for task in client.status(group="gpu").tasks:
    print(task.id, task.status, task.label)

print(client.log(2, lines=10))
```

## Development

```bash
./pmon --config /path/to/pueue.yml
mkdir -p .tmp
PYTHONPATH=src python3.13 -B -m unittest discover -s tests -v
```

The source launcher locates Python 3.11+ or uses `PMON_PYTHON` when set. It does
not install global launchers or change shell configuration. In a source checkout,
an existing pueue executable on PATH can be used; platform wheels bundle it.

Build and publishing instructions are in `RELEASING.md`. Official upstream
executables are pinned by SHA-256. Source builds download those files during
wheel construction; installing a prebuilt wheel needs no additional download.

## License

Pmon is MIT-licensed. Bundled pueue executables retain their upstream MIT/Apache-2.0
licenses; both license texts are included in the distributions.
