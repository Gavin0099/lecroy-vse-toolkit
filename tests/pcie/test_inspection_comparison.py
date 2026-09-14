import copy
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import build_inspection_comparison as comparison


def sha(char: str) -> str:
    return char * 64


def make_observation(file_name: str, trace_sha: str, types: list[str]) -> dict:
    rows = []
    for index, type_code in enumerate(types):
        family, subtype = ("Msg", "MsgD") if type_code == "0xE" else ("Cfg", "CfgRd0")
        packet_index = index * 2 + (100 if trace_sha.startswith("A") else 200)
        rows.append(
            {
                "packet_index": packet_index,
                "event_family": "TLP",
                "vendor_channel": "Downstream",
                "vendor_type_code_hex": type_code,
                "link_width": 1,
                "extractor_time_display": f"{4.4 + index / 1000:.3f} sec",
                "gui_crosscheck": {
                    "status": "MATCHED",
                    "family": family,
                    "subtype": subtype,
                    "time_seconds": f"4.400{index:06d}",
                    "link_width": 1,
                },
            }
        )
    return {
        "schema_version": comparison.SCHEMA_VERSION,
        "report_kind": comparison.REPORT_KIND,
        "report_date": "2026-09-14",
        "trace": {
            "file_name": file_name,
            "source_path": f"C:/traces/{file_name}",
            "size_bytes": 1000,
            "sha256": trace_sha,
            "last_write_utc": "2026-06-11T07:13:41.4022556Z",
            "ground_truth": "UNKNOWN",
        },
        "software": {
            "product": "Teledyne LeCroy PCIe Protocol Analysis",
            "version": "13.26 Build 43 BETA",
            "executable_path": "C:/LeCroy/PETracer.exe",
            "executable_sha256": sha("D"),
        },
        "extractor": {
            "script_path": "scripts/pcie/p0-d1-tlps.pevs",
            "script_sha256": sha("C"),
            "scope": "First five TLP callbacks only",
            "record_cap": 5,
            "fields": ["in.Index", "TimeToText(in.Time)", "in.TLPType", "in.LinkWidth"],
            "time_representation": "Coarse vendor display text",
        },
        "status": {
            "extraction": "PASS_BOUNDED",
            "ground_truth": "UNKNOWN",
            "diagnostic_result": "NOT_EVALUATED",
            "coverage": comparison.EXPECTED_COVERAGE,
        },
        "evidence": {
            "extractor_log_path": "evidence/output.log",
            "extractor_log_sha256": sha("E"),
            "gui_image_path": "evidence/gui.png",
            "gui_image_sha256": sha("F"),
            "gui_rows_checked": 5,
        },
        "observations": rows,
        "gui_context": {
            "visible_packet_indices": [row["packet_index"] for row in rows],
            "intervening_non_extracted_indices": [],
            "next_tlp_visible_beyond_cap": rows[-1]["packet_index"] + 2,
            "interpretation": "The image shows the sampled TLPs.",
        },
        "limitations": ["First five TLP records only."],
    }


class InspectionComparisonTests(unittest.TestCase):
    def setUp(self):
        self.left = make_observation(
            "S0-Remove SD7-A.pex", sha("A"), ["0xE", "0x9", "0x9", "0x9", "0x9"]
        )
        self.right = make_observation(
            "S0-Remove SD7-B.pex", sha("B"), ["0xE", "0xE", "0x9", "0x9", "0x9"]
        )

    def test_comparison_reports_bounded_sample_counts_without_event_alignment(self):
        pair = comparison.compare_observations(self.left, self.right)
        self.assertEqual(
            pair["type_counts"],
            [
                {"type_code": "0x9", "trace_a": 4, "trace_b": 3},
                {"type_code": "0xE", "trace_a": 1, "trace_b": 2},
            ],
        )
        page = comparison.render_html(pair, sha("1"), sha("2"))
        self.assertIn("<title>PCIe Trace Inspection Comparison</title>", page)
        self.assertIn("<h1>PCIe Trace Inspection Comparison</h1>", page)
        self.assertIn(comparison.SAMPLE_BOUNDARY_NOTE, page)
        self.assertLess(page.index(comparison.SAMPLE_BOUNDARY_NOTE), page.index("<th>TLP Type code</th>"))
        self.assertIn("Observed：", page)
        self.assertIn("Not established：", page)
        self.assertIn("故障原因（root cause）", page)
        self.assertIn("Type code 排列順序：兩份樣本不同", page)
        self.assertIn("Packet index 間隔模式：兩份樣本相同", page)
        self.assertIn("A 的第 1 筆不代表和 B 的第 1 筆是同一個封包", page)
        self.assertIn("實際測試結果尚未確認", page)
        # Sample composition is descriptive only: no difference column, no outcome wording.
        self.assertNotIn("A − B", page)
        self.assertNotIn("PASS", page.split("<body>")[0] + page.split("</h1>")[0])
        # Neither fixture filename carries an outcome-like token, so no hint section appears.
        self.assertNotIn("Filename hints", page)
        self.assertNotIn("Fail", page)
        self.assertNotIn("<script", page.casefold())

        class Parser(HTMLParser):
            pass

        Parser().feed(page)

    def test_identical_sample_shapes_are_described_not_scored(self):
        same_shape = make_observation(
            "S0-Remove SD7-B.pex", sha("B"), ["0xE", "0x9", "0x9", "0x9", "0x9"]
        )
        pair = comparison.compare_observations(self.left, same_shape)
        page = comparison.render_html(pair, sha("1"), sha("2"))
        self.assertIn("Type code 樣本組成：兩份樣本相同", page)
        self.assertIn("Type code 排列順序：兩份樣本相同", page)
        self.assertIn("不表示兩份 trace 的行為相同", page)

    def test_filename_hint_is_conditional_and_never_ground_truth(self):
        self.assertEqual(comparison.filename_outcome_hints("S0-Remove SD7-1329-Fail.pex"), ["Fail"])
        self.assertEqual(comparison.filename_outcome_hints("Disable ASPM--Insert SD7-hang-2.pex"), ["hang"])
        self.assertEqual(comparison.filename_outcome_hints("S0-Remove SD7-1350.pex"), [])
        self.assertEqual(comparison.filename_outcome_hints("Failover-capture.pex"), [])

        hinted = make_observation(
            "S0-Remove SD7-1329-Fail.pex", sha("B"), ["0xE", "0x9", "0x9", "0x9", "0x9"]
        )
        pair = comparison.compare_observations(self.left, hinted)
        page = comparison.render_html(pair, sha("1"), sha("2"))
        self.assertIn(
            "Trace B filename contains <code>Fail</code>; this is treated only as a filename hint "
            "and not as ground truth.",
            page,
        )
        self.assertNotIn("Trace A filename contains", page)
        self.assertEqual(pair["trace_b"]["status"]["ground_truth"], "UNKNOWN")

    def test_rejects_unqualified_or_incompatible_inputs(self):
        bad_ground_truth = copy.deepcopy(self.left)
        bad_ground_truth["trace"]["ground_truth"] = "FAIL"
        with self.assertRaisesRegex(comparison.ComparisonError, "UNKNOWN ground truth"):
            comparison.validate_observation(bad_ground_truth, "Trace A")

        different_extractor = copy.deepcopy(self.right)
        different_extractor["extractor"]["script_sha256"] = sha("9")
        with self.assertRaisesRegex(comparison.ComparisonError, "extractor.script_sha256"):
            comparison.compare_observations(self.left, different_extractor)

        short_sample = copy.deepcopy(self.right)
        short_sample["observations"].pop()
        with self.assertRaisesRegex(comparison.ComparisonError, "exactly five"):
            comparison.validate_observation(short_sample, "Trace B")

        missing_gui_index = copy.deepcopy(self.right)
        missing_gui_index["gui_context"]["visible_packet_indices"].pop()
        with self.assertRaisesRegex(comparison.ComparisonError, "GUI context omits"):
            comparison.validate_observation(missing_gui_index, "Trace B")

        same_trace = copy.deepcopy(self.right)
        same_trace["trace"]["sha256"] = self.left["trace"]["sha256"]
        with self.assertRaisesRegex(comparison.ComparisonError, "same source SHA-256"):
            comparison.compare_observations(self.left, same_trace)

    def test_html_escapes_trace_identity(self):
        hostile = copy.deepcopy(self.left)
        hostile["trace"]["file_name"] = '</title><script>alert("x")</script>'
        pair = comparison.compare_observations(hostile, self.right)
        page = comparison.render_html(pair, sha("1"), sha("2"))
        self.assertNotIn('<script>alert("x")</script>', page)
        self.assertIn("&lt;script&gt;", page)

    def test_builder_writes_new_repo_local_html_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left_path = root / "left.json"
            right_path = root / "right.json"
            left_path.write_text(json.dumps(self.left), encoding="utf-8")
            right_path.write_text(json.dumps(self.right), encoding="utf-8")
            target = root / "reports" / "compare.html"

            result = comparison.build_comparison(left_path, right_path, target, root)
            self.assertTrue(result.is_file())
            self.assertIn("Trace A", result.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(comparison.ComparisonError, "Refusing to overwrite"):
                comparison.build_comparison(left_path, right_path, target, root)

            with tempfile.TemporaryDirectory() as outside_dir:
                outside = Path(outside_dir) / "outside.html"
                with self.assertRaisesRegex(comparison.ComparisonError, "inside the repository"):
                    comparison.build_comparison(left_path, right_path, outside, root)


if __name__ == "__main__":
    unittest.main()
