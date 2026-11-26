from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import pcie_phase_evidence as phase
import pcie_event_coverage as coverage

# Synthetic wire fixture, with independently chosen constant values; the parser
# must consume the recorded native mapping instead of assuming numeric enums.
VALUES = dict(CHANNEL_1=1,CHANNEL_2=2,LINK_DOWN=1,LINK_UP=2,
              DETECT=10,POLLING=11,CONFIG=12,L0=13,RECOVERY=14,HOT_RESET=15,DISABLED=16,UNDEFINED=255)


def log(rows=None):
    if rows is None:
        rows=[('LINK',10,'1','Upstream','1','LINK_CONDITION'),
              ('LTSSM',11,'1','Upstream','11,255,1,255,packet','LTSSM_CHANGE'),
              ('LTSSM',20,'2','Downstream','13,255,1,255,packet','LTSSM_CHANGE')]
    result=[phase.HEADER]+['PCIE_PHASE_CONST|'+k+'|'+str(v) for k,v in VALUES.items()]
    for family,index,ch,direction,data,counter in rows:
        result.append(f'PCIE_PHASE_ROW|{family}|{index}|1.000 sec|{ch}|{direction}|1|123|456|{data}')
    for name in phase.NAMES:
        matching=[r[1] for r in rows if r[-1]==name]
        result.append(f'PCIE_PHASE_COUNT|{name}|{len(matching)}|{min(matching) if matching else 0}|{max(matching) if matching else 0}')
    return '\n'.join(result+['PCIE_PHASE_END|reason=trace_end',phase.DONE])


class PhaseEvidenceTests(unittest.TestCase):
    def test_settings_native_readback_and_script_error(self):
        text=log().replace(phase.HEADER,phase.HEADER+'\nPCIE_PHASE_SETTINGS|nfm_ignore_errors|63')
        settings=phase.parse(text,100)['ltssm_ignore_settings']
        self.assertEqual(settings['nfm_ignore_errors'],63)
        self.assertEqual(settings['ignored_error_classes'],['TS','FTS','EIEOS','DLLP','TLP','EIOS'])
        self.assertEqual(settings['gui_equivalence'],'NOT_ESTABLISHED')
        self.assertEqual(phase.parse(log(),100)['ltssm_ignore_settings'],'UNKNOWN_NATIVE_DEFAULT')
        for bad in (text.replace('errors|63','errors|64'),text.replace('errors|63','errors|63\nPCIE_PHASE_SETTINGS|nfm_ignore_errors|31'),text+'\n***ERROR***: No channels found to be sent.'):
            with self.assertRaises(ValueError):phase.parse(bad,100)

    def test_native_precision_kept_and_raw_link_not_promoted(self):
        data=phase.parse(log(),100)
        self.assertEqual(data['events'][0]['constant_name'],'LINK_DOWN')
        self.assertEqual(data['events'][0]['semantic_status'],'RAW_CONSTANT_ONLY')
        self.assertEqual(data['events'][1]['state_name'],'POLLING')
        self.assertEqual(data['events'][1]['time_object'],[1,123,456])
        self.assertEqual(data['events'][1]['time_display'],'1.000 sec')
        self.assertEqual(data['events'][2]['direction'],'Downstream')

    def test_invalid_and_unknown_channel_remain_observations(self):
        text=log([('LTSSM',9,'9','Channel 9','13,255,0,255,packet','LTSSM_CHANGE')])
        row=phase.parse(text,100)['events'][0]
        self.assertEqual(row['valid'],0)
        self.assertEqual(row['direction'],'UNKNOWN')
        self.assertEqual(row['link_identity'],'UNKNOWN')

    def test_missing_done_duplicate_wrong_order_partial_bad_time_rejected(self):
        valid=log()
        variants=[valid.replace(phase.DONE,''),valid.replace('PCIE_PHASE_COUNT|TLP|0|0|0',''),
                  valid.replace('PCIE_PHASE_COUNT|LTSSM_CHANGE|2','PCIE_PHASE_COUNT|LTSSM_CHANGE|3'),
                  valid.replace('|20|1.000 sec','|5|1.000 sec'),
                  valid.replace('|1|123|456|','|1|1000000000|456|'),
                  valid.replace('|1|123|456|','|1|123|1000|'),valid+'\nPCIE_PHASE_END|reason=trace_end']
        for text in variants:
            with self.subTest(text=text[-70:]),self.assertRaises(ValueError): phase.parse(text,100)
        row=('LTSSM',11,'1','Upstream','13,255,1,255,packet','LTSSM_CHANGE')
        with self.assertRaises(ValueError):phase.parse(log([row,row]),100)
        with self.assertRaises(ValueError):phase.parse(valid,20)

    def test_idle_and_packet_state_same_index_are_distinct(self):
        rows=[('LTSSM',11,'1','Upstream','11,255,1,255,idle','LTSSM_CHANGE'),
              ('LTSSM',11,'1','Upstream','13,255,1,255,packet','LTSSM_CHANGE')]
        self.assertEqual(len(phase.parse(log(rows),100)['events']),2)

    def test_bound_log_coverage_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'phase.txt';path.write_text(log(),encoding='utf-8')
            binding=coverage.identity(uuid.uuid4().hex,'a'*64,'b'*64,'13.26.0.43')
            receipt=dict(log_sha256=coverage.digest(path),finished=dict(result=2))
            data=phase.load(d,receipt,binding,100)
            self.assertEqual(data['events'][0]['display_trace_sha256'],'b'*64)
            self.assertGreater(data['events'][0]['evidence_ref']['line'],1)
            self.assertTrue(all(c['full_trace_coverage']=='UNKNOWN' for c in data['coverage']))
            self.assertEqual(data['coverage'][0]['event_level_completeness'],'OBSERVATION_COMPLETE_IN_DECLARED_SCOPE')
            path.write_text(log().replace('|11|1.000 sec','|12|1.000 sec'))
            with self.assertRaises(ValueError):phase.load(d,receipt,binding,100)

    def test_link_mapping_is_qualified_by_version_and_recorded_constants(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'phase.txt'
            for version,expected in [('13.26.0.43','VERSION_MAPPING_VERIFIED'),('13.40.0.1','RAW_CONSTANT_ONLY')]:
                path.write_text(log(),encoding='utf-8')
                binding=coverage.identity(uuid.uuid4().hex,'a'*64,'b'*64,version)
                receipt=dict(log_sha256=coverage.digest(path),finished=dict(result=2))
                self.assertEqual(phase.load(d,receipt,binding,100)['events'][0]['semantic_status'],expected)
            path.write_text(log().replace('PCIE_PHASE_CONST|LINK_DOWN|1','PCIE_PHASE_CONST|LINK_DOWN|3'),encoding='utf-8')
            binding=coverage.identity(uuid.uuid4().hex,'a'*64,'b'*64,'13.26.0.43')
            receipt=dict(log_sha256=coverage.digest(path),finished=dict(result=2))
            self.assertNotEqual(phase.load(d,receipt,binding,100)['events'][0]['semantic_status'],'VERSION_MAPPING_VERIFIED')


if __name__=='__main__':unittest.main()
