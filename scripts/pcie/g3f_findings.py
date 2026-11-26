#!/usr/bin/env python3
"""PCIe-G3f: structured, engineer-readable findings from G3e evidence groups.

One finding per G3e group; membership is not changed. Each finding answers: where to look,
what was observed, why it was surfaced, what else is nearby, and what is not known.
Local segments split a group for reading only, by merging G3d context blocks whose TLP row
ranges overlap. No new distance threshold, no ranking, no interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pcie.g3f-findings/v1"
LECROY_HINT = "LeCroy PETracer: Search > Go to Packet (Ctrl+G)."
BASIS_TEXT = {
    "shared_anchor_packet": "members anchor the same packet",
    "shared_association_lineage": "members are on the same G2b same-key association lineage",
    "request_or_completion_is_other_candidate_anchor": "a request or completion of one member is an anchor of another",
    "none_singleton": "no strong relationship to any other candidate; kept alone",
}
ROLE_OF_BLOCK = {
    "request_to_completion": ("request", "completion"),
    "first_request": ("first_request",),
    "repeated_request": ("repeated_request",),
}


class G3fError(ValueError):
    """Inputs are inconsistent or an invariant failed."""


def _segments(member_ids: list[str], contexts_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for cid in member_ids:
        for block in contexts_by_id[cid]["context_blocks"]:
            rows = block["before"]["rows"] + block["anchor"]["rows"] + block["after"]["rows"]
            blocks.append({
                "candidate_id": cid,
                "block": block["block"],
                "row_lo": rows[0]["row"],
                "row_hi": rows[-1]["row"],
                "anchor_rows": block["anchor"]["rows"],
                "context_rows": rows,
                "truncated": [side for side in ("before", "after") if block[side]["status"] != "COMPLETE"],
            })
    blocks.sort(key=lambda b: (b["row_lo"], b["row_hi"], b["candidate_id"]))
    merged: list[list[dict[str, Any]]] = []
    for b in blocks:
        if merged and b["row_lo"] <= max(x["row_hi"] for x in merged[-1]):
            merged[-1].append(b)
        else:
            merged.append([b])
    return [{"blocks": group, "row_lo": min(b["row_lo"] for b in group), "row_hi": max(b["row_hi"] for b in group)} for group in merged]


def build(groups: dict[str, Any], candidates: list[dict[str, Any]], nearby: dict[str, Any], contexts: dict[str, Any],
          fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cand_by_id = {c["candidate_id"]: c for c in candidates}
    contexts_by_id = {c["candidate_id"]: c for c in contexts["candidates"]}
    nearby_by_id = {c["candidate_id"]: c for c in nearby["candidates"]}
    row_of = {f["packet_index"]: f["row"] for f in fields}
    detectors = groups.get("detectors") or {}
    if not (set(cand_by_id) == set(contexts_by_id) == set(nearby_by_id)):
        raise G3fError("Candidate ids differ between G3, G3c and G3d")

    findings: list[dict[str, Any]] = []
    seen: list[str] = []
    for number, g in enumerate(groups["groups"], start=1):
        members = g["members"]
        seen.extend(members)
        segments = _segments(members, contexts_by_id)
        segment_out = []
        segment_anchor_packets: list[set[int]] = []
        for seg in segments:
            segment_anchor_packets.append({
                r["packet_index"] for b in seg["blocks"] for r in b["anchor_rows"]
                if any(m.startswith("ANCHOR_") for m in r["markers"])
            })
        # Place each G3c message in the segment holding the anchor G3c measured it from;
        # fall back to the segment whose context rows contain it.
        message_segment: dict[int, int] = {}
        for cid in members:
            for m in nearby_by_id[cid]["nearby_messages"]:
                if m["packet"] in message_segment:
                    continue
                reference = m.get("gap_reference_packet")
                target = next((i for i, packets in enumerate(segment_anchor_packets) if reference in packets), None)
                if target is None:
                    m_row = row_of.get(m["packet"])
                    target = next((i for i, seg in enumerate(segments) if m_row is not None and seg["row_lo"] <= m_row <= seg["row_hi"]), None)
                if target is not None:
                    message_segment[m["packet"]] = target
        message_info = {m["packet"]: m for cid in members for m in nearby_by_id[cid]["nearby_messages"]}
        for index, (letter, seg) in enumerate(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", segments)):
            anchors: dict[int, dict[str, Any]] = {}
            for b in seg["blocks"]:
                for r in b["anchor_rows"]:
                    if not any(m.startswith("ANCHOR_") for m in r["markers"]):
                        continue
                    entry = anchors.setdefault(r["packet_index"], {
                        "packet": r["packet_index"], "display_time": r["time_display"], "channel": r["channel"],
                        "type": r["vendor_type_name"], "requester": r["requester_bdf"], "tag": r["tag"],
                        "completer": r["completer_bdf"], "status": r["compl_status_name"], "roles": [],
                    })
                    for marker in r["markers"]:
                        if marker.startswith("ANCHOR_"):
                            entry["roles"].append(f"{b['candidate_id']}:{marker[len('ANCHOR_'):].lower()}")
            messages = {
                packet: {"packet": packet, "message": message_info[packet]["message_name"],
                         "display_time": message_info[packet]["display_time"], "relationship": "temporal_correlation_only"}
                for packet, target in message_segment.items() if target == index
            }
            segment_out.append({
                "segment": letter,
                "go_to_packet": min(anchors),
                "display_times": sorted({a["display_time"] for a in anchors.values()}),
                "anchor_packet_range": [min(anchors), max(anchors)],
                "anchors": [anchors[p] for p in sorted(anchors)],
                "candidates": sorted({b["candidate_id"] for b in seg["blocks"]}),
                "nearby_messages": [messages[p] for p in sorted(messages)],
                "context_refs": [{"candidate_id": b["candidate_id"], "g3d_block": b["block"],
                                  "tlp_rows": [b["row_lo"], b["row_hi"]], "truncated_sides": b["truncated"]} for b in seg["blocks"]],
            })
        unplaced = sorted(set(message_info) - set(message_segment))

        member_detectors = sorted({cand_by_id[cid]["detector"] for cid in members})
        anchor_packets = g["anchor_packets"]
        crosschecks = [
            {"candidate_id": cid, "result": cand_by_id[cid]["gui_crosscheck"]["result"],
             "lecroy_view": cand_by_id[cid]["gui_crosscheck"]["lecroy_view"].split(" (")[0]}
            for cid in members if cand_by_id[cid].get("gui_crosscheck")
        ]
        unknowns = [
            "Interpretation NOT_EVALUATED: no statement that this is abnormal, a fault, or related to the reported failure.",
            "Ground truth for the trace is UNKNOWN.",
        ]
        span = anchor_packets[-1] - anchor_packets[0]
        if len(segment_out) > 1 and len(members) > 1:
            unknowns.append(
                f"Grouping expresses {', '.join(BASIS_TEXT[b] for b in g['grouping_basis'])}. It does not establish that "
                f"observations in separate local segments (trace span {span} packets) belong to the same failure episode."
            )
        elif len(segment_out) > 1:
            unknowns.append(
                f"This candidate's anchors lie in separate local segments (trace span {span} packets). Their shared association key "
                f"does not establish that they belong to the same failure episode."
            )
        if any(s["nearby_messages"] for s in segment_out):
            unknowns.append("Nearby messages are temporal correlation only; causality is NOT ESTABLISHED. G3c's 64-packet bound is a prototype heuristic chosen after seeing its v1 results.")
        if "G3A_NON_SUCCESS_COMPLETION" in member_detectors:
            checked = {c["candidate_id"] for c in crosschecks}
            unchecked = [cid for cid in members if cand_by_id[cid]["detector"] == "G3A_NON_SUCCESS_COMPLETION" and cid not in checked]
            if unchecked:
                unknowns.append(f"Request/completion association for {', '.join(unchecked)} rests on the G2b nearest-preceding same-key rule and was not GUI-cross-checked.")
        if "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION" in member_detectors:
            unknowns.append("Same-key reappearance does not establish a requester retransmission, an illegal Tag reuse, or a completion missing from the capture.")

        findings.append({
            "finding_id": f"F{number:03d}",
            "group_id": g["group_id"],
            "where_to_look": {
                "primary_go_to_packet": g["primary_go_to_packet"],
                "primary_rule": g["primary_go_to_rule"],
                "segment_go_to_packets": [s["go_to_packet"] for s in segment_out],
                "lecroy_hint": LECROY_HINT,
            },
            "what_was_observed": {
                "candidate_observations": g["observations"],
                "local_segments": segment_out,
                "nearby_messages_outside_segments": unplaced,
            },
            "why_surfaced": {
                "detectors": [{"detector": d, "surfaces": detectors.get(d, {}).get("surfaces")} for d in member_detectors],
                "grouping_basis": g["grouping_basis"],
                "grouping_basis_text": [BASIS_TEXT[b] for b in g["grouping_basis"]],
                "group_relationship": g["relationship"],
                "members": members,
            },
            "gui_crosschecks": crosschecks,
            "trace_span_packets": anchor_packets[-1] - anchor_packets[0],
            "not_known": unknowns,
            "interpretation": "NOT_EVALUATED",
        })
    if sorted(seen) != sorted(cand_by_id) or len(seen) != len(set(seen)):
        raise G3fError("Every candidate must appear in exactly one finding")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    names = ("groups", "candidates", "nearby", "contexts", "fields")
    for n in names:
        parser.add_argument(f"--{n}", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise G3fError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raws = {n: getattr(args, n).read_bytes() for n in names}
        data = {n: json.loads(raws[n].decode("utf-8")) for n in names}
        g3 = data["candidates"]
        groups = {**data["groups"], "detectors": g3["detectors"]}
        findings = build(groups, g3["candidates"], data["nearby"], data["contexts"], data["fields"])
        after = {n: hashlib.sha256(getattr(args, n).read_bytes()).hexdigest().upper() for n in names}
        if after != {n: hashlib.sha256(raws[n]).hexdigest().upper() for n in names}:
            raise G3fError("An input changed during G3f")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G3fError) as exc:
        print(f"G3f not produced: {exc}", file=sys.stderr)
        return 2
    output = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {n: {"path": getattr(args, n).as_posix(), "sha256": after[n]} for n in names},
        "trace_ground_truth": "UNKNOWN",
        "ordering": "capture order of primary Go to Packet; not a ranking",
        "segmentation": "G3d context blocks merged when their TLP row ranges overlap; display only, membership unchanged",
        "findings_total": len(findings),
        "findings": findings,
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "findings.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema_version": SCHEMA_VERSION, "findings_total": len(findings),
                      "multi_segment_findings": sum(1 for f in findings if len(f["what_was_observed"]["local_segments"]) > 1)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
