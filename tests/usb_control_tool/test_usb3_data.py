"""Native field fixtures reviewed against U02/U03 outputs and GUI anchors."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb3_triage as u3


def raw(rows=None, summary='USB3-END|3174690|3174689|1|1|1|1|1|1|0|0|1|22|0'):
    return dict(format='usb-protocol-data/v1',trace_sha256='f'*64,error='',integrity_unchanged=True,
                script_unchanged=True,native_exited=True,run_result=2,finished_result=2,finished_count=1,
                reports=(rows if rows is not None else [
                    'U02|8|0|67664|6|5|27|11|4|11|4|LGOOD_11|SSP',
                    'U03|629253|13|897383272|5|4|71|1873296|0|1873296|0|0|LFPS_WAKE_U3|SS',
                    'U3LT|8|0|67664|6|5'])+[summary])


class DataTests(unittest.TestCase):
    def test_reviewed_packet_and_duration_anchors(self):
        d=u3.normalize(raw());link=next(e for e in d['events'] if e['kind']=='LINK_CMD');lf=next(e for e in d['events'] if e['kind']=='LFPS')
        self.assertEqual((link['index'],link['timestamp_ns'],link['name'],link['info_raw'],link['crc5_raw']),(8,67664,'LGOOD_11',11,4))
        self.assertEqual((lf['index'],lf['timestamp_ns'],lf['duration_ns']),(629253,13897383272,1873296))
        self.assertEqual(d['state'],'analyzed');self.assertFalse(d['coverage']['truncated'])
        self.assertFalse(any('state' in e for e in d['events']))
    def test_zero_selected_on_usb2_only_is_not_pass(self):
        d=u3.normalize(raw([], 'USB3-END|100|0|0|0|0|0|0|0|0|0|0|1|0'))
        self.assertEqual(d['state'],'not_observed');self.assertEqual(d['events'],[])
        self.assertFalse(d['coverage']['capture_end_known'])
        speed_only=u3.normalize(raw([], 'USB3-END|162|1|0|0|0|0|0|0|0|52|109|7|0'))
        self.assertEqual(speed_only['state'],'not_observed')
        self.assertEqual(speed_only['coverage']['pd_packet_events'],52)
    def test_output_cap_and_unknown_mode_stay_partial(self):
        d=u3.normalize(raw(summary='USB3-END|3174690|3174689|100|20|1|1|1|1|1|0|1|22|0'))
        self.assertEqual(d['state'],'partial');self.assertTrue(d['coverage']['truncated'])
        self.assertEqual(d['coverage']['link_total'],100);self.assertEqual(d['coverage']['emitted_link'],1)
    def test_malformed_count_duplicate_truncated_and_error_not_success(self):
        cases=[]
        r=raw();r['reports'].pop();cases.append(r)
        r=raw();r['reports'].append(r['reports'][-1]);cases.append(r)
        r=raw();r['reports'][0]=r['reports'][0].replace('|67664|','|1000000000|');cases.append(r)
        r=raw();r['reports'].insert(0,r['reports'][0]);cases.append(r)
        r=raw();r['native_exited']=False;cases.append(r)
        r=raw();r['error']='native failure';cases.append(r)
        for r in cases:
            with self.assertRaises(ValueError):u3.normalize(r)
    def test_filename_and_marker_are_not_inputs_to_normalization(self):
        a=raw();b=copy.deepcopy(a);b.update(source='FAIL_known_time.usb',engineer_marker=13897383272)
        self.assertEqual(u3.normalize(a),u3.normalize(b))


if __name__=='__main__':unittest.main()
