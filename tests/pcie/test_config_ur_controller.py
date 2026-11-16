"""Verify publication and Packet ownership through the normal desktop IPC."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import sys
import tempfile
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb_control_app as app
from pcie_pipeline import CleanupUnknown


class ConfigUrControllerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.tool = tool = app.Tool(root/'tool')
        folder = tool.root/'case'
        (folder/'analysis').mkdir(parents=True)
        source, working = root/'source.pex', folder/'display-working.pex'
        for path in source, working:
            path.write_bytes(b'fixture captures are read-only inputs')
        identity = app.snapshot(source)
        self.case_id = 'c'*32
        self.sha = identity['sha256']
        self.ns = 'native_trace_packet_zero_based'
        tool.case = dict(id=self.case_id,name=source.name,source=source,working=working,
                         folder=folder,before=identity,working_before=app.snapshot(working),
                         model=dict(protocol='pcie',native_navigation='owned',packet_namespace=self.ns,
                                    source_trace_sha256=self.sha,display_trace_sha256=self.sha,
                                    coverage=dict(native_packet_count=100),candidates=[]))
        self.entered = threading.Event()
        self.resume = threading.Event()
        acquire = SimpleNamespace(run=self.acquire)
        analysis = SimpleNamespace(analyze=self.result)
        report = SimpleNamespace(write=self.write)
        patched = patch.dict(sys.modules,pcie_config_ur_acquisition=acquire,
                             pcie_config_ur_analysis=analysis,pcie_config_ur_report=report)
        patched.start()
        self.addCleanup(patched.stop)
        mutex = patch.object(app,'native_exclusive',nullcontext)
        mutex.start()
        self.addCleanup(mutex.stop)
        self.acquire_module = acquire
        self.report_module = report

    def acquire(self,working,analysis_root,output,binding,cancel,progress):
        self.entered.set()
        progress('extracting fixture')
        if not self.resume.wait(5):
            raise TimeoutError('fixture never released')
        if cancel.is_set():
            raise InterruptedError('cancelled fixture')
        return binding

    def result(self,binding):
        def event(index,direction):
            return dict(packet_index=index,direction=direction,time_ns=index*100,
                        time_display=str(index),evidence=[dict(fields=['packet_index','direction','time_ns'])])
        return dict(binding,schema='pcie.config-ur-evidence/v1',
                    rows=[dict(id='p12',request=event(12,'Downstream'),completion=event(13,'Upstream'),
                               readback=dict(request=event(14,'Downstream'),completion=event(15,'Upstream')))])

    def write(self,out,result):
        (out/'index.json').write_text('{}',encoding='utf-8')

    def start(self):
        return self.tool.native_command(dict(action='config_ur_run',case_id=self.case_id))

    def status(self):
        return json.loads((self.tool.root/'status.json').read_text(encoding='utf-8'))

    def test_publishes_supplement_and_navigates_verified_readback(self):
        self.assertTrue(self.start())
        self.assertTrue(self.entered.wait(3))
        self.assertEqual(self.status()['phase'],'config_ur')
        self.assertEqual(self.status()['case_id'],self.case_id)
        self.assertNotIn('index',self.status()['config_ur'])
        self.resume.set()
        self.tool.thread.join(5)
        state = self.status()
        self.assertEqual(state['config_ur']['state'],'ready')
        index = self.tool.case['folder']/state['config_ur']['index']
        self.assertTrue(index.is_file())
        evidence = json.loads(index.with_name('evidence.json').read_text(encoding='utf-8'))
        self.assertEqual(evidence['source_trace_sha256'],self.sha)
        self.assertEqual(evidence['rows'][0]['readback']['completion']['packet_index'],15)
        self.assertTrue(json.loads((self.tool.case['folder']/'integrity.json').read_text())['source_and_working_unchanged'])
        command = dict(action='config_ur_navigate',case_id=self.case_id,row_id='p12',target='read_completion')
        with self.assertRaises(ValueError):
            self.tool.native_command(dict(command,row_id='p16'))
        with self.assertRaises(ValueError):
            self.tool.native_command(dict(command,case_id='d'*32))

        def open_worker(directory,binding):
            by_packet = {item['packet_index']:item for item in binding['request']['anchors']}
            self.assertEqual(set(by_packet),{12,13,14,15})
            self.assertEqual(by_packet[15]['timestamp'],dict(value=1500,unit='ns'))
            def goto(action,target):
                self.assertEqual(target['index'],15)
                return {'state':'viewport_ready'}
            return SimpleNamespace(request=goto)
        with patch('pcie_navigation_service.Worker',side_effect=open_worker):
            self.assertTrue(self.tool.native_command(command))
            self.tool.thread.join(5)
        self.assertEqual(self.status()['phase'],'viewport_ready')
        self.assertEqual(self.status()['config_ur'],state['config_ur'])

    def test_cancel_preserves_main_case_and_retries(self):
        self.assertTrue(self.start())
        self.assertTrue(self.entered.wait(3))
        self.assertFalse(self.start())
        self.assertTrue(self.tool.native_command({'action':'cancel'}))
        self.assertEqual(self.status()['phase'],'config_ur')
        self.resume.set()
        self.tool.thread.join(5)
        self.assertEqual(self.status()['case_id'],self.case_id)
        self.assertEqual(self.status()['config_ur']['state'],'cancelled')
        self.assertNotIn('index',self.status()['config_ur'])
        self.assertTrue(self.start())
        self.tool.thread.join(5)
        self.assertEqual(self.status()['config_ur']['state'],'ready')

    def test_no_publication_on_partial_report_write_or_unknown_cleanup(self):
        def fail_report(out,result):
            self.write(out,result)
            raise OSError('fixture export failed')
        self.report_module.write = fail_report
        self.resume.set()
        self.assertTrue(self.start())
        self.tool.thread.join(5)
        self.assertEqual(self.status()['config_ur']['state'],'error')
        self.assertNotIn('index',self.status()['config_ur'])
        self.assertEqual(self.status()['case_id'],self.case_id)

        def refuse(*args):
            raise CleanupUnknown('fixture process did not close')
        self.acquire_module.run = refuse
        self.assertTrue(self.start())
        self.tool.thread.join(5)
        self.assertEqual(self.status()['phase'],'cleanup_unknown')
        self.assertEqual(self.status()['case_id'],self.case_id)
        self.assertFalse(self.start())
