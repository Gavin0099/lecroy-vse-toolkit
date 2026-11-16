import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parents[1] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(TEST_DIR))

import run_pcie_triage as runner
from test_g3f_findings import build_inputs, pkt


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_bundle(root: Path, *, tamper=None):
    _, _, _, _, fields = build_inputs()
    fields_bytes = json.dumps(fields).encode("utf-8")
    messages = [{"packet_index": pkt(26), "time_display": "5.880 sec", "channel": "Downstream", "tlp_type_hex": "0xD", "requester_id": 0,
                 "message_code": 48, "message_code_name": "ERR_COR", "message_route": 0, "message_route_name": "TOROOTCOMPLEX"}]
    messages_bytes = json.dumps(messages).encode("utf-8")
    (root / "fields.json").write_bytes(fields_bytes)
    (root / "messages.json").write_bytes(messages_bytes)
    fields_summary = {"status": "PASS_FIELD_PROBE_OUTPUT", "rows": len(fields), "fields_json_canonical_sha256": sha(fields_bytes)}
    messages_summary = {"status": "PASS_MESSAGE_FIELD_PROBE_OUTPUT", "messages_json_sha256": sha(messages_bytes), "g2a_fields_sha256": sha(fields_bytes)}
    manifest = {
        "schema_version": runner.INPUT_SCHEMA,
        "trace": {"file_name": "sample.pex", "sha256": "B" * 64, "tlp_count": len(fields)},
        "fields": {"path": "fields.json", "sha256": sha(fields_bytes), "verifier_summary": "fields-summary.json"},
        "messages": {"path": "messages.json", "sha256": sha(messages_bytes), "verifier_summary": "messages-summary.json"},
    }
    if tamper:
        tamper(manifest, fields_summary, messages_summary)
    (root / "fields-summary.json").write_text(json.dumps(fields_summary), encoding="utf-8")
    (root / "messages-summary.json").write_text(json.dumps(messages_summary), encoding="utf-8")
    (root / "input.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root / "input.json"


class RunnerTests(unittest.TestCase):
    def test_end_to_end_package_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "package"
            self.assertEqual(runner.main(["--input-manifest", str(write_bundle(root)), "--output-dir", str(out), "--repo-root", str(root)]), 0)
            for name in ("report.html", "report.md", "findings.json", "run-manifest.json", "使用說明.md"):
                self.assertTrue((out / name).is_file(), name)
            manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PASS")
            self.assertEqual([s["stage"] for s in manifest["stages"]], ["validate_inputs", "g2b", "g3ab", "g3c", "g3d", "g3e", "g3f", "g7", "g8"])
            self.assertTrue(all(s["status"] == "PASS" for s in manifest["stages"]))
            self.assertEqual(manifest["package"]["report.html"], sha((out / "report.html").read_bytes()))
            self.assertEqual(manifest["trace"]["sha256"], "B" * 64)
            self.assertIn("g3f", manifest["script_sha256"])
            self.assertIn(manifest["run_id"], (out / "使用說明.md").read_text(encoding="utf-8"))

    def assert_fails_at_validation(self, tamper, message):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "package"
            code = runner.main(["--input-manifest", str(write_bundle(root, tamper=tamper)), "--output-dir", str(out), "--repo-root", str(root)])
            self.assertEqual(code, 2)
            manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest["status"], manifest["failed_stage"]), ("FAILED", "validate_inputs"))
            self.assertIn(message, manifest["error"])
            self.assertFalse((out / "report.html").exists())

    def test_fail_closed_on_hash_mismatch(self):
        self.assert_fails_at_validation(lambda m, fs, ms: m["fields"].update(sha256="C" * 64), "differs from the input manifest")

    def test_fail_closed_on_unverified_extraction(self):
        self.assert_fails_at_validation(lambda m, fs, ms: fs.update(status="FAILED"), "not PASS_FIELD_PROBE_OUTPUT")

    def test_fail_closed_on_messages_from_other_extraction(self):
        self.assert_fails_at_validation(lambda m, fs, ms: ms.update(g2a_fields_sha256="D" * 64), "different fields.json")

    def test_fail_closed_on_tlp_count_mismatch(self):
        self.assert_fails_at_validation(lambda m, fs, ms: m["trace"].update(tlp_count=31), "differ from trace tlp_count")

    def test_conversion_provenance_reaches_reports_readme_and_manifest(self):
        provenance = {"original_sha256": "F" * 64, "conversion": "PETracer 12.36 (Build 19) → 13.26 (Build 43) format update",
                      "analysis_target": "converted disposable copy", "packet_index_note": runner.g7_render_markdown.PACKET_INDEX_NOTE}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "package"
            bundle = write_bundle(root, tamper=lambda m, fs, ms: m["trace"].update(provenance=provenance))
            self.assertEqual(runner.main(["--input-manifest", str(bundle), "--output-dir", str(out), "--repo-root", str(root)]), 0)
            note = runner.g7_render_markdown.PACKET_INDEX_NOTE
            for name in ("report.md", "report.html", "使用說明.md"):
                text = (out / name).read_text(encoding="utf-8")
                self.assertIn(note, text, name)
                self.assertIn("F" * 64, text, name)
            manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["trace"]["provenance"]["original_sha256"], "F" * 64)

    def test_fail_closed_on_altered_packet_index_note(self):
        base = {"original_sha256": "F" * 64, "conversion": "x", "analysis_target": "converted disposable copy"}
        self.assert_fails_at_validation(lambda m, fs, ms: m["trace"].update(provenance={**base, "packet_index_note": "packet 編號一致"}),
                                        "packet index caveat")
        self.assert_fails_at_validation(lambda m, fs, ms: m["trace"].update(provenance={**base, "original_sha256": "B" * 64,
                                        "packet_index_note": runner.g7_render_markdown.PACKET_INDEX_NOTE}), "a conversion changes the file")

    def test_refuses_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "package"
            out.mkdir()
            self.assertEqual(runner.main(["--input-manifest", str(write_bundle(root)), "--output-dir", str(out), "--repo-root", str(root)]), 2)
            self.assertFalse((out / "run-manifest.json").exists())

    def test_stage_failure_stops_before_reports(self):
        def break_fields(m, fs, ms):
            data = json.loads(Path(tempdir_root[0], "fields.json").read_text(encoding="utf-8"))
            for row in data:
                row.pop("tlp_type_hex")
            raw = json.dumps(data).encode("utf-8")
            Path(tempdir_root[0], "fields.json").write_bytes(raw)
            m["fields"]["sha256"] = sha(raw)
            fs["fields_json_canonical_sha256"] = sha(raw)
            ms["g2a_fields_sha256"] = sha(raw)
        with tempfile.TemporaryDirectory() as temporary:
            tempdir_root = [temporary]
            root = Path(temporary)
            out = root / "package"
            code = runner.main(["--input-manifest", str(write_bundle(root, tamper=break_fields)), "--output-dir", str(out), "--repo-root", str(root)])
            self.assertEqual(code, 2)
            manifest = json.loads((out / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual((manifest["status"], manifest["failed_stage"]), ("FAILED", "g2b"))
            self.assertFalse((out / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
