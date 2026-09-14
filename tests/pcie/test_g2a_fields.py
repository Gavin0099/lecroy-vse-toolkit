import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_g2a_fields as g2a


def g1_rows() -> list[dict]:
    return [
        {"row": 1, "packet_index": 100, "time_display": "5.897 sec", "event_family": "TLP", "channel": "Downstream", "tlp_type_hex": "0x9", "link_width": 1},
        {"row": 2, "packet_index": 105, "time_display": "5.897 sec", "event_family": "TLP", "channel": "Upstream", "tlp_type_hex": "0x12", "link_width": 1},
        {"row": 3, "packet_index": 110, "time_display": "6.055 sec", "event_family": "TLP", "channel": "Downstream", "tlp_type_hex": "0xE", "link_width": 1},
    ]


G1A = {"tlp_callback_count": 3, "first_tlp_index": 100, "last_tlp_index": 110}
ROWS = [
    "PCIE_G2A_TLP|100| 5.897 sec|Downstream|0x9|3|0x0000|NA|NA",
    "PCIE_G2A_TLP|105| 5.897 sec|Upstream|0x12|3|0x0000|0x0100|0",
    "PCIE_G2A_TLP|110| 6.055 sec|Downstream|0xE|NA|0x0000|NA|NA",
]


def make_log(rows=None, end: str = "PCIE_G2A_END|rows=3|reason=trace_end", extra=None) -> str:
    return "\n".join([g2a.HEADER, *(ROWS if rows is None else rows), *(extra or []), end, "", g2a.DONE_MARKER, ""])


class G2aFieldsTests(unittest.TestCase):
    def test_parses_na_as_null_without_defaults(self):
        rows = g2a.parse_fields(make_log(), G1A, g1_rows())
        self.assertEqual(rows[0]["completer_id"], None)
        self.assertEqual(rows[0]["compl_status"], None)
        self.assertEqual(rows[1]["completer_id"], 0x0100)
        self.assertEqual(rows[1]["compl_status"], 0)
        self.assertIsNone(rows[2]["tag"])

    def test_availability_is_reported_per_type(self):
        table = g2a.availability(g2a.parse_fields(make_log(), G1A, g1_rows()))
        self.assertEqual(table["0x9"]["completer_id"], {"present": 0, "null": 1, "distinct_count": 0, "distinct_sample": []})
        self.assertEqual(table["0x12"]["compl_status"]["present"], 1)
        self.assertEqual(list(table), ["0x9", "0xE", "0x12"])

    def test_sample_decodes_routing_ids_and_status(self):
        rows = g2a.parse_fields(make_log(), G1A, g1_rows())
        cpl = g2a.sample(rows, 105)
        self.assertEqual((cpl["requester_bdf"], cpl["completer_bdf"], cpl["compl_status_name"]), ("000:00.0", "001:00.0", "SC"))
        self.assertIsNone(g2a.sample(rows, 100)["completer_bdf"])
        with self.assertRaisesRegex(g2a.G2aFieldsError, "not in the probe output"):
            g2a.sample(rows, 999)

    def test_rows_must_match_g1_export_and_count(self):
        shifted = list(ROWS)
        shifted[1] = shifted[1].replace("|Upstream|", "|Downstream|")
        with self.assertRaisesRegex(g2a.G2aFieldsError, "Row 2 channel differs"):
            g2a.parse_fields(make_log(rows=shifted), G1A, g1_rows())
        with self.assertRaisesRegex(g2a.G2aFieldsError, "Expected 3 rows"):
            g2a.parse_fields(make_log(rows=ROWS[:2]), G1A, g1_rows())
        with self.assertRaisesRegex(g2a.G2aFieldsError, "Expected 3 rows"):
            g2a.parse_fields(make_log(end="PCIE_G2A_END|rows=2|reason=trace_end"), G1A, g1_rows())

    def test_rejects_malformed_values_runtime_error_and_duplicate_end(self):
        bad = list(ROWS)
        bad[0] = bad[0].replace("|3|0x0000|", "|0|0|")
        with self.assertRaisesRegex(g2a.G2aFieldsError, "Unrecognized"):
            g2a.parse_fields(make_log(rows=bad), G1A, g1_rows())
        with self.assertRaisesRegex(g2a.G2aFieldsError, "runtime-error"):
            g2a.parse_fields(make_log(extra=["runtime error: field not found"]), G1A, g1_rows())
        doubled = make_log().replace("PCIE_G2A_END|rows=3|reason=trace_end", "PCIE_G2A_END|rows=3|reason=trace_end\nPCIE_G2A_END|rows=3|reason=trace_end")
        with self.assertRaisesRegex(g2a.G2aFieldsError, "one END"):
            g2a.parse_fields(doubled, G1A, g1_rows())

    def test_outputs_round_trip_and_refuse_existing_directory(self):
        rows = g2a.parse_fields(make_log(), G1A, g1_rows())
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "out"
            tsv, _ = g2a.write_outputs(rows, target)
            self.assertIn("NA", tsv.read_text(encoding="utf-8"))
            with self.assertRaisesRegex(g2a.G2aFieldsError, "existing output directory"):
                g2a.write_outputs(rows, target)


if __name__ == "__main__":
    unittest.main()
