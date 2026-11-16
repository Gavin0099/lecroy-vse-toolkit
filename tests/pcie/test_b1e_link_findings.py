import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/pcie"))
import b1d_mux_rules as b1d
import b1e_link_findings as b1e
from test_b1d_mux_rules import fixture


class B1eTests(unittest.TestCase):
    def documents(self):
        training, context = fixture()
        return training, context, b1d.evaluate(training, context)

    def test_preserves_rule_status_evidence_and_milestone_scope(self):
        training, _, evaluation = self.documents()
        result = b1e.build(evaluation, training)
        self.assertEqual(result["investigation_focus"]["stage"], "AFTER_BIDIRECTIONAL_L0")
        self.assertEqual(result["overall_verdict"], "NOT_CLAIMED")
        for i, f in enumerate(result["findings"]):
            self.assertEqual(f["status"], evaluation["evaluations"][i]["status"])
            self.assertEqual(f["evidence"], evaluation["evaluations"][i]["evidence"])
            self.assertEqual(f["finding_id"], f"B1E-{i+1:03}")
        self.assertEqual(result["findings"][0]["category"], "EXPECTED_CONTEXT")
        self.assertEqual(result["findings"][5]["category"], "OBSERVATION_ONLY")
        self.assertFalse(any(f["is_rule_mismatch"] for f in result["findings"]))

    def test_width_mismatch_is_a_finding_but_not_an_overall_verdict(self):
        t, c = fixture()
        t["phases"][3]["inner_records"][0]["width"] = 2
        result = b1e.build(b1d.evaluate(t, c), t)
        f = next(f for f in result["findings"] if f["rule_id"] == "LINK_WIDTH_SAMPLES")
        self.assertEqual((f["category"], f["status"]), ("RULE_MISMATCH", "FAIL"))
        self.assertEqual(result["overall_verdict"], "NOT_CLAIMED")

    def test_no_l0_does_not_reopen_supported_mux_connectivity(self):
        t, c = fixture()
        t["phases"][4]["steps"] = []
        result = b1e.build(b1d.evaluate(t, c), t)
        self.assertEqual(result["states"]["mux_switch"]["status"], "PASS")
        self.assertEqual(result["investigation_focus"]["stage"], "LINK_ESTABLISHMENT_EVIDENCE_GAP")

    def test_crc_missing_is_unknown_and_nonzero_crc_or_nak_is_not_a_product_fail(self):
        t, c, evaluation = self.documents()
        result = b1e.build(evaluation, t)
        self.assertIsNone(result["observations"]["crc_flags"]["tlp_bad_lcrc"]["count"])
        for p in t["phases"]:
            if p["kind"] != "NO_OBSERVED_EVENTS":
                p["err_subflags"] = {"tlp_bad_lcrc": 0, "dllp_bad_crc": 0}
        t["phases"][1]["err_subflags"]["dllp_bad_crc"] = 1
        t["phases"][1]["inner_records"].append({"kind": "nak", "packet_index": 12, "time_display": "0.1 sec", "channel": "Downstream", "seq": 7})
        result = b1e.build(b1d.evaluate(t, c), t)
        self.assertEqual(result["observations"]["crc_flags"]["dllp_bad_crc"]["count"], 1)
        self.assertEqual(result["observations"]["nak_records"][0]["seq"], 7)
        self.assertFalse(any(f["is_rule_mismatch"] for f in result["findings"]))

    def test_tampered_evaluation_status_source_or_evidence_is_rejected(self):
        t, _, evaluation = self.documents()
        for key, value in (("status", "PASS"), ("evidence", []), ("engineer_questions", [7])):
            with self.subTest(key=key):
                broken = copy.deepcopy(evaluation)
                broken["evaluations"][5][key] = value
                with self.assertRaises(b1e.B1eError):
                    b1e.build(broken, t)

    def test_cli_hash_gates_and_output_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            t, c = fixture()
            raw = json.dumps(t).encode("utf-8")
            source = b"Engineer fixture.\n"
            c["training_sha256"] = hashlib.sha256(raw).hexdigest().upper()
            c["provenance"]["document_sha256"] = hashlib.sha256(source).hexdigest().upper()
            evaluation = b1d.evaluate(t, c)
            evaluation["input"] = {"training_sha256": c["training_sha256"], "source_document_sha256": c["provenance"]["document_sha256"]}
            (root / "evaluation.json").write_text(json.dumps(evaluation), encoding="utf-8")
            (root / "training.json").write_bytes(raw)
            (root / "engineer.md").write_bytes(source)
            args = ["--evaluation", str(root / "evaluation.json"), "--training", str(root / "training.json"), "--source-document", str(root / "engineer.md"), "--output-dir", str(root / "out")]
            self.assertEqual(b1e.main(args), 0)
            output = (root / "out/findings.json").read_bytes()
            self.assertEqual(b1e.main(args), 2)
            self.assertEqual((root / "out/findings.json").read_bytes(), output)
            self.assertEqual((root / "training.json").read_bytes(), raw)
            (root / "training.json").write_bytes(raw + b" ")
            args[-1] = str(root / "changed")
            self.assertEqual(b1e.main(args), 2)
            self.assertFalse((root / "changed").exists())

    def test_real_hang_focus_is_after_l0_without_created_anomalies(self):
        t = json.loads((ROOT / "artifacts/evidence/pcie-b1c-r1-hang-20260915/training.json").read_text(encoding="utf-8"))
        e = json.loads((ROOT / "artifacts/evidence/pcie-b1d-hang-20260930/r2-run1/evaluation.json").read_text(encoding="utf-8"))
        result = b1e.build(e, t)
        self.assertEqual(result["investigation_focus"]["stage"], "AFTER_BIDIRECTIONAL_L0")
        self.assertFalse(any(f["is_rule_mismatch"] for f in result["findings"]))
        self.assertEqual(result["observations"]["nak_records"][0]["packet_index"], 225042)
        self.assertEqual(result["observations"]["crc_flags"]["tlp_bad_lcrc"]["count"], 0)
        self.assertEqual(result["observations"]["crc_flags"]["dllp_bad_crc"]["count"], 0)
        self.assertEqual(next(f for f in result["findings"] if f["rule_id"] == "TS_ERROR_TOLERANCE")["status"], "NOT_EVALUATED")


if __name__ == "__main__":
    unittest.main()
