#!/usr/bin/env python3
"""Check a saved PCIe-G2a field probe log against the verified G1 export and summarize field availability by TLP type."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_g1a_log import DONE_MARKER, RUNTIME_ERROR_RE, G1aLogError, check_log  # noqa: E402
from verify_g1b_rows import canonical_json_bytes  # noqa: E402


HEADER = "PCIE_G2A_TLP_FIELDS_V1 fields=tag,requester_id,completer_id,compl_status"
ROW_RE = re.compile(
    r"^PCIE_G2A_TLP\|(?P<index>\d+)\|(?P<time>[^|]+)\|(?P<channel>[^|]+)\|(?P<type>0x[0-9A-Fa-f]+)\|"
    r"(?P<tag>NA|\d+)\|(?P<requester>NA|0x[0-9A-Fa-f]{4})\|(?P<completer>NA|0x[0-9A-Fa-f]{4})\|(?P<status>NA|\d+)$"
)
END_RE = re.compile(r"^PCIE_G2A_END\|rows=(?P<rows>\d+)\|reason=trace_end$")
FIELDS = ("tag", "requester_id", "completer_id", "compl_status")
COLUMNS = ("row", "packet_index", "time_display", "channel", "tlp_type_hex", *FIELDS)
# PCIe completion status codes as used by the installed vendor compliance scripts (CRS is 2 per the PCIe spec).
STATUS_NAMES = {0: "SC", 1: "UR", 2: "CRS", 4: "CA"}


class G2aFieldsError(ValueError):
    """The log does not establish a complete, G1-consistent field probe."""


def decode_bdf(value: int | None) -> str | None:
    """Render a 16-bit routing ID as bus:device.function (vendor GUI shows the same three parts)."""
    if value is None:
        return None
    return f"{value >> 8:03d}:{(value >> 3) & 0x1F:02d}.{value & 0x7}"


def parse_fields(text: str, g1a: dict[str, Any], g1_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines()]
    if lines.count(HEADER) != 1:
        raise G2aFieldsError("Expected exactly one G2a header")
    if lines.count(DONE_MARKER) != 1:
        raise G2aFieldsError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise G2aFieldsError("The log contains a runtime-error marker")

    rows: list[dict[str, Any]] = []
    ends: list[int] = []
    for line in lines:
        if not line.startswith("PCIE_G2A_") or line == HEADER:
            continue
        if match := ROW_RE.fullmatch(line):
            if ends:
                raise G2aFieldsError("Row emitted after the END marker")
            rows.append(
                {
                    "row": len(rows) + 1,
                    "packet_index": int(match["index"]),
                    "time_display": match["time"].strip(),
                    "channel": match["channel"].strip(),
                    "tlp_type_hex": "0x" + match["type"][2:].upper(),
                    "tag": None if match["tag"] == "NA" else int(match["tag"]),
                    "requester_id": None if match["requester"] == "NA" else int(match["requester"], 16),
                    "completer_id": None if match["completer"] == "NA" else int(match["completer"], 16),
                    "compl_status": None if match["status"] == "NA" else int(match["status"]),
                }
            )
        elif match := END_RE.fullmatch(line):
            ends.append(int(match["rows"]))
        else:
            raise G2aFieldsError(f"Unrecognized G2a line: {line[:80]}")

    total = g1a["tlp_callback_count"]
    if ends != [total] or len(rows) != total:
        raise G2aFieldsError(f"Expected {total} rows and one END reporting {total}; log has {len(rows)} rows, END {ends}")
    if len(g1_rows) != total:
        raise G2aFieldsError("G1 export row count differs from the G1a total")
    for row, ref in zip(rows, g1_rows):
        for key in ("packet_index", "time_display", "channel", "tlp_type_hex"):
            if row[key] != ref[key]:
                raise G2aFieldsError(f"Row {row['row']} {key} differs from the verified G1 export")
    return rows


def availability(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per vendor TLP type code: how many rows had each field non-null, and the distinct values seen (capped)."""
    table: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["tlp_type_hex"]].append(row)
    for code in sorted(grouped, key=lambda value: int(value, 16)):
        group = grouped[code]
        entry: dict[str, Any] = {"rows": len(group)}
        for field in FIELDS:
            values = [row[field] for row in group if row[field] is not None]
            distinct = sorted(set(values))
            entry[field] = {
                "present": len(values),
                "null": len(group) - len(values),
                "distinct_count": len(distinct),
                "distinct_sample": distinct[:8],
            }
        table[code] = entry
    return table


def sample(rows: list[dict[str, Any]], packet_index: int) -> dict[str, Any]:
    for row in rows:
        if row["packet_index"] == packet_index:
            return {
                **row,
                "requester_bdf": decode_bdf(row["requester_id"]),
                "completer_bdf": decode_bdf(row["completer_id"]),
                "compl_status_name": None if row["compl_status"] is None else STATUS_NAMES.get(row["compl_status"], "UNKNOWN"),
            }
    raise G2aFieldsError(f"Sample packet {packet_index} is not in the probe output")


def write_outputs(rows: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    if output_dir.exists():
        raise G2aFieldsError(f"Refusing to reuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    tsv_path = output_dir / "fields.tsv"
    json_path = output_dir / "fields.json"
    with tsv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: ("NA" if row[key] is None else row[key]) for key in COLUMNS} for row in rows)
    with json_path.open("xb") as stream:
        stream.write(canonical_json_bytes(rows))
    if json.loads(json_path.read_text(encoding="utf-8")) != rows:
        raise G2aFieldsError("Re-read JSON does not equal the parsed rows")
    with tsv_path.open(encoding="utf-8", newline="") as stream:
        if sum(1 for _ in csv.DictReader(stream, delimiter="\t")) != len(rows):
            raise G2aFieldsError("Re-read TSV row count differs")
    return tsv_path, json_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Saved G2a VSE output log")
    parser.add_argument("--g1a-log", type=Path, required=True, help="Verified G1a log of the same trace")
    parser.add_argument("--g1-rows", type=Path, required=True, help="Verified G1 canonical rows.json of the same trace")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for fields.tsv, fields.json, summary.json")
    parser.add_argument("--sample", type=int, action="append", default=[], help="Packet index to print for GUI comparison")
    args = parser.parse_args(argv)
    try:
        raw = args.log.read_bytes()
        g1a = check_log(args.g1a_log.read_bytes().decode("utf-8-sig"))
        g1_rows = json.loads(args.g1_rows.read_text(encoding="utf-8"))
        rows = parse_fields(raw.decode("utf-8-sig"), g1a, g1_rows)
        samples = [sample(rows, index) for index in args.sample]
        tsv_path, json_path = write_outputs(rows, args.output_dir)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, G1aLogError, G2aFieldsError) as exc:
        print(f"G2a log not accepted: {exc}", file=sys.stderr)
        return 2

    summary = {
        "status": "PASS_FIELD_PROBE_OUTPUT",
        "rows": len(rows),
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "g1_rows_sha256": hashlib.sha256(args.g1_rows.read_bytes()).hexdigest().upper(),
        "fields_tsv_sha256": hashlib.sha256(tsv_path.read_bytes()).hexdigest().upper(),
        "fields_json_canonical_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest().upper(),
        "availability_by_tlp_type": availability(rows),
        "gui_samples": samples,
        "not_established": [
            "GUI agreement of sample values (compared separately against retained GUI screenshots)",
            "whether a non-null value on a TLP type is meaningful for that type (a reader may return 0 instead of null)",
            "request/completion pairing (G2b)",
            "vendor TLP type code to TLP name mapping beyond GUI-observed samples",
        ],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
