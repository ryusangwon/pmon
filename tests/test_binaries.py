import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pmon import binaries


class BundledBinaryTests(unittest.TestCase):
    def test_bundled_executable_works_without_system_install(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'.tmp') as tmp:
            module=Path(tmp)/'binaries.py'
            dest=Path(tmp)/'_bin/pueue'
            dest.parent.mkdir()
            dest.write_bytes(b'fixture')
            with patch.object(binaries,'__file__',str(module)),patch.object(binaries.sys,'platform','darwin'),\
                    patch.object(binaries.shutil,'which',return_value=None):
                self.assertEqual(binaries.resolve_binary('pueue'),str(dest))

    def test_passthrough_refuses_home_defaults(self):
        with patch.object(binaries,'resolve_binary',return_value='/fixture/pueue'),\
                patch.object(binaries.sys,'argv',['pmon-pueue','status']),\
                patch.dict(binaries.os.environ,{},clear=True),\
                patch.object(binaries.subprocess,'call') as run,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(binaries.pueue_main(),2)
            run.assert_not_called()

    def test_explicit_config_passed_as_arguments_without_shell(self):
        with patch.object(binaries,'resolve_binary',return_value='/fixture/pueue'),\
                patch.object(binaries.sys,'argv',['pmon-pueue','--config','a b.yml','status']),\
                patch.object(binaries.subprocess,'call',return_value=0) as run:
            self.assertEqual(binaries.pueue_main(),0)
            run.assert_called_once_with(['/fixture/pueue','--config','a b.yml','status'])


if __name__=='__main__': unittest.main()
