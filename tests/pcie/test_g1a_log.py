import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_g1a_log as g1a


def make_log(body: list[str], done: bool = True) -> str:
    lines = [
        "Running verification script...",
        "Test Description : ",
        "PCIe G1a full-trace TLP count probe - v1",
        g1a.HEADER,
        *body,
    ]
    if done:
        lines += ["", g1a.DONE_MARKER, ""]
    return "\n".join(lines)


PROGRESS = ["PCIE_G1A_PROGRESS|250000|2400000", "PCIE_G1A_PROGRESS|500000|2900000"]
SUMMARY = "PCIE_G1A_SUMMARY|tlp_count=612345|first_index=1944516|first_time= 4.848 sec|last_index=3100000"


class G1aLogTests(unittest.TestCase):
    def test_accepts_complete_count_only_traversal(self):
        result = g1a.check_log(make_log(PROGRESS + [SUMMARY]))
        self.assertEqual(result["status"], "PASS_COUNT_ONLY")
        self.assertEqual(result["tlp_callback_count"], 612345)
        self.assertEqual(result["first_tlp_index"], 1944516)
        self.assertEqual(result["first_tlp_time_display"], "4.848 sec")
        self.assertEqual(result["progress_markers"], 2)
        self.assertIn("total event count (vendor index is an identifier, not a count)", result["not_established"])

    def test_missing_summary_or_done_is_not_a_complete_traversal(self):
        with self.assertRaisesRegex(g1a.G1aLogError, "finish summary"):
            g1a.check_log(make_log(PROGRESS))
        with self.assertRaisesRegex(g1a.G1aLogError, "completion marker"):
            g1a.check_log(make_log(PROGRESS + [SUMMARY], done=False))

    def test_rejects_runtime_error_and_unknown_lines(self):
        with self.assertRaisesRegex(g1a.G1aLogError, "runtime-error"):
            g1a.check_log(make_log(["No events found to be sent", SUMMARY]))
        with self.assertRaisesRegex(g1a.G1aLogError, "Unrecognized"):
            g1a.check_log(make_log(["PCIE_G1A_ROW|1|2", SUMMARY]))

    def test_rejects_inconsistent_progress(self):
        with self.assertRaisesRegex(g1a.G1aLogError, "Progress marker 2"):
            g1a.check_log(make_log(["PCIE_G1A_PROGRESS|250000|10", "PCIE_G1A_PROGRESS|700000|20", SUMMARY]))
        with self.assertRaisesRegex(g1a.G1aLogError, "strictly increasing"):
            g1a.check_log(make_log(["PCIE_G1A_PROGRESS|250000|20", "PCIE_G1A_PROGRESS|500000|20", SUMMARY]))
        behind = "PCIE_G1A_SUMMARY|tlp_count=400000|first_index=1|first_time= 1.000 sec|last_index=3100000"
        with self.assertRaisesRegex(g1a.G1aLogError, "behind"):
            g1a.check_log(make_log(PROGRESS + [behind]))
        with self.assertRaisesRegex(g1a.G1aLogError, "marker count"):
            g1a.check_log(make_log(PROGRESS[:1] + [SUMMARY]))

    def test_zero_tlp_trace_is_reported_without_positions(self):
        zero = "PCIE_G1A_SUMMARY|tlp_count=0|first_index=0|first_time=|last_index=0"
        result = g1a.check_log(make_log([zero]))
        self.assertEqual(result["tlp_callback_count"], 0)
        self.assertIsNone(result["first_tlp_index"])


if __name__ == "__main__":
    unittest.main()
