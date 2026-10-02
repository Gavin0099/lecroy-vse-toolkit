import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2b_config_access as b2b
import b2a_register_fields as b2a
from test_b2a_register_fields import fixture


def inputs():
    rows,end,meta=fixture()
    return dict(schema=b2a.SCHEMA,status='PASS_REGISTER_FIELD_PROBE',rows=rows,tlps=end['tlps'],input={'trace':{'sha256':'fixture'}}),meta


class ConfigTests(unittest.TestCase):
    def test_reuse_after_invalid_completion_cannot_return_successor_value(self):
        p,m=inputs()
        original=copy.deepcopy(p['rows'])
        p['rows'][1]['completer_id']=512
        f=bytearray.fromhex(p['rows'][1]['frame_prefix']);f[7:9]=bytes.fromhex('0200')
        p['rows'][1]['frame_prefix']=f.hex().upper();m[1]['completer_id']=512
        p['rows'][2:2]=[{**original[0],'packet_index':3160}, {**original[1],'packet_index':3170}]
        m[2:2]=[{**m[0],'packet_index':3160}, {**m[1],'packet_index':3170,'completer_id':256}]
        for i,row in enumerate(m):row['row']=i+1
        p['tlps']=5
        d=b2b.build(p,m,3200,4000)
        for r in d['accesses'][:2]:
            self.assertEqual(r['value_status'],'AMBIGUOUS_KEY_REUSE')
            self.assertIsNone(r['read_value'])

    def test_unprobed_locked_completions_remain_unknown(self):
        for typ in ('0x13','0x14'):
            p,m=inputs();fields={r['packet_index']:r for r in p['rows']}
            m[1]['tlp_type_hex']=typ;del fields[3150]
            q,amb,unmatched=b2b.associate_config(m,fields)
            self.assertEqual(q[0]['completions'][0]['field_status'],'NOT_CAPTURED_BY_B2A')
            self.assertIsNone(q[0]['completions'][0]['register_data'])
            self.assertEqual(unmatched,[])
            del p['rows'][1]
            d=b2b.build(p,m,3200,4000)
            self.assertIsNone(d['accesses'][0]['read_value'])
            self.assertEqual(d['accesses'][0]['value_status'],'UNKNOWN')
            q,amb,unmatched=b2b.associate_config(m[1:],fields)
            self.assertEqual(unmatched[0]['field_status'],'NOT_CAPTURED_BY_B2A')

    def test_read_and_partial_write_are_different_evidence(self):
        p,m=inputs();d=b2b.build(p,m,3200,4000)
        read,write=d['accesses']
        self.assertEqual(read['read_value'],0xF7C30001);self.assertIsNone(read['write_value'])
        self.assertEqual(write['write_value'],0x800B);self.assertEqual(write['first_be'],3)
        self.assertIsNone(write['read_value']);self.assertEqual(write['value_status'],'WRITE_REQUEST_OBSERVED')
        self.assertEqual(write['epoch'],'disconnect_interval');self.assertEqual(read['target_bdf'],'001:00.0')

    def test_late_completion_does_not_attach_to_closed_config(self):
        p,m=inputs();fields={r['packet_index']:r for r in p['rows']}
        late={**m[1],'row':4,'packet_index':5000};m.append(late);fields[5000]={**fields[3150],'packet_index':5000,'register_data':None}
        q,amb,unmatched=b2b.associate_config(m,fields)
        self.assertEqual([r['packet_index'] for r in q[0]['completions']],[3150])
        self.assertEqual([r['packet_index'] for r in unmatched],[5000])

    def test_memory_request_reserves_key(self):
        p,m=inputs();fields={r['packet_index']:r for r in p['rows']}
        mem={**m[0],'row':2,'packet_index':3149,'tlp_type_hex':'0x1'};m.insert(1,mem)
        q,amb,unmatched=b2b.associate_config(m,fields)
        self.assertEqual(q[0]['completions'],[]);self.assertEqual(q[1]['completions'][0]['packet_index'],3150)
        self.assertIn(3148,amb);self.assertIn(3149,amb)

    def test_reissue_no_return_is_ambiguous_for_both(self):
        p,m=inputs();fields={r['packet_index']:r for r in p['rows']}
        duplicate={**m[0],'packet_index':3149,'row':2};m.insert(1,duplicate);fields[3149]={**fields[3148],'packet_index':3149}
        q,amb,_=b2b.associate_config(m,fields)
        self.assertEqual(amb,{3148,3149});self.assertEqual(q[0]['outcome'],b2b.g2b.REISSUED)

    def test_wrong_target_status_or_direction_never_returns_value(self):
        for field,value,header in [('completer_id',512,None),('compl_status',1,None),('channel','Downstream',None)]:
            p,m=inputs();r=p['rows'][1];r[field]=value;m[1][field]=value
            f=bytearray.fromhex(r['frame_prefix'])
            if field=='completer_id':f[7:9]=bytes.fromhex('0200')
            if field=='compl_status':f[9]=0x20
            r['frame_prefix']=f.hex().upper()
            d=b2b.build(p,m,3200,4000)
            self.assertIsNone(d['accesses'][0]['read_value'])

    def test_anchor_and_coverage_failures(self):
        p,m=inputs()
        with self.assertRaises(ValueError):b2b.build(p,m,4000,3200)
        p['tlps']=4
        with self.assertRaises(ValueError):b2b.build(p,m,3200,4000)

    def test_real_case_old_identity_and_no_post_reconnect_cfg(self):
        root=Path(__file__).resolve().parents[2];p=root/'artifacts/evidence/pcie-b2a-hang-20260930/verified1/fields.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        probe=json.loads(p.read_text());meta=json.loads((root/'artifacts/evidence/pcie-p4a-hang-20260914/g2a/export/fields.json').read_text())
        d=b2b.build(probe,meta,225041,1479760)
        self.assertEqual(d['summary'],dict(config_requests=61,reads=32,writes=29,observed_read_returns=30,after_reconnect_requests=0))
        vid=next(r for r in d['accesses'] if r['packet_index']==3207)
        self.assertEqual(vid['read_value'],0x976717A0);self.assertEqual(vid['epoch'],'before_disconnect')
        self.assertTrue(all(r['read_value'] is None for r in d['accesses'] if r['epoch']=='disconnect_interval'))


if __name__=='__main__':unittest.main()
