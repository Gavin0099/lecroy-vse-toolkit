import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
import pcie_selection_probe as p
import s01_contract as s

class PcieSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.plan=p.prepare(Path(self.tmp.name)/"p","a"*64)
        self.profile=self.plan["profiles"][0]
        self.run={"status":"COM_RUN_COMPLETE","identities_unchanged":True,"steps":{"finish_event":{"result_name":"DONE"}}}
        self.row={"kind":"p01-row","index":10,"level":0,"channel":1,"event_raw":20,"time2":[1,2,3]}
        self.end={"kind":"p01-end","visited":17,"selected":1,"emitted":1,"mismatches":0,"native_level":0}

    def test_handwritten_callback_denominators_time2_and_unknown_accuracy(self):
        a=p.assess(self.run,[json.dumps(self.row,separators=(',',':')),json.dumps(self.end,separators=(',',':'))],self.profile)
        self.assertEqual(a["counts"]["visited"],17);self.assertEqual(a["rows"][0]["time2"],[1,2,3])
        self.assertEqual(a["measurement_resolution"],"unknown");self.assertEqual(a["qualification"],"NOT_EVALUATED")

    def test_empty_window_is_unknown_not_absence(self):
        e=dict(self.end,selected=0,emitted=0)
        a=p.assess(self.run,[json.dumps(e,separators=(',',':'))],self.plan["profiles"][1])
        self.assertEqual(a["empty_observation"],"unknown")

    def test_named_levels_and_event_selectors_are_not_magic_numbers(self):
        self.assertIn('SendLevelOnly(_LINK)',p.script("link-all"));self.assertIn('SendLevelOnly(_SPLIT)',p.script("split-all"))
        self.assertIn('SendTraceEventOnly(_PKT_DLLP)',p.script("packet-dllp"));self.assertIn('SendTraceEventOnly(_PKT_TLP)',p.script("packet-tlp"))
        p.validate_plan(self.plan)

    def test_missing_duplicate_end_and_forged_counts_are_rejected(self):
        for ends in [[],[self.end,self.end],[dict(self.end,emitted=2)],[dict(self.end,mismatches=1)]]:
            lines=[json.dumps(self.row,separators=(',',':'))]+[json.dumps(x,separators=(',',':')) for x in ends]
            with self.assertRaises(s.ContractError):p.assess(self.run,lines,self.profile)

    def test_boolean_range_wrong_namespace_and_time_components_rejected(self):
        for update in [{"index":True},{"index":201},{"level":1},{"time2":[1,1000000000,0]},{"time2":[1,0,1000]}]:
            r=dict(self.row,**update)
            with self.assertRaises(s.ContractError):p.assess(self.run,[json.dumps(r,separators=(',',':')),json.dumps(self.end,separators=(',',':'))],self.profile)

    def test_failed_integrity_or_finish_cannot_qualify(self):
        for update in [{"identities_unchanged":False},{"steps":{"finish_event":{"result_name":"PASSED"}}},{"status":"COM_RUN_FAILED"}]:
            with self.assertRaises(s.ContractError):p.assess(dict(self.run,**update),[],self.profile)

    def test_altered_plan_flags_script_path_or_verdict_are_rejected(self):
        for mutate in [lambda d:d["profiles"][0].update(script="../../a.pevs"),lambda d:d.update(verdict="PASS"),lambda d:d["profiles"].pop()]:
            plan=copy.deepcopy(self.plan);mutate(plan)
            with self.assertRaises(s.ContractError):p.validate_plan(plan)
        with self.assertRaises(FileExistsError):p.prepare(Path(self.tmp.name)/"p","a"*64)

if __name__=="__main__":unittest.main()
