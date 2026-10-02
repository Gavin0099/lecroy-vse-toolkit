import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2f_snapshot_diff as b2f
import b2e_snapshot_query as b2e
import b2a_register_fields as b2a
from test_b2c_capability_resolution import fixture,ROOT,REF


class DiffTests(unittest.TestCase):
    def test_earlier_pointer_width_snapshot_is_not_current_source_replay(self):
        with tempfile.TemporaryDirectory() as t:
            output=Path(t)/'diff'
            args=['--before',str(ROOT/'artifacts/evidence/pcie-b2e-hang-20260930/before-run1/snapshot.json'),
                  '--after',str(ROOT/'artifacts/evidence/pcie-b2e-delivery-20261002/after-run1/snapshot.json'),
                  '--log',str(ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'),
                  '--reference',str(ROOT/'docs/pcie-register-reference.json'),'--output-dir',str(output)]
            self.assertEqual(b2f.main(args),2)
            self.assertFalse(output.exists())

    def test_same_epoch_observed_change_and_unknown(self):
        log=fixture()
        log['accesses'].append({**log['accesses'][0],'packet_index':30,'read_value':None,'write_value':4})
        before=b2e.build(log,REF,256,40,[(0x300,4)])
        log['accesses'].append({**log['accesses'][0],'packet_index':96,'read_value':1,'completions':[{'packet_index':97}]})
        log['accesses'].append({**log['accesses'][0],'packet_index':98,'read_value':None,'write_value':7})
        after=b2e.build(log,REF,256,99,[(0x300,4)])
        d=b2f.compare(before,after)
        self.assertEqual(next(r for r in d['registers'] if r['byte_offset']==12)['read_relation'],'OBSERVED_VALUE_CHANGED')
        self.assertEqual(next(r for r in d['registers'] if r['byte_offset']==12)['write_intent_relation'],'OBSERVED_VALUE_CHANGED')
        self.assertEqual(next(r for r in d['registers'] if r['byte_offset']==0x300)['read_relation'],'EVIDENCE_GAP')
        self.assertEqual(d['overall_verdict'],'NOT_CLAIMED')

    def test_cross_epoch_and_bdf_never_changed_or_zero(self):
        before=b2e.build(fixture(),REF,256,99);after=b2e.build(fixture(),REF,256,250)
        for d in (b2f.compare(before,after),b2f.compare(before,{**before,'device_id':512})):
            self.assertFalse(d['comparable_device_epoch']);self.assertTrue(all(r['read_relation']=='NOT_COMPARABLE_DEVICE_EPOCH' for r in d['registers']))

    def test_cli_rejects_tamper_and_identity_then_produces_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);log=p/'log.json';ref=p/'ref.json';log.write_text(json.dumps(fixture()));ref.write_text(json.dumps(REF))
            a=b2e.build(fixture(),REF,256,99);b=b2e.build(fixture(),REF,256,250)
            for d,name in ((a,'before.json'),(b,'after.json')):
                d['input']={'log_sha256':b2a.sha(log),'reference_sha256':b2a.sha(ref)};(p/name).write_text(json.dumps(d))
            argv=['--before',str(p/'before.json'),'--after',str(p/'after.json'),'--log',str(log),'--reference',str(ref),'--output-dir',str(p/'output')]
            a['registers'][0]['read_value']=123;(p/'before.json').write_text(json.dumps(a))
            self.assertEqual(b2f.main(argv),2);self.assertFalse((p/'output').exists())
            a=b2e.build(fixture(),REF,256,99);a['input']=b['input'];(p/'before.json').write_text(json.dumps(a))
            a['input']={**a['input'],'log_sha256':'wrong-hash'};(p/'before.json').write_text(json.dumps(a))
            self.assertEqual(b2f.main(argv),2);self.assertFalse((p/'output').exists())
            a['input']=b['input'];(p/'before.json').write_text(json.dumps(a))
            self.assertEqual(b2f.main(argv),0);self.assertEqual(b2f.main(argv),2)

    def test_reversed_order(self):
        a=b2e.build(fixture(),REF,256,99)
        with self.assertRaises(ValueError):b2f.compare(a,{**a,'packet_index':1})

    def test_real_before_after_epoch_boundary(self):
        p=ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        log=json.loads(p.read_text());d=b2f.compare(b2e.build(log,REF,256,225040),b2e.build(log,REF,256,1484414,[(0x90,2)]))
        self.assertFalse(d['comparable_device_epoch'])
        r=next(r for r in d['registers'] if r['byte_offset']==0x90 and r['width_bytes']==2)
        self.assertEqual(r['before']['write_intent_value'],0x42);self.assertIsNone(r['after']['write_intent_value'])


if __name__=='__main__':unittest.main()
