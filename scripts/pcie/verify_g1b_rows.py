#!/usr/bin/env python3
"""Check a saved PCIe-G1b row export log against its verified G1a count, write TSV/JSON, and re-read both."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_inspection_report import InspectionError, parse_vendor_log  # noqa: E402
from verify_g1a_log import DONE_MARKER, RUNTIME_ERROR_RE, G1aLogError, check_log  # noqa: E402


HEADER_RE = re.compile(r"^PCIE_G1B_TLP_ROWS_V2 cap=(?P<cap>\d+) time=vendor_display_text$")
ROW_RE = re.compile(
    r"^PCIE_G1B_TLP\|(?P<index>\d+)\|(?P<time>[^|]+)\|(?P<family>[^|]+)\|"
    r"(?P<channel>[^|]+)\|(?P<type>0x[0-9A-Fa-f]+)\|(?P<width>\d+)$"
)
END_RE = re.compile(r"^PCIE_G1B_END\|rows=(?P<rows>\d+)\|reason=(?P<reason>cap|trace_end)$")
ALLOWED_CAPS = (1000, 10000)
COLUMNS = ("row", "packet_index", "time_display", "event_family", "channel", "tlp_type_hex", "link_width")


class G1bRowsError(ValueError):
    """The log does not establish the expected row export."""


def parse_rows(text: str, g1a: dict[str, Any]) -> tuple[int, str, list[dict[str, Any]]]:
    """Parse rows; the expected count is min(cap, verified G1a TLP callback count)."""
    lines = [line.strip() for line in text.splitlines()]
    headers = [match for line in lines if (match := HEADER_RE.fullmatch(line))]
    if len(headers) != 1:
        raise G1bRowsError("Expected exactly one G1b v2 header")
    cap = int(headers[0]["cap"])
    if cap not in ALLOWED_CAPS:
        raise G1bRowsError(f"Unexpected G1b cap {cap}")
    if lines.count(DONE_MARKER) != 1:
        raise G1bRowsError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise G1bRowsError("The log contains a runtime-error marker")

    rows: list[dict[str, Any]] = []
    ends: list[re.Match[str]] = []
    for line in lines:
        if not line.startswith("PCIE_G1B_") or HEADER_RE.fullmatch(line):
            continue
        if match := ROW_RE.fullmatch(line):
            if ends:
                raise G1bRowsError("Row emitted after the END marker")
            if match["family"] != "TLP":
                raise G1bRowsError(f"Non-TLP family in row {len(rows) + 1}")
            width = int(match["width"])
            if width < 1:
                raise G1bRowsError(f"Invalid link width in row {len(rows) + 1}")
            rows.append(
                {
                    "row": len(rows) + 1,
                    "packet_index": int(match["index"]),
                    "time_display": match["time"].strip(),
                    "event_family": match["family"],
                    "channel": match["channel"].strip(),
                    "tlp_type_hex": "0x" + match["type"][2:].upper(),
                    "link_width": width,
                }
            )
        elif match := END_RE.fullmatch(line):
            ends.append(match)
        else:
            raise G1bRowsError(f"Unrecognized G1b line: {line[:80]}")

    total = g1a["tlp_callback_count"]
    expected_rows = min(cap, total)
    expected_reason = "cap" if total >= cap else "trace_end"
    if len(ends) != 1:
        raise G1bRowsError(f"Expected exactly one END marker; found {len(ends)}")
    end_rows, end_reason = int(ends[0]["rows"]), ends[0]["reason"]
    if end_reason != expected_reason:
        raise G1bRowsError(f"END reason {end_reason} but G1a total {total} with cap {cap} requires {expected_reason}")
    if len(rows) != expected_rows or end_rows != expected_rows:
        raise G1bRowsError(f"Expected {expected_rows} rows (min of cap {cap}, G1a {total}); log has {len(rows)}, END says {end_rows}")
    indices = [row["packet_index"] for row in rows]
    if any(later <= earlier for earlier, later in zip(indices, indices[1:])):
        raise G1bRowsError("Packet indices are not strictly increasing")
    if rows and indices[0] != g1a["first_tlp_index"]:
        raise G1bRowsError("First row index differs from the G1a first TLP index")
    if rows and expected_rows == total and indices[-1] != g1a["last_tlp_index"]:
        raise G1bRowsError("Last row index differs from the G1a last TLP index")
    return cap, end_reason, rows


def crosscheck_d1(rows: list[dict[str, Any]], d1_text: str) -> str:
    """Compare the first five rows with the retained D1 extractor output of the same trace."""
    try:
        d1_rows = parse_vendor_log(d1_text, expected_count=5)
    except InspectionError as exc:
        raise G1bRowsError(f"D1 reference log rejected: {exc}") from exc
    for row, d1 in zip(rows[:5], d1_rows, strict=True):
        pairs = (
            (row["packet_index"], d1["packet_index"]),
            (row["time_display"], d1["extractor_time_display"]),
            (row["channel"], d1["vendor_channel"]),
            (row["tlp_type_hex"], d1["vendor_type_code_hex"]),
            (row["link_width"], d1["link_width"]),
        )
        if any(left != right for left, right in pairs):
            raise G1bRowsError(f"Row {row['row']} differs from the D1 reference")
    return "MATCHED_FIRST_FIVE"


def canonical_json_bytes(rows: list[dict[str, Any]]) -> bytes:
    return (json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_tsv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise G1bRowsError(f"Unexpected TSV columns in {path}")
        return [
            {**raw, "row": int(raw["row"]), "packet_index": int(raw["packet_index"]), "link_width": int(raw["link_width"])}
            for raw in reader
        ]


def write_and_reread(rows: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    if output_dir.exists():
        raise G1bRowsError(f"Refusing to reuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    tsv_path = output_dir / "rows.tsv"
    json_path = output_dir / "rows.json"
    with tsv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("xb") as stream:
        stream.write(canonical_json_bytes(rows))
    if read_tsv(tsv_path) != rows:
        raise G1bRowsError("Re-read TSV does not equal the parsed rows")
    if json.loads(json_path.read_text(encoding="utf-8")) != rows:
        raise G1bRowsError("Re-read JSON does not equal the parsed rows")
    return tsv_path, json_path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Saved G1b VSE output log")
    parser.add_argument("--g1a-log", type=Path, required=True, help="Saved G1a log of the same trace (source of the total)")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for rows.tsv, rows.json, summary.json")
    parser.add_argument("--d1-log", type=Path, help="Retained D1 output log of the same trace (optional)")
    args = parser.parse_args(argv)
    try:
        raw = args.log.read_bytes()
        g1a_raw = args.g1a_log.read_bytes()
        g1a = check_log(g1a_raw.decode("utf-8-sig"))
        cap, reason, rows = parse_rows(raw.decode("utf-8-sig"), g1a)
        d1_status = crosscheck_d1(rows, args.d1_log.read_text(encoding="utf-8-sig")) if args.d1_log else "NOT_RUN"
        tsv_path, json_path = write_and_reread(rows, args.output_dir)
    except (OSError, UnicodeDecodeError, G1aLogError, G1bRowsError) as exc:
        print(f"G1b log not accepted: {exc}", file=sys.stderr)
        return 2

    sample_numbers = sorted({1, (len(rows) + 1) // 2, len(rows)})
    summary = {
        "status": "PASS_ROW_EXPORT",
        "cap": cap,
        "end_reason": reason,
        "rows": len(rows),
        "g1a_tlp_callback_count": g1a["tlp_callback_count"],
        "complete_export": len(rows) == g1a["tlp_callback_count"],
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "g1a_log_sha256": hashlib.sha256(g1a_raw).hexdigest().upper(),
        "log_bytes": len(raw),
        "log_bytes_per_row": round(len(raw) / len(rows), 1) if rows else None,
        "rows_tsv_sha256": sha256_path(tsv_path),
        "rows_json_canonical_sha256": sha256_path(json_path),
        "first_packet_index": rows[0]["packet_index"] if rows else None,
        "last_packet_index": rows[-1]["packet_index"] if rows else None,
        "d1_crosscheck": d1_status,
        "gui_sample_rows_to_check": [rows[number - 1] for number in sample_numbers] if rows else [],
        "not_established": [
            "GUI agreement for sampled rows (checked manually and recorded separately)",
            "wall-clock runtime (recorded from GUI observation)",
            "reproducibility (G1d)",
            "all PETracer events; only TLP callbacks of this subscription are exported",
            "precise timestamps; time_display is coarse vendor display text",
            "transaction fields such as Tag/RequesterId/CompleterId/ComplStatus (G2a)",
        ],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
