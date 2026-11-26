import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_g3c0_messages as g3c0

G2A = [
    {"packet_index": 10, "time_display": "4.848 sec", "channel": "Downstream", "tlp_type_hex": "0xE", "requester_id": 0},
    {"packet_index": 20, "time_display": "4.853 sec", "channel": "Upstream", "tlp_type_hex": "0x11", "requester_id": 0},
    {"packet_index": 30, "time_display": "4.853 sec", "channel": "Upstream", "tlp_type_hex": "0xD", "requester_id": 0x100},
]
ROWS = [
    "PCIE_G3C0_MSG|10| 4.848 sec|Downstream|0xE|0x0000|0x7F|0x4",
    "PCIE_G3C0_MSG|30| 4.853 sec|Upstream|0xD|0x0100|0x30|0x0",
]


def make_log(rows=None, end="PCIE_G3C0_END|tlps=3|messages=2|reason=trace_end", extra=None):
    return "\n".join([g3c0.HEADER, *(ROWS if rows is None else rows), *(extra or []), end, "", g3c0.DONE_MARKER, ""])


class G3c0Tests(unittest.TestCase):
    def test_maps_codes_and_routes_from_vendor_constants(self):
        rows = g3c0.parse_messages(make_log(), 3, G2A)
        self.assertEqual((rows[1]["message_code_name"], rows[1]["message_route_name"]), ("ERR_COR", "TOROOTCOMPLEX"))
        self.assertEqual(rows[0]["message_code_name"], "VENDOR1")

    def test_na_fields_stay_null_and_unknown_codes_are_unmapped(self):
        rows = g3c0.parse_messages(make_log(rows=[ROWS[0].replace("|0x7F|0x4", "|NA|NA"), ROWS[1].replace("|0x30|", "|0x6A|")]), 3, G2A)
        self.assertIsNone(rows[0]["message_code"])
        self.assertIsNone(rows[0]["message_code_name"])
        self.assertEqual(rows[1]["message_code_name"], "UNMAPPED")

    def test_counts_and_identity_bind_to_g1a_and_g2a(self):
        with self.assertRaisesRegex(g3c0.G3c0Error, "G1a verified 4"):
            g3c0.parse_messages(make_log(), 4, G2A)
        with self.assertRaisesRegex(g3c0.G3c0Error, "Expected 2 message rows"):
            g3c0.parse_messages(make_log(rows=ROWS[:1], end="PCIE_G3C0_END|tlps=3|messages=1|reason=trace_end"), 3, G2A)
        with self.assertRaisesRegex(g3c0.G3c0Error, "requester_id differs"):
            g3c0.parse_messages(make_log(rows=[ROWS[0], ROWS[1].replace("|0x0100|", "|0x0000|")]), 3, G2A)

    def test_rejects_runtime_error_and_duplicate_end(self):
        with self.assertRaisesRegex(g3c0.G3c0Error, "runtime-error"):
            g3c0.parse_messages(make_log(extra=["runtime error: MessageRoute"]), 3, G2A)
        doubled = make_log().replace("PCIE_G3C0_END|tlps=3|messages=2|reason=trace_end", "PCIE_G3C0_END|tlps=3|messages=2|reason=trace_end\nPCIE_G3C0_END|tlps=3|messages=2|reason=trace_end")
        with self.assertRaisesRegex(g3c0.G3c0Error, "exactly one END"):
            g3c0.parse_messages(doubled, 3, G2A)


if __name__ == "__main__":
    unittest.main()
