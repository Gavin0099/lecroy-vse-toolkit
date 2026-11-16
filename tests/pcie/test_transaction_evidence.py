from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import pcie_transaction_evidence as tx
import pcie_event_coverage as coverage

# Reviewed wire fixture: packet indices and Link/Split indices are distinct.
CONSTANTS=dict(packet=0,link=1,split=4,CHANNEL_1=1,CHANNEL_2=2,
               CFGRD0=9,CFGWR0=10,CFGRD1=11,CFGWR1=12,CPL=17,CPLD=18)

def row(ns='packet',index=10,ns_time=100,target=256,tag=4,psn=99,status='NA',channel=2):
    return f'PCIE_TX_ROW|{ns}|{index}|1.000 sec|{channel}|Downstream|1|{ns_time}|0|9|0|{tag}|{target}|248|{psn}|{status}|1|2'

def log(rows=None):
    rows=rows if rows is not None else [row(),row('link',1),row('split',0,status=0)]
    lines=[tx.HEADER]+[f'PCIE_TX_CONST|{k}|{v}' for k,v in CONSTANTS.items()]+rows
    for ns in tx.LEVELS:
        indices=[int(r.split('|')[2]) for r in rows if r.split('|')[1]==ns]
        lines.append(f'PCIE_TX_COUNT|{ns}|{len(indices)}|{indices[0] if indices else 0}|{indices[-1] if indices else 0}')
    return '\n'.join(lines+['PCIE_TX_END|reason=trace_end',tx.DONE])


class TransactionTests(unittest.TestCase):
    def test_typed_native_start_uses_time_identity_not_transaction_index(self):
        result=tx.crosscheck(tx.parse(log(),100))
        self.assertEqual([r['packet_index'] for r in result['native_starts']],[10,10])
        self.assertEqual([r['native_index'] for r in result['native_starts']],[1,0])
        self.assertEqual(result['native_starts'][1]['completion_label'],'SC')
        self.assertEqual(result['native_starts'][1]['child_packet_mapping'],'NOT_ESTABLISHED')

    def test_unknown_direction_time_and_ambiguous_identity_cannot_map(self):
        for rows in ([row(channel=9),row('link',1,channel=9)],
                     [row(),row('link',1).replace('|1|100|0|9|','|1|100|NA|9|')],
                     [row(),row(index=11),row('link',1)]):
            result=tx.crosscheck(tx.parse(log(rows),100))['native_starts'][0]
            self.assertIsNone(result['packet_index'])
            self.assertNotEqual(result['mapping'],'EXACT_TYPED_START')

    def test_similarity_keeps_target_and_psn_distinct_from_retry(self):
        rows=[row(),row(index=11,ns_time=120),row(index=12,ns_time=140,target=512)]
        result=tx.crosscheck(tx.parse(log(rows),100))['request_similarities']
        self.assertEqual([r['observation'] for r in result],['SAME_KEY_SAME_CONFIG_TARGET','SAME_KEY_DIFFERENT_OR_UNKNOWN_TARGET'])
        self.assertTrue(result[0]['same_psn'])
        self.assertTrue(all(r['interpretation']=='OBSERVATION_ONLY' for r in result))

    def test_link_boundary_partitions_tag_reuse(self):
        result=tx.parse(log([row(),row(index=20,ns_time=200)]),100)
        phase=dict(events=[dict(packet_index=15,semantic_status='VERSION_MAPPING_VERIFIED',semantic='LINK_DOWN')])
        self.assertEqual(tx.crosscheck(result,phase)['request_similarities'],[])

    def test_completion_status_is_reported_without_failure_verdict(self):
        for status,label in [(0,'SC'),(1,'UR'),(2,'CRS'),(4,'CA'),(7,'UNKNOWN')]:
            result=tx.crosscheck(tx.parse(log([row(),row('split',0,status=status)]),100))
            self.assertEqual(result['native_starts'][0]['completion_label'],label)
            self.assertNotIn('fault',result)

    def test_malformed_duplicate_out_of_range_and_partial_logs_rejected(self):
        source=log()
        variants=[source.replace(tx.DONE,''),source+ '\nPCIE_TX_END|reason=trace_end',
                  source.replace('|100|0|9|','|1000000000|0|9|'),
                  source.replace('PCIE_TX_COUNT|packet|1|10|10','PCIE_TX_COUNT|packet|2|10|10'),
                  log([row(),row()]),source.replace('CHANNEL_2|2','CHANNEL_2|1')]
        for value in variants:
            with self.subTest(value=value[-70:]),self.assertRaises(ValueError):tx.parse(value,100)
        with self.assertRaises(ValueError):tx.parse(source,10)

    def test_receipt_bound_source_and_cap_scope(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'transactions.txt';path.write_text(log(),encoding='utf-8')
            binding=coverage.identity(uuid.uuid4().hex,'a'*64,'b'*64,'13.26.0.43')
            receipt=dict(log_sha256=coverage.digest(path),finished=dict(result=2))
            result=tx.load(d,receipt,binding,100)
            self.assertEqual(result['rows'][0]['packet_namespace'],'converted_trace_packet_zero_based')
            self.assertEqual(result['coverage'][2]['native_index_namespace'],'split')
            self.assertTrue(all(r['full_trace_coverage']=='UNKNOWN' for r in result['coverage']))
            path.write_text(log([row(index=11)]),encoding='utf-8')
            with self.assertRaises(ValueError):tx.load(d,receipt,binding,100)

    def test_g2_agreement_normalizes_only_display_padding(self):
        result=tx.parse(log([row().replace('|1.000 sec|','| 1.000 sec|')]),100)
        fields=[dict(packet_index=10,tlp_type_hex='0x9',channel='Downstream',time_display='1.000 sec',requester_id=0,tag=4,compl_status=None)]
        tx.validate_against_fields(result,fields)
        fields[0]['tag']=5
        with self.assertRaises(ValueError):tx.validate_against_fields(result,fields)


if __name__=='__main__':unittest.main()
