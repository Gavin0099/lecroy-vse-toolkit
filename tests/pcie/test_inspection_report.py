import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import build_inspection_report as report


INDICES = [100, 101, 103, 105, 107]
GUI_ROWS = [
    {"packet_index": 100, "vendor_type_code_hex": "0xE", "family": "Msg", "subtype": "MsgD", "time_seconds": "4.847933004000", "link_width": 1},
    {"packet_index": 101, "vendor_type_code_hex": "0x9", "family": "Cfg", "subtype": "CfgRd0", "time_seconds": "4.847933068000", "link_width": 1},
    {"packet_index": 103, "vendor_type_code_hex": "0x9", "family": "Cfg", "subtype": "CfgRd0", "time_seconds": "4.847937356000", "link_width": 1},
    {"packet_index": 105, "vendor_type_code_hex": "0x9", "family": "Cfg", "subtype": "CfgRd0", "time_seconds": "4.847939414000", "link_width": 1},
    {"packet_index": 107, "vendor_type_code_hex": "0x9", "family": "Cfg", "subtype": "CfgRd0", "time_seconds": "4.847948900000", "link_width": 1},
]


def valid_log() -> str:
    rows = [
        "PCIE_D1_TLP|100| 4.848 sec|TLP|Downstream|0xE|1",
        "PCIE_D1_TLP|101| 4.848 sec|TLP|Downstream|0x9|1",
        "PCIE_D1_TLP|103| 4.848 sec|TLP|Downstream|0x9|1",
        "PCIE_D1_TLP|105| 4.848 sec|TLP|Downstream|0x9|1",
        "PCIE_D1_TLP|107| 4.848 sec|TLP|Downstream|0x9|1",
    ]
    return "\n".join([report.HEADER, *rows, report.DONE_MARKER])


class InspectionReportTests(unittest.TestCase):
    def test_parse_accepts_five_records_with_normal_completion(self):
        rows = report.parse_vendor_log(valid_log())
        self.assertEqual([row["packet_index"] for row in rows], INDICES)
        self.assertEqual(rows[0]["vendor_type_code_hex"], "0xE")
        self.assertEqual(rows[0]["extractor_time_display"], "4.848 sec")

    def test_parse_rejects_error_missing_done_and_wrong_count(self):
        with self.assertRaises(report.InspectionError):
            report.parse_vendor_log(valid_log() + "\nRuntime Error: failed")
        with self.assertRaises(report.InspectionError):
            report.parse_vendor_log(valid_log().replace(report.DONE_MARKER, ""))
        short_log = "\n".join(valid_log().splitlines()[:-2] + [report.DONE_MARKER])
        with self.assertRaises(report.InspectionError):
            report.parse_vendor_log(short_log)

    def make_repo_and_manifest(self, root: Path) -> Path:
        files = {
            "input/trace.pex": b"external trace identity fixture",
            "bin/PETracer.exe": b"executable identity fixture",
            "scripts/extractor.pevs": b"unchanged VSE script fixture",
            "evidence/output.log": valid_log().encode("utf-8"),
            "evidence/gui.png": b"GUI evidence identity fixture",
        }
        for relative, contents in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
        hash_path = lambda relative: report.sha256_file(root / relative)
        crosscheck = [dict(row) for row in GUI_ROWS]
        context = [index - 1944416 for index in range(1944516, 1944526)]
        manifest = {
            "report_date": "2026-09-12",
            "source_trace": {
                "path": "input/trace.pex", "file_name": "trace.pex",
                "size_bytes": (root / "input/trace.pex").stat().st_size,
                "sha256": hash_path("input/trace.pex"),
                "last_write_utc": report.format_mtime_utc(root / "input/trace.pex"),
                "ground_truth": "UNKNOWN",
            },
            "software": {
                "product": "Teledyne LeCroy PCIe Protocol Analysis",
                "version": "13.26 Build 43 BETA", "executable_path": "bin/PETracer.exe",
                "executable_sha256": hash_path("bin/PETracer.exe"),
            },
            "extractor": {
                "script_path": "scripts/extractor.pevs", "script_sha256": hash_path("scripts/extractor.pevs"),
                "scope": "Five TLP records only", "record_cap": 5,
                "fields": ["in.Index", "TimeToText(in.Time)", "in.TLPType", "in.LinkWidth"],
                "time_representation": "Coarse vendor display text.",
            },
            "execution": {
                "output_log_path": "evidence/output.log", "output_log_sha256": hash_path("evidence/output.log"),
                "completion_marker": report.DONE_MARKER,
            },
            "gui_crosscheck": {
                "image_path": "evidence/gui.png", "image_sha256": hash_path("evidence/gui.png"),
                "rows": crosscheck, "visible_packet_indices": context,
                "intervening_non_extracted_indices": [102, 104, 106, 108],
                "next_tlp_visible_beyond_cap": 109,
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def test_builder_binds_identities_and_reports_bounded_unknown_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.make_repo_and_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            data = report.build_observations(manifest, root)
            self.assertEqual(data["status"]["extraction"], "PASS_BOUNDED")
            self.assertEqual(data["status"]["ground_truth"], "UNKNOWN")
            self.assertEqual(data["status"]["diagnostic_result"], "NOT_EVALUATED")
            self.assertEqual(len(data["observations"]), 5)
            self.assertEqual(data["observations"][0]["gui_crosscheck"]["subtype"], "MsgD")
            self.assertNotIn("findings", data)

    def test_builder_rejects_trace_hash_drift_and_gui_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.make_repo_and_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            trace_file = root / "input/trace.pex"
            trace_file.write_bytes(b"X" + trace_file.read_bytes()[1:])
            with self.assertRaisesRegex(report.InspectionError, "SHA-256"):
                report.build_observations(manifest, root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.make_repo_and_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["gui_crosscheck"]["rows"][0]["link_width"] = 2
            with self.assertRaisesRegex(report.InspectionError, "link-width"):
                report.build_observations(manifest, root)

    def test_renderers_share_json_and_html_escapes_evidence_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.make_repo_and_manifest(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            data = report.build_observations(manifest, root)
            data["trace"]["file_name"] = '<img src=x onerror="alert(1)">'
            markdown = report.render_markdown(data, "log.txt", "gui.png")
            page = report.render_html(data, "log.txt", "gui.png")
            self.assertIn("Ground truth | **UNKNOWN**", markdown)
            self.assertIn("NOT_EVALUATED", markdown)
            self.assertIn("<title>PCIe Trace Inspection — &lt;img", page)
            self.assertNotIn('<img src=x onerror="alert(1)">', page)
            self.assertNotIn("<script", page.casefold())
            self.assertIn("4.848 sec", page)
            self.assertIn("4.847933004000", page)

    def test_bundle_writes_one_structured_source_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.make_repo_and_manifest(root)
            target = root / "reports" / "trace-inspection"
            json_path, md_path, html_path = report.build_bundle(manifest, target, root)
            self.assertTrue(json_path.is_file() and md_path.is_file() and html_path.is_file())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("PASS — bounded first five TLP records", md_path.read_text(encoding="utf-8"))
            self.assertIn("前五筆 TLP 範圍", html_path.read_text(encoding="utf-8"))
            self.assertEqual(data["observations"][0]["packet_index"], 100)
            with self.assertRaisesRegex(report.InspectionError, "Refusing to overwrite"):
                report.build_bundle(manifest, target, root)


if __name__ == "__main__":
    unittest.main()
