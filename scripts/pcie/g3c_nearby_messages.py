#!/usr/bin/env python3
"""PCIe-G3c: attach nearby Message TLPs to G3a/G3b candidates within a fixed TLP-row window.

"Nearby" requires both a bounded count of TLP rows in capture order and a bounded vendor
packet-index distance. Neither bound uses timestamps. The packet bound exists because TLP rows
can be adjacent across long stretches of the capture that contain no TLPs.
Every attachment is temporal correlation only; nothing here states or implies causality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pcie.g3c-nearby-messages/v2"
DEFAULT_WINDOW_TLP_ROWS = 8
DEFAULT_MAX_PACKET_GAP = 64
WINDOW_RATIONALE = (
    "TLP-row window additionally bounded by vendor packet-index distance: v1 (rows only) attached messages "
    "that were row-adjacent but about 148000 packets away across a stretch without TLPs."
)


class G3cError(ValueError):
    """Inputs are inconsistent or unusable."""


def _anchor_spans(candidate: dict[str, Any], row_of: dict[int, int]) -> list[dict[str, Any]]:
    def row(packet: int) -> int:
        if packet not in row_of:
            raise G3cError(f"Candidate {candidate['candidate_id']} packet {packet} is not a TLP row of the G2a export")
        return row_of[packet]

    if candidate["detector"] == "G3A_NON_SUCCESS_COMPLETION":
        packets = [candidate["request"]["packet_index"], candidate["completion"]["packet_index"]]
        return [{"anchors": ["request", "completion"], "packets": packets, "rows": [row(p) for p in packets]}]
    if candidate["detector"] == "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION":
        first = candidate["first_request"]["packet_index"]
        repeated = candidate["repeated_request"]["packet_index"]
        return [
            {"anchors": ["first_request"], "packets": [first], "rows": [row(first)]},
            {"anchors": ["repeated_request"], "packets": [repeated], "rows": [row(repeated)]},
        ]
    raise G3cError(f"Unknown detector {candidate['detector']}")


def attach(candidates: list[dict[str, Any]], fields: list[dict[str, Any]], messages: list[dict[str, Any]],
           window: int = DEFAULT_WINDOW_TLP_ROWS,
           max_packet_gap: int = DEFAULT_MAX_PACKET_GAP) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if window < 0 or max_packet_gap < 0:
        raise G3cError("Window and packet bound must be non-negative")
    row_of = {r["packet_index"]: r["row"] for r in fields}
    if len(row_of) != len(fields):
        raise G3cError("Duplicate packet index in G2a export")
    for m in messages:
        if m["packet_index"] not in row_of:
            raise G3cError(f"Message {m['packet_index']} is not a TLP row of the G2a export")
    results: list[dict[str, Any]] = []
    attached_packets: set[int] = set()
    for candidate in candidates:
        spans = _anchor_spans(candidate, row_of)
        nearby: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for span in spans:
            lo, hi = min(span["rows"]), max(span["rows"])
            span["window_rows"] = [lo - window, hi + window]
            for m in messages:
                m_row = row_of[m["packet_index"]]
                if not lo - window <= m_row <= hi + window:
                    continue
                if lo <= m_row <= hi:
                    position, anchor_packet, row_gap = "inside_anchor_span", span["packets"][0], 0
                elif m_row < lo:
                    position, anchor_packet, row_gap = "before", min(span["packets"]), m_row - lo
                else:
                    position, anchor_packet, row_gap = "after", max(span["packets"]), m_row - hi
                packet_gap = m["packet_index"] - anchor_packet
                if abs(packet_gap) > max_packet_gap:
                    excluded.append({"span_anchors": span["anchors"], "packet": m["packet_index"], "message_name": m["message_code_name"],
                                     "tlp_row_gap": row_gap, "packet_gap": packet_gap, "gap_reference_packet": anchor_packet})
                    continue
                nearby.append({
                    "span_anchors": span["anchors"],
                    "packet": m["packet_index"],
                    "display_time": m["time_display"],
                    "position": position,
                    "tlp_row_gap": row_gap,
                    "packet_gap": packet_gap,
                    "gap_reference_packet": anchor_packet,
                    "message_type": m["tlp_type_hex"],
                    "message_code": m["message_code"],
                    "message_name": m["message_code_name"],
                    "requester_id": m["requester_id"],
                    "routing": m["message_route_name"],
                    "relationship": "temporal_correlation_only",
                })
                attached_packets.add(m["packet_index"])
        results.append({
            "candidate_id": candidate["candidate_id"],
            "detector": candidate["detector"],
            "candidate_packet": candidate["anchor_packet"],
            "candidate_time": candidate["anchor_time_display"],
            "window": {"unit": "TLP rows in capture order", "rows_each_side": window, "max_abs_packet_gap": max_packet_gap,
                       "spans": [{"anchors": s["anchors"], "anchor_packets": s["packets"], "window_rows": s["window_rows"]} for s in spans]},
            "nearby_messages": nearby,
            "excluded_beyond_packet_bound": excluded,
            "interpretation": "NOT_EVALUATED",
        })
    unattached = [
        {"packet": m["packet_index"], "display_time": m["time_display"], "message_name": m["message_code_name"],
         "routing": m["message_route_name"], "requester_id": m["requester_id"]}
        for m in messages if m["packet_index"] not in attached_packets
    ]
    return results, unattached


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True, help="G3 candidates.json")
    parser.add_argument("--fields", type=Path, required=True, help="G2a canonical fields.json")
    parser.add_argument("--messages", type=Path, required=True, help="G3c-0 messages.json")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW_TLP_ROWS, help="TLP rows on each side")
    parser.add_argument("--max-packet-gap", type=int, default=DEFAULT_MAX_PACKET_GAP, help="Maximum absolute vendor packet-index distance")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise G3cError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raws = {name: path.read_bytes() for name, path in (("candidates", args.candidates), ("fields", args.fields), ("messages", args.messages))}
        candidates = json.loads(raws["candidates"].decode("utf-8"))["candidates"]
        results, unattached = attach(candidates, json.loads(raws["fields"].decode("utf-8")), json.loads(raws["messages"].decode("utf-8")), args.window, args.max_packet_gap)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G3cError) as exc:
        print(f"G3c not produced: {exc}", file=sys.stderr)
        return 2
    output = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {name: {"path": path.as_posix(), "sha256": hashlib.sha256(raws[name]).hexdigest().upper()}
                   for name, path in (("candidates", args.candidates), ("fields", args.fields), ("messages", args.messages))},
        "window": {"unit": "TLP rows in capture order", "rows_each_side": args.window, "max_abs_packet_gap": args.max_packet_gap,
                   "rationale": WINDOW_RATIONALE},
        "ground_truth": "UNKNOWN",
        "causality": "NOT_ESTABLISHED",
        "candidates_with_nearby_messages": sum(1 for r in results if r["nearby_messages"]),
        "candidates_total": len(results),
        "attachments_excluded_by_packet_bound": sum(len(r["excluded_beyond_packet_bound"]) for r in results),
        "messages_not_near_any_candidate": unattached,
        "candidates": results,
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "nearby_messages.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("schema_version", "inputs", "window", "candidates_with_nearby_messages", "candidates_total", "attachments_excluded_by_packet_bound", "messages_not_near_any_candidate")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
