import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_recovery_observations as p
import s01_contract as s

C = {"LTSSM_STATE_RECOVERY": 101, "LTSSM_STATE_HOT_RESET": 102, "LTSSM_STATE_L0": 103,
     "LTSSM_STATE_RECOVERY_RCVREQL": 104, "LINK_CONDITION_LINK_UP": 7, "LINK_CONDITION_LINK_DOWN": 8}
SHA = "a" * 64


def row(index=10, state=101, valid=1, channel="Upstream", substate=0):
    return {"kind": "ltssm", "packet_index": index, "channel": channel, "time_display": "1.123 sec",
            "state": state, "substate": substate, "subsubstate": 0, "valid": valid}


class RecoveryTests(unittest.TestCase):
    def test_recovery_point_not_entry_interval_or_timeout(self):
        value = p.analyze([row(), row(20, 103)], C, SHA)
        self.assertEqual(value["observations"]["recovery_state"], {"state": "observed", "sample_count": 1})
        self.assertEqual(value["transitions"][0]["elapsed_time"], "unknown")
        self.assertEqual(value["transitions"][0]["continuous_state_interval"], "unknown")
        self.assertEqual(value["entry_exit_qualification"], "NOT_EVALUATED")

    def test_invalid_point_visible_but_not_positive(self):
        value = p.analyze([row(valid=0)], C, SHA)
        self.assertEqual(value["points"][0]["raw"]["state"], 101)
        self.assertEqual(value["points"][0]["validity"], "invalid")
        self.assertEqual(value["observations"]["recovery_state"]["state"], "unknown")

    def test_duplicate_is_one_observation_with_both_refs(self):
        value = p.analyze([row(), row()], C, SHA)
        self.assertEqual(value["observations"]["recovery_state"]["sample_count"], 1)
        self.assertEqual(value["points"][1]["duplicate_of"], 0)
        self.assertEqual([r["source_pointer"] for r in value["points"]], ["/0", "/1"])

    def test_conflicting_same_packet_is_ambiguous(self):
        value = p.analyze([row(), row(state=103)], C, SHA)
        self.assertTrue(all(r["validity"] == "ambiguous" for r in value["points"]))
        self.assertEqual(value["observations"]["recovery_state"]["state"], "unknown")

    def test_eq_and_hot_reset_no_electrical_verdict(self):
        value = p.analyze([row(substate=104), row(20, 102)], C, SHA)
        self.assertEqual(value["observations"]["equalization_state"]["state"], "observed")
        self.assertEqual(value["observations"]["hot_reset_state"]["state"], "observed")
        self.assertEqual(value["physical_reset"], "unknown")
        self.assertEqual(value["coverage"]["perst_sideband"], "unknown")

    def test_missing_direction_unknown_mode_and_empty_not_absence(self):
        value = p.analyze([row()], C, SHA)
        self.assertEqual(value["channels_observed"], ["Upstream"])
        self.assertEqual(value["role_mapping"], "unknown")
        self.assertEqual(value["coverage"]["epoch"], "unknown")
        empty = p.analyze([], C, SHA)
        self.assertTrue(all(v["state"] == "unknown" for v in empty["observations"].values()))

    def test_unknown_state_and_label_not_trusted(self):
        source = row(state=999); source["state_name"] = "RECOVERY"
        value = p.analyze([source], C, SHA)
        self.assertEqual(value["points"][0]["state_name_from_constant"], "unknown")
        self.assertEqual(value["observations"]["recovery_state"]["state"], "unknown")

    def test_order_numeric_types_and_validity_rejected(self):
        for key, bad in [("packet_index", -1), ("state", True), ("valid", 2), ("time_display", "0.1ms")]:
            source = row(); source[key] = bad
            with self.assertRaises(s.ContractError): p.analyze([source], C, SHA)
        with self.assertRaises(s.ContractError): p.analyze([row(20), row(10)], C, SHA)
        constants = copy.deepcopy(C); constants["LTSSM_STATE_HOT_RESET"] = 101
        with self.assertRaises(s.ContractError): p.analyze([row()], constants, SHA)

    def test_link_labels_remain_native_points(self):
        source = {"kind": "link_condition", "packet_index": 10, "channel": "Downstream", "time_display": "1.123 sec", "type": 7}
        value = p.analyze([source], C, SHA)
        self.assertEqual(value["link_condition_points"][0]["name_from_constant"], "LINK_UP")
        self.assertEqual(value["link_condition_points"][0]["electrical_link_state"], "unknown")

    def test_empty_render_is_unknown_not_no_recovery(self):
        value = p.analyze([], C, SHA); value["sources"] = {}; value["limitations"] = ["capture unknown"]
        page = p.render(value, Path.cwd())
        self.assertIn("未知", page); self.assertNotIn("已觀測到 0", page)


if __name__ == "__main__": unittest.main()
