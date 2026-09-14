#!/usr/bin/env python3
"""PCIe-G1d: compare two verified G1b/G1c export directories row by row."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_g1b_rows import COLUMNS, G1bRowsError, canonical_json_bytes, read_tsv, sha256_path  # noqa: E402


def load_export(directory: Path) -> dict[str, Any]:
    tsv_path = directory / "rows.tsv"
    json_path = directory / "rows.json"
    tsv_rows = read_tsv(tsv_path)
    json_bytes = json_path.read_bytes()
    json_rows = json.loads(json_bytes.decode("utf-8"))
    if tsv_rows != json_rows:
        raise G1bRowsError(f"{directory}: rows.tsv and rows.json disagree")
    if canonical_json_bytes(json_rows) != json_bytes:
        raise G1bRowsError(f"{directory}: rows.json is not canonical")
    return {"rows": json_rows, "tsv_sha256": sha256_path(tsv_path), "json_sha256": sha256_path(json_path)}


def compare_exports(first: dict[str, Any], second: dict[str, Any], expected_rows: int | None = None) -> dict[str, Any]:
    left, right = first["rows"], second["rows"]
    if expected_rows is not None and (len(left) != expected_rows or len(right) != expected_rows):
        raise G1bRowsError(f"Row counts {len(left)}/{len(right)} differ from expected {expected_rows}")
    if len(left) != len(right):
        raise G1bRowsError(f"Row counts differ: {len(left)} vs {len(right)}")
    if [row["packet_index"] for row in left] != [row["packet_index"] for row in right]:
        raise G1bRowsError("Packet index sequences differ")
    for a, b in zip(left, right):
        for column in COLUMNS:
            if a[column] != b[column]:
                raise G1bRowsError(f"Row {a['row']} differs in {column}: {a[column]!r} vs {b[column]!r}")
    if first["json_sha256"] != second["json_sha256"] or first["tsv_sha256"] != second["tsv_sha256"]:
        raise G1bRowsError("Canonical TSV/JSON digests differ")
    return {
        "status": "PASS_REPRODUCED",
        "rows": len(left),
        "rows_tsv_sha256": first["tsv_sha256"],
        "rows_json_canonical_sha256": first["json_sha256"],
        "compared_columns": list(COLUMNS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path, help="First verified export directory")
    parser.add_argument("second", type=Path, help="Second verified export directory")
    parser.add_argument("--expected-rows", type=int, help="Required row count, e.g. the G1a total")
    args = parser.parse_args(argv)
    try:
        result = compare_exports(load_export(args.first), load_export(args.second), args.expected_rows)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, G1bRowsError) as exc:
        print(f"G1d exports not reproduced: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
