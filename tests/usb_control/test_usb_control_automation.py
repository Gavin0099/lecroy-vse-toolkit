"""API-only CSV is partial evidence; absent fields must stay unknown."""
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb_control_automation as adapter
import usb_control_triage as engine


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.csv=self.root/'transfers.csv'
        self.row={'Transfer':'3','Sp':'H','Control':'Control:GET','Ad':'5','Ep':'0',
                  'bRequest':'GET_DESCRIPTOR','wValue':'CONFIGURATION type, Index 0',
                  'wIndex':'0x0000','Time Stamp':'12.345678901','Cplt':'NO','Marker':'FAIL answer',
                  'wLength':'','Not Enough Data':'0 bytes'}

    def write(self,rows):
        with self.csv.open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(self.row));writer.writeheader();writer.writerows(rows)
        m={'adapter':'native_transfer_csv','automation_completed':True,'error':'','trace_sha256':'a'*64,
           'csv_sha256':hashlib.sha256(self.csv.read_bytes()).hexdigest(),
           'integrity':dict(source_unchanged=True,working_copy_unchanged=True,working_copy_readonly=True)}
        path=self.root/'raw-result.json';path.write_text(json.dumps(m),encoding='utf-8');return path

    def test_partial_csv_uses_same_engine_and_does_not_invent_payload(self):
        d=adapter.csv_projection(self.write([self.row]));e=d['events'][0]
        self.assertIsNone(e['data_length']);self.assertIsNone(e['requested_length'])
        self.assertIsNone(e['halted']);self.assertIsNone(e['duration_ns'])
        self.assertEqual(e['timestamp_ns'],12_345_678_901)
        self.assertEqual(e['value'],512)
        c=engine.discover(d)['candidates'][0]
        self.assertEqual(c['transfer_indices'],[3]);self.assertIn('確認有無 DATA',c['next_step'])
        self.assertIn('未知',engine.render(engine.discover(d)))

    def test_blank_completion_and_shortage_flag_are_not_completed_or_failed(self):
        row=dict(self.row,Cplt='')
        d=adapter.csv_projection(self.write([row]))
        self.assertIsNone(d['events'][0]['completed'])
        self.assertEqual(engine.discover(d)['candidates'],[])

    def test_marker_and_filename_do_not_affect_projection(self):
        a=adapter.csv_projection(self.write([self.row]))
        b=adapter.csv_projection(self.write([dict(self.row,Marker='PASS new annotation')]))
        self.assertEqual(engine.discover(a),engine.discover(b))

    def test_malformed_duplicate_and_tampered_csv_fail_closed(self):
        for rows in [[self.row,self.row],[dict(self.row,**{'Time Stamp':'12.1234567891'})]]:
            with self.assertRaises(engine.InputError):adapter.csv_projection(self.write(rows))
        m=self.write([self.row]);self.csv.write_text('bad header\n',encoding='utf-8')
        with self.assertRaises(engine.InputError):adapter.csv_projection(m)

    def test_unsupported_class_request_is_not_misclassified_as_standard(self):
        d=adapter.csv_projection(self.write([dict(self.row,bRequest='0x06',wValue='0x2900')]))
        self.assertIsNone(d['events'][0]['request_type'])
        self.assertEqual(engine.discover(d)['candidates'],[])


if __name__=='__main__':unittest.main()
