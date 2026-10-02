import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2d_observed_state as b2d
from test_b2c_capability_resolution import fixture,ROOT,REF


class StateTests(unittest.TestCase):
    def test_read_not_available_before_completion(self):
        log=fixture()
        self.assertEqual(b2d.build(log,256,10)['read_bytes'],{})
        self.assertEqual(b2d.build(log,256,11)['read_bytes']['12']['value'],0)

    def test_partial_write_does_not_replace_reads_or_fill_other_bytes(self):
        log=fixture();w={**log['accesses'][0],'packet_index':30,'write_value':0x11223344,'read_value':None,'register_byte_offset':12,'first_be':5,'access_id':'write-fixture'}
        for r in log['accesses']:r['write_value']=None
        log['accesses'].append(w)
        s=b2d.build(log,256,30)
        self.assertEqual(s['read_bytes']['12']['value'],0)
        self.assertEqual(s['write_intent_bytes']['12']['value'],0x44)
        self.assertEqual(s['write_intent_bytes']['14']['value'],0x22)
        self.assertNotIn('13',s['write_intent_bytes']);self.assertNotIn('15',s['write_intent_bytes'])

    def test_epoch_and_bdf_isolation_and_crossing_completion(self):
        log=fixture()
        for r in log['accesses']:r['write_value']=None
        for packet in (150,250):self.assertEqual(b2d.build(log,256,packet)['read_bytes'],{})
        self.assertEqual(b2d.build(log,512,99)['read_bytes'],{})
        log['accesses'][0]['completions'][0]['packet_index']=201
        self.assertNotIn('12',b2d.build(log,256,99)['read_bytes'])
        self.assertNotIn('12',b2d.build(log,256,250)['read_bytes'])

    def test_real_old_zero_and_new_unknown(self):
        p=ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        log=json.loads(p.read_text());old=b2d.build(log,256,225040);new=b2d.build(log,256,1484414)
        # Literal real probe: packet 10354 writes 0x42 at offset 0x90.
        # Public reference ASPM mask 0x3 yields L1-enable=2; this is intent only.
        self.assertEqual(old['write_intent_bytes']['144']['value'],0x42)
        self.assertEqual(old['write_intent_bytes']['144']['request_packet'],10354)
        self.assertEqual(old['read_bytes']['12']['value'],0)
        self.assertEqual(new['read_bytes'],{});self.assertEqual(new['write_intent_bytes'],{})

    def test_same_bdf_offset_and_vid_did_do_not_prove_epoch_continuity(self):
        log=fixture();base=log['accesses'][0]
        log['accesses'].append({**base,'packet_index':30,'register_byte_offset':0,'read_value':0x976717A0,'completions':[{'packet_index':31}]})
        log['accesses'].append({**base,'packet_index':40,'read_value':None,'write_value':0x42,'register_byte_offset':0x70})
        log['accesses'].append({**base,'packet_index':201,'epoch':'after_reconnect','register_byte_offset':0,'read_value':0x976717A0,'completions':[{'packet_index':202}]})
        # Matching VID/DID is an observation, not a continuity proof.
        old=b2d.build(log,256,99);new=b2d.build(log,256,250)
        self.assertEqual(old['read_bytes']['0']['value'],new['read_bytes']['0']['value'])
        self.assertIn('12',old['read_bytes']);self.assertNotIn('12',new['read_bytes'])
        self.assertIn('112',old['write_intent_bytes']);self.assertEqual(new['write_intent_bytes'],{})


if __name__=='__main__':unittest.main()
