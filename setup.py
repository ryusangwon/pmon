"""Build platform wheels containing checksum-pinned upstream executables.

Wheel installation does not run installers, contact the network, or start a
daemon. Source builds fetch the same pinned files while building the wheel.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import urllib.request

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.bdist_wheel import bdist_wheel

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT/'tools/pueue.lock.json').read_text())


def target_name():
    explicit = os.environ.get('PMON_BUILD_TARGET')
    if explicit:
        if explicit not in LOCK['targets']:
            raise RuntimeError('Unsupported PMON_BUILD_TARGET: '+explicit)
        return explicit
    system = {'Darwin':'macos', 'Linux':'linux', 'Windows':'windows'}.get(platform.system())
    arch = {'arm64':'arm64', 'aarch64':'arm64', 'x86_64':'x86_64', 'AMD64':'x86_64'}.get(platform.machine())
    name = f'{system}-{arch}'
    if name not in LOCK['targets']:
        raise RuntimeError('Unsupported platform: '+name)
    return name


def macos_minimum(binary):
    """Derive wheel compatibility from the upstream Mach-O load commands."""
    data = binary.read_bytes()
    if data[:4] != b'\xcf\xfa\xed\xfe':
        raise RuntimeError('Expected little-endian 64-bit Mach-O')
    count = struct.unpack_from('<I', data, 16)[0]
    offset = 32
    for _ in range(count):
        cmd, size = struct.unpack_from('<II', data, offset)
        if cmd in (0x32, 0x24):
            version = struct.unpack_from('<I', data, offset+(12 if cmd == 0x32 else 8))[0]
            return version >> 16, (version >> 8) & 255
        offset += size
    raise RuntimeError('Mach-O minimum deployment target missing')


def assert_static_elf(binary):
    data = binary.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise RuntimeError('Expected little-endian 64-bit ELF')
    offset = struct.unpack_from('<Q',data,32)[0]
    size, count = struct.unpack_from('<HH',data,54)
    for i in range(count):
        entry = offset+i*size
        kind = struct.unpack_from('<I',data,entry)[0]
        if kind == 3:
            raise RuntimeError('ELF interpreter found: cannot claim libc-independent compatibility')
        if kind == 2:
            start = struct.unpack_from('<Q',data,entry+8)[0]
            length = struct.unpack_from('<Q',data,entry+32)[0]
            for pos in range(start,start+length,16):
                tag = struct.unpack_from('<q',data,pos)[0]
                if tag == 1: raise RuntimeError('ELF shared-library dependency found')
                if tag == 0: break


class BundledBuild(build_py):
    def run(self):
        super().run()
        target = target_name()
        dest = Path(self.build_lib)/'pmon/_bin'
        if dest.exists(): shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        manifest = {'version':LOCK['version'], 'target':target, 'source':LOCK['source'], 'assets':{}}
        cache = ROOT/'.cache/upstream'
        cache.mkdir(parents=True, exist_ok=True)
        for tool, asset in LOCK['targets'][target].items():
            source = cache/asset['name']
            if not source.exists():
                request = urllib.request.Request(asset['url'], headers={'User-Agent':'pueue-pmon-build'})
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read(32*1024*1024)
                if hashlib.sha256(data).hexdigest() != asset['sha256']:
                    raise RuntimeError('Upstream checksum mismatch: '+asset['name'])
                source.write_bytes(data)
            if hashlib.sha256(source.read_bytes()).hexdigest() != asset['sha256']:
                raise RuntimeError('Cached upstream checksum mismatch: '+asset['name'])
            if target.startswith('linux'): assert_static_elf(source)
            filename = tool+('.exe' if target.startswith('windows') else '')
            shutil.copyfile(source, dest/filename)
            (dest/filename).chmod(0o755)
            manifest['assets'][filename] = asset
        (dest/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        for license in ('LICENSE.MIT','LICENSE.APACHE'):
            shutil.copyfile(ROOT/'third_party/pueue'/license, dest/license)


class PlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self):
        target = target_name()
        if target.startswith('macos'):
            cache = ROOT/'.cache/upstream'
            minimum = max(macos_minimum(cache/a['name']) for a in LOCK['targets'][target].values())
            major, minor = minimum
            if major >= 11: minor = 0
            tag = f'macosx_{major}_{minor}_{"arm64" if target.endswith("arm64") else "x86_64"}'
        else:
            tag = {'linux-x86_64':'manylinux_2_17_x86_64.musllinux_1_2_x86_64',
                   'linux-arm64':'manylinux_2_17_aarch64.musllinux_1_2_aarch64',
                   'windows-x86_64':'win_amd64'}[target]
        return 'py3', 'none', tag


setup(cmdclass={'build_py':BundledBuild, 'bdist_wheel':PlatformWheel})
