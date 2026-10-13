import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_field_probe as p
import s01_contract as s

SHA = "c" * 64


def oracle_row(profile, native_type=0):
    # Explicit independent applicability sets from fixture-oracles.md.
    if profile == "dllp":
        applies = {"AckNak_SeqNum", "BadCRC", "InvalidEncoding", "FCError"} if native_type == 0 else {"VC_ID", "HdrFC", "DataFC", "HdrScale", "DataScale", "BadCRC", "InvalidEncoding", "FCError"}
        fields = ["AckNak_SeqNum", "VC_ID", "HdrFC", "DataFC", "HdrScale", "DataScale", "BadCRC", "InvalidEncoding", "FCError"]
    else:
        applies = {"Type", "Fmt", "PSN", "Length", "BadLCRC", "BadECRC", "ErrorLengthField"}
        if native_type == 18: applies |= {"ByteCount", "LowerAddr", "ComplStatus"}
        fields = ["Type", "Fmt", "PSN", "Length", "ByteCount", "LowerAddr", "ComplStatus", "BadLCRC", "BadECRC", "ErrorLengthField"]
    return {"kind": "p03-row", "profile": profile, "index": 1000, "level": 0, "channel": 1, "native_type": native_type,
            "time2": [0, 12, 0], "fields": {f: {"state": "available", "value": 0} if f in applies else {"state": "not_applicable", "value": None} for f in fields}}


class P03Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.plan = p.prepare(Path(self.tmp.name) / "plan", SHA)

    def fixture(self, profile="dllp", native_type=0, present=True):
        types = [0, 1, 4, 5, 6, 12, 13, 14, 8, 9, 10] if profile == "dllp" else [1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19, 20]
        records = [oracle_row(profile, native_type)] if present else []
        records += [{"kind": "p03-count", "native_type": t, "visited": int(present and t == native_type)} for t in types]
        records.append({"kind": "p03-end", "visited": int(present), "known": int(present), "emitted": int(present), "mismatches": 0, "native_level": 0})
        run = {"status": "COM_RUN_COMPLETE", "identities_unchanged": True,
               "steps": {"finish_event": {"result_name": "DONE"}, "close": {"ok": True}, "process_exit": {"ok": True}},
               "pre": {"script": {"sha256": self.plan["profiles"][profile]}, "files": [{"sha256": SHA}]}}
        return run, records

    def assess(self, run, records, profile="dllp"):
        return p.assess(run, [json.dumps(r, separators=(",", ":")) for r in records], self.plan, profile)

    def test_ack_fc_request_completion_oracles(self):
        for profile, native_type in [("dllp", 0), ("dllp", 8), ("tlp", 1), ("tlp", 18)]:
            with self.subTest(profile=profile, native_type=native_type):
                run, rows = self.fixture(profile, native_type)
                value = self.assess(run, rows, profile)
                self.assertEqual(value["rows"][0], rows[0]); self.assertEqual(value["qualification"], "NOT_EVALUATED")

    def test_unknown_not_unsupported(self):
        run, rows = self.fixture(); rows[0]["fields"]["AckNak_SeqNum"] = {"state": "unknown", "value": None}
        self.assertEqual(self.assess(run, rows)["rows"][0]["fields"]["AckNak_SeqNum"]["state"], "unknown")
        for state in ["unsupported", "not_applicable", "not_observed", "available"]:
            rows[0]["fields"]["AckNak_SeqNum"]["state"] = state
            with self.assertRaises(s.ContractError): self.assess(run, rows)

    def test_zero_length_and_scales_are_raw(self):
        run, rows = self.fixture("tlp", 1)
        self.assertEqual(self.assess(run, rows, "tlp")["rows"][0]["fields"]["Length"]["value"], 0)
        run, rows = self.fixture("dllp", 8)
        self.assertEqual(self.assess(run, rows)["scale_semantics"], "raw_vendor_encoding_only")

    def test_inapplicable_credit_value_rejected(self):
        run, rows = self.fixture(); rows[0]["fields"]["HdrFC"] = {"state": "available", "value": 0}
        with self.assertRaises(s.ContractError): self.assess(run, rows)

    def test_boolean_negative_and_extra_field_rejected(self):
        for bad in [True, -1, "0"]:
            run, rows = self.fixture(); rows[0]["fields"]["AckNak_SeqNum"]["value"] = bad
            with self.assertRaises(s.ContractError): self.assess(run, rows)
        run, rows = self.fixture(); rows[0]["fields"]["hidden_verdict"] = {"state": "available", "value": 1}
        with self.assertRaises(s.ContractError): self.assess(run, rows)

    def test_empty_is_unknown(self):
        run, rows = self.fixture(present=False); value = self.assess(run, rows)
        self.assertEqual(value["rows"], []); self.assertEqual(value["counts"]["0"]["observation"], "unknown")

    def test_integrity_close_binding_failure(self):
        for key in ["integrity", "close", "source", "script", "finish"]:
            run, rows = self.fixture()
            if key == "integrity": run["identities_unchanged"] = False
            elif key == "close": run["steps"]["close"]["ok"] = False
            elif key == "source": run["pre"]["files"][0]["sha256"] = "f" * 64
            elif key == "script": run["pre"]["script"]["sha256"] = "f" * 64
            else: run["steps"]["finish_event"]["result_name"] = "PASSED"
            with self.assertRaises(s.ContractError): self.assess(run, rows)

    def test_duplicate_truncated_end_and_type_counts(self):
        run, rows = self.fixture()
        for bad in [rows + [rows[-1]], rows[:-1], rows[:1] + rows[2:], rows[:1] + [rows[1]] + rows[1:], rows[1:] + rows[:1]]:
            with self.assertRaises(s.ContractError): self.assess(run, bad)

    def test_denominator_and_namespace(self):
        for key, val in [("emitted", 2), ("visited", 0), ("native_level", 4), ("mismatches", 1)]:
            run, rows = self.fixture(); rows[-1][key] = val
            with self.assertRaises(s.ContractError): self.assess(run, rows)

    def test_sample_cap_and_order(self):
        run, rows = self.fixture()
        row = rows[0]; samples = [dict(copy.deepcopy(row), index=1000 + i) for i in range(8)]
        rows[1]["visited"] = 9; rows[-1].update(visited=9, known=9, emitted=8)
        records = samples + rows[1:]
        self.assertEqual(len(self.assess(run, records)["rows"]), 8)
        records[1]["index"] = 1000
        with self.assertRaises(s.ContractError): self.assess(run, records)

    def test_plan_mutation(self):
        for key, val in [("cap_per_type", 9), ("selection", "whole_capture"), ("schema_version", "legacy")]:
            plan = copy.deepcopy(self.plan); plan[key] = val
            with self.assertRaises(s.ContractError): p.validate_plan(plan)
        self.assertEqual(hashlib.sha256(p.script("dllp").encode()).hexdigest(), self.plan["profiles"]["dllp"])


if __name__ == "__main__": unittest.main()
