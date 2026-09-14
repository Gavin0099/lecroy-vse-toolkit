import copy
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import compare_g1_exports as g1d
import verify_g1b_rows as g1b

D1_LOG = Path(__file__).resolve().parents[2] / "artifacts/evidence/pcie-staircase-20260912/d1-vendor-saved-output.log.txt"
D1_FIRST_FIVE = [(1944516, "0xE"), (1944517, "0x9"), (1944519, "0x9"), (1944521, "0x9"), (1944523, "0x9")]


def index_of(number: int) -> int:
    return D1_FIRST_FIVE[number][0] if number < 5 else 1944523 + 2 * (number - 4)


def g1a_result(total: int) -> dict:
    return {"tlp_callback_count": total, "first_tlp_index": index_of(0), "last_tlp_index": index_of(total - 1)}


def make_log(cap: int = 1000, rows: int = 938, end_rows: int | None = None, reason: str | None = None,
             extra_end: bool = False, extra: list[str] | None = None) -> str:
    body = []
    for number in range(rows):
        type_code = D1_FIRST_FIVE[number][1] if number < 5 else "0x4"
        body.append(f"PCIE_G1B_TLP|{index_of(number)}| 4.848 sec|TLP|Downstream|{type_code}|1")
    reason = reason or ("cap" if rows >= cap else "trace_end")
    end = f"PCIE_G1B_END|rows={rows if end_rows is None else end_rows}|reason={reason}"
    lines = [f"PCIE_G1B_TLP_ROWS_V2 cap={cap} time=vendor_display_text", *body, *(extra or []), end]
    if extra_end:
        lines.append(end)
    lines += ["", g1b.DONE_MARKER, ""]
    return "\n".join(lines)


class G1bRowsTests(unittest.TestCase):
    def test_trace_end_before_cap_exports_every_g1a_tlp(self):
        cap, reason, rows = g1b.parse_rows(make_log(cap=1000, rows=938), g1a_result(938))
        self.assertEqual((cap, reason, len(rows)), (1000, "trace_end", 938))
        self.assertEqual(rows[-1]["packet_index"], index_of(937))
        self.assertEqual(g1b.crosscheck_d1(rows, D1_LOG.read_text(encoding="utf-8-sig")), "MATCHED_FIRST_FIVE")

    def test_cap_reached_before_trace_end(self):
        cap, reason, rows = g1b.parse_rows(make_log(cap=1000, rows=1000), g1a_result(5000))
        self.assertEqual((reason, len(rows)), ("cap", 1000))

    def test_exactly_one_end_with_the_required_reason(self):
        with self.assertRaisesRegex(g1b.G1bRowsError, "exactly one END"):
            g1b.parse_rows(make_log(rows=938, extra_end=True), g1a_result(938))
        with self.assertRaisesRegex(g1b.G1bRowsError, "requires trace_end"):
            g1b.parse_rows(make_log(rows=938, reason="cap"), g1a_result(938))
        with self.assertRaisesRegex(g1b.G1bRowsError, "exactly one END"):
            g1b.parse_rows(make_log(rows=938).replace("PCIE_G1B_END|rows=938|reason=trace_end\n", ""), g1a_result(938))

    def test_row_count_must_match_min_of_cap_and_g1a_total(self):
        with self.assertRaisesRegex(g1b.G1bRowsError, "Expected 938 rows"):
            g1b.parse_rows(make_log(rows=937), g1a_result(938))
        with self.assertRaisesRegex(g1b.G1bRowsError, "Expected 938 rows"):
            g1b.parse_rows(make_log(rows=938, end_rows=937), g1a_result(938))

    def test_first_and_last_index_bind_to_g1a(self):
        shifted = g1a_result(938)
        shifted["last_tlp_index"] += 2
        with self.assertRaisesRegex(g1b.G1bRowsError, "Last row index"):
            g1b.parse_rows(make_log(rows=938), shifted)
        shifted = g1a_result(938)
        shifted["first_tlp_index"] = 1
        with self.assertRaisesRegex(g1b.G1bRowsError, "First row index"):
            g1b.parse_rows(make_log(rows=938), shifted)

    def test_rejects_runtime_error_unknown_line_and_row_after_end(self):
        with self.assertRaisesRegex(g1b.G1bRowsError, "runtime-error"):
            g1b.parse_rows(make_log(extra=["script error at line 3"]), g1a_result(938))
        with self.assertRaisesRegex(g1b.G1bRowsError, "Unrecognized"):
            g1b.parse_rows(make_log(extra=["PCIE_G1B_TAG|5"]), g1a_result(938))
        late = make_log(rows=938).replace(
            "PCIE_G1B_END|rows=938|reason=trace_end", "PCIE_G1B_END|rows=938|reason=trace_end\nPCIE_G1B_TLP|9999999| 4.848 sec|TLP|Downstream|0x4|1"
        )
        with self.assertRaisesRegex(g1b.G1bRowsError, "after the END"):
            g1b.parse_rows(late, g1a_result(938))

    def test_tsv_json_round_trip_and_g1d_reproduction(self):
        _, _, rows = g1b.parse_rows(make_log(rows=938), g1a_result(938))
        with tempfile.TemporaryDirectory() as temporary:
            first, second, third = (Path(temporary) / name for name in ("run1", "run2", "run3"))
            g1b.write_and_reread(rows, first)
            g1b.write_and_reread(copy.deepcopy(rows), second)
            with self.assertRaisesRegex(g1b.G1bRowsError, "existing output directory"):
                g1b.write_and_reread(rows, first)
            result = g1d.compare_exports(g1d.load_export(first), g1d.load_export(second), expected_rows=938)
            self.assertEqual((result["status"], result["rows"]), ("PASS_REPRODUCED", 938))

            changed = copy.deepcopy(rows)
            changed[499]["tlp_type_hex"] = "0x5"
            g1b.write_and_reread(changed, third)
            with self.assertRaisesRegex(g1b.G1bRowsError, "Row 500 differs in tlp_type_hex"):
                g1d.compare_exports(g1d.load_export(first), g1d.load_export(third))
            with self.assertRaisesRegex(g1b.G1bRowsError, "expected 939"):
                g1d.compare_exports(g1d.load_export(first), g1d.load_export(second), expected_rows=939)


if __name__ == "__main__":
    unittest.main()
