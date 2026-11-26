from pathlib import Path
import json
import sys
import tempfile
import unittest
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pcie'))
import pcie_detail_windows as detail
import native_navigation as nav

class Exporter:
    def __init__(self,work,missing=False,fail=False):self.work=work;self.missing=missing;self.fail=fail
    def ExportToText(self,path,first,last):
        if self.fail:raise RuntimeError('native timeout')
        rows=[first] if self.missing else range(first,last+1)
        text=f' File {self.work}.\n From Packet #{first} to Packet #{last}.\n'
        text+=''.join(f'Packet({i}) Downstream CfgRd0\nTime Stamp(0009.512236870000s)\n' for i in rows)
        Path(path).write_text(text,encoding='utf-8')

class DetailTests(unittest.TestCase):
    def test_windows_dynamic_merge_clamp_and_limit(self):
        loc=[{'packet_index':i} for i in (4,30,80,190)]
        last={'last_supported_milestone':{'anchor':{'packet_index':195}}}
        windows=detail.propose(loc,last,200)
        self.assertEqual([(w['first'],w['last']) for w in windows],[(0,62),(64,112),(179,199)])
        self.assertNotIn(190,[a['packet_index'] for w in windows for a in w['anchors']])
        self.assertEqual(detail.propose([],None,0),[])
        for i in (-1,200,True):
            with self.assertRaises(ValueError):detail.propose([{'packet_index':i}],None,200)

    def test_native_binding_tamper_and_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);work=root/'display-working.pex';work.write_bytes(b'fixture')
            windows=detail.propose([{'packet_index':20}],None,80)
            binding=dict(source_trace_sha256='a'*64,display_trace_sha256=nav.digest(work),packet_namespace='display-working')
            data=detail.acquire(Exporter(work),root,work,binding,windows)
            def save():
                p=root/'detail-windows.json';p.write_text(json.dumps(data),encoding='utf-8')
                return dict(sha256=nav.digest(p),status=data['status'],packet_count=data['packet_count'])
            receipt=save();loaded=detail.load(root,receipt,binding,windows)
            self.assertEqual(loaded['packet_count'],49)
            self.assertEqual(Decimal(loaded['windows'][0]['rows'][0]['timestamp_picoseconds']),Decimal('9512236870000'))
            for change in ('count','row','missing','coverage'):
                modified=json.loads(json.dumps(data))
                if change=='count':data['packet_count']+=1
                if change=='row':data['windows'][0]['rows'][0]['packet_index']=5
                if change=='missing':data['windows'][0]['missing_anchors']=[20]
                if change=='coverage':data['full_trace_coverage']='COMPLETE'
                with self.assertRaises(ValueError):detail.load(root,save(),binding,windows)
                data=modified
            receipt=save()
            with self.assertRaises(ValueError):detail.load(root,receipt,dict(binding,source_trace_sha256='b'*64),windows)
            (root/'detail-window-0.txt').write_text('tampered',encoding='utf-8')
            with self.assertRaises(ValueError):detail.load(root,receipt,binding,windows)

    def test_missing_anchor_and_export_failure_are_explicit_partial(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/'display-working.pex';windows=detail.propose([{'packet_index':20}],None,80)
            for exporter in (Exporter(work,missing=True),Exporter(work,fail=True)):
                data=detail.acquire(exporter,d,work,{},windows)
                self.assertEqual(data['status'],'partial')
                self.assertNotEqual(data['windows'][0]['status'],'complete')
            with self.assertRaises(InterruptedError):detail.acquire(Exporter(work),d,work,{},windows,lambda:True)

    def test_wrong_file_range_duplicate_and_outside_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)/'display-working.pex';path=Path(d)/'out.txt';window=dict(first=2,last=4)
            Exporter(work).ExportToText(path,2,4);text=path.read_text()
            for altered in (text.replace(str(work),str(work.with_name('other.pex'))),text.replace('to Packet #4','to Packet #5'),text.replace('Packet(3)','Packet(2)'),text.replace('Packet(4)','Packet(9)')):
                with self.assertRaises(ValueError):detail.parse(altered,work,window)
            self.assertEqual(detail.parse(text.replace('Time Stamp','unavailable'),work,window)[0]['timestamp_seconds'],None)

if __name__=='__main__':unittest.main()
