import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import unquote
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_protocol_appendix as a
import s01_contract as s

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "artifacts/evidence/p03-serial-20261013"
FROZEN = Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
TIMELINE = FROZEN / "artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json"


class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.ids = []; self.links = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "id": self.ids.append(value)
            if key == "href": self.links.append(value)


class AppendixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.dependencies = a.frozen_renderer(FROZEN)
        cls.base = cls.report.build_model(cls.report.adapter.verified_timeline(TIMELINE, FROZEN), FROZEN)
        probes = {}; sources = {}
        for profile in ["dllp", "tlp"]:
            probes[profile], sources[profile] = a.load_probe(EVIDENCE / "prepared/plan.json", EVIDENCE / (profile + "-a"), profile)
        cls.appendix = a.build_appendix(probes, cls.base["capture_sha256"], sources)
        a.bind_authorities(cls.appendix)

    def test_base_bytes_and_w1_states_unchanged(self):
        md = self.report.render_markdown(self.base, "."); webpage = self.report.render_html(self.base, ".")
        new_md, new_html = a.compose(md, webpage, self.appendix, ROOT)
        self.assertTrue(new_md.startswith(md))
        _, section = a.render_block(self.appendix, ROOT)
        self.assertEqual(new_html.replace(section, ""), webpage)
        self.assertTrue(all(i["observation"]["effective_state"] == "UNKNOWN" and i["observation"]["expected_state"] == "UNKNOWN" and i["observation"]["policy_result"] == "NOT_EVALUATED" for i in self.base["intents"]))

    def test_raw_unknown_na_and_missing_evidence_equal_in_both_formats(self):
        md, webpage = a.render_block(self.appendix, ROOT)
        for text in ["AckNak_SeqNum=1682", "HdrFC=80", "未知（API 空值）", "不適用", "未知（抽樣沒有記錄）", "連續的雙向 capture、mode 與 epoch"]:
            self.assertIn(text, md); self.assertIn(text, webpage)
        self.assertEqual(self.appendix["qualification"], "NOT_EVALUATED")
        self.assertNotIn("extensions", self.appendix); self.assertNotIn("verdict", self.appendix)
        self.assertEqual(self.appendix["coverage"]["epoch"], "unknown")

    def test_every_row_source_pointer_resolves_and_equal(self):
        for profile, probe in self.appendix["profiles"].items():
            source = self.appendix["sources"][profile]["observations"]
            data = s.read_json(Path(source["path"]))
            for i, row in enumerate(probe["rows"]):
                self.assertEqual(self.report.contract.pointer_value(data, "/rows/" + str(i)), row)

    def test_html_unique_ids_offline_and_escaped(self):
        md, webpage = a.render_block(self.appendix, ROOT); parser = Tags(); parser.feed(webpage)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertNotIn("script", parser.tags)
        for url in parser.links:
            self.assertFalse(url.startswith(("http:", "https:", "javascript:")))
            self.assertTrue((ROOT / unquote(url.split("#")[0])).exists())
        model = copy.deepcopy(self.appendix); model["missing_evidence"] = ["<script>alert(1)</script>"]
        _, escaped = a.render_block(model, ROOT)
        self.assertNotIn("<script>", escaped); self.assertIn("&lt;script&gt;", escaped)

    def test_capture_mismatch_rejected(self):
        with self.assertRaises(s.ContractError): a.build_appendix(self.appendix["profiles"], "f" * 64, self.appendix["sources"])

    def test_cross_drive_links_are_offline_file_uris(self):
        target = a.link({"path": str(EVIDENCE / "dllp-a/observations.json")}, "/rows/0", FROZEN.parent)
        self.assertTrue(target.startswith("file:///E:/")); self.assertTrue(target.endswith("#%2Frows%2F0"))

    def test_opaque_or_raw_tampering_rejected_before_render(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for rel in ["before.json", "after.json", "observations.json", "native/com-run.json", "native/report-lines.json"]:
                destination = target / rel; destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(EVIDENCE / "dllp-a" / rel, destination)
            original = s.read_json(target / "observations.json")
            for mutation in ["opaque", "value", "unknown_to_pass"]:
                data = copy.deepcopy(original)
                if mutation == "opaque": data["extensions"] = {"verdict": "PASS"}
                elif mutation == "value": data["rows"][0]["fields"]["HdrFC"]["value"] = 81
                else: data["coverage"]["epoch"] = "PASS"
                (target / "observations.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(s.ContractError): a.load_probe(EVIDENCE / "prepared/plan.json", target, "dllp")

    def test_dependencies_match_pinned_commit_and_new_output_only(self):
        self.assertGreaterEqual(len(self.dependencies), 10)
        with self.assertRaises(s.ContractError): a.generate(FROZEN, TIMELINE, EVIDENCE / "prepared/plan.json", EVIDENCE / "dllp-a", EVIDENCE / "tlp-a", FROZEN / "not-created-output")


if __name__ == "__main__": unittest.main()
