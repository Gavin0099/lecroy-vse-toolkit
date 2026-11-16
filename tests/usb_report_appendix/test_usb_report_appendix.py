import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import usb_report_appendix as a
import s01_contract as s

ROOT = Path(__file__).resolve().parents[2]
C5 = ROOT / "c5-output-20260911-v3/suspicious-regions.json"
PLAN = ROOT / "artifacts/evidence/serial-slices-20261013/u02-prepared/plan.json"
RUN = ROOT / "artifacts/evidence/serial-slices-20261013/u02-run-a"


class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.ids = []; self.links = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "id": self.ids.append(value)
            if key == "href": self.links.append(value)


class UsbAppendixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.model = a.load_model(C5, PLAN, RUN)

    def test_historical_values_untouched_and_qualification_unknown(self):
        self.assertEqual(self.model["historical_c5"], s.read_json(C5))
        b = self.model["native_command_observations"]
        self.assertEqual(b["qualification"], "NOT_EVALUATED")
        self.assertEqual(b["coverage"]["epoch"], "unknown")
        self.assertEqual(b["coverage"]["retention"], "unknown")
        self.assertNotIn("verdict", b); self.assertNotIn("extensions", b)

    def test_base_html_exactly_preserved_after_section_removed(self):
        b = self.model["native_command_observations"]; base = "<html><main>historical score PASS</main></html>"
        rendered = a.compose(base, b, ROOT)
        self.assertEqual(rendered.replace(a.render_block(b, ROOT), ""), base)
        with self.assertRaises(s.ContractError): a.compose(base + base, b, ROOT)

    def test_all_packet_rows_and_pointers_are_same_source(self):
        b = self.model["native_command_observations"]; data = s.read_json(Path(b["sources"]["observations"]["path"]))
        for i, row in enumerate(b["observation"]["records"]):
            self.assertEqual(data["records"][i], row)
            self.assertEqual(row["packet_ref"]["trace_sha256"], b["trace_sha256"])
        self.assertEqual(b["observation"]["exported_count"], 128)

    def test_unknown_and_candidates_do_not_become_root_cause(self):
        b = self.model["native_command_observations"]; page = a.render_block(b, ROOT)
        for text in ["166196", "128", "CRC5 未重新計算", "capture", "epoch", "SS／SSP", "故障根因"]:
            self.assertIn(text, page)
        empty = copy.deepcopy(b); empty["observation"]["records"] = []; empty["observation"].update(callback_count=0, exported_count=0)
        unknown_page = a.render_block(empty, ROOT)
        self.assertIn("未知", unknown_page); self.assertNotIn("沒有 LINK_CMD", unknown_page)

    def test_html_escaping_offline_ids_and_link_resolution(self):
        b = copy.deepcopy(self.model["native_command_observations"])
        b["observation"]["records"][0]["name_vendor"] = "<script>alert(1)</script>"
        page = a.render_block(b, ROOT); tags = Tags(); tags.feed(page)
        self.assertNotIn("script", tags.tags); self.assertIn("&lt;script&gt;", page)
        self.assertEqual(len(tags.ids), len(set(tags.ids)))
        for url in tags.links:
            self.assertFalse(url.startswith(("http:", "https:", "javascript:")))
            self.assertTrue((ROOT / unquote(url.split("#")[0])).exists())

    def test_bad_baseline_identity_and_opaque_observations_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory); bad_c5 = target / "c5.json"; baseline = s.read_json(C5)
            baseline["trace_integrity_qualified"] = False; bad_c5.write_text(json.dumps(baseline), encoding="utf-8")
            with self.assertRaises(s.ContractError): a.load_model(bad_c5, PLAN, RUN)
            for rel in ["before.json", "integrity.json", "observations.json", "result.json"]:
                shutil.copyfile(RUN / rel, target / rel)
            observation = s.read_json(target / "observations.json"); observation["extensions"] = {"root_cause": "CRC_FAIL"}
            (target / "observations.json").write_text(json.dumps(observation), encoding="utf-8")
            with self.assertRaises(s.ContractError): a.load_model(C5, PLAN, target)
            shutil.copyfile(RUN / "observations.json", target / "observations.json")
            before = s.read_json(target / "before.json"); before["source"]["sha256"] = "f" * 64
            (target / "before.json").write_text(json.dumps(before), encoding="utf-8")
            with self.assertRaises(s.ContractError): a.load_model(C5, PLAN, target)


if __name__ == "__main__": unittest.main()
