"""Paging preserves every source item and publishes no oversized generation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
import pcie_ui_pages as pages
import pcie_large_io as large
import pcie_model_storage as storage
import pcie_model_worker
from test_stage_workspace import stage_fixture, workspace
from test_phase_evidence import log as phase_log


class PageTests(unittest.TestCase):
    def test_all_items_once_and_primary_first_without_mutating_evidence(self):
        model=dict(analysis_id="a"*32, candidates=[dict(rank=i) for i in range(47)],
                   observations=[], flow_items=[dict(scenario_id=str(i),rank=i) for i in range(53)],
                   flow_analysis=dict(displayed_scenarios=["52","51","50"],
                     scenarios=[dict(scenario_id=str(i),fact="原始證據") for i in range(53)]))
        before=copy.deepcopy(model)
        with tempfile.TemporaryDirectory() as d:
            index=pages.write(d,model)
            for group in ("candidates","flow_items","observations"):
                values=[]
                for name in index["groups"][group]["pages"]:
                    path=Path(d)/name
                    self.assertLessEqual(path.stat().st_size,pages.MAX_BYTES)
                    page=json.loads(path.read_text(encoding="utf-8"))
                    self.assertLessEqual(len(page[group]),20)
                    values+=page[group]
                self.assertCountEqual(values,model[group])
            first=json.loads((Path(d)/index["groups"]["flow_items"]["pages"][0]).read_text(encoding="utf-8"))
            self.assertEqual([r["scenario_id"] for r in first["flow_items"][:3]],["52","51","50"])
            self.assertEqual(model,before)

    def test_failed_new_generation_preserves_previous_index(self):
        with tempfile.TemporaryDirectory() as d:
            m=dict(analysis_id="b"*32,candidates=[],flow_items=[],observations=[])
            pages.write(d,m);index=(Path(d)/"ui-index.json").read_bytes()
            m["candidates"]=[dict(evidence="x"*(pages.MAX_BYTES+1))]
            with self.assertRaises(ValueError):pages.write(d,m)
            self.assertEqual((Path(d)/"ui-index.json").read_bytes(),index)

    def test_model_writer_size_limit_is_not_a_published_result(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"model.json"
            with self.assertRaises(large.ResourceLimit):large.write_json_bounded(path,{"proof":"漢"*100},10)
            self.assertFalse(path.exists());self.assertTrue(path.with_name(path.name+".partial").exists())

    def test_real_offline_worker_matches_independent_in_process_model(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=stage_fixture(root)
            expected=workspace.compose(root,aid)
            actual=pcie_model_worker.compose(root,aid)
            self.assertEqual(actual,expected)
            self.assertTrue((root/"model-resources.jsonl").read_text().strip())
            self.assertFalse((root/"model-handoff").exists())

    def test_real_worker_low_tlp_many_flow_scenarios_spill_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);aid=stage_fixture(root)
            first_packet=120
            count=350
            rows=[]
            for packet in range(first_packet,first_packet+count*2,2):
                rows.append(('LINK',packet,'1','Upstream','1','LINK_CONDITION'))
                rows.append(('LTSSM',packet+1,'1','Upstream','13,255,1,255,packet','LTSSM_CHANGE'))
            path=root/'phase.txt'
            path.write_text(phase_log(rows).replace('|TLP|0|0|0','|TLP|2|100|110'),encoding='utf-8')
            worker=workspace.read(root/'worker.json')
            worker['native_packet_count']=first_packet+count*2
            next(p for p in worker['probes'] if p['name']=='phase')['log_sha256']=workspace.nav.digest(path)
            (root/'worker.json').write_text(json.dumps(worker),encoding='utf-8')

            expected=workspace.compose(root,aid)
            self.assertGreater(len(pages.encoded(expected)),large.DEFAULTS['max_model_bytes'])
            actual=pcie_model_worker.compose(root,aid)
            self.assertEqual(actual,expected)
            self.assertEqual(actual['coverage']['tlp_count'],2)
            self.assertSetEqual({item['locator']['packet_index'] for item in actual['flow_items']
                                 if item['locator']['direction']=='Upstream'},
                                set(range(first_packet+1,first_packet+count*2,2)))
            self.assertFalse((root/'disk-index.json').exists())
            manifest=root/pcie_model_worker.MODEL_NAME
            self.assertLessEqual(manifest.stat().st_size,large.DEFAULTS['max_model_bytes'])
            self.assertFalse(manifest.with_suffix('.json.partial').exists())
            self.assertIn('worker_handoff',workspace.read(manifest))
            self.assertNotIn('worker_handoff',actual)

    def test_flow_handoff_rejects_incomplete_modified_or_other_job_attachment(self):
        model=dict(analysis_id='a'*32,source_trace_sha256='b'*64,display_trace_sha256='c'*64,
                   flow_analysis=dict(scenarios=[{'text':'場'*900}]),flow_items=[{'text':'觀'*900}])
        for defect in ('missing', 'content', 'other_job', 'size', 'incomplete'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                root=Path(d)
                with patch.dict(large.DEFAULTS,max_model_bytes=1024):
                    pcie_model_worker.write_model(root,model)
                attachment=root/'model-handoff/items.json'
                path=root/pcie_model_worker.MODEL_NAME
                manifest=workspace.read(path)
                refs=manifest['worker_handoff']['refs']
                if defect=='missing':
                    attachment.unlink()
                elif defect=='content':
                    attachment.write_bytes(attachment.read_bytes().replace('觀'.encode(), '文'.encode(), 1))
                elif defect=='other_job':
                    value=workspace.read(attachment)
                    value['binding']['analysis_id']='d'*32
                    attachment.write_bytes(pages.encoded(value))
                    refs['items.json']['sha256']=workspace.nav.digest(attachment)
                elif defect=='size':
                    refs['items.json']['bytes']=pcie_model_worker.FLOW_BUDGET+1
                else:
                    del refs['items.json']
                path.write_bytes(pages.encoded(manifest))
                error={'missing':FileNotFoundError,'size':large.ResourceLimit}.get(defect,ValueError)
                with self.assertRaises(error):
                    pcie_model_worker.read_model(root,model['analysis_id'],1024)

    def test_flow_handoff_preserves_existing_external_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            model=dict(analysis_id='a'*32,source_trace_sha256='b'*64,display_trace_sha256='c'*64,
                       display_trace_path=str(root/'display-working.pex'),limitations=[],
                       flow_analysis=dict(scenarios=[{'text':'場'*900}]),flow_items=[{'text':'觀'*900}],
                       stage_summary=dict(events=[{'packet_index':1}]))
            packed=storage.pack(model,root)
            with patch.dict(large.DEFAULTS,max_model_bytes=2048):
                pcie_model_worker.write_model(root,packed)
            actual=pcie_model_worker.read_model(root,model['analysis_id'],2048)
            self.assertEqual(actual,packed)
            self.assertEqual(storage.expand(actual)['stage_summary'],model['stage_summary'])

    def test_flow_handoff_total_budget_refusal_does_not_publish_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            model=dict(analysis_id='a'*32,source_trace_sha256='b'*64,display_trace_sha256='c'*64,
                       flow_analysis=dict(scenarios=[{'text':'場'*900}]),flow_items=[{'text':'觀'*900}])
            # Each attachment is smaller than this budget. Together they are over it.
            with patch.dict(large.DEFAULTS,max_model_bytes=1024), patch.object(pcie_model_worker,'FLOW_BUDGET',4000):
                with self.assertRaises(large.ResourceLimit):
                    pcie_model_worker.write_model(root,model)
            self.assertTrue((root/'model-handoff/scenarios.json').is_file())
            self.assertFalse((root/pcie_model_worker.MODEL_NAME).exists())

    def test_model_worker_cancel_and_memory_refusal_publish_nothing(self):
        for mode in ("cancel","memory"):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d);aid=stage_fixture(root);cancel=threading.Event()
                if mode=="cancel":cancel.set()
                with patch.object(pcie_model_worker.resources,"sample",return_value={"private_commit_bytes":10**12}):
                    with self.assertRaises(InterruptedError if mode=="cancel" else large.ResourceLimit):
                        pcie_model_worker.compose(root,aid,cancel)
                self.assertFalse((root/"desktop-model.json").exists())


if __name__=="__main__":unittest.main()
