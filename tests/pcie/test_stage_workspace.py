from pathlib import Path
import tempfile
import unittest

from test_workspace import fixture,workspace,probe
from test_phase_evidence import log as phase_log
from test_transaction_evidence import log as tx_log,row as tx_row


def stage_fixture(root,zero=False):
    aid=fixture(root,zero=zero)
    request=workspace.read(root/'request.json');request['extraction_profile']='stage-v1';probe.write(root/'request.json',request)
    worker=workspace.read(root/'worker.json');worker['extraction_profile']='stage-v1'
    worker['capabilities']=dict(file_version='13.26.0.43')
    text=phase_log()
    if not zero:text=text.replace('PCIE_PHASE_COUNT|TLP|0|0|0','PCIE_PHASE_COUNT|TLP|2|100|110')
    (root/'phase.txt').write_text(text,encoding='utf-8')
    rows=[] if zero else [tx_row(index=100,tag=3),tx_row(index=110,ns_time=200,tag=3).replace('1.000 sec','1.001 sec')]
    (root/'transactions.txt').write_text(tx_log(rows),encoding='utf-8')
    for name in ('phase','transactions'):
        worker['probes'].append(dict(name=name,finished=dict(result=2),log_sha256=workspace.nav.digest(root/(name+'.txt'))))
    probe.write(root/'worker.json',worker)
    return aid


class StageWorkspaceTests(unittest.TestCase):
    def test_stage_and_legacy_candidates_share_current_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=workspace.compose(root,stage_fixture(root))
            self.assertEqual(m['candidates'][0]['locator']['packet_index'],100)
            self.assertEqual(m['stage_summary']['last_supported_milestone']['anchor']['packet_index'],110)
            self.assertEqual(m['stage_summary']['source_trace_sha256'],m['trace_sha256'])
            self.assertEqual(len(m['coverage']['event_families']),12)
            self.assertEqual(len(m['transaction_crosscheck']['request_similarities']),1)
            self.assertEqual(m['observations'][0]['native_targets'][0]['index'],110)
            self.assertEqual(m['observations'][0]['locator']['source_trace_sha256'],m['trace_sha256'])
            self.assertEqual(m['candidate_count_total'],1)

    def test_zero_tlp_still_keeps_link_and_l0_observations(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=workspace.compose(root,stage_fixture(root,True))
            self.assertEqual(m['candidate_count_total'],0)
            self.assertEqual(m['stage_summary']['last_supported_milestone']['kind'],'DIRECTION_L0_OBSERVED')
            self.assertEqual(m['coverage']['full_trace_coverage'],'UNKNOWN')
            self.assertEqual(m['observations'][0]['native_targets'][0]['index'],20)
            m['observations'][0]['native_targets'][0]['index']=21
            with self.assertRaises(ValueError):workspace.validate(m)

    def test_detail_rows_are_bound_deduplicated_and_available_for_last_stage(self):
        import pcie_detail_windows as detail
        from test_detail_windows import Exporter
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=stage_fixture(root);m=workspace.compose(root,aid)
            windows=detail.propose(workspace.read(root/'analysis.json')['locators'],m['stage_summary'],m['coverage']['native_packet_count'])
            binding={k:m[k] for k in ('source_trace_sha256','display_trace_sha256','packet_namespace')}
            data=detail.acquire(Exporter(root/'display-working.pex'),root,root/'display-working.pex',binding,windows)
            probe.write(root/'detail-windows.json',data)
            request=workspace.read(root/'request.json');request['detail_windows']=True;probe.write(root/'request.json',request)
            worker=workspace.read(root/'worker.json');worker['native_details']=dict(sha256=workspace.nav.digest(root/'detail-windows.json'),status=data['status'],packet_count=data['packet_count']);probe.write(root/'worker.json',worker)
            m=workspace.compose(root,aid)
            rows=m['candidates'][0]['context'];indices=[r['index'] for r in rows]
            self.assertEqual(indices,sorted(set(indices)))
            self.assertIn('native_evidence_ref',next(r for r in rows if r['index']==100))
            self.assertTrue(m['observations'][0]['context'])
            self.assertIn('原生區間明細',workspace.render(m))
            (root/'detail-window-0.txt').write_text('wrong',encoding='utf-8')
            with self.assertRaises(ValueError):workspace.compose(root,aid)

    def test_missing_wrong_hash_profile_partial_and_contradictory_logs_rejected(self):
        for defect in ('missing','hash','profile','partial','counter','field'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                root=Path(d);aid=stage_fixture(root);worker=workspace.read(root/'worker.json')
                if defect=='missing':(root/'phase.txt').unlink()
                elif defect=='hash':(root/'phase.txt').write_text('wrong')
                elif defect=='profile':worker['extraction_profile']='tlp-v1'
                elif defect=='partial':worker['probes'][-1]['finished']['result']=1
                elif defect=='counter':
                    path=root/'phase.txt';path.write_text(path.read_text().replace('|TLP|2|100|110','|TLP|3|100|110'))
                    worker['probes'][-2]['log_sha256']=workspace.nav.digest(path)
                else:
                    path=root/'transactions.txt';path.write_text(path.read_text().replace('|9|0|3|','|9|0|7|'))
                    worker['probes'][-1]['log_sha256']=workspace.nav.digest(path)
                probe.write(root/'worker.json',worker)
                with self.assertRaises((ValueError,FileNotFoundError)):workspace.compose(root,aid)


if __name__=='__main__':unittest.main()
