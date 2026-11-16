"""Observable HTTP/ownership boundary regressions; never opens LeCroy."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import usb_control_app as app


def oracle(digest):
    return {'format':'usb-control-inspection/v1','rule_version':'fixture', 'trace_sha256':digest,
            'scope':'USB2 EP0','status':'candidates_found','episode_count':4,'omitted_episodes':1,
            'coverage':{'visited_transfers':10,'eligible_controls':10,'unsupported_controls':0,'truncated':False},
            'limitations':['not a pass verdict'],
            'candidates':[{'rank':r,'title':'<unsafe>','start_ns':1234567890,'end_ns':1234567990,
                           'address':5,'endpoint':0,'transfer_indices':[i],'context':[],
                           'facts':['observed'],'reasons':['inspect'],'next_step':'check native',
                           'evidence_gaps':['partial']} for r,i in enumerate([562,372,446],1)]}


class FakeWorker:
    calls=[]
    gate=None
    failure=None
    def __init__(self, root, binding):
        self.binding=binding
    def request(self, action, transfer=None, timeout=90):
        self.calls.append((action,transfer))
        if self.gate:self.gate.wait(3)
        if self.failure:raise self.failure
        return {'state':'api_returned','transfer':transfer,'gui_confirmed':False,'open_count':1}
    def close(self):pass


class ToolTests(unittest.TestCase):
    def setUp(self):
        # Fake native operations must not depend on an engineer's live sessions.
        for replacement in (patch.object(app,'servers',return_value=[]),
                            patch.object(app,'NATIVE_MUTEX_NAME',r'Local\TriageTest.'+uuid.uuid4().hex)):
            replacement.start();self.addCleanup(replacement.stop)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'含 空白 $(); trace.usb';self.source.write_bytes(b'independent trace fixture')
        self.model=self.root/'inspection.json';self.model.write_text(json.dumps(oracle(hashlib.sha256(self.source.read_bytes()).hexdigest())))
        FakeWorker.calls=[];FakeWorker.gate=None;FakeWorker.failure=None
        self.tool=app.Tool(self.root/'run',FakeWorker);self.tool.load_report(self.model,self.source)
        self.server=app.serve(self.tool)
    def tearDown(self):
        if FakeWorker.gate:FakeWorker.gate.set()
        if self.tool.thread:self.tool.thread.join(4)
        self.server.shutdown();self.server.server_close()
        for p in self.root.rglob('*'):
            if p.is_file():p.chmod(stat.S_IWRITE|stat.S_IREAD)
        self.temp.cleanup()
    def request(self,method,path,data=None,**headers):
        defaults={'Host':self.server.authority,'Origin':self.server.origin,
                  'X-Trace-Session':self.tool.token,'Content-Type':'application/json'}
        defaults.update(headers)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        conn.request(method,path,json.dumps(data) if data is not None else None,defaults)
        response=conn.getresponse();body=response.read();code=response.status;conn.close();return code,body
    def nav(self,rank=1):return {'case_id':self.tool.case['id'],'rank':rank}
    def wait(self):
        self.tool.thread.join(3);self.assertFalse(self.tool.thread.is_alive())
    def test_valid_navigation_maps_candidate_not_client_unit(self):
        self.assertEqual(self.request('POST','/navigate',self.nav(2))[0],202);self.wait()
        self.assertEqual(FakeWorker.calls,[('goto',372)])
        self.assertEqual(self.tool.public()['phase'],'api_returned')
        self.assertFalse(self.tool.public()['last_navigation']['gui_confirmed'])
    def test_native_workspace_navigation_reuses_candidate_authorization(self):
        self.assertTrue(self.tool.native_command({'action':'navigate',**self.nav(3)}));self.wait()
        self.assertEqual(FakeWorker.calls,[('goto',446)])
        self.assertTrue(self.tool.native_command({'action':'end'}));self.wait()
        self.assertEqual(self.tool.public()['phase'],'report')
        self.assertIsNone(self.tool.worker)
    def test_native_workspace_rejects_arbitrary_unit_path_or_stale_case(self):
        for command in [{'action':'navigate','case_id':'old','rank':1},
                        {'action':'navigate',**self.nav(),'transfer':999},
                        {'action':'navigate',**self.nav(),'path':'other.usb'},[],{'action':'unknown'}]:
            with self.assertRaises(ValueError):self.tool.native_command(command)
        self.assertEqual(FakeWorker.calls,[])
    def test_host_origin_token_rejected_without_worker(self):
        for headers in [{'Host':'localhost:'+str(self.server.server_port)}, {'Origin':'http://evil.invalid'},
                        {'Origin':'null'}, {'Origin':''},{'X-Trace-Session':'old'},
                        {'Origin':'http://127.0.0.1:1'}]:
            self.assertEqual(self.request('POST','/navigate',self.nav(),**headers)[0],403)
        self.assertEqual(FakeWorker.calls,[]);self.assertIsNone(self.tool.worker)
    def test_bad_candidate_or_extra_path_never_calls_worker(self):
        for data in [self.nav(0),self.nav(True),self.nav(4),{'case_id':'stale','rank':1},
                     {**self.nav(),'transfer':999},{**self.nav(),'path':'x;Write-Output HACK'}]:
            self.assertEqual(self.request('POST','/navigate',data)[0],400)
        self.assertEqual(FakeWorker.calls,[])
    def test_busy_repeated_click_is_single_inflight_operation(self):
        FakeWorker.gate=threading.Event()
        self.assertEqual(self.request('POST','/navigate',self.nav())[0],202)
        self.assertEqual(self.request('POST','/navigate',self.nav())[0],409)
        self.assertEqual(self.request('GET','/status')[0],200)
        FakeWorker.gate.set();self.wait();self.assertEqual(FakeWorker.calls,[('goto',562)])
    def test_unresponsive_worker_does_not_freeze_http_or_allow_retry(self):
        FakeWorker.failure=TimeoutError('unknown')
        self.request('POST','/navigate',self.nav());self.wait()
        self.assertEqual(self.tool.public()['phase'],'unresponsive')
        self.assertEqual(self.request('GET','/status')[0],200)
        self.assertEqual(self.request('POST','/navigate',self.nav())[0],400)
        self.assertEqual(len(FakeWorker.calls),1)
    def test_real_unresponsive_ipc_child_keeps_status_server_responsive(self):
        # Real subprocess + actual NativeWorker transport, deliberately no COM.
        # Fault injection is separate from the real native successful landings.
        class Hung(app.NativeWorker):
            def __init__(self,root,binding):
                self.root=Path(root);self.root.mkdir();(self.root/'ready.json').write_text('{}')
                self.proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])
            def request(self,action,transfer=None,timeout=90):
                return super().request(action,transfer,timeout=.4)
            def close(self):
                self.proc.terminate();self.proc.wait(3)
        self.tool.worker_factory=Hung
        try:
            self.request('POST','/navigate',self.nav());self.wait()
            self.assertEqual(self.tool.public()['phase'],'unresponsive')
            start=time.monotonic();self.assertEqual(self.request('GET','/status')[0],200)
            self.assertLess(time.monotonic()-start,1)
            self.assertEqual(self.request('POST','/navigate',self.nav())[0],400)
        finally:
            if self.tool.worker:self.tool.worker.close();self.tool.worker=None
    def test_integrity_change_stops_before_worker(self):
        self.source.write_bytes(b'changed')
        self.request('POST','/navigate',self.nav());self.wait()
        self.assertEqual(self.tool.public()['phase'],'error');self.assertEqual(FakeWorker.calls,[])
    def test_wrong_trace_identity_rejected(self):
        self.source.write_bytes(b'wrong source')
        with self.assertRaisesRegex(ValueError,'SHA-256'):self.tool.load_report(self.model,self.source)
    @unittest.skipUnless(os.name=='nt','Windows AppData redirection regression')
    def test_new_appdata_output_is_canonical_after_creation(self):
        # LeCroy's COM server cannot see a calling app's virtual AppData path.
        candidate=Path(os.environ['LOCALAPPDATA'])/'LeCroyTraceTriage'/('test-'+uuid.uuid4().hex)
        tool=app.Tool(candidate)
        try:
            self.assertEqual(tool.root,candidate.resolve(strict=True))
            self.assertTrue(tool.root.is_dir())
        finally:
            tool.root.rmdir()
    def test_page_shows_omitted_scope_identity_and_escapes_content(self):
        code,raw=self.request('GET','/');text=raw.decode()
        self.assertEqual(code,200);self.assertIn('另 1 個未顯示',text)
        self.assertIn('未涵蓋 USB3 Link',text);self.assertIn('&lt;unsafe&gt;',text)
        self.assertIn('在 LeCroy 定位',text);self.assertIn(self.source.name,text)
    def test_no_http_path_import_or_file_browsing(self):
        self.assertEqual(self.request('POST','/import',{'path':str(self.source)})[0],400)
        self.assertEqual(self.request('GET','/../inspection.json')[0],404)
        self.assertEqual(self.request('GET','/navigate')[0],404)
        self.assertEqual(FakeWorker.calls,[])
    def test_session_secret_not_written_to_evidence(self):
        self.request('POST','/navigate',self.nav());self.wait()
        for path in (self.root/'run').rglob('*'):
            if path.is_file() and path.suffix in ('.json','.jsonl','.html'):
                self.assertNotIn(self.tool.token,path.read_text(encoding='utf-8'))
    @unittest.skipUnless(os.name=='nt','Windows PowerShell runtime check')
    def test_legacy_ps_module_isolation_hashes_fixture(self):
        fixture=self.root/'檔案 $();.usb';fixture.write_bytes(b'abc')
        probe=Path(__file__).with_name('environment-probe.ps1')
        result=subprocess.run([app.POWERSHELL,'-NoProfile','-MTA','-File',str(probe),'-InputPath',str(fixture)],
            stdin=subprocess.DEVNULL,capture_output=True,env=app.powershell_environment(),timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual(data['sha256'],'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(data['module'],'Microsoft.PowerShell.Utility');self.assertEqual(data['edition'],'Desktop')
    @unittest.skipUnless(os.name=='nt','Windows mutex check')
    def test_separate_tool_threads_cannot_acquire_native_at_once(self):
        outcomes=[]
        def other():
            try:
                with app.native_exclusive():outcomes.append('acquired')
            except RuntimeError:outcomes.append('rejected')
        with app.native_exclusive():
            thread=threading.Thread(target=other);thread.start();thread.join(3)
        self.assertEqual(outcomes,['rejected'])


if __name__=='__main__':unittest.main()
