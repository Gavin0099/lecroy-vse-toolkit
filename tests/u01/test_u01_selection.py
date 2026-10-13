"""Handwritten transport cases based on LC-04 and U01 contract, not live traces."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import u01_selection as u
import s01_contract as s


class U01Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "prepared"
        self.plan = u.prepare(self.out, "a" * 64, "SYNTHETIC-U01", 10, 20)

    def result(self, selection="packet-crc-on"):
        # Seven integer context fields plus completion sentinel. The callback
        # payload schema comes from LC-04 PDF19/20/89, counters from U01 design.
        return {"selection": selection, "trace_sha256": "a" * 64,
                "script_sha256": next(p["script_sha256"] for p in self.plan["profiles"] if p["id"] == selection),
                "integrity": {"source_unchanged": True, "working_copy_unchanged": True, "working_copy_readonly": True},
                "run_result": 2, "finished_result": 2, "error": "",
                "rows": [[10, 0, 5, 4, 300, 1, 2, -1], [20, 0, 6, 4, 301, 1, 3, -1]],
                "summary": [17, 2, 2, 0, 0], "software_version": "SYNTHETIC-10.40",
                "constants_sha256": "b" * 64, "manual_sha256": "c" * 64}

    def test_seven_named_selections_use_reviewed_flags_and_native_names(self):
        p = self.out / "packet-default.vse"
        self.assertNotIn("SendPktsWithBadCRC", p.read_text())
        self.assertIn("SendPktsWithBadCRC(0);", (self.out / "packet-crc-off.vse").read_text())
        self.assertIn("SendPktsWithBadCRC(1);", (self.out / "packet-crc-on.vse").read_text())
        self.assertIn("SendLevelOnly(_TRA);", (self.out / "transaction-all.vse").read_text())
        self.assertIn("SendTransfer(_ANY, _ANY, _ANY);", (self.out / "transfer-default.vse").read_text())
        self.assertIn("SendTransfer(_ANY, _ANY, _ANY, 1, 0);", (self.out / "transfer-complete.vse").read_text())
        self.assertIn("SendTransfer(_ANY, _ANY, _ANY, 0, 0);", (self.out / "transfer-incomplete.vse").read_text())

    def test_negative_inapplicable_sentinel_uses_explicit_wire_token(self):
        # Independent regression evidence: diagnostic-3 did not enter OnStart;
        # changing only the inline -1 to 0 in diagnostic-4 compiled and returned.
        # The fixed template must retain NA by a named wire token, not false/0.
        text = (self.out / "packet-default.vse").read_text()
        self.assertIn('in.Time[1], "NOT_APPLICABLE"]);', text)
        self.assertNotIn("in.Time[1], -1]);", text)
        old = copy.deepcopy(self.plan); old["schema_version"] = "u01.selection-plan/v1"
        with self.assertRaises(s.ContractError): u.validate_plan(old)

    def test_prepare_refuses_overwrite_and_invalid_inputs_before_writing(self):
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaises(FileExistsError): u.prepare(self.out, "a" * 64, "x")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})
        for start, end in [(True, 3), (-1, 3), (21, 20), (0, 1_000_000_001)]:
            path = Path(self.tmp.name) / "invalid"
            with self.assertRaises(s.ContractError): u.prepare(path, "a" * 64, "x", start, end)
            self.assertFalse(path.exists())

    def test_plan_rejects_changed_flags_hash_level_namespaces_and_extra_keys(self):
        mutations = [lambda p: p["profiles"][0].update(calls=["ScriptPassed();"]),
                     lambda p: p["profiles"][0].update(script="../../anything.vse"),
                     lambda p: p["profiles"].pop(), lambda p: p.update(verdict="PASS"),
                     lambda p: p["requested_range"].update(namespace="packet_for_all_levels"),
                     lambda p: p["requested_range"].update(start="10")]
        for mutate in mutations:
            doc = copy.deepcopy(self.plan); mutate(doc)
            with self.assertRaises(s.ContractError): u.validate_plan(doc)

    def test_counts_range_and_manifest_have_handwritten_expected_results(self):
        result = self.result()
        original = copy.deepcopy(result)
        a = u.validate_result(result, self.plan, "packet-crc-on")
        self.assertEqual((a["callback_count"], a["window_callback_count"], a["exported_row_count"]), (17, 2, 2))
        self.assertEqual(a["delivered_index_bounds"], [10, 20])
        self.assertFalse(a["sample_truncated"])
        m = u.manifest_from_result(result, self.plan, "packet-crc-on", "fixture://result", "d" * 64)
        self.assertEqual(s.validate_manifest(m), [])
        self.assertEqual(m["observations"][0]["state"], "observed")
        self.assertEqual(m["observations"][0]["coverage"]["retention"], "unknown")
        self.assertEqual(m["trace"]["facts"]["mode"]["state"], "unknown")
        self.assertEqual(result, original)

    def test_empty_success_is_unknown_and_does_not_prove_bad_crc_absence(self):
        r = self.result(); r["rows"] = []; r["summary"] = [17, 0, 0, 0, 0]
        a = u.validate_result(r, self.plan, "packet-crc-on")
        self.assertIsNone(a["delivered_index_bounds"])
        self.assertEqual(a["bad_crc_coverage"], "unknown")
        self.assertEqual(a["qualification"], "NOT_EVALUATED")
        m = u.manifest_from_result(r, self.plan, "packet-crc-on", "fixture://empty", "d" * 64)
        self.assertEqual(m["observations"][0]["state"], "unknown")
        self.assertEqual(m["observations"][0]["count"], 0)

    def test_each_identity_and_integrity_guard_is_required(self):
        for key in ["source_unchanged", "working_copy_unchanged", "working_copy_readonly"]:
            for value in [False, 1, "true", None]:
                r = self.result(); r["integrity"][key] = value
                with self.assertRaises(s.ContractError): u.validate_result(r, self.plan, "packet-crc-on")
        for key in ["trace_sha256", "script_sha256", "selection"]:
            r = self.result(); r[key] = "mismatch"
            with self.assertRaises(s.ContractError): u.validate_result(r, self.plan, "packet-crc-on")

    def test_missing_end_marker_false_run_and_partial_delivery_fail(self):
        for key, value in [("run_result", True), ("finished_result", 0), ("error", "parse failure"), ("summary", None), ("summary", [17, 2, 1, 0, 0]), ("summary", [17, 2, 2, 1, 0])]:
            r = self.result(); r[key] = value
            with self.assertRaises(s.ContractError): u.validate_result(r, self.plan, "packet-crc-on")

    def test_bad_callback_fields_do_not_get_silently_coerced(self):
        for pos, value in [(0, 21), (0, True), (1, 1), (2, -1), (3, "4"), (6, 1_000_000_000), (7, 1)]:
            r = self.result(); r["rows"][0][pos] = value
            with self.assertRaises(s.ContractError): u.validate_result(r, self.plan, "packet-crc-on")

    def test_transfer_completion_is_checked_without_packet_index_claim(self):
        for selection, completion in [("transfer-complete", 1), ("transfer-incomplete", 0), ("transfer-default", 0)]:
            r = self.result(selection); r["rows"] = [[10, 3, 5, 4, 1, 1, 2, completion]]; r["summary"] = [4, 1, 1, 0, 3]
            a = u.validate_result(r, self.plan, selection)
            self.assertEqual(a["native_level"], 3)
            self.assertEqual(a["incomplete_transfer_coverage"], "unknown")
            if selection != "transfer-default":
                r["rows"][0][-1] = 1 - completion
                with self.assertRaises(s.ContractError): u.validate_result(r, self.plan, selection)

    def test_sample_limit_is_explicit_partial_not_complete(self):
        r = self.result(); r["rows"] = [r["rows"][0]] * 512; r["summary"] = [900, 600, 512, 0, 0]
        a = u.validate_result(r, self.plan, "packet-crc-on")
        self.assertTrue(a["sample_truncated"])
        m = u.manifest_from_result(r, self.plan, "packet-crc-on", "fixture://partial", "d" * 64)
        self.assertEqual(m["observations"][0]["coverage"]["extraction"], "partial")

    def test_cli_assessment_stdout_and_input_preservation(self):
        result_file = Path(self.tmp.name) / "result.json"
        result_file.write_text(json.dumps(self.result()), encoding="utf-8")
        before = result_file.read_bytes()
        p = subprocess.run([sys.executable, "-X", "utf8", "-B", str(ROOT / "tools/u01_selection.py"), "assess", "--plan", str(self.out / "plan.json"), "--result", str(result_file), "--selection", "packet-crc-on"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["assessment"]["qualification"], "NOT_EVALUATED")
        self.assertEqual(result_file.read_bytes(), before)

    def seven_results(self):
        names = ["packet-default", "packet-crc-off", "packet-crc-on", "transaction-all", "transfer-default", "transfer-complete", "transfer-incomplete"]
        results = {name: self.result(name) for name in names}
        for name in names:
            level = 3 if name.startswith("transfer") else 1 if name == "transaction-all" else 0
            for row in results[name]["rows"]:
                row[1] = level
                row[-1] = 0 if name == "transfer-incomplete" else 1 if name.startswith("transfer") else -1
            results[name]["summary"][-1] = level
        return results

    def test_like_level_comparison_preserves_unknown_coverage_and_handwritten_delta(self):
        results = self.seven_results()
        results["packet-crc-on"]["rows"].pop()
        results["packet-crc-on"]["summary"] = [17, 1, 1, 0, 0]
        c = u.compare_results(results, self.plan)
        self.assertEqual(c["comparisons"][0]["window_callback_count_delta"], 0)
        self.assertTrue(c["comparisons"][0]["exported_samples_equal"])
        self.assertEqual(c["comparisons"][1]["window_callback_count_delta"], -1)
        self.assertEqual(c["qualification"], "NOT_EVALUATED")
        self.assertTrue(all(a["bad_crc_coverage"] == "unknown" for a in c["assessments"]))

    def test_comparison_rejects_missing_mode_source_drift_and_namespace_mismatch(self):
        for mutate in [lambda r: r.pop("packet-default"),
                       lambda r: r["packet-crc-on"].update(constants_sha256="e" * 64),
                       lambda r: r["packet-crc-on"]["summary"].__setitem__(-1, 1)]:
            results = self.seven_results(); mutate(results)
            with self.assertRaises(s.ContractError): u.compare_results(results, self.plan)


if __name__ == "__main__": unittest.main()
