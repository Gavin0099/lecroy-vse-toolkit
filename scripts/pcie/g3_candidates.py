#!/usr/bin/env python3
"""PCIe-G3a/G3b candidate detectors over G2b request/completion associations.

Candidates are places worth an engineer's look, not anomalies or faults: every candidate
carries interpretation NOT_EVALUATED and lists what it does not establish. No ranking or grouping.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pcie.g3-candidates/v1"
REISSUED = "SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED"
ASSOCIATION_BASIS = "nearest preceding non-posted request with the same (RequesterId, Tag) in capture order (G2b-2)"

DETECTORS = {
    "G3A_NON_SUCCESS_COMPLETION": {
        "surfaces": "An associated completion reports a status other than SC.",
        "does_not_establish": [
            "that the request was invalid or the device misbehaved (UR can be expected, e.g. probing absent functions)",
            "a causal link to any user-visible failure",
            "that the association is correct when earlier same-key requests were reissued, unless GUI-cross-checked",
        ],
    },
    "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION": {
        "surfaces": "Same association key observed again before an associated completion was observed in the captured sequence.",
        "does_not_establish": [
            "that the requester retransmitted the request",
            "that this is not an analyzer or capture representation effect",
            "that the Tag reuse is protocol-illegal",
            "that the earlier request's completion did not occur outside the capture",
        ],
    },
}


class G3Error(ValueError):
    """Association input is unusable for candidate detection."""


def _request_ref(q: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_index": q["packet_index"], "time_display": q["time_display"], "channel": q["channel"],
        "type": q["vendor_type_name"], "requester_bdf": q["requester_bdf"], "tag": q["tag"],
    }


def _completion_ref(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_index": c["packet_index"], "time_display": c["time_display"], "channel": c["channel"],
        "type": c["vendor_type_name"], "type_evidence": c["type_evidence"], "completer_bdf": c["completer_bdf"],
        "compl_status": c["compl_status"], "compl_status_name": c["compl_status_name"],
        "packet_gap_from_request": c["packet_gap_from_request"],
    }


def _chain_end(request: dict[str, Any], by_packet: dict[int, dict[str, Any]]) -> dict[str, Any]:
    current = request
    seen = set()
    while current["outcome"] == REISSUED:
        if current["packet_index"] in seen:
            raise G3Error("Cyclic reissue chain")
        seen.add(current["packet_index"])
        nxt = by_packet.get(current.get("reissued_at_packet"))
        if nxt is None:
            raise G3Error(f"Reissue target of {current['packet_index']} is missing")
        current = nxt
    return current


def detect(requests: list[dict[str, Any]], crosschecks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    by_packet = {q["packet_index"]: q for q in requests}
    if len(by_packet) != len(requests):
        raise G3Error("Duplicate request packet index")
    checks = {(c["request_packet"], c["completion_packet"]): c for c in (crosschecks or [])}
    reissued_into: dict[int, int] = {}
    for q in requests:
        if q["outcome"] == REISSUED:
            end = _chain_end(q, by_packet)
            reissued_into[end["packet_index"]] = reissued_into.get(end["packet_index"], 0) + 1

    candidates: list[dict[str, Any]] = []
    for q in requests:
        for c in q["completions"]:
            if c["compl_status"] == 0:
                continue
            check = checks.get((q["packet_index"], c["packet_index"]))
            candidates.append({
                "detector": "G3A_NON_SUCCESS_COMPLETION",
                "anchor_packet": c["packet_index"],
                "anchor_time_display": c["time_display"],
                "why_surfaced": DETECTORS["G3A_NON_SUCCESS_COMPLETION"]["surfaces"],
                "request": _request_ref(q),
                "completion": _completion_ref(c),
                "association_basis": ASSOCIATION_BASIS,
                "earlier_same_key_requests_reissued_into_this_request": reissued_into.get(q["packet_index"], 0),
                "gui_crosscheck": None if check is None else {k: check[k] for k in ("lecroy_view", "result", "screenshots")},
                "interpretation": "NOT_EVALUATED",
            })
        if q["outcome"] == REISSUED:
            repeated = by_packet[q["reissued_at_packet"]]
            end = _chain_end(q, by_packet)
            later = end["completions"]
            candidates.append({
                "detector": "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION",
                "anchor_packet": q["packet_index"],
                "anchor_time_display": q["time_display"],
                "why_surfaced": DETECTORS["G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION"]["surfaces"],
                "requester_bdf": q["requester_bdf"],
                "tag": q["tag"],
                "first_request": _request_ref(q),
                "repeated_request": _request_ref(repeated),
                "packet_gap": repeated["packet_index"] - q["packet_index"],
                "completion_observed_later_for_same_key": "YES" if later else "NO",
                "later_completion": None if not later else {
                    **_completion_ref(later[0]),
                    "associated_with_request_packet": end["packet_index"],
                    "note": "attributed by G2b to the last request of the same-key chain, not necessarily to first_request",
                },
                "interpretation": "NOT_EVALUATED",
            })
    candidates.sort(key=lambda item: (item["anchor_packet"], item["detector"]))
    for number, candidate in enumerate(candidates, start=1):
        candidate["candidate_id"] = f"C{number:03d}"
    return candidates


def build(associations_path: Path, crosschecks_path: Path | None) -> dict[str, Any]:
    raw = associations_path.read_bytes()
    requests = json.loads(raw.decode("utf-8"))
    crosschecks = None
    crosschecks_sha = None
    if crosschecks_path is not None:
        cross_raw = crosschecks_path.read_bytes()
        crosschecks = json.loads(cross_raw.decode("utf-8"))["crosschecks"]
        crosschecks_sha = hashlib.sha256(cross_raw).hexdigest().upper()
    candidates = detect(requests, crosschecks)
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate["detector"]] = counts.get(candidate["detector"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "input": {
            "associations_path": associations_path.as_posix(),
            "associations_sha256": hashlib.sha256(raw).hexdigest().upper(),
            "gui_crosschecks_path": None if crosschecks_path is None else crosschecks_path.as_posix(),
            "gui_crosschecks_sha256": crosschecks_sha,
        },
        "ground_truth": "UNKNOWN",
        "detectors": DETECTORS,
        "ranking": "NONE",
        "grouping": "NONE (G3e)",
        "candidate_counts": counts,
        "candidates": candidates,
    }


def write(result: dict[str, Any], output_dir: Path) -> None:
    if output_dir.exists():
        raise G3Error(f"Refusing to reuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    (output_dir / "candidates.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "candidates.tsv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("candidate_id", "detector", "anchor_packet", "time", "request_packet", "request_type", "tag",
                         "other_packet", "status_or_later", "gui_crosscheck", "interpretation"))
        for c in result["candidates"]:
            if c["detector"] == "G3A_NON_SUCCESS_COMPLETION":
                row = (c["request"]["packet_index"], c["request"]["type"], c["request"]["tag"],
                       c["completion"]["packet_index"], c["completion"]["compl_status_name"],
                       "" if c["gui_crosscheck"] is None else c["gui_crosscheck"]["result"])
            else:
                row = (c["first_request"]["packet_index"], c["first_request"]["type"], c["tag"],
                       c["repeated_request"]["packet_index"], c["completion_observed_later_for_same_key"], "")
            writer.writerow((c["candidate_id"], c["detector"], c["anchor_packet"], c["anchor_time_display"], *row, c["interpretation"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--associations", type=Path, required=True, help="G2b associations.json")
    parser.add_argument("--gui-crosschecks", type=Path, help="Optional GUI cross-check record")
    parser.add_argument("--output-dir", type=Path, required=True, help="New output directory")
    args = parser.parse_args(argv)
    try:
        result = build(args.associations, args.gui_crosschecks)
        write(result, args.output_dir)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G3Error) as exc:
        print(f"G3 candidates not produced: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in ("schema_version", "input", "ground_truth", "candidate_counts")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
