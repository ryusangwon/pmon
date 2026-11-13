import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pmon import Client, PueueError
from pmon.client import parse_task, Snapshot
from pmon.cli import main
from pmon.view import clean, render, cell


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.tmp')
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name)/'config.yml'
        self.config.write_text('{}')

    def client(self):
        with patch('pmon.client.shutil.which', return_value='/bin/pueue'):
            return Client(self.config)

    def test_status_uses_explicit_config_and_drops_environment(self):
        raw = {'tasks': {'7': {'group':'gpu','label':'train','envs':{'TOKEN':'private'},
            'status':{'Running':{'start':'2026-11-14T00:00:00+09:00'}}}}, 'groups': {'gpu': {'parallel_tasks':1}}}
        with patch('pmon.client.subprocess.run', return_value=subprocess.CompletedProcess([],0,json.dumps(raw))) as run:
            result = self.client().status(group='gpu')
        self.assertEqual(result.tasks[0].status,'Running')
        self.assertNotIn('private',repr(result))
        self.assertEqual(run.call_args.args[0],['/bin/pueue','--config',str(self.config),'status','--json'])

    def test_failed_and_stashed_states(self):
        failed = parse_task('1', {'status':{'Done':{'result':{'Failed':2}}}})
        self.assertEqual(failed.status,'Failed')
        self.assertIn('2',failed.result)
        self.assertEqual(parse_task('2',{'status':'Stashed'}).status,'Stashed')
        self.assertEqual(parse_task('3',{'status':{'Done':{'result':'Success'}}}).status,'Success')

    def test_log_returns_only_bounded_output(self):
        raw = {'5':{'task':{'envs':{'TOKEN':'private'}},'output':'line\n'}}
        with patch('pmon.client.subprocess.run', return_value=subprocess.CompletedProcess([],0,json.dumps(raw))) as run:
            self.assertEqual(self.client().log(5,lines=8),'line\n')
        self.assertEqual(run.call_args.args[0][-3:],['--lines','8','5'])

    def test_write_commands_are_rejected_before_subprocess(self):
        with patch('pmon.client.subprocess.run') as run:
            with self.assertRaises(PueueError): self.client()._query('kill','1')
            run.assert_not_called()

    def test_timeout_is_a_connection_error(self):
        with patch('pmon.client.subprocess.run',side_effect=subprocess.TimeoutExpired('pueue',3)):
            with self.assertRaises(PueueError): self.client().status()

    def test_malformed_json(self):
        with patch('pmon.client.subprocess.run',return_value=subprocess.CompletedProcess([],0,'not json')):
            with self.assertRaises(PueueError): self.client().status()

    def test_missing_config_does_not_run_pueue(self):
        with patch('pmon.client.subprocess.run') as run:
            with self.assertRaises(PueueError): Client(self.config.with_name('missing'))
            run.assert_not_called()

    def test_render_active_before_history_and_strip_controls(self):
        tasks = tuple(parse_task(str(i),{'label':'x','status':{'Done':{'result':'Success'}}}) for i in range(50))
        active = parse_task('99',{'status':'Running','label':'live\x1b[31m','dependencies':[3]})
        text = render(Snapshot((*tasks,active),{},'now'),width=80,height=24)
        self.assertIn('live',text)
        self.assertIn('99',text)
        self.assertNotIn('\x1b',text)
        self.assertIn('생략',text)
        self.assertEqual(clean('\x1b]0;bad\x07hello'),'hello')
        self.assertEqual(cell('한글',3),'한 ')

    def test_json_cli_is_sanitized_and_single_shot(self):
        task=parse_task('1',{'status':'Queued','label':'test'})
        output=io.StringIO()
        with patch('pmon.cli.Client') as cls,contextlib.redirect_stdout(output):
            cls.return_value.status.return_value=Snapshot((task,),{},'now')
            self.assertEqual(main(['--config',str(self.config),'--json']),0)
            cls.return_value.status.assert_called_once()
        self.assertEqual(json.loads(output.getvalue())['tasks'][0]['status'],'Queued')


if __name__ == '__main__': unittest.main()
