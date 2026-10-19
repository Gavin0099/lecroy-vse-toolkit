"""One-copy and per-protocol failure behavior with persisted native fixtures."""
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb_triage_pipeline as pipeline
import usb_control_app as app
from test_usb3_data import raw
import test_pd_data as pd_fixture


class PipelineTests(unittest.TestCase):
    def run_case(self, fail_usb2=False, pd_present=False, fail_pd=False):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
        source=root/'input.usb';source.write_bytes(b'reviewed independent input')
        before=app.snapshot(source);digest=before['sha256'];calls=[]
        def native(args,output,stage,progress,resources):
            # The observable contract is actual files, one unchanged readonly
            # input and continuation after one protocol fails, not call counts.
            work=Path(args[args.index('-TracePath')+1]);out=Path(args[args.index('-Output')+1]);out.mkdir()
            self.assertFalse(work.stat().st_mode & stat.S_IWRITE)
            self.assertEqual(app.snapshot(work)['sha256'],digest);calls.append(work)
            if 'EP0' in stage:
                if fail_usb2:return 1
                m=dict(format='usb-control-inspection/v1',trace_sha256=digest,rule_version='fixture',candidates=[],
                       scope='USB2 EP0 fixture',coverage=dict(truncated=False,eligible_controls=1),limitations=['fixture'],episode_count=0)
                app.atomic_json(out/'inspection.json',m)
            elif 'USB3' in stage:
                r=raw([], 'USB3-END|100|0|0|0|0|0|0|0|0|'+('1' if pd_present else '0')+'|1|1|0');r['trace_sha256']=digest
                app.atomic_json(out/'raw-result.json',r)
            else:
                if fail_pd:return 1
                fixture=pd_fixture.PDDataTests();fixture.evidence(out)
                header=json.loads((out/'headers/raw-result.json').read_text());header['trace_sha256']=digest;app.atomic_json(out/'headers/raw-result.json',header)
                meta=json.loads((out/'raw-result.json').read_text());meta.update(trace_sha256=digest,header_raw_sha256=hashlib.sha256((out/'headers/raw-result.json').read_bytes()).hexdigest());app.atomic_json(out/'raw-result.json',meta)
            return 0
        with patch.object(pipeline,'command',side_effect=native):result=pipeline.run(source,root/'run')
        m=json.loads(result['model'].read_text(encoding='utf-8'))
        self.assertEqual(app.snapshot(source),before);self.assertEqual(calls,[result['working']]*(3 if pd_present else 2))
        self.assertEqual(list((root/'run').rglob('*.usb')),[result['working']])
        self.assertTrue(json.loads((root/'run/integrity.json').read_text())['source_unchanged'])
        self.assertIn('不代表 USB PASS', (root/'run/report.html').read_text(encoding='utf-8'))
        for p in root.rglob('*'):
            if p.is_file():p.chmod(stat.S_IWRITE|stat.S_IREAD)
        return m
    def test_one_copy_all_stages_and_per_protocol_empty_states(self):
        m=self.run_case();self.assertEqual([a['state'] for a in m['analyses']],['analyzed','not_observed','not_observed'])
    def test_one_protocol_failure_is_visible_and_does_not_skip_other_protocols(self):
        m=self.run_case(True);self.assertEqual([a['state'] for a in m['analyses']],['failed','not_observed','not_observed'])
    def test_pd_presence_uses_same_copy_and_missing_output_is_visible_failure(self):
        m=self.run_case(pd_present=True);self.assertEqual(m['analyses'][2]['state'],'analyzed')
        m=self.run_case(pd_present=True,fail_pd=True);self.assertEqual([a['state'] for a in m['analyses']],['analyzed','not_observed','failed'])


if __name__=='__main__':unittest.main()
