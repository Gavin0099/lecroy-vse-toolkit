#!/usr/bin/env python3
"""PCIe-G3d: bounded TLP context windows around G3a/G3b candidates.

Presentation only: no new candidates, no ranking, no interpretation. Nearby messages are copied
from G3c output, not recomputed. The context size is an explicit presentation heuristic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pcie.g3d-context-windows/v1"
DEFAULT_CONTEXT_ROWS = 5
TRUNCATED = "TRUNCATED_AT_CAPTURE_BOUNDARY"
COMPLETE = "COMPLETE"
LECROY_HINT = (
    "LeCroy PETracer: Search > Go to Packet (Ctrl+G). The trace view also shows DLLP and other "
    "non-TLP packets between the TLP rows listed here."
)


class G3dError(ValueError):
    """Inputs are inconsistent."""


def _bdf(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value >> 8:03d}:{(value >> 3) & 0x1F:02d}.{value & 0x7}"


def _row_table(fields: list[dict[str, Any]], roles: list[dict[str, Any]], associations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(fields) != len(roles):
        raise G3dError("G2a fields and G2b roles differ in length")
    request_by_packet = {q["packet_index"]: q for q in associations}
    request_of_completion = {c["packet_index"]: q["packet_index"] for q in associations for c in q["completions"]}
    table: list[dict[str, Any]] = []
    for position, (field, role) in enumerate(zip(fields, roles), start=1):
        if field["row"] != position or role["row"] != position or field["packet_index"] != role["packet_index"]:
            raise G3dError(f"Row {position} is not aligned between G2a fields and G2b roles")
        association: dict[str, Any] | None = None
        if role["role"] == "NON_POSTED_REQUEST":
            q = request_by_packet.get(field["packet_index"])
            if q is None:
                raise G3dError(f"Request {field['packet_index']} missing from G2b associations")
            association = {"outcome": q["outcome"], "completion_packets": [c["packet_index"] for c in q["completions"]]}
        elif role["role"] == "COMPLETION_CANDIDATE":
            association = {"associated_request_packet": request_of_completion.get(field["packet_index"])}
        status = field["compl_status"]
        previous_packet = table[-1]["packet_index"] if table else None
        table.append({
            "row": position,
            "packet_index": field["packet_index"],
            # Raw distance to the previous TLP row; large values mean non-TLP stretches of the capture.
            "packet_gap_from_previous_tlp_row": None if previous_packet is None else field["packet_index"] - previous_packet,
            "time_display": field["time_display"],
            "channel": field["channel"],
            "tlp_type_hex": field["tlp_type_hex"],
            "vendor_type_name": role["vendor_type_name"],
            "role": role["role"],
            "requester_bdf": _bdf(field["requester_id"]),
            "tag": field["tag"],
            "completer_bdf": _bdf(field["completer_id"]),
            "compl_status": status,
            "compl_status_name": None if status is None else {0: "SC", 1: "UR", 2: "CRS", 4: "CA"}.get(status, "UNKNOWN"),
            "association": association,
        })
    return table


def build(fields, roles, associations, candidates, nearby, context_rows: int = DEFAULT_CONTEXT_ROWS) -> list[dict[str, Any]]:
    if context_rows < 0:
        raise G3dError("Context rows must be non-negative")
    table = _row_table(fields, roles, associations)
    row_of = {r["packet_index"]: r["row"] for r in table}
    nearby_by_id = {c["candidate_id"]: c for c in nearby["candidates"]}
    if set(nearby_by_id) != {c["candidate_id"] for c in candidates}:
        raise G3dError("G3c nearby-message candidates do not match G3 candidates")

    anchors_by_row: dict[int, list[str]] = {}
    for c in candidates:
        packets = ([c["request"]["packet_index"], c["completion"]["packet_index"]]
                   if c["detector"] == "G3A_NON_SUCCESS_COMPLETION"
                   else [c["first_request"]["packet_index"], c["repeated_request"]["packet_index"]])
        for packet in packets:
            if packet not in row_of:
                raise G3dError(f"Candidate {c['candidate_id']} packet {packet} is not a TLP row")
            anchors_by_row.setdefault(row_of[packet], []).append(c["candidate_id"])

    total = len(table)
    results: list[dict[str, Any]] = []
    for c in candidates:
        g3c = nearby_by_id[c["candidate_id"]]
        message_packets = {m["packet"] for m in g3c["nearby_messages"]}
        if c["detector"] == "G3A_NON_SUCCESS_COMPLETION":
            primary, secondary = c["request"]["packet_index"], c["completion"]["packet_index"]
            spans = [("request_to_completion", row_of[primary], row_of[secondary],
                      {row_of[primary]: "ANCHOR_REQUEST", row_of[secondary]: "ANCHOR_COMPLETION"})]
        else:
            primary, secondary = c["first_request"]["packet_index"], c["repeated_request"]["packet_index"]
            spans = [("first_request", row_of[primary], row_of[primary], {row_of[primary]: "ANCHOR_FIRST_REQUEST"}),
                     ("repeated_request", row_of[secondary], row_of[secondary], {row_of[secondary]: "ANCHOR_REPEATED_REQUEST"})]

        def render(row: dict[str, Any], markers: dict[int, str]) -> dict[str, Any]:
            flags = [markers[row["row"]]] if row["row"] in markers else []
            if row["packet_index"] in message_packets:
                flags.append("NEARBY_MESSAGE_G3C")
            others = [cid for cid in anchors_by_row.get(row["row"], []) if cid != c["candidate_id"]]
            return {**row, "markers": flags, "also_anchor_of_candidates": others}

        blocks = []
        for name, lo, hi, markers in spans:
            before_lo = max(1, lo - context_rows)
            after_hi = min(total, hi + context_rows)
            blocks.append({
                "block": name,
                "goto_packet": table[lo - 1]["packet_index"],
                "before": {
                    "status": TRUNCATED if lo - context_rows < 1 else COMPLETE,
                    "rows": [render(r, markers) for r in table[before_lo - 1:lo - 1]],
                },
                "anchor": {"rows": [render(r, markers) for r in table[lo - 1:hi]]},
                "after": {
                    "status": TRUNCATED if hi + context_rows > total else COMPLETE,
                    "rows": [render(r, markers) for r in table[hi:after_hi]],
                },
            })
        results.append({
            "candidate_id": c["candidate_id"],
            "detector": c["detector"],
            "candidate_anchor": {
                "primary_goto_packet": primary,
                "secondary_packet": secondary,
                "anchor_time_display": c["anchor_time_display"],
                "lecroy_hint": LECROY_HINT,
            },
            "context_blocks": blocks,
            "nearby_messages_from_g3c": g3c["nearby_messages"],
            "nearby_messages_excluded_by_g3c_bound": g3c["excluded_beyond_packet_bound"],
            "interpretation": "NOT_EVALUATED",
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name, help_text in (("fields", "G2a fields.json"), ("roles", "G2b roles.json"), ("associations", "G2b associations.json"),
                            ("candidates", "G3 candidates.json"), ("nearby", "G3c nearby_messages.json")):
        parser.add_argument(f"--{name}", type=Path, required=True, help=help_text)
    parser.add_argument("--context-rows", type=int, default=DEFAULT_CONTEXT_ROWS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    names = ("fields", "roles", "associations", "candidates", "nearby")
    try:
        if args.output_dir.exists():
            raise G3dError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raws = {n: getattr(args, n).read_bytes() for n in names}
        data = {n: json.loads(raws[n].decode("utf-8")) for n in names}
        results = build(data["fields"], data["roles"], data["associations"], data["candidates"]["candidates"], data["nearby"], args.context_rows)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G3dError) as exc:
        print(f"G3d not produced: {exc}", file=sys.stderr)
        return 2
    output = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {n: {"path": getattr(args, n).as_posix(), "sha256": hashlib.sha256(raws[n]).hexdigest().upper()} for n in names},
        "context_window": {"unit": "TLP rows in capture order", "rows_before": args.context_rows, "rows_after": args.context_rows,
                           "status": "PRESENTATION_HEURISTIC"},
        "g3c_window_note": "Nearby messages are copied from G3c; its 64-packet bound is a prototype heuristic chosen after seeing v1 results, not a proven PCIe rule.",
        "ground_truth": "UNKNOWN",
        "ranking": "NONE",
        "new_candidates": 0,
        "candidates": results,
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "contexts.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    truncated = sum(1 for r in results for b in r["context_blocks"] for side in ("before", "after") if b[side]["status"] == TRUNCATED)
    print(json.dumps({"schema_version": SCHEMA_VERSION, "candidates": len(results), "context_blocks": sum(len(r["context_blocks"]) for r in results),
                      "truncated_sides": truncated, "context_window": output["context_window"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
