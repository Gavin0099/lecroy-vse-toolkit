"""Native target identity and protocol status boundaries; no COM activation."""
import copy
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import usb_control_app as app
import usb_triage_model as model


def fixture(digest):
    analyses = []
    for protocol in model.PROTOCOLS:
        t = model.target(protocol, 0 if protocol == 'USB3' else 3, 8, 123000000)
        analyses.append(dict(protocol=protocol, state='analyzed', coverage={'source': 'review fixture'},
                             scope='fixture only', limitations=[], episode_count=1,
                             candidates=[dict(title=protocol+' <card>', start_ns=123000000, end_ns=123000000,
                                              native_targets=[t], facts=['independent fixture'],
                                              reasons=['inspect'], next_step='check native', context=[], evidence_gaps=[])]))
    return model.compose(digest, analyses)


class Worker:
    def __init__(self, root, binding):
        self.binding = binding
        self.calls = []
    def request(self, action, target=None):
        self.calls.append((action, target))
        return dict(state='api_returned', target=target, gui_confirmed=False, open_count=1)
    def close(self):
        pass


class ExpansionTests(unittest.TestCase):
    def test_observed_flow_separate_count_and_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'source.usb';source.write_bytes(b'flow fixture')
            m=fixture(hashlib.sha256(source.read_bytes()).hexdigest());flow=copy.deepcopy(m['candidates'][2]);flow.update(rank=1,kind='observation');m['observations']=[flow];m['analyses'][2]['observation_count']=1
            app.validate_model(m);self.assertEqual(m['episode_count'],3)
            text=model.render(m);self.assertIn('已觀察流程',text)
            f=root/'inspection.json';f.write_text(json.dumps(m));tool=app.Tool(root/'session',Worker)
            with patch.object(app,'servers',return_value=[]):
                try:
                    tool.load_report(f,source);case=tool.case['id']
                    self.assertTrue(tool.native_command(dict(action='navigate',case_id=case,rank=1,target_index=0,item_kind='observation')))
                    tool.thread.join(3);self.assertEqual(tool.worker.calls[0][1]['protocol'],'PD')
                    for kind,rank in [('observation',2),('invented',1)]:
                        with self.assertRaises(ValueError):tool.navigate(case,rank,0,kind)
                    tool.close_navigation()
                finally:
                    for p in root.rglob('*'):
                        if p.is_file():p.chmod(stat.S_IREAD|stat.S_IWRITE)
    def test_protocol_and_level_are_part_of_identity(self):
        m = fixture('a'*64)
        self.assertEqual([c['native_targets'][0] for c in m['candidates']],
                         [model.target('USB2',3,8,123000000),model.target('USB3',0,8,123000000),model.target('PD',3,8,123000000)])
        for protocol, level, index in [('USB3',3,8),('USB2',0,8),('PD',2,8),('PD',3,-1),('PD',False,8),('PD',0,True)]:
            with self.assertRaises(ValueError):model.target(protocol,level,index)
    def test_bad_hash_status_total_and_cross_protocol_target_rejected(self):
        base=fixture('a'*64)
        for mutate in [lambda m:m.update(trace_sha256='wrong'),
                       lambda m:m['analyses'][0].update(state='not_observed'),
                       lambda m:m['analyses'][0].update(episode_count=0),
                       lambda m:m['candidates'][1]['native_targets'][0].update(protocol='PD'),
                       lambda m:m['candidates'][2]['native_targets'][0].update(path='other.usb')]:
            m=copy.deepcopy(base);mutate(m)
            with self.assertRaises(ValueError):app.validate_model(m)
    def test_scope_states_not_rendered_as_pass_and_content_escaped(self):
        m=fixture('a'*64)
        m['candidates']=[]
        for a,state in zip(m['analyses'],['not_observed','partial','failed']):
            a.update(state=state,episode_count=0,limitations=['<missing>'])
        text=model.render(m)
        self.assertIn('未觀察到',text);self.assertIn('資料部分缺漏',text);self.assertIn('執行失敗',text)
        self.assertIn('&lt;missing&gt;',text);self.assertNotIn('<missing>',text)
        self.assertIn('不能當成 USB PASS',text)
    def test_controller_selects_only_bound_target_and_reuses_worker(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'source.usb';source.write_bytes(b'fixture bytes')
            m=fixture(hashlib.sha256(source.read_bytes()).hexdigest())
            m['candidates'][2]['native_targets'].append(model.target('PD',0,160,7000000000))
            path=root/'inspection.json';path.write_text(json.dumps(m))
            tool=app.Tool(root/'session',Worker)
            with patch.object(app,'servers',return_value=[]):
                try:
                    tool.load_report(path,source)
                    case=tool.case['id']
                    self.assertTrue(tool.native_command(dict(action='navigate',case_id=case,rank=3,target_index=1)))
                    tool.thread.join(3);self.assertFalse(tool.thread.is_alive())
                    worker=tool.worker
                    self.assertEqual(worker.calls,[('goto',model.target('PD',0,160,7000000000))])
                    self.assertEqual(worker.binding['trace_sha256'],m['trace_sha256'])
                    self.assertEqual(len(worker.binding['targets']),4)
                    self.assertIn('PKT',tool.public()['message'])
                    self.assertFalse(tool.public()['last_navigation']['gui_confirmed'])
                    for request in [dict(action='navigate',case_id='old',rank=1),
                                    dict(action='navigate',case_id=case,rank=1,target_index=99),
                                    dict(action='navigate',case_id=case,rank=1,target={'level':0,'index':999})]:
                        with self.assertRaises(ValueError):tool.native_command(request)
                    self.assertEqual(len(worker.calls),1)
                    self.assertTrue(tool.navigate(case,2));tool.thread.join(3)
                    self.assertIs(tool.worker,worker)
                    self.assertEqual(worker.calls[-1][1],model.target('USB3',0,8,123000000))
                    tool.integrity();tool.close_navigation()
                finally:
                    for p in root.rglob('*'):
                        if p.is_file():p.chmod(stat.S_IREAD|stat.S_IWRITE)


if __name__ == '__main__':unittest.main()
