"""Handwritten observation fixtures implement the engineer Q1-Q7 contract.

Expected statuses are explicit acceptance requirements, not production-derived
values. The real-case test checks B1c-x2's independent 384,993-event evidence.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "pcie"))
import b1d_mux_rules as b1d


def fixture():
    def state(packet, channel, name, valid=1, time="1.4 sec"):
        return {"kind": "ltssm", "packet_index": packet, "time_display": time, "channel": channel,
                "state": name, "state_valid": valid}

    def phase(first, last, time, kind, steps, inner=None, samples=None, errors=0):
        return {"kind": kind, "first_index": first, "last_index": last, "first_time": time, "last_time": time,
                "events": last - first + 1, "counts": {"os_ts1": errors}, "err_any": errors,
                "error_subtype": "UNKNOWN" if errors else None, "steps": steps,
                "inner_records": inner or [], "gui_samples": samples or [], "ltssm_at_start": {}}

    phases = [
        phase(10, 10, "0.0 sec", "DETECT", [
            {"kind": "link_condition", "packet_index": 10, "time_display": "0.0 sec", "channel": "Upstream", "type_name": "LINK_DOWN"},
            state(10, "Upstream", "DETECT", 0, "0.0 sec")]),
        phase(11, 19, "0.1 sec", "POLLING", [state(11, "Downstream", "POLLING", 0, "0.1 sec")], errors=8),
        {"kind": "NO_OBSERVED_EVENTS", "after_index": 19, "after_time": "0.1 sec", "before_index": 20, "before_time": "1.4 sec", "duration_seconds": "1.3"},
        phase(20, 29, "1.4 sec", "CONFIG", [
            {"kind": "link_condition", "packet_index": 20, "time_display": "1.4 sec", "channel": "Upstream", "type_name": "LINK_UP"},
            state(20, "Upstream", "POLLING"), state(22, "Downstream", "CONFIG")],
            inner=[{"kind": "speed_width", "packet_index": 21, "time_display": "1.4 sec", "channel": "Upstream", "speed": 0, "width": 1}],
            samples=[{"packet_index": 21, "speed": "2.5", "width": "x1", "gui_error_labels": ["TSRsrvErr"]}], errors=2),
        phase(30, 32, "1.4 sec", "L0", [state(30, "Downstream", "L0"), state(31, "Upstream", "L0")],
            inner=[{"kind": "tlp", "packet_index": 32, "time_display": "1.4 sec", "channel": "Upstream", "tlp_type": 13}]),
    ]
    training = {"schema": "pcie.b1c-training-timeline/v2", "input": {"summary_status": "PASS_WINDOW_EXPORT", "window": {"start": 10, "end": 32}},
                "phases": phases, "unknowns": ["GUI subtype sample only; raw speed labels not probed"]}
    context = {
        "schema": "pcie.b1d-product-context/v1", "provenance": {"source_kind": "owner_relayed_engineer_answers", "document": "engineer.md", "received_date": "2026-09-30"},
        "operation": {"kind": "sde_insert_mux_switch", "interposer": "between_rc_and_mux", "to_device": "SDE", "disconnect_packet": 10, "reconnect_packet": 20, "approx_disconnect_seconds": "1.4"},
        "expectations": {"width": 1, "target_speed_gt_s": "8.0", "link_down_expected": True,
                         "disconnect_recovery_polling_or_silence_allowed": True, "new_device_initialization_required": True},
        "rule_questions": {"SWITCH_LINK_DOWN": [1], "DISCONNECT_ACTIVITY": [1, 2, 3], "MUX_CONNECTIVITY": [7], "BIDIRECTIONAL_L0": [2],
                           "LINK_WIDTH_SAMPLES": [4], "INITIAL_GEN1_SAMPLE": [], "TARGET_SPEED_OBSERVED": [4], "MUX_DISCONNECT_DURATION": [1, 3],
                           "TRAINING_TIMEOUT": [2, 3], "TS_ERROR_TOLERANCE": [5], "HOTPLUG_INIT_ACTIVITY": [2, 6], "DEVICE_INITIALIZATION_COMPLETED": [2, 6]},
        "case": {"reported_symptom": "owner-reported device not visible; BSOD 0x124"},
    }
    return training, context


def statuses(doc):
    return {r["rule_id"]: r["status"] for r in doc["evaluations"]}


class B1dTests(unittest.TestCase):
    def test_bilateral_training_is_supported_but_initialization_remains_unknown(self):
        t, c = fixture()
        result = b1d.evaluate(t, c)
        self.assertEqual(statuses(result), {
            "SWITCH_LINK_DOWN": "PASS", "DISCONNECT_ACTIVITY": "PASS", "MUX_CONNECTIVITY": "PASS", "BIDIRECTIONAL_L0": "PASS",
            "LINK_WIDTH_SAMPLES": "PASS", "INITIAL_GEN1_SAMPLE": "INCONCLUSIVE", "TARGET_SPEED_OBSERVED": "INCONCLUSIVE",
            "MUX_DISCONNECT_DURATION": "NOT_EVALUATED", "TRAINING_TIMEOUT": "NOT_EVALUATED", "TS_ERROR_TOLERANCE": "NOT_EVALUATED",
            "HOTPLUG_INIT_ACTIVITY": "INCONCLUSIVE", "DEVICE_INITIALIZATION_COMPLETED": "NOT_EVALUATED"})
        self.assertEqual(result["states"]["mux_switch"]["state"], "MUX_SWITCH_COMPLETED")
        self.assertIsNone(result["states"]["device_initialization"]["value"])
        self.assertEqual(result["overall_verdict"], "NOT_CLAIMED")
        self.assertFalse(any(d["blocks_this_version"] for d in result["validation_debt"]))

    def test_one_sided_training_does_not_claim_mux_failure_or_completion(self):
        t, c = fixture()
        t["phases"][3]["steps"] = [r for r in t["phases"][3]["steps"] if r.get("channel") != "Downstream"]
        # Downstream training before reconnect cannot satisfy Q7.
        t["phases"][1]["steps"][0]["state_valid"] = 1
        result = b1d.evaluate(t, c)
        self.assertEqual(statuses(result)["MUX_CONNECTIVITY"], "INCONCLUSIVE")
        self.assertEqual(result["states"]["mux_switch"]["state"], "MUX_SWITCH_COMPLETION_NOT_ESTABLISHED")

    def test_invalid_and_carried_states_cannot_supply_training_evidence(self):
        for variant in ("invalid", "carried"):
            with self.subTest(variant=variant):
                t, c = fixture()
                if variant == "invalid":
                    t["phases"][3]["steps"][-1]["state_valid"] = 0
                else:
                    t["phases"][3]["steps"].pop()
                    t["phases"][3]["ltssm_at_start"] = {"Downstream": {"state": "POLLING", "state_valid": 1}}
                self.assertEqual(statuses(b1d.evaluate(t, c))["MUX_CONNECTIVITY"], "INCONCLUSIVE")

    def test_only_one_valid_l0_cannot_start_bilateral_initialization_check(self):
        for variant in ("missing", "invalid"):
            with self.subTest(variant=variant):
                t, c = fixture()
                if variant == "missing":
                    t["phases"][4]["steps"].pop()
                else:
                    t["phases"][4]["steps"][1]["state_valid"] = 0
                t["phases"][4]["inner_records"][0].update(channel="Downstream", tlp_type=9)
                result = b1d.evaluate(t, c)
                self.assertEqual(statuses(result)["BIDIRECTIONAL_L0"], "INCONCLUSIVE")
                self.assertEqual(statuses(result)["HOTPLUG_INIT_ACTIVITY"], "INCONCLUSIVE")

    def test_mux_connectivity_can_pass_without_any_l0(self):
        t, c = fixture()
        t["phases"][4]["steps"] = []
        result = b1d.evaluate(t, c)
        self.assertEqual(statuses(result)["MUX_CONNECTIVITY"], "PASS")
        self.assertEqual(statuses(result)["BIDIRECTIONAL_L0"], "INCONCLUSIVE")
        self.assertEqual(result["states"]["mux_switch"]["state"], "MUX_SWITCH_COMPLETED")
        self.assertEqual(result["states"]["link_l0"]["state"], "BIDIRECTIONAL_L0_NOT_ESTABLISHED")
        connectivity = next(r for r in result["evaluations"] if r["rule_id"] == "MUX_CONNECTIVITY")
        self.assertEqual(connectivity["engineer_questions"], [7])
        self.assertEqual({e["state"] for e in connectivity["evidence"]}, {"POLLING", "CONFIG"})

    def test_l0_alone_does_not_replace_the_q7_training_criterion(self):
        t, c = fixture()
        t["phases"][3]["steps"] = [r for r in t["phases"][3]["steps"] if r["kind"] != "ltssm"]
        s = statuses(b1d.evaluate(t, c))
        self.assertEqual(s["MUX_CONNECTIVITY"], "INCONCLUSIVE")
        self.assertEqual(s["BIDIRECTIONAL_L0"], "PASS")

    def test_initial_gen1_is_observation_without_an_engineer_acceptance_rule(self):
        t, c = fixture()
        result = b1d.evaluate(t, c)
        sample = next(r for r in result["evaluations"] if r["rule_id"] == "INITIAL_GEN1_SAMPLE")
        self.assertEqual(sample["status"], "INCONCLUSIVE")
        self.assertEqual(sample["assessment_kind"], "observation_only")
        self.assertEqual(sample["engineer_questions"], [])
        self.assertEqual(sample["evidence"][0]["speed"], "2.5")
        self.assertEqual(result["observations"]["initial_speed_sample"]["packet_index"], 21)
        self.assertNotIn("初始 Gen1 可出現", sample["summary"])
        c["expectations"]["initial_gen1_allowed"] = True
        with self.assertRaisesRegex(b1d.B1dError, "No engineer acceptance rule"):
            b1d.evaluate(t, c)

    def test_target_speed_wording_distinguishes_absent_and_present_samples(self):
        t, c = fixture()
        absent = next(r for r in b1d.evaluate(t, c)["evaluations"] if r["rule_id"] == "TARGET_SPEED_OBSERVED")
        self.assertEqual(absent["status"], "INCONCLUSIVE")
        self.assertEqual(absent["evidence"], [])
        self.assertIn("未在既有 GUI speed 樣本中觀察到", absent["summary"])
        self.assertNotIn("曾觀察到 target rate", absent["limitation"])
        t["phases"][3]["gui_samples"][0]["speed"] = "8.0"
        present = next(r for r in b1d.evaluate(t, c)["evaluations"] if r["rule_id"] == "TARGET_SPEED_OBSERVED")
        self.assertEqual(present["status"], "PASS")
        self.assertIn("曾觀察到 target rate", present["limitation"])

    def test_width_mismatch_is_fail_even_when_other_samples_are_x1(self):
        for variant in ("record", "gui"):
            with self.subTest(variant=variant):
                t, c = fixture()
                if variant == "record":
                    t["phases"][3]["inner_records"][0]["width"] = 2
                else:
                    t["phases"][3]["gui_samples"][0]["width"] = "x2"
                result = b1d.evaluate(t, c)
                self.assertEqual(statuses(result)["LINK_WIDTH_SAMPLES"], "FAIL")
                self.assertEqual(result["overall_verdict"], "NOT_CLAIMED")

    def test_no_width_sample_is_inconclusive(self):
        t, c = fixture()
        t["phases"][3]["inner_records"] = []
        t["phases"][3]["gui_samples"] = []
        self.assertEqual(statuses(b1d.evaluate(t, c))["LINK_WIDTH_SAMPLES"], "INCONCLUSIVE")

    def test_unprobed_raw_speed_code_cannot_prove_gen3(self):
        t, c = fixture()
        t["phases"][3]["inner_records"][0]["speed"] = 2
        t["phases"][3]["gui_samples"] = []
        s = statuses(b1d.evaluate(t, c))
        self.assertEqual(s["TARGET_SPEED_OBSERVED"], "INCONCLUSIVE")
        self.assertEqual(s["INITIAL_GEN1_SAMPLE"], "INCONCLUSIVE")

    def test_gui_gen3_speed_is_observed_without_using_capability_data_rate(self):
        t, c = fixture()
        sample = t["phases"][3]["gui_samples"][0]
        sample["fields"] = {"data_rate": "8.0 GT/s, 16.0 GT/s"}
        self.assertEqual(statuses(b1d.evaluate(t, c))["TARGET_SPEED_OBSERVED"], "INCONCLUSIVE")
        sample["speed"] = "8.0"
        s = statuses(b1d.evaluate(t, c))
        self.assertEqual(s["TARGET_SPEED_OBSERVED"], "PASS")
        self.assertEqual(s["DEVICE_INITIALIZATION_COMPLETED"], "NOT_EVALUATED")

    def test_gen1_sample_after_l0_is_not_mislabeled_as_initial_training(self):
        t, c = fixture()
        sample = t["phases"][3]["gui_samples"].pop()
        sample["packet_index"] = 32
        t["phases"][4]["gui_samples"].append(sample)
        s = statuses(b1d.evaluate(t, c))
        self.assertEqual(s["INITIAL_GEN1_SAMPLE"], "INCONCLUSIVE")
        self.assertEqual(s["TARGET_SPEED_OBSERVED"], "INCONCLUSIVE")

    def test_config_request_is_activity_not_initialization_completion(self):
        t, c = fixture()
        t["phases"][4]["inner_records"][0].update(channel="Downstream", tlp_type=9)
        result = b1d.evaluate(t, c)
        self.assertEqual(statuses(result)["HOTPLUG_INIT_ACTIVITY"], "PASS")
        self.assertEqual(result["states"]["hotplug_activity"]["state"], "HOTPLUG_INIT_OBSERVED")
        self.assertEqual(statuses(result)["DEVICE_INITIALIZATION_COMPLETED"], "NOT_EVALUATED")
        self.assertIsNone(result["states"]["device_initialization"]["value"])

    def test_config_before_l0_or_in_wrong_direction_does_not_satisfy_activity(self):
        for variant in ("before_l0", "upstream"):
            with self.subTest(variant=variant):
                t, c = fixture()
                record = {"kind": "tlp", "packet_index": 25 if variant == "before_l0" else 32,
                          "time_display": "1.4 sec", "channel": "Downstream" if variant == "before_l0" else "Upstream", "tlp_type": 9}
                t["phases"][3 if variant == "before_l0" else 4]["inner_records"].append(record)
                self.assertEqual(statuses(b1d.evaluate(t, c))["HOTPLUG_INIT_ACTIVITY"], "INCONCLUSIVE")

    def test_no_numeric_thresholds_are_invented_for_time_or_errors(self):
        t, c = fixture()
        t["phases"][2].update(before_time="2.8 sec", duration_seconds="2.7")
        for phase in t["phases"][3:]:
            phase.update(first_time="2.8 sec", last_time="2.8 sec")
            for r in phase["steps"] + phase["inner_records"]:
                r["time_display"] = "2.8 sec"
        result = b1d.evaluate(t, c)
        self.assertEqual(result["observations"]["switch_link_down_to_reconnect_seconds"], "2.8")
        self.assertEqual(result["observations"]["has_errors"], 10)
        for rule in ("MUX_DISCONNECT_DURATION", "TRAINING_TIMEOUT", "TS_ERROR_TOLERANCE"):
            self.assertEqual(statuses(result)[rule], "NOT_EVALUATED")

    def test_bad_evidence_and_unattributed_context_are_rejected(self):
        changes = [
            lambda t, c: t.update(schema="pcie.b1c-training-timeline/v1"),
            lambda t, c: t["input"].update(summary_status="FAIL"),
            lambda t, c: c["provenance"].update(source_kind="anonymous_guess"),
            lambda t, c: c["rule_questions"].pop("MUX_CONNECTIVITY"),
            lambda t, c: t["phases"][3].update(first_index=19),
            lambda t, c: t["phases"][3].update(last_time="0.0 sec"),
            lambda t, c: t["phases"][3].update(err_any=-1),
            lambda t, c: t["phases"][3]["inner_records"][0].update(packet_index=999),
            lambda t, c: t["phases"][3]["gui_samples"][0].update(packet_index=999),
            lambda t, c: t["phases"][3]["steps"][1].update(state_valid=True),
            lambda t, c: t["phases"][2].update(duration_seconds="1.4"),
            lambda t, c: c["expectations"].update(width=2),
            lambda t, c: c["operation"].update(reconnect_packet=19),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                t, c = fixture()
                change(t, c)
                with self.assertRaises((b1d.B1dError, KeyError)):
                    b1d.evaluate(t, c)

    def test_every_record_pointer_resolves_to_the_original_input(self):
        t, c = fixture()
        result = b1d.evaluate(t, c)
        for rule in result["evaluations"]:
            for e in rule["evidence"]:
                node = t
                for part in e["source"].strip("/").split("/"):
                    node = node[int(part)] if isinstance(node, list) else node[part]
                if "packet_index" in e:
                    self.assertEqual(node["packet_index"], e["packet_index"])
                elif "count" in e:
                    self.assertEqual(node["err_any"], e["count"])
                    self.assertEqual(node["first_index"], e["first_index"])
                else:
                    self.assertEqual(node["kind"], "NO_OBSERVED_EVENTS")
                    self.assertEqual(node["after_index"], e["after_index"])

    def cli_files(self, directory):
        t, c = fixture()
        raw = (json.dumps(t) + "\n").encode("utf-8")
        source = b"Engineer Q1-Q7 fixture; Gen3 x1; no numeric time limit.\n"
        root = Path(directory)
        (root / "training.json").write_bytes(raw)
        (root / "engineer.md").write_bytes(source)
        c["training_sha256"] = hashlib.sha256(raw).hexdigest().upper()
        c["provenance"]["document_sha256"] = hashlib.sha256(source).hexdigest().upper()
        (root / "context.json").write_text(json.dumps(c), encoding="utf-8")
        return ["--training", str(root / "training.json"), "--context", str(root / "context.json"), "--source-document", str(root / "engineer.md"), "--output-dir", str(root / "out")]

    def test_cli_writes_traceable_outputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.cli_files(temp)
            root = Path(temp)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(b1d.main(args), 0)
            document = json.loads((root / "out/evaluation.json").read_text(encoding="utf-8"))
            markdown = (root / "out/evaluation.md").read_text(encoding="utf-8")
            self.assertEqual(document["overall_verdict"], "NOT_CLAIMED")
            self.assertIn("INITIAL_GEN1_SAMPLE | INCONCLUSIVE", markdown)
            self.assertIn("trace 觀察；無工程師接受規則", markdown)
            self.assertIn("TARGET_SPEED_OBSERVED | INCONCLUSIVE", markdown)
            self.assertIn("TRAINING_TIMEOUT | NOT_EVALUATED", markdown)
            self.assertIn("僅代表此 sample", markdown)
            output_before = (root / "out/evaluation.json").read_bytes()
            self.assertEqual(b1d.main(args), 2)
            self.assertEqual((root / "out/evaluation.json").read_bytes(), output_before)
            for name, raw in before.items():
                self.assertEqual((root / name).read_bytes(), raw)

    def test_cli_rejects_changed_training_or_engineer_source_before_writing(self):
        for name in ("training.json", "engineer.md"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                args = self.cli_files(temp)
                path = Path(temp) / name
                path.write_bytes(path.read_bytes() + b" ")
                self.assertEqual(b1d.main(args), 2)
                self.assertFalse((Path(temp) / "out").exists())

    def test_real_hang_evidence_has_scoped_results_without_reopening_b1c(self):
        directory = ROOT / "artifacts/evidence/pcie-b1d-hang-20260930"
        t = json.loads((ROOT / "artifacts/evidence/pcie-b1c-r1-hang-20260915/training.json").read_text(encoding="utf-8"))
        c = json.loads((directory / "product-context-r1.json").read_text(encoding="utf-8"))
        result = b1d.evaluate(t, c)
        s = statuses(result)
        self.assertEqual(result["observations"]["has_errors"], 384993)  # Independent B1c-x2 total.
        self.assertEqual(result["observations"]["switch_link_down_to_reconnect_seconds"], "1.400")
        for rule in ("MUX_CONNECTIVITY", "BIDIRECTIONAL_L0", "LINK_WIDTH_SAMPLES"):
            self.assertEqual(s[rule], "PASS")
        for rule in ("INITIAL_GEN1_SAMPLE", "TARGET_SPEED_OBSERVED", "HOTPLUG_INIT_ACTIVITY"):
            self.assertEqual(s[rule], "INCONCLUSIVE")
        for rule in ("TRAINING_TIMEOUT", "TS_ERROR_TOLERANCE", "DEVICE_INITIALIZATION_COMPLETED"):
            self.assertEqual(s[rule], "NOT_EVALUATED")
        l0 = next(r for r in result["evaluations"] if r["rule_id"] == "BIDIRECTIONAL_L0")
        self.assertEqual([e["packet_index"] for e in l0["evidence"]], [1484273, 1484298])


if __name__ == "__main__":
    unittest.main()
