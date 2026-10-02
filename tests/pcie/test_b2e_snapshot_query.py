import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2e_snapshot_query as b2e
import b2d_observed_state as b2d
from test_b2c_capability_resolution import fixture,ROOT,REF


class QueryTests(unittest.TestCase):
    def test_same_bdf_and_vid_did_do_not_inherit_snapshot_names_or_intent(self):
        log=fixture();base=log['accesses'][0]
        log['accesses'].append({**base,'packet_index':30,'register_byte_offset':0,'read_value':0x976717A0,'completions':[{'packet_index':31}]})
        log['accesses'].append({**base,'packet_index':40,'read_value':None,'write_value':0x42,'register_byte_offset':0x70})
        log['accesses'].append({**base,'packet_index':201,'epoch':'after_reconnect','register_byte_offset':0,'read_value':0x976717A0,'completions':[{'packet_index':202}]})
        snapshot=b2e.build(log,REF,256,250,[(0x70,2)])
        row=next(r for r in snapshot['registers'] if r['byte_offset']==0x70)
        self.assertEqual(row['names'],[])
        self.assertIsNone(row['read_value']);self.assertIsNone(row['write_intent_value'])
        identity=next(r for r in snapshot['registers'] if r['byte_offset']==0)
        self.assertEqual(identity['read_value'],0x976717A0)

    def test_zero_unknown_and_read_completion_boundary(self):
        log=fixture();before=b2e.build(log,REF,256,10,[(12,4),(0x300,4)]);after=b2e.build(log,REF,256,11,[(12,4)])
        self.assertTrue(all(r['read_value'] is None for r in before['registers']))
        self.assertEqual(next(r for r in after['registers'] if r['byte_offset']==12)['read_value'],0)

    def test_partial_intent_and_later_write_keeps_read(self):
        log=fixture();log['accesses'].append({**log['accesses'][0],'write_value':0x11223344,'read_value':None,'first_be':1,'packet_index':30})
        state=b2d.build(log,256,30);r=b2e.query_bytes(state,12,4)
        self.assertEqual(r['read_value'],0);self.assertIsNone(r['write_intent_value']);self.assertTrue(r['read_has_later_write'])
        self.assertEqual(r['write_intent_bytes'][0]['value'],0x44);self.assertIsNone(r['write_intent_bytes'][1])

    def test_new_epoch_no_inherited_name_or_value_and_invalid_query(self):
        d=b2e.build(fixture(),REF,256,250,[(0x70,2)])
        r=next(r for r in d['registers'] if r['byte_offset']==0x70)
        self.assertEqual(r['names'],[]);self.assertIsNone(r['read_value']);self.assertIsNone(r['write_intent_value'])
        state=b2d.build(fixture(),256,99)
        for off,width in ((4095,4),(-1,1),(0,3)):
            with self.assertRaises(ValueError):b2e.query_bytes(state,off,width)

    def test_real_link_control_is_intent_not_readback(self):
        p=ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        log=json.loads(p.read_text());d=b2e.build(log,REF,256,225040)
        r=next(r for r in d['registers'] if 'LinkControl' in r['names'])
        self.assertEqual(r['write_intent_value'],0x42);self.assertIsNone(r['read_value']);self.assertEqual(r['write_evidence_packets'],[10354])


if __name__=='__main__':unittest.main()
