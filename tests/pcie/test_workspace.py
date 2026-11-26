from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from test_trace_import import logs, DONE
import pcie_workspace as workspace
import pcie_trace_import as importer
import pcie_navigation_probe as probe
import native_navigation as nav


def fixture(root, complete=False, zero=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    source=root/'來源 空白.PEX';source.write_bytes(b'independent test capture identity')
    work=root/'display-working.pex';work.write_bytes(source.read_bytes());work.chmod(0o444)
    request=dict(source_trace=nav.identity(source),display_trace=nav.identity(source))
    probe.write(root/'request.json',request)
    logs(root,complete)
    if zero:
        (root/'count.txt').write_text('PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none\nPCIE_G1A_SUMMARY|tlp_count=0|first_index=0|first_time=|last_index=0\n'+DONE)
    result=importer.finish_extraction(root,request)
    worker=dict(status=result['status'],before=request,after=request,working_before=nav.identity(work),working_after=nav.identity(work),
                inputs_unchanged=True,working_unchanged=True,scripts_unchanged=True,native_packet_count=120,
                probes=[dict(name=n,finished=dict(result=2),log_sha256=nav.digest(root/(n+'.txt'))) for n in (['count'] if zero else importer.PROBES)])
    probe.write(root/'worker.json',worker)
    return uuid.uuid4().hex


class WorkspaceTests(unittest.TestCase):
    def test_provenance_precision_and_report_share_same_model(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=fixture(root);m=workspace.compose(root,aid)
            self.assertEqual(m['coverage']['tlp_count'],2)
            self.assertEqual(m['coverage']['native_packet_count'],120)
            self.assertEqual(m['coverage']['full_trace_coverage'],'UNKNOWN')
            self.assertEqual(m['candidates'][0]['locator']['packet_index'],100)
            self.assertEqual(m['candidates'][0]['locator']['direction'],'Downstream')
            self.assertIsNone(m['candidates'][0]['start_ns'])
            self.assertEqual(m['sort_mode'],'capture_order')
            self.assertIn('1.000 sec',workspace.markdown(m))
            self.assertIn('Packet 100',workspace.render(m))
            # Frozen-case contamination is about evidence, not incidental hex
            # digits in a freshly generated SHA-256 (which can contain "545").
            self.assertEqual({r['index'] for r in m['candidates'][0]['context']},{100,110})
            self.assertTrue(all(Path(r['path']).resolve().is_relative_to(root.resolve()) for r in m['evidence_refs']))

    def test_zero_and_normal_pair_are_not_pass(self):
        for zero in (False,True):
            with self.subTest(zero=zero),tempfile.TemporaryDirectory() as d:
                root=Path(d);m=workspace.compose(root,fixture(root,complete=True,zero=zero))
                self.assertEqual(m['candidates'],[])
                self.assertIn('不代表 PCIe PASS',workspace.markdown(m))

    def test_wrong_hash_missing_ref_partial_and_out_of_range_rejected(self):
        for defect in ('source','display','raw','missing','partial','range','locator','namespace','receipt'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                root=Path(d);aid=fixture(root)
                if defect=='source':(root/'來源 空白.PEX').write_bytes(b'changed')
                elif defect=='display':
                    p=root/'display-working.pex';p.chmod(0o666);p.write_bytes(b'changed')
                elif defect=='raw':(root/'fields.txt').write_text('changed')
                elif defect=='missing':(root/'report/stages/g3e/groups.json').unlink()
                elif defect in ('partial','range','receipt'):
                    p=root/'worker.json';v=workspace.read(p)
                    if defect=='partial':v['probes'][0]['finished']['result']=1
                    elif defect=='range':v['native_packet_count']=100
                    else:v['before']['display_trace']['sha256']='a'*64
                    probe.write(p,v)
                else:
                    p=root/'analysis.json';v=workspace.read(p)
                    v['locators'][0]['packet_index' if defect=='locator' else 'packet_namespace']=0 if defect=='locator' else 'original'
                    probe.write(p,v)
                with self.assertRaises((ValueError,FileNotFoundError)):workspace.compose(root,aid)

    def test_cross_run_frozen_or_other_directory_references_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';aid=fixture(a);fixture(b)
            # Same bytes, different run: even a matching hash is not authorization
            # to substitute another directory's verified output.
            p=a/'triage-input.json';v=workspace.read(p)
            v['fields']['path']=str(b/'verified-fields/fields.json');probe.write(p,v)
            with self.assertRaises(ValueError):workspace.compose(a,aid)

    def test_unknown_native_count_does_not_enable_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=fixture(root);p=root/'worker.json';v=workspace.read(p);v.pop('native_packet_count');probe.write(p,v)
            m=workspace.compose(root,aid)
            self.assertEqual(m['native_navigation'],'unavailable')
            self.assertIsNone(m['coverage']['native_packet_count'])

    def test_stale_id_tampered_target_and_fake_precision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=workspace.compose(root,fixture(root))
            for defect in ('id','index','time'):
                v=copy.deepcopy(m)
                if defect=='id':v['candidates'][0]['id']='old:F001'
                if defect=='index':v['candidates'][0]['native_targets'][0]['index']=110
                if defect=='time':v['candidates'][0]['start_ns']=1000000000
                with self.assertRaises(ValueError):workspace.validate(v)

    def test_replay_preserves_capture_order_and_all_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=fixture(root)
            first=workspace.compose(root,aid);second=workspace.compose(root,aid)
            self.assertEqual(first,second)
            self.assertEqual(first['displayed_candidates'],[c['id'] for c in first['candidates'][:3]])


if __name__=='__main__':unittest.main()
