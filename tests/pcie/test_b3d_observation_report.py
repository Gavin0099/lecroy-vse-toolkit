import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b3d_observation_report as report
import b3b_unified_timeline as adapter

ROOT=Path(__file__).resolve().parents[2]
TIMELINE=ROOT/'artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json'


class Tags(HTMLParser):
    def __init__(self):super().__init__();self.tags=[];self.attrs=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag);self.attrs.extend(attrs)
        self.ids += [v for k,v in attrs if k=='id']


class ObservationReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=adapter.verified_timeline(TIMELINE,ROOT)
        cls.model=report.build_model(cls.doc,ROOT)
        cls.markdown=report.render_markdown(cls.model,'../../../..')
        cls.webpage=report.render_html(cls.model,'../../../..')

    def test_markdown_and_html_preserve_rule_states_and_key_values(self):
        expected={'MUX_CONNECTIVITY':'PASS','BIDIRECTIONAL_L0':'PASS','INITIAL_GEN1_SAMPLE':'INCONCLUSIVE',
                  'TARGET_SPEED_OBSERVED':'INCONCLUSIVE','TRAINING_TIMEOUT':'NOT_EVALUATED',
                  'TS_ERROR_TOLERANCE':'NOT_EVALUATED','HOTPLUG_INIT_ACTIVITY':'INCONCLUSIVE'}
        by_id={r['id']:r for r in self.model['rules']}
        for key,status in expected.items():
            self.assertEqual(by_id[key]['status'],status)
            self.assertIn(key,self.markdown.replace('\\_','_'));self.assertIn(key,self.webpage)
            self.assertIn(status,self.markdown);self.assertIn(status,self.webpage)
        for text in ['10354','0x42','L1_ENABLE_WRITE_INTENT','SOURCE_SCOPE_GATE','1.312','384,993','FAIL_OWNER_RELAYED']:
            self.assertIn(text,self.markdown.replace('\\_','_'));self.assertIn(text,self.webpage)
        for text in ['990799','1096918','1479761','Time UNKNOWN',self.doc['capture_sha256']]:
            self.assertIn(text,self.markdown);self.assertIn(text,self.webpage)

    def test_concrete_observations_have_resolving_evidence(self):
        for group in ['rules','intents','config','link']:
            for item in self.model[group]:
                self.assertTrue(item['evidence'])
                for ref in item['evidence']:
                    payload=json.loads((ROOT/self.model['sources'][ref['source_id']]['path']).read_bytes())
                    report.contract.pointer_value(payload,ref['json_pointer'])

    def test_ground_truth_is_engineer_report_not_root_cause(self):
        self.assertFalse(self.model['case']['crash_dump_verified'])
        self.assertIn('工程師回報，非 trace 自動判定',self.markdown)
        self.assertIn('Root cause UNKNOWN',self.webpage)
        self.assertTrue(all(r['observation']['effective_state']=='UNKNOWN' and
                            r['observation']['expected_state']=='UNKNOWN' and
                            r['observation']['policy_result']=='NOT_EVALUATED' for r in self.model['intents']))

    def test_rule_title_reference_matches_rule_identity(self):
        source=json.loads((ROOT/self.model['sources']['findings']['path']).read_bytes())
        for rule in self.model['rules']:
            refs=[r for r in rule['evidence'] if r['source_id']=='findings']
            self.assertEqual(len(refs),1)
            finding=report.contract.pointer_value(source,refs[0]['json_pointer'])
            self.assertEqual(finding['rule_id'],rule['id'])
            self.assertEqual(finding['title'],rule['title'])

    def test_statuses_come_from_cited_source_and_rendered_model(self):
        source=json.loads((ROOT/self.model['sources']['watchlist']['path']).read_bytes())
        self.assertEqual(self.model['watchlist_status'],source['status'])
        self.assertEqual(self.model['product_rule_evaluation'],source['product_rule_evaluation'])
        self.assertEqual([r['json_pointer'] for r in self.model['watchlist_status_evidence']],['/status','/product_rule_evaluation'])
        m=copy.deepcopy(self.model);m['watchlist_status']='SOURCE_STATUS_SENTINEL'
        for rendered in [report.render_markdown(m,'../../../..'),report.render_html(m,'../../../..')]:
            self.assertIn('SOURCE_STATUS_SENTINEL',rendered.replace('\\_','_'))
            self.assertNotIn('SOURCE_SCOPE_GATE',rendered.replace('\\_','_'))
            self.assertNotIn('B2h conditional',rendered)

    def test_opaque_extensions_not_report_facts(self):
        doc=copy.deepcopy(self.doc);doc['extensions']['root_cause']='UNTRUSTED_CAUSAL_SENTINEL'
        model=report.build_model(doc,ROOT)
        self.assertNotIn('UNTRUSTED_CAUSAL_SENTINEL',report.render_markdown(model,'../../../..'))
        self.assertNotIn('UNTRUSTED_CAUSAL_SENTINEL',report.render_html(model,'../../../..'))

    def test_hostile_text_is_escaped_not_active_markup(self):
        m=copy.deepcopy(self.model)
        text='<script>alert(1)</script> [run](javascript:bad) |\n# injected'
        m['rules'][0]['summary']=text;m['case']['reported_symptom']=text
        markdown=report.render_markdown(m,'../../../..');webpage=report.render_html(m,'../../../..')
        parser=Tags();parser.feed(webpage)
        self.assertNotIn('script',parser.tags);self.assertIn('&lt;script&gt;',webpage)
        self.assertNotIn('[run](javascript:bad)',markdown)
        self.assertNotIn('\n# injected',markdown)
        self.assertFalse(any(k.lower().startswith('on') for k,v in parser.attrs))

    def test_html_is_offline_and_packet_anchors_unique(self):
        parser=Tags();parser.feed(self.webpage)
        self.assertNotIn('script',parser.tags);self.assertNotIn('iframe',parser.tags)
        self.assertFalse(any(k=='src' or (k=='href' and v.startswith(('http:','https:','//'))) for k,v in parser.attrs))
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertIn('packet-10354',parser.ids);self.assertIn('config-225043',parser.ids)

    def test_display_times_and_unknown_tail_not_promoted_to_absence(self):
        self.assertEqual(self.model['observations']['post_l0_observed_seconds'],'0.000')
        self.assertIn('顯示時間無差不代表物理時間為零',self.markdown)
        self.assertTrue(any(r['id']=='HOTPLUG_INIT_ACTIVITY' and r['status']=='INCONCLUSIVE' for r in self.model['rules']))
        self.assertEqual(len(self.model['config']),61)
        self.assertTrue(all(r['epoch']!='after_reconnect' for r in self.model['config']))

    def test_cli_rejects_existing_output_and_tampered_timeline(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'tampered.json';d=copy.deepcopy(self.doc);d['events'][0]['details']['invented']=True
            p.write_text(json.dumps(d),encoding='utf-8');out=Path(temp)/'output'
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pcie/b3d_observation_report.py'),
                              '--timeline',str(p),'--source-root',str(ROOT),'--output-dir',str(out)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertFalse(out.exists())
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pcie/b3d_observation_report.py'),
                              '--timeline',str(TIMELINE),'--source-root',str(ROOT),'--output-dir',temp],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)


if __name__=='__main__':unittest.main()
