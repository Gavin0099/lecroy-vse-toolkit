import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_b1a_link_fields as b1a

CAPS = {"ltssm": 500, "linkcond": 200, "speedwidth": 100, "nak": 50, "err": 50}


def counts(**overrides):
    base = {name: 0 for name in b1a.COUNT_NAMES}
    base.update(tlp=704, dllp=10, ordered_set=6, link_condition=2, eie=1, other_event=0,
                dllp_ack=6, dllp_nak=1, dllp_fc=3, os_ts1=3, os_ts2=2, os_skip=1,
                error_events=1, ltssm_present=723, ltssm_changes=2, speed_present=723, width_present=723,
                speed_width_changes=1)
    base.update(overrides)
    return base


def make_log(c=None, caps=CAPS, records=None, events=None, extra=None, done=True):
    c = c or counts()
    events = sum(c[k] for k in ("tlp", "dllp", "ordered_set", "link_condition", "eie", "other_event")) if events is None else events
    records = records if records is not None else [
        "PCIE_B1A_LINKCOND|3000|8.100 sec|Downstream|2",
        "PCIE_B1A_LTSSM|3001|8.101 sec|Downstream|2|4|0|0|1",
        "PCIE_B1A_SPEEDWIDTH|3001|8.101 sec|Downstream|2|3|4",
        "PCIE_B1A_LTSSM|3002|8.102 sec|Upstream|2|4|0|0|1",
        "PCIE_B1A_ERR|225050|9.513 sec|Upstream|2",
        "PCIE_B1A_NAK|225051|9.513 sec|Upstream|17",
        "PCIE_B1A_LINKCOND|1480000|10.900 sec|Downstream|2",
    ]
    lines = ["PCIE_B1A_LINK_FIELDS_V1 caps=" + ",".join(f"{k}:{v}" for k, v in caps.items()), *records, *(extra or [])]
    lines += [f"PCIE_B1A_COUNT|{name}={value}" for name, value in c.items()]
    lines += [f"PCIE_B1A_END|events={events}|reason=trace_end", ""]
    if done:
        lines.append(b1a.DONE_MARKER)
    return "\n".join(lines) + "\n"


class B1aLinkFieldTests(unittest.TestCase):
    def test_accepts_consistent_probe_output(self):
        result = b1a.parse_log(make_log(), {"tlp_callback_count": 704})
        self.assertEqual(result["events"], 723)
        self.assertEqual(len(result["records"]["ltssm"]), 2)
        self.assertEqual(result["records"]["nak"][0], {"channel": "Upstream", "seq": 17, "packet_index": 225051, "time_display": "9.513 sec"})

    def test_rejects_inconsistent_sums(self):
        with self.assertRaisesRegex(b1a.B1aLogError, "END reports"):
            b1a.parse_log(make_log(events=724))
        with self.assertRaisesRegex(b1a.B1aLogError, "DLLP type counts"):
            b1a.parse_log(make_log(counts(dllp_ack=5)))
        with self.assertRaisesRegex(b1a.B1aLogError, "Ordered set type counts"):
            b1a.parse_log(make_log(counts(os_ts1=2)))

    def test_sample_count_must_equal_min_of_population_and_cap(self):
        with self.assertRaisesRegex(b1a.B1aLogError, "ltssm: 2 samples"):
            b1a.parse_log(make_log(counts(ltssm_changes=3)))
        capped = {**CAPS, "ltssm": 1}
        with self.assertRaisesRegex(b1a.B1aLogError, "ltssm: 2 samples"):
            b1a.parse_log(make_log(caps=capped))

    def test_rejects_missing_end_done_runtime_error_and_unknown_lines(self):
        with self.assertRaisesRegex(b1a.B1aLogError, "completion marker"):
            b1a.parse_log(make_log(done=False))
        with self.assertRaisesRegex(b1a.B1aLogError, "runtime-error"):
            b1a.parse_log(make_log(extra=["script error at line 40"]))
        with self.assertRaisesRegex(b1a.B1aLogError, "Unrecognized"):
            b1a.parse_log(make_log(extra=["PCIE_B1A_REPLAY|1|x|y"]))
        with self.assertRaisesRegex(b1a.B1aLogError, "exactly one END"):
            b1a.parse_log(make_log().replace("PCIE_B1A_END|events=723|reason=trace_end\n", ""))

    def test_tlp_count_must_match_g1a(self):
        with self.assertRaisesRegex(b1a.B1aLogError, "differs from G1a"):
            b1a.parse_log(make_log(), {"tlp_callback_count": 703})

    def test_cli_writes_summary_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "b1a.log"
            log.write_text(make_log(), encoding="utf-8")
            out = Path(temporary) / "out"
            self.assertEqual(b1a.main([str(log), "--output-dir", str(out)]), 0)
            self.assertTrue((out / "summary.json").is_file() and (out / "records.json").is_file())
            self.assertEqual(b1a.main([str(log), "--output-dir", str(out)]), 2)


if __name__ == "__main__":
    unittest.main()
