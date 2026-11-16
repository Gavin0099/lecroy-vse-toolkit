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
import pcie_model_worker
from test_stage_workspace import stage_fixture, workspace


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
