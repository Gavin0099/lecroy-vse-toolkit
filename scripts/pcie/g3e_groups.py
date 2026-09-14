#!/usr/bin/env python3
"""PCIe-G3e: group G3a/G3b candidates by shared evidence only.

Merging uses exactly three strong relationships, fixed before looking at results:
  1. shared_anchor_packet: two candidates anchor the same packet;
  2. shared_association_lineage: their G2b same-key reissue chains end at the same request;
  3. request_or_completion_is_other_candidate_anchor: a G3a request/completion is another
     candidate's anchor (recorded in addition to shared_anchor_packet).
Same time, same nearby message, overlapping context, same RequesterId/Tag or same status
never merge on their own. No severity, confidence, priority or interpretation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pcie.g3e-candidate-groups/v1"
REISSUED = "SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED"
G3A = "G3A_NON_SUCCESS_COMPLETION"
G3B = "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION"


class G3eError(ValueError):
    """Inputs are inconsistent or grouping invariants failed."""


def _anchors(c: dict[str, Any]) -> list[tuple[int, str]]:
    if c["detector"] == G3A:
        return [(c["request"]["packet_index"], "request"), (c["completion"]["packet_index"], "completion")]
    if c["detector"] == G3B:
        return [(c["first_request"]["packet_index"], "first_request"), (c["repeated_request"]["packet_index"], "repeated_request")]
    raise G3eError(f"Unknown detector {c['detector']}")


def _lineage_end(packet: int, by_packet: dict[int, dict[str, Any]]) -> tuple[int, list[int]]:
    chain = [packet]
    current = by_packet.get(packet)
    if current is None:
        raise G3eError(f"Request {packet} missing from G2b associations")
    while current["outcome"] == REISSUED:
        nxt = current.get("reissued_at_packet")
        if nxt in chain or nxt not in by_packet:
            raise G3eError(f"Broken reissue chain at {current['packet_index']}")
        chain.append(nxt)
        current = by_packet[nxt]
    return current["packet_index"], chain


def group(candidates: list[dict[str, Any]], associations: list[dict[str, Any]], nearby: dict[str, Any]) -> list[dict[str, Any]]:
    by_packet = {q["packet_index"]: q for q in associations}
    ids = [c["candidate_id"] for c in candidates]
    if len(set(ids)) != len(ids):
        raise G3eError("Duplicate candidate id")
    nearby_by_id = {c["candidate_id"]: c for c in nearby["candidates"]}
    if set(nearby_by_id) != set(ids):
        raise G3eError("G3c candidates do not match G3 candidates")

    info: dict[str, dict[str, Any]] = {}
    for c in candidates:
        start = c["request"]["packet_index"] if c["detector"] == G3A else c["first_request"]["packet_index"]
        end, chain = _lineage_end(start, by_packet)
        info[c["candidate_id"]] = {"candidate": c, "anchors": _anchors(c), "lineage_end": end, "lineage_chain": chain}

    parent = {cid: cid for cid in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges: list[dict[str, Any]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ia, ib = info[a], info[b]
            basis: list[str] = []
            evidence: dict[str, Any] = {}
            shared = sorted({p for p, _ in ia["anchors"]} & {p for p, _ in ib["anchors"]})
            if shared:
                basis.append("shared_anchor_packet")
                evidence["shared_anchor_packets"] = shared
                roles_a = {p: r for p, r in ia["anchors"]}
                roles_b = {p: r for p, r in ib["anchors"]}
                if any(
                    (ia["candidate"]["detector"] == G3A and roles_a[p] in ("request", "completion"))
                    != (ib["candidate"]["detector"] == G3A and roles_b[p] in ("request", "completion"))
                    for p in shared
                ):
                    basis.append("request_or_completion_is_other_candidate_anchor")
                evidence["anchor_roles"] = {a: {str(p): roles_a[p] for p in shared}, b: {str(p): roles_b[p] for p in shared}}
            if ia["lineage_end"] == ib["lineage_end"]:
                basis.append("shared_association_lineage")
                evidence["lineage_end_request_packet"] = ia["lineage_end"]
            if basis:
                edges.append({"members": [a, b], "basis": basis, "evidence": evidence})
                parent[find(a)] = find(b)

    components: dict[str, list[str]] = {}
    for cid in ids:
        components.setdefault(find(cid), []).append(cid)

    groups: list[dict[str, Any]] = []
    for members in components.values():
        member_set = set(members)
        group_edges = [e for e in edges if set(e["members"]) <= member_set]
        request_packets = sorted(
            p for cid in members for p, role in info[cid]["anchors"] if role in ("request", "first_request", "repeated_request")
        )
        anchor_packets = sorted(p for cid in members for p, _ in info[cid]["anchors"])
        primary = request_packets[0] if request_packets else anchor_packets[0]
        lineage_packets = sorted({p for cid in members for p in info[cid]["lineage_chain"]})
        observations = []
        for cid in sorted(members, key=lambda x: info[x]["anchors"][0][0]):
            c = info[cid]["candidate"]
            if c["detector"] == G3A:
                observations.append({
                    "candidate_id": cid,
                    "observed": f"{c['request']['type']} request {c['request']['packet_index']} (Tag {c['request']['tag']}) has associated completion "
                                f"{c['completion']['packet_index']} with status {c['completion']['compl_status_name']}",
                })
            else:
                observations.append({
                    "candidate_id": cid,
                    "observed": f"{c['first_request']['type']} request {c['first_request']['packet_index']} (Tag {c['tag']}): same association key "
                                f"observed again at {c['repeated_request']['packet_index']} ({c['repeated_request']['type']}) before an associated completion was observed",
                })
        messages = {}
        for cid in members:
            for m in nearby_by_id[cid]["nearby_messages"]:
                messages[m["packet"]] = {"packet": m["packet"], "message_name": m["message_name"], "display_time": m["display_time"]}
        times = sorted({info[cid]["candidate"]["anchor_time_display"] for cid in members})
        groups.append({
            "members": sorted(members, key=lambda x: info[x]["anchors"][0][0]),
            "grouping_basis": sorted({b for e in group_edges for b in e["basis"]}) or ["none_singleton"],
            "relationship": "grouped_by_shared_evidence" if len(members) > 1 else "singleton_no_strong_relationship",
            "edges": group_edges,
            "primary_go_to_packet": primary,
            "primary_go_to_rule": "earliest request packet among member anchors; earliest anchor packet if none",
            "anchor_packets": anchor_packets,
            "lineage": {
                "request_packets": lineage_packets,
                "packet_span": lineage_packets[-1] - lineage_packets[0] if lineage_packets else 0,
            },
            "observations": observations,
            "auxiliary_descriptors_not_used_for_grouping": {
                "anchor_time_displays": times,
                "nearby_messages_from_g3c": [messages[k] for k in sorted(messages)],
                "detectors": sorted({info[cid]["candidate"]["detector"] for cid in members}),
            },
            "interpretation": "NOT_EVALUATED",
        })
    groups.sort(key=lambda g: (g["primary_go_to_packet"], g["members"][0]))
    for number, g in enumerate(groups, start=1):
        g["group_id"] = f"G{number:03d}"

    seen = [cid for g in groups for cid in g["members"]]
    if sorted(seen) != sorted(ids) or len(seen) != len(set(seen)):
        raise G3eError("Grouping invariant failed: every candidate must appear in exactly one group")
    return groups


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--associations", type=Path, required=True)
    parser.add_argument("--nearby", type=Path, required=True)
    parser.add_argument("--protected-outputs", type=Path, nargs="*", default=[], help="Earlier outputs that must stay byte-identical")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise G3eError(f"Refusing to reuse existing output directory: {args.output_dir}")
        protected_before = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in args.protected_outputs}
        raws = {n: getattr(args, n).read_bytes() for n in ("candidates", "associations", "nearby")}
        candidates = json.loads(raws["candidates"].decode("utf-8"))["candidates"]
        groups = group(candidates, json.loads(raws["associations"].decode("utf-8")), json.loads(raws["nearby"].decode("utf-8")))
        protected_after = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in args.protected_outputs}
        if protected_after != protected_before:
            raise G3eError("A protected earlier output changed during G3e")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G3eError) as exc:
        print(f"G3e not produced: {exc}", file=sys.stderr)
        return 2
    output = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {n: {"path": getattr(args, n).as_posix(), "sha256": hashlib.sha256(raws[n]).hexdigest().upper()} for n in raws},
        "protected_outputs_unchanged": protected_after,
        "merge_rules": ["shared_anchor_packet", "shared_association_lineage", "request_or_completion_is_other_candidate_anchor"],
        "not_merge_rules": ["same display time", "same nearby message", "overlapping context", "same RequesterId", "same Tag", "same completion status"],
        "group_count_target": "NONE",
        "ground_truth": "UNKNOWN",
        "candidates_total": len(candidates),
        "groups_total": len(groups),
        "groups": groups,
    }
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "groups.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("schema_version", "candidates_total", "groups_total", "protected_outputs_unchanged")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
