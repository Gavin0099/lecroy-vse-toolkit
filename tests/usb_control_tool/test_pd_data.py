"""Minimal native field fixtures from the reviewed PD Capabilities sample."""
import json
import hashlib
import tempfile
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import pd_triage as pd


def raw():
    return dict(format='usb-protocol-data/v1',trace_sha256='a'*64,error='',integrity_unchanged=True,
                script_unchanged=True,native_exited=True,run_result=2,finished_result=2,finished_count=1,
                reports=['PDBASE|110|7|165679376|9|33|2','PDHDR|110|1|1|0|1|1|1|6',
                         'PDBASE|160|7|760863328|9|47|1','PDHDR|160|1|1|0|0|0|1|6',
                         'PDVDM|160|DisplayPort|DP Configure|NAK','PD-END|2|2'])


class PDDataTests(unittest.TestCase):
    def evidence(self, root, header=None, no_transfer=False):
        folder=root/'headers';folder.mkdir()
        body=json.dumps(header or raw()).encode();(folder/'raw-result.json').write_bytes(body)
        exports=[]
        for level,name,kind in [(1,'transactions.csv','Transaction'),(3,'transfers.csv','Transfer')]:
            csv_body=('Rec Chan,'+kind+',Time Stamp,DR,PR,Msg Type,Voltage\nPD,0,7.165679376,DFP,SRC,Source Cap,5.00 V\n').encode()
            (root/name).write_bytes(csv_body)
            exports.append(dict(level=level,file=name,state='no_output' if no_transfer and level==3 else 'returned',identity=dict(sha256=hashlib.sha256(csv_body).hexdigest(),size=len(csv_body))))
        meta=dict(format='pd-native-data/v1',trace_sha256='a'*64,error='',integrity_unchanged=True,native_exited=True,exports=exports,header_raw_sha256=hashlib.sha256(body).hexdigest())
        (root/'raw-result.json').write_text(json.dumps(meta))
    def test_saved_evidence_hashes_and_cable_role_applicability(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);r=raw();r['reports'][1]=r['reports'][1].replace('PDHDR|110|1|','PDHDR|110|2|')
            self.evidence(root,r);d=pd.load(root);row=d['transactions'][0]
            self.assertEqual(row['sop'],"SOP'");self.assertIsNone(row['data_role']);self.assertIsNone(row['power_role'])
            self.assertEqual(pd.cell(row,'PR'),'SRC')
            with (root/'transfers.csv').open('ab') as f:f.write(b'\n')
            with self.assertRaisesRegex(ValueError,'CSV evidence changed'):pd.load(root)
    def test_api_returned_without_output_and_ambiguous_anchor_are_partial(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);r=raw()
            r['reports'][-1:-1]=['PDBASE|111|7|165679376|9|33|2','PDHDR|111|1|1|0|1|1|1|6']
            r['reports'][-1]='PD-END|3|3'
            self.evidence(root,r,True);d=pd.load(root)
            self.assertEqual(d['state'],'partial');self.assertIsNone(d['transactions'][0]['packet_anchor'])
            self.assertEqual(d['transfers'],[])
    def test_reviewed_packet_header_sop_and_vdm_fields(self):
        packets,c=pd.headers(raw())
        self.assertEqual((packets[0]['index'],packets[0]['timestamp_ns'],packets[0]['sop'],packets[0]['object_count']),(110,7165679376,'SOP',1))
        self.assertEqual((packets[1]['index'],packets[1]['timestamp_ns'],packets[1]['vdm']['command_type']),(160,7760863328,'NAK'))
        self.assertFalse(c['headers_truncated'])
    def test_csv_duplicate_fields_preserved_and_ambiguous_values_not_collapsed(self):
        body=b',Rec Chan,Transaction,Msg Type,Voltage,Voltage,Time Stamp,DR,PR\n,PD,0,Source Cap,5.00 V,9.00 V,7.165679376,DFP,SRC\n'
        r=pd.csv_rows(body,1)[0]
        self.assertEqual(pd.cell(r,'Voltage'),None)
        self.assertEqual([v for k,v in r['cells'] if k=='Voltage'],['5.00 V','9.00 V'])
        self.assertEqual(r['timestamp_ns'],7165679376)
    def test_blank_duration_is_unknown_and_native_units_retained(self):
        body=b'Rec Chan,Transfer,Time Stamp,Time,DP Configure,Status,Max Cur,Voltage\nPD,8,7.759134390,,DP Configure,NAKed,0.90 A,5.00 V\n'
        r=pd.csv_rows(body,3)[0]
        self.assertIsNone(r['duration_display']);self.assertEqual(pd.cell(r,'Max Cur'),'0.90 A');self.assertEqual(r['status'],'NAKed')
    def test_malformed_missing_end_wrong_fields_and_truncated_csv_fail(self):
        for reports in [raw()['reports'][:-1],raw()['reports']+['PD-END|2|2'],
                        [r for r in raw()['reports'] if not r.startswith('PDHDR|110|')],
                        ['PDHDR|110|1|1|0|1|1|1|6','PD-END|1|1']]:
            r=raw();r['reports']=reports
            with self.assertRaises(ValueError):pd.headers(r)
        for body in [b'Transfer,Time Stamp\n0,7.1\n', b'Rec Chan,Transfer,Time Stamp\nPD,8\n',
                     b'Rec Chan,Transfer,Time Stamp\nPD,8,7.0\nPD,8,7.0\n']:
            with self.assertRaises(ValueError):pd.csv_rows(body,3)
        for value in ['NaN','Infinity','-1','0.0000000001']:
            with self.assertRaises(ValueError):pd.ns(value)


if __name__=='__main__':unittest.main()
