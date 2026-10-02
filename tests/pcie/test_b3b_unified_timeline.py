import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import b3b_unified_timeline as adapter
import b3a_event_contract as contract

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'artifacts/evidence/pcie-unified-timeline-20261002/inputs.json'


class UnifiedTimelineTests(unittest.TestCase):
    def test_unmatched_and_missing_completion_do_not_become_read_state(self):
        unmatched=[r for r in self.doc['events'] if r['details'].get('unmatched_completion_candidate')]
        self.assertEqual(len(unmatched),44)
        self.assertTrue(all(not r['details']['config_completions'] for r in unmatched))
        row=next(r for r in self.doc['events'] if r['packet_index']==225043 and r['layer']=='TLP')
        self.assertEqual(row['details']['config_request']['completion_packets'],[])
        self.assertEqual(row['details']['config_request']['value_status'],'AMBIGUOUS_KEY_REUSE')
        self.assertEqual(row['state_claims']['policy_result'],'NOT_EVALUATED')

    def test_manifest_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'outside-manifest.json';p.write_text('{}')
            with self.assertRaises(ValueError):adapter.inputs(ROOT,p)
    @classmethod
    def setUpClass(cls):
        cls.doc=adapter.build(ROOT,MANIFEST)
        cls.raw,cls.paths=adapter.inputs(ROOT,MANIFEST)
        cls.data={k:json.loads(cls.raw[k]) for k in adapter.JSON_INPUTS}

    def test_source_records_and_packet_counts_conserved(self):
        self.assertEqual(len(self.doc['events']),704+39)  # 43 link records include four existing TLPs.
        self.assertEqual(len(self.doc['intervals']),33)
        self.assertEqual(sum(r['counts']['events'] for r in self.doc['intervals']),1259373)
        self.assertEqual(sum(r['counts']['err_any'] for r in self.doc['intervals']),384993)
        for r in self.doc['events']:
            if r['layer']=='TLP':
                row=contract.pointer_value(self.data['metadata'],r['evidence'][0]['json_pointer'])
                self.assertEqual((r['packet_index'],r['time_display'],r['direction']),
                                 (row['packet_index'],row['time_display'],row['channel']))

    def test_write_intent_is_not_applied_policy_or_root_cause(self):
        row=next(r for r in self.doc['events'] if r['packet_index']==10354)
        intent=row['details']['register_write_intent']
        self.assertEqual((intent['observation_kind'],intent['observed_write_intent']),('L1_ENABLE_WRITE_INTENT',0x42))
        self.assertEqual(row['state_claims'],contract.UNKNOWN_CLAIMS)
        self.assertEqual(row['classification'],'WRITE_INTENT')
        self.assertEqual(intent['completion_packets'],[10358])

    def test_read_returns_are_at_completion_only_and_epochs_isolated(self):
        requests=[r for r in self.doc['events'] if r['details'].get('config_request')]
        self.assertEqual(len(requests),61)
        self.assertTrue(all('read_value' not in r['details']['config_request'] for r in requests))
        self.assertFalse(any(r['device_epoch']=='after_reconnect' for r in requests))
        self.assertTrue(all(r['device_identity']=='UNKNOWN' and r['identity_continuity_proof'] is None for r in self.doc['events']))
        returned=[c for r in self.doc['events'] for c in r['details'].get('config_completions',[]) if c['read_return_observation'] is not None]
        self.assertEqual(len(returned),30)

    def test_overlapping_tlp_evidence_not_duplicated(self):
        for packet in [225043,225048,1484399,1484414]:
            rows=[r for r in self.doc['events'] if r['packet_index']==packet and r['layer']=='TLP']
            self.assertEqual(len(rows),1)
            self.assertTrue(any(e['source_id']=='link_timeline' for e in rows[0]['evidence']))

    def test_invalid_states_and_nak_stay_observations(self):
        invalid=[r for r in self.doc['events'] if r['details'].get('link_record',{}).get('valid')==0]
        self.assertTrue(invalid)
        self.assertTrue(all(r['state_claims']['policy_result']=='NOT_EVALUATED' for r in invalid))
        nak=[r for r in self.doc['events'] if r['kind']=='nak']
        self.assertEqual([r['packet_index'] for r in nak],[225042])
        self.assertNotIn('replay',nak[0]['details'])

    def test_sample_times_not_invented_and_gap_not_a_packet(self):
        samples=[s for r in self.doc['intervals'] for s in r['details']['gui_samples']]
        self.assertEqual([s['sample']['packet_index'] for s in samples],[990799,1096918,1479761])
        self.assertTrue(all('time_display' not in s['sample'] for s in samples))
        gap=self.doc['gaps'][0]
        self.assertEqual((gap['after_index'],gap['before_index'],gap['display_duration_seconds']),(1479759,1479760,'1.312'))
        self.assertNotIn('packet_index',gap)

    def test_connectivity_and_l0_have_independent_sourced_milestones(self):
        by_id={r['id']:r for r in self.doc['milestones']}
        self.assertEqual((by_id['MUX_CONNECTIVITY']['status'],by_id['BIDIRECTIONAL_L0']['status']),('PASS','PASS'))
        self.assertEqual(by_id['BIDIRECTIONAL_L0']['basis'],'B1D_OBSERVATION_MILESTONE')
        e=contract.pointer_value(self.data['evaluation'],by_id['MUX_CONNECTIVITY']['evidence'][0]['json_pointer'])
        self.assertFalse(any(r.get('state')=='L0' for r in e['evidence']))
        self.assertEqual(by_id['INITIAL_GEN1_SAMPLE']['status'],'INCONCLUSIVE')
        self.assertEqual(by_id['TS_ERROR_TOLERANCE']['status'],'NOT_EVALUATED')

    def test_changed_metadata_capture_and_config_fact_rejected(self):
        raw=copy.deepcopy(self.raw);raw['metadata']+=b' '
        with self.assertRaises(ValueError):adapter.verify_config(raw,self.data)
        data=copy.deepcopy(self.data);data['raw_probe']['input']['trace']['sha256']='A'*64
        with self.assertRaises(ValueError):adapter.verify_config(self.raw,data)
        data=copy.deepcopy(self.data);data['accesses']['accesses'][0]['read_value']=123
        with self.assertRaises(ValueError):adapter.verify_config(self.raw,data)
        data=copy.deepcopy(self.data);data['context']['operation']['reconnect_packet']+=1
        with self.assertRaises(ValueError):adapter.verify_config(self.raw,data)

    def test_wrong_link_capture_invalid_state_or_totals_rejected(self):
        for mutation in ['capture','state','count']:
            data=copy.deepcopy(self.data)
            if mutation=='capture':data['gui']['trace_sha256']='A'*64
            elif mutation=='state':data['training']['phases'][0]['steps'][1]['state_valid']=1
            else:data['link_summary']['totals']['err_any']+=1
            with self.assertRaises(ValueError):adapter.verify_link(self.raw,data,self.doc['capture_sha256'])

    def test_packet_order_preserved_with_equal_display_times(self):
        packets=[r['packet_index'] for r in self.doc['events']]
        self.assertEqual(packets,sorted(packets))
        rows=[r for r in self.doc['events'] if r['packet_index'] in [8658,9915,10354]]
        self.assertEqual([r['time_display'] for r in rows],['8.314 sec']*3)
        self.assertEqual([r['display_quantum_seconds'] for r in rows],['0.001']*3)

    def test_cli_refuses_existing_output_and_consumer_rejects_changed_fact(self):
        with tempfile.TemporaryDirectory() as temp:
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pcie/b3b_unified_timeline.py'),
                              '--manifest',str(MANIFEST),'--source-root',str(ROOT),'--output-dir',temp],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            p=Path(temp)/'timeline.json';doc=copy.deepcopy(self.doc)
            next(r for r in doc['events'] if r['packet_index']==10354)['details']['register_write_intent']['observed_write_intent']=0
            p.write_text(json.dumps(doc),encoding='utf-8')
            with self.assertRaises(ValueError):adapter.verified_timeline(p,ROOT)


if __name__=='__main__':unittest.main()
