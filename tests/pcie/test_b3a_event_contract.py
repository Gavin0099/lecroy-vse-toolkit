import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/pcie'))
import b3a_event_contract as contract

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'artifacts/evidence/pcie-w1-20261002/representative.json'


class EventContractTests(unittest.TestCase):
    def test_source_alias_cannot_bypass_count_and_gap_consistency(self):
        self.doc['sources']['link_alias']=copy.deepcopy(self.doc['sources']['link'])
        self.sources['link_alias']=self.sources['link']
        interval=copy.deepcopy(self.doc['intervals'][0]);interval['evidence'][0]['source_id']='link_alias'
        self.doc['intervals'].append(interval)
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)
        self.doc['intervals'].pop()
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)
    def test_gap_cannot_cover_same_source_segment_counts(self):
        self.doc['gaps']=[{'after_index':225040,'before_index':225051,
                          'after_time':'9.511 sec','before_time':'9.513 sec',
                          'after_display_quantum_seconds':'0.001','before_display_quantum_seconds':'0.001',
                          'display_duration_seconds':'0.002','claim':'NO_OBSERVED_EVENTS_IN_SOURCE_WINDOW',
                          'evidence':[contract.evidence('link','/0')]}]
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)

    def test_duplicate_segment_counts_cannot_inflate_intervals(self):
        self.doc['intervals'].append(copy.deepcopy(self.doc['intervals'][0]))
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)
    def test_nested_identity_claims_are_rejected(self):
        for field,value in [('device_identity','KNOWN'),('identity_continuity_proof','same BDF')]:
            for target in ('details','extensions'):
                doc=copy.deepcopy(self.doc)
                if target=='details':doc['events'][0]['details']={'nested':[{field:value}]}
                else:doc['extensions']={'nested':[{field:value}]}
                with self.assertRaises(ValueError): contract.validate(doc,self.sources)
    def test_segment_total_and_category_bounds(self):
        for mode in ('missing','category','span'):
            doc=copy.deepcopy(self.doc);counts=doc['intervals'][0]['counts']
            if mode=='missing':del counts['events']
            elif mode=='category':counts['tlp']=11
            else:counts['events']=9
            with self.assertRaises(ValueError): contract.validate(doc,self.sources)

    def test_gap_cannot_contain_event_from_same_source(self):
        self.doc['gaps']=[{'after_index':8600,'before_index':9000,
                          'after_time':'8.313 sec','before_time':'8.315 sec',
                          'after_display_quantum_seconds':'0.001','before_display_quantum_seconds':'0.001',
                          'display_duration_seconds':'0.002','claim':'NO_OBSERVED_EVENTS_IN_SOURCE_WINDOW',
                          'evidence':[contract.evidence('watchlist','')]}]
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)
        self.doc['gaps'][0]['evidence']=[contract.evidence('training','/phases/7')]
        contract.validate(self.doc,self.sources)  # Other-source coverage is not silently expanded.
    def test_undeclared_claim_fields_and_extensions_are_checked(self):
        for field,value in [('effective_state','L1'),('policy_result','FAIL')]:
            doc=copy.deepcopy(self.doc);doc['events'][0][field]=value
            with self.assertRaises(ValueError): contract.validate(doc,self.sources)
            doc=copy.deepcopy(self.doc);doc['extensions']={'nested':[{field:value}]}
            with self.assertRaises(ValueError): contract.validate(doc,self.sources)
    def test_details_cannot_promote_claims_at_any_depth(self):
        for field,value in [('effective_state','L1'),('expected_state','DISABLED'),('policy_result','FAIL')]:
            for detail in [{field:value},{'nested':[{field:value}]}]:
                doc=copy.deepcopy(self.doc);doc['events'][0]['details']=detail
                with self.assertRaises(ValueError): contract.validate(doc,self.sources)

    def test_alias_cannot_duplicate_observation(self):
        event=copy.deepcopy(self.doc['events'][0]);event['event_id']='arbitrary-second-id'
        self.doc['events'].insert(0,event)  # Alias keeps the old lexicographic ordering valid.
        with self.assertRaises(ValueError): contract.validate(self.doc,self.sources)

    def test_sources_array_is_controlled_cli_error(self):
        self.doc['sources']=[]
        with self.assertRaises(ValueError): contract.validate(self.doc,{})
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'invalid.json';p.write_text(json.dumps(self.doc))
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/pcie/b3a_event_contract.py'),
                              '--timeline',str(p),'--source-root',str(ROOT)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
    def test_negative_fixture_cases_execute_validator(self):
        cases=json.loads((FIXTURE.parent/'negative-cases.json').read_text())
        for case in cases:
            doc=copy.deepcopy(self.doc)
            prefix,key=case['path'].rsplit('/',1)
            parent=contract.pointer_value(doc,prefix)
            parent[int(key) if isinstance(parent,list) else key]=case['value']
            with self.subTest(reason=case['reason']):
                with self.assertRaises(ValueError): contract.validate(doc,self.sources)
    def setUp(self):
        self.doc = json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.sources = contract.load_sources(self.doc, ROOT)

    def test_real_representative_fixture_preserves_intent_and_precision(self):
        result = contract.validate(self.doc, self.sources)
        self.assertEqual(result['packet_observations'], 2)
        self.assertEqual([r['packet_index'] for r in self.doc['events']], [8658, 10354])
        self.assertEqual(self.doc['events'][1]['details']['observed_write_intent'], 0x42)
        self.assertEqual(self.doc['events'][1]['display_quantum_seconds'], '0.001')
        self.assertEqual(self.doc['events'][1]['state_claims'], contract.UNKNOWN_CLAIMS)

    def test_wrong_capture_and_changed_source_are_rejected(self):
        self.doc['sources']['watchlist']['capture_sha256'] = 'A' * 64
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.sources['watchlist'] += b' '
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_missing_source_or_pointer_rejected(self):
        with self.assertRaises(ValueError): contract.validate(self.doc, {})
        self.doc['events'][0]['evidence'][0]['json_pointer'] = '/observations/10000'
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_epoch_and_identity_are_not_inferred_from_bdf(self):
        self.doc['events'][0]['device_epoch'] = 'after_reconnect'
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.doc['events'][0]['identity_continuity_proof'] = 'same BDF/VID-DID'
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_same_display_time_uses_packet_order_not_causation(self):
        self.assertEqual(self.doc['events'][0]['time_display'], self.doc['events'][1]['time_display'])
        self.doc['events'].reverse()
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.doc['events'].append(copy.deepcopy(self.doc['events'][-1]))
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_no_observation_to_effective_or_policy_promotion(self):
        for field, value in [('effective_state', 'L1'), ('expected_state', 'DISABLED'), ('policy_result', 'FAIL')]:
            doc = copy.deepcopy(self.doc); doc['events'][0]['state_claims'][field] = value
            with self.assertRaises(ValueError): contract.validate(doc, self.sources)

    def test_time_precision_and_packet_type(self):
        self.doc['events'][0]['display_quantum_seconds'] = '0.000001'
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.doc['events'][0]['packet_index'] = True
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_path_escape_rejected(self):
        self.doc['sources']['watchlist']['path'] = '../outside.json'
        with self.assertRaises(ValueError): contract.load_sources(self.doc, ROOT)

    def test_interval_and_gap_do_not_invent_packets_or_direction(self):
        self.assertEqual(self.doc['intervals'][0]['counts']['dllp_nak'], 1)
        self.assertEqual(self.doc['gaps'][0]['display_duration_seconds'], '1.312')
        self.doc['intervals'][0]['direction'] = 'Downstream'
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.doc['gaps'][0]['packet_index'] = 1479759
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_missing_field_and_negative_counts_rejected(self):
        del self.doc['coverage']
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)
        self.setUp(); self.doc['intervals'][0]['counts']['dllp_nak'] = -1
        with self.assertRaises(ValueError): contract.validate(self.doc, self.sources)

    def test_machine_field_contract_matches_executable_validator(self):
        d=json.loads((ROOT/'docs/pcie-observation-timeline-contract-v1.json').read_text())
        names={'document':'document_fields','event':'packet_observation_fields',
               'interval':'interval_fields','gap':'gap_fields','milestone':'milestone_fields',
               'source':'source_fields','evidence':'evidence_fields'}
        for kind,name in names.items(): self.assertEqual(d[name],contract.FIELDS[kind].split())


if __name__ == '__main__': unittest.main()
