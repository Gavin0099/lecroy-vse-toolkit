import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))

import verify_b1b0_constants as b1b0

VALUES = {"_PKT_TLP": 2, "_PKT_DLLP": 3, "_PKT_ORDERED_SET": 5, "_PKT_LINK_CONDITION": 6, "_CHANNEL_1": 1, "_CHANNEL_2": 2,
          "LINK_CONDITION_LINK_DOWN": 1, "LINK_CONDITION_LINK_UP": 2, "LTSSM_STATE_DETECT": 1, "LTSSM_STATE_POLLING": 2,
          "LTSSM_STATE_CONFIG": 3, "LTSSM_STATE_L0": 4, "LTSSM_STATE_RECOVERY": 5}


def make(values=VALUES, extra=(), done=True):
    lines = ["Test Description :", b1b0.HEADER, *[f"PCIE_B1B0_CONST|{k}={v}" for k, v in values.items()], *extra, b1b0.END, ""]
    if done:
        lines.append(b1b0.DONE_MARKER)
    return "\n".join(lines)


class B1b0Tests(unittest.TestCase):
    def test_parses_constants(self):
        self.assertEqual(b1b0.parse(make()), VALUES)

    def test_rejects_missing_duplicate_and_non_distinct_packet_events(self):
        with self.assertRaisesRegex(b1b0.B1b0Error, "Missing constants"):
            b1b0.parse(make({k: v for k, v in VALUES.items() if k != "LTSSM_STATE_L0"}))
        with self.assertRaisesRegex(b1b0.B1b0Error, "Duplicate"):
            b1b0.parse(make(extra=["PCIE_B1B0_CONST|_PKT_TLP=2"]))
        with self.assertRaisesRegex(b1b0.B1b0Error, "not distinct"):
            b1b0.parse(make({**VALUES, "_PKT_DLLP": 2}))

    def test_rejects_runtime_error_and_missing_done(self):
        with self.assertRaisesRegex(b1b0.B1b0Error, "runtime-error"):
            b1b0.parse(make(extra=["script error at line 3"]))
        with self.assertRaisesRegex(b1b0.B1b0Error, "completion marker"):
            b1b0.parse(make(done=False))


if __name__ == "__main__":
    unittest.main()
