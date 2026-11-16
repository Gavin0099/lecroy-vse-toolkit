import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b2g_watchlist_prepare as b2g
from test_b2c_capability_resolution import fixture,ROOT,REF

EV={'product_context':{'provenance':{'source_kind':'fixture'},'case':{'reported_symptom':'Disable ASPM case condition; no BDF scope supplied'}}}


class PreparationTests(unittest.TestCase):
    def test_read_completion_crossing_disconnect_is_not_readback(self):
        log=fixture();template=log['accesses'][0]
        write={**template,'packet_index':50,'read_value':None,'write_value':2,
               'register_byte_offset':0x70,'first_be':3,'target_bdf':'001:00.0',
               'completions':[],'time_display':'1.000 sec'}
        log['accesses'] += [write,{**write,'packet_index':98,'read_value':2,
                                  'write_value':None,'first_be':15,
                                  'completions':[{'packet_index':101}]}]
        self.assertEqual(b2g.build(log,REF,EV)['observations'][0]['read_back_evidence_packets'],[])
    def test_readback_excludes_old_requests_and_superseded_writes(self):
        log=fixture();template=log['accesses'][0]
        def write(p,value=2):
            return {**template,'packet_index':p,'read_value':None,'write_value':value,
                    'register_byte_offset':0x70,'first_be':3,'target_bdf':'001:00.0',
                    'completions':[],'time_display':'1.000 sec'}
        def read(p,c):
            return {**write(p),'read_value':2,'write_value':None,'first_be':15,
                    'completions':[{'packet_index':c}]}
        log['accesses'] += [read(45,55),write(50),write(60),read(70,71)]
        rows=b2g.build(log,REF,EV)['observations']
        self.assertEqual([r['read_back_evidence_packets'] for r in rows],[[],[71]])

    def test_read_completion_after_overlapping_write_is_not_candidate(self):
        log=fixture();template=log['accesses'][0]
        write={**template,'packet_index':50,'read_value':None,'write_value':2,
               'register_byte_offset':0x70,'first_be':3,'target_bdf':'001:00.0',
               'completions':[],'time_display':'1.000 sec'}
        log['accesses'] += [write,{**write,'packet_index':55,'read_value':2,
                                  'write_value':None,'first_be':15,'completions':[{'packet_index':65}]},
                            {**write,'packet_index':60,'first_be':2}]
        self.assertFalse(b2g.build(log,REF,EV)['observations'][0]['read_back_observed'])

    def test_readback_does_not_cross_epoch_or_device(self):
        log=fixture();template=log['accesses'][0]
        write={**template,'packet_index':50,'read_value':None,'write_value':2,
               'register_byte_offset':0x70,'first_be':3,'target_bdf':'001:00.0',
               'completions':[],'time_display':'1.000 sec'}
        log['accesses'] += [write,{**write,'packet_index':60,'read_value':2,
                                  'write_value':None,'first_be':15,'epoch':'after_reconnect',
                                  'completions':[{'packet_index':61}]}]
        self.assertFalse(b2g.build(log,REF,EV)['observations'][0]['read_back_observed'])
    def test_enabled_intent_is_observation_not_product_fail(self):
        log=fixture();log['accesses'].append({**log['accesses'][0],'packet_index':50,'read_value':None,'write_value':2,'register_byte_offset':0x70,'target_bdf':'001:00.0','completions':[],'time_display':'1.000 sec'})
        d=b2g.build(log,REF,EV)
        self.assertEqual(d['product_rule_evaluation'],'NOT_EVALUATED');self.assertEqual(d['implemented_product_watchlist_rules'],[])
        self.assertEqual(d['observations'][0]['aspm_control_requested_bits'],2);self.assertFalse(d['observations'][0]['read_back_observed'])
        row=d['observations'][0]
        self.assertEqual(row['observation_kind'],'L1_ENABLE_WRITE_INTENT')
        self.assertEqual((row['observed_write_intent'],row['aspm_control_intent']),(2,'L1'))
        self.assertEqual((row['effective_state'],row['expected_state'],row['policy_result']),('UNKNOWN','UNKNOWN','NOT_EVALUATED'))
        self.assertEqual(d['schema'],'pcie.b2g-watchlist-preparation/v2')
        self.assertEqual(d['status'],'SOURCE_SCOPE_GATE');self.assertEqual(len(d['required_inputs']),4)
        self.assertTrue(all(v is None for v in d['product_policy'].values()))

    def test_readback_requires_return_after_write(self):
        log=fixture();log['accesses'].append({**log['accesses'][0],'packet_index':50,'read_value':None,'write_value':2,'register_byte_offset':0x70,'target_bdf':'001:00.0','completions':[],'time_display':'1.000 sec'})
        log['accesses'].append({**log['accesses'][0],'packet_index':60,'read_value':2,'register_byte_offset':0x70,'completions':[{'packet_index':61}]})
        row=b2g.build(log,REF,EV)['observations'][0]
        self.assertTrue(row['read_back_observed']);self.assertEqual(row['read_back_evidence_packets'],[61])
        self.assertEqual((row['effective_state'],row['expected_state'],row['policy_result']),('UNKNOWN','UNKNOWN','NOT_EVALUATED'))

    def test_partial_word_does_not_promote_unselected_bytes(self):
        log=fixture();log['accesses'].append({**log['accesses'][0],'packet_index':50,'read_value':None,'write_value':0xFF02,'register_byte_offset':0x70,'first_be':1,'target_bdf':'001:00.0','completions':[],'time_display':'1.000 sec'})
        row=b2g.build(log,REF,EV)['observations'][0]
        self.assertIsNone(row['observed_write_intent']);self.assertEqual(row['aspm_control_intent'],'L1')
        self.assertEqual(row['effective_state'],'UNKNOWN')

    def test_disabled_and_both_enabled_remain_unassessed_without_policy(self):
        for value,intent,kind in ((0,'DISABLED','ASPM_DISABLE_WRITE_INTENT'),(1,'L0S','L0S_ENABLE_WRITE_INTENT'),(3,'L0S_AND_L1','L1_ENABLE_WRITE_INTENT')):
            log=fixture();log['accesses'].append({**log['accesses'][0],'packet_index':50,'read_value':None,'write_value':value,'register_byte_offset':0x70,'target_bdf':'001:00.0','completions':[],'time_display':'1.000 sec'})
            row=b2g.build(log,REF,EV)['observations'][0]
            self.assertEqual((row['aspm_control_intent'],row['observation_kind']),(intent,kind))
            self.assertEqual(row['policy_result'],'NOT_EVALUATED')

    def test_real_three_writes_and_no_new_sde_state_claim(self):
        p=ROOT/'artifacts/evidence/pcie-b2b-hang-20260930/r2-run1/accesses.json'
        if not p.exists():self.skipTest('local trace evidence unavailable')
        d=b2g.build(json.loads(p.read_text()),REF,EV)
        self.assertEqual([(r['packet_index'],r['aspm_control_requested_bits']) for r in d['observations']],[(8658,2),(9915,0),(10354,2)])
        self.assertEqual([r['completion_packets'] for r in d['observations']],[[8660],[9918],[10358]])
        self.assertTrue(all(not r['read_back_observed'] for r in d['observations']))
        self.assertEqual(d['status'],'SOURCE_SCOPE_GATE')
        row=next(r for r in d['observations'] if r['packet_index']==10354)
        self.assertEqual((row['register'],row['bdf'],row['observed_write_intent']),('PCI_EXP_LNKCTL','001:00.0',0x42))
        self.assertEqual(row['observation_kind'],'L1_ENABLE_WRITE_INTENT')
        self.assertTrue(all(r['effective_state']=='UNKNOWN' and r['expected_state']=='UNKNOWN' and r['policy_result']=='NOT_EVALUATED' for r in d['observations']))


if __name__=='__main__':unittest.main()
