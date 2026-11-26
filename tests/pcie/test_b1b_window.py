import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))

import verify_b1b_window as b1b


def seg_lines(n, first, last, events, tlp=0, err=0, ack=0, fc=0, ts1=0):
    return [
        f"PCIE_B1B_SEG|{n}|{first}|9.5{n:02d} sec|{last}|9.5{n:02d} sec|{events}|{tlp}",
        f"PCIE_B1B_SEGPKT|{n}|{ack}|0|{fc}|0|0|{ts1}|0|0|0|0|0",
        f"PCIE_B1B_SEGERR|{n}|{err}|0|{err}|0|0|0|0|0|0|0|0|0|0|0",
    ]


def make_log(extra=None, end="PCIE_B1B_END|events=30|tlp=2|err_any=5|segments=2|reason=trace_end", done=True, header="PCIE_B1B_WINDOW_V1 start=100 end=200"):
    lines = [header,
             "PCIE_B1B_LINKCOND|100| 9.512 sec|Upstream|1",
             "PCIE_B1B_LTSSM|100| 9.512 sec|Upstream|6|1|0|34|0",
             "PCIE_B1B_NAK|101| 9.512 sec|Downstream|1682",
             "PCIE_B1B_TLP|102| 9.512 sec|Downstream|9",
             "PCIE_B1B_TLP|107| 9.512 sec|Downstream|9",
             *seg_lines(1, 100, 109, 10, tlp=2, ack=1, fc=5),
             "PCIE_B1B_LTSSM|110| 9.513 sec|Downstream|5|5|12|0|1",
             "PCIE_B1B_SPEEDWIDTH|110| 9.513 sec|Downstream|5|0|1",
             *(extra or []),
             *seg_lines(2, 110, 200, 20, err=5, ts1=15),
             end, ""]
    if done:
        lines.append(b1b.DONE_MARKER)
    return "\n".join(lines) + "\n"


class B1bWindowTests(unittest.TestCase):
    def test_accepts_consistent_export_and_crosschecks_tlp(self):
        result = b1b.parse_export(make_log(), [{"packet_index": 50}, {"packet_index": 102}, {"packet_index": 107}, {"packet_index": 300}])
        self.assertEqual(result["totals"], {"events": 30, "tlp": 2, "err_any": 5, "segments": 2})
        self.assertEqual([r["kind"] for r in result["records"]], ["link_condition", "ltssm", "nak", "tlp", "tlp", "ltssm", "speed_width"])

    def test_rejects_sum_and_tlp_mismatches(self):
        with self.assertRaisesRegex(b1b.B1bWindowError, "event count"):
            b1b.parse_export(make_log(end="PCIE_B1B_END|events=31|tlp=2|err_any=5|segments=2|reason=trace_end"))
        with self.assertRaisesRegex(b1b.B1bWindowError, "TLP or error"):
            b1b.parse_export(make_log(end="PCIE_B1B_END|events=30|tlp=2|err_any=4|segments=2|reason=trace_end"))
        with self.assertRaisesRegex(b1b.B1bWindowError, "differ from the G1 export"):
            b1b.parse_export(make_log(), [{"packet_index": 102}])

    def test_rejects_records_outside_window_and_broken_segments(self):
        with self.assertRaisesRegex(b1b.B1bWindowError, "outside the window"):
            b1b.parse_export(make_log(extra=["PCIE_B1B_NAK|250| 9.6 sec|Downstream|1"]))
        with self.assertRaisesRegex(b1b.B1bWindowError, "are not 1"):
            b1b.parse_export(make_log(end="PCIE_B1B_END|events=30|tlp=2|err_any=5|segments=3|reason=trace_end"))
        broken = make_log().replace("PCIE_B1B_SEGPKT|2|0|0|0|0|0|15|0|0|0|0|0\n", "")
        with self.assertRaisesRegex(b1b.B1bWindowError, "triples"):
            b1b.parse_export(broken)

    def test_rejects_runtime_error_unknown_line_and_missing_done(self):
        with self.assertRaisesRegex(b1b.B1bWindowError, "runtime-error"):
            b1b.parse_export(make_log(extra=["script error at line 9"]))
        with self.assertRaisesRegex(b1b.B1bWindowError, "Unrecognized"):
            b1b.parse_export(make_log(extra=["PCIE_B1B_REPLAY|120|x|y"]))
        with self.assertRaisesRegex(b1b.B1bWindowError, "completion marker"):
            b1b.parse_export(make_log(done=False))

    def test_timeline_names_codes_with_constants(self):
        result = b1b.parse_export(make_log())
        constants = {"_PKT_LINK_CONDITION": 6, "_PKT_ORDERED_SET": 5, "LTSSM_STATE_DETECT": 1, "LTSSM_STATE_RECOVERY": 5,
                     "LTSSM_STATE_RECOVERY_RCVRLOCK": 12, "LTSSM_STATE_UNDEFINED": 0, "LTSSM_NO_STATE": 34, "LINK_CONDITION_LINK_DOWN": 1}
        timeline = b1b.build_timeline(result, constants)
        self.assertEqual(timeline[0]["kind"], "segment")
        ltssm = [r for r in timeline if r["kind"] == "ltssm"]
        self.assertEqual([r["state_name"] for r in ltssm], ["DETECT", "RECOVERY.RECOVERY_RCVRLOCK"])
        self.assertEqual(next(r for r in timeline if r["kind"] == "link_condition")["type_name"], "LINK_DOWN")

    def test_cli_writes_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "b1b.txt"
            log.write_text(make_log(), encoding="utf-8")
            out = Path(temporary) / "out"
            self.assertEqual(b1b.main([str(log), "--output-dir", str(out)]), 0)
            self.assertEqual(json.loads((out / "summary.json").read_text(encoding="utf-8"))["status"], "PASS_WINDOW_EXPORT")
            self.assertEqual(b1b.main([str(log), "--output-dir", str(out)]), 2)


if __name__ == "__main__":
    unittest.main()
