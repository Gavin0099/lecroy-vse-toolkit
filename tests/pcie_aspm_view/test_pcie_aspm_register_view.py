import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_aspm_register_view as p

SHA = "AA" * 32


def inputs(raw=0x42, known=0xffff):
    data, mask = [0] * 1024, [0] * 1024; data[0x90 // 4] = raw; mask[0x90 // 4] = known
    snapshot = {"bdf": 256, "pre": [{"path": "fixture", "sha256": SHA}], "packets": {"10": {"GetData": [data, mask], "entries": []}}, "identities_unchanged": True, "process_exit_ok": True}
    log = {"schema": "pcie.b2b-config-access/v1", "trace": {"sha256": SHA}, "anchors": {"disconnect_packet": 20, "reconnect_packet": 30}, "accesses": []}
    cap = {"device_id": 256, "epoch": "before_disconnect", "registers": {"LinkControl": {"byte_offset": 0x90, "capability_evidence": [{"completion_packet": 5}]}}}
    return snapshot, log, cap, p.rd.load(p.DEFINITION)


class AspmTests(unittest.TestCase):
    def test_independent_bit_examples_and_no_effective_state(self):
        for raw, expected in [(0x42, [2, 1, 0]), (0x100, [0, 0, 1])]:
            value = p.build(*inputs(raw), 10)
            self.assertEqual([r["catc_merged"]["value"] for r in value["register_view"]["rows"]], expected)
            self.assertEqual(value["effective_state"], "UNKNOWN")
            self.assertEqual(value["policy_result"], "NOT_EVALUATED")
            self.assertEqual(value["clkreq_electrical_action"], "unknown")

    def test_partial_mask_preserves_unknown_clock_bits(self):
        value = p.build(*inputs(0x142, 3), 10)
        self.assertEqual([r["catc_merged"]["value"] for r in value["register_view"]["rows"]], [2, None, None])
        self.assertTrue(all(r["last_read_back"]["value"] is None for r in value["register_view"]["rows"]))

    def test_missing_rc_and_wire_state_are_unknown(self):
        value = p.build(*inputs(), 10)
        self.assertEqual(value["rc_observations"], "unknown")
        self.assertEqual(value["wire_ltssm_pm_observations"], "unknown")
        self.assertEqual(value["l1ss_named_fields"], "not_qualified")

    def test_wrong_device_epoch_offset_and_future_discovery_rejected(self):
        for change in ["device", "epoch", "offset", "discovery"]:
            snapshot, log, cap, definition = inputs()
            if change == "device": snapshot["bdf"] = 0
            elif change == "epoch": cap["epoch"] = "after_reconnect"
            elif change == "offset": cap["registers"]["LinkControl"]["byte_offset"] = 0x80
            else: cap["registers"]["LinkControl"]["capability_evidence"][0]["completion_packet"] = 11
            with self.assertRaises(ValueError): p.build(snapshot, log, cap, definition, 10)

    def test_snapshot_hash_or_integrity_mismatch_rejected(self):
        snapshot, log, cap, definition = inputs(); snapshot["pre"][0]["sha256"] = "BB" * 32
        with self.assertRaises(ValueError): p.build(snapshot, log, cap, definition, 10)
        snapshot, log, cap, definition = inputs(); snapshot["identities_unchanged"] = False
        with self.assertRaises(ValueError): p.build(snapshot, log, cap, definition, 10)

    def test_definition_cannot_slide_bit_or_add_opaque_policy(self):
        snapshot, log, cap, definition = inputs(); definition["registers"][0]["fields"][1]["lsb"] = 7
        with self.assertRaises(ValueError): p.build(snapshot, log, cap, definition, 10)
        snapshot, log, cap, definition = inputs(); definition["registers"][0]["fields"].append(copy.deepcopy(definition["registers"][0]["fields"][0]))
        with self.assertRaises(ValueError): p.build(snapshot, log, cap, definition, 10)


if __name__ == "__main__": unittest.main()
