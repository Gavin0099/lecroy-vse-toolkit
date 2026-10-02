#!/usr/bin/env python3
"""PCIe-G2b: classify TLP roles (G2b-1) and associate completions with non-posted requests (G2b-2).

Input is the verified G2a canonical fields.json. Nothing here judges a transaction complete,
timed out, or faulty; unmatched and non-successful rows are observations only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Vendor TLP type constants as documented in the installed
# Scripts/VFScripts/VS_constants.inc (SHA-256 799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D).
VENDOR_TLP_TYPES = {
    0: "Invalid", 1: "MRd(32)", 2: "MRdLk(32)", 3: "MWr(32)", 4: "MRd(64)", 5: "MRdLk(64)", 6: "MWr(64)",
    7: "IORd", 8: "IOWr", 9: "CfgRd0", 10: "CfgWr0", 11: "CfgRd1", 12: "CfgWr1",
    13: "Msg", 14: "MsgD", 15: "MsgAS", 16: "MsgASD", 17: "Cpl", 18: "CplD", 19: "CplLk", 20: "CplDLk",
    21: "FetchAdd(32)", 22: "FetchAdd(64)", 23: "Swap(32)", 24: "Swap(64)", 25: "CAS(32)", 26: "CAS(64)",
}
VENDOR_CONSTANTS_SOURCE = "Scripts/VFScripts/VS_constants.inc SHA-256 799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D"
# Codes whose name was also observed in the LeCroy GUI for a packet of the 1350 trace.
GUI_CONFIRMED_CODES = {9: "packet 2097003", 14: "packet 1944516", 18: "packet 2121703"}

NON_POSTED_REQUESTS = {
    "MRd(32)", "MRdLk(32)", "MRd(64)", "MRdLk(64)", "IORd", "IOWr", "CfgRd0", "CfgWr0", "CfgRd1", "CfgWr1",
    "FetchAdd(32)", "FetchAdd(64)", "Swap(32)", "Swap(64)", "CAS(32)", "CAS(64)",
}
COMPLETIONS = {"Cpl", "CplD", "CplLk", "CplDLk"}
POSTED_OR_OTHER = {"MWr(32)", "MWr(64)", "Msg", "MsgD", "MsgAS", "MsgASD"}
# Completion status codes: 0/1/4 from vendor compliance constants; 2 (CRS) per the PCIe specification.
STATUS_NAMES = {0: "SC", 1: "UR", 2: "CRS", 4: "CA"}

NON_POSTED_REQUEST = "NON_POSTED_REQUEST"
COMPLETION_CANDIDATE = "COMPLETION_CANDIDATE"
POSTED = "POSTED_OR_OTHER"
UNKNOWN = "UNKNOWN"

COMPLETIONS_OBSERVED = "COMPLETIONS_OBSERVED"
NONE_OBSERVED = "NONE_OBSERVED_IN_CAPTURE"
REISSUED = "SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED"
ORPHAN = "NO_PRECEDING_REQUEST_IN_CAPTURE"


class G2bError(ValueError):
    """Input rows are not a usable G2a field export."""


def bdf(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value >> 8:03d}:{(value >> 3) & 0x1F:02d}.{value & 0x7}"


def classify(row: dict[str, Any]) -> dict[str, Any]:
    """G2b-1: role from the vendor constant name, checked against the row's field shape."""
    code = int(row["tlp_type_hex"], 16)
    name = VENDOR_TLP_TYPES.get(code)
    evidence = "UNMAPPED" if name is None else ("GUI_CONFIRMED+VENDOR_CONSTANT" if code in GUI_CONFIRMED_CODES else "VENDOR_CONSTANT")
    completion_shaped = row["completer_id"] is not None and row["compl_status"] is not None
    notes: list[str] = []
    if name in NON_POSTED_REQUESTS:
        role = NON_POSTED_REQUEST
        if row["tag"] is None or row["requester_id"] is None:
            role, notes = UNKNOWN, ["request type without RequesterId/Tag"]
        elif row["completer_id"] is not None or row["compl_status"] is not None:
            notes.append("request type carries completion fields")
    elif name in COMPLETIONS:
        role = COMPLETION_CANDIDATE
        if not completion_shaped or row["tag"] is None or row["requester_id"] is None:
            role, notes = UNKNOWN, ["completion type without CompleterId/ComplStatus/RequesterId/Tag"]
    elif name in POSTED_OR_OTHER:
        role = POSTED
        if completion_shaped:
            notes.append("posted type carries completion fields")
    else:
        role = UNKNOWN
        notes.append("type code not in vendor constant table" if name is None else "type not assigned a role")
    return {
        "row": row["row"],
        "packet_index": row["packet_index"],
        "tlp_type_hex": row["tlp_type_hex"],
        "vendor_type_name": name,
        "type_evidence": evidence,
        "role": role,
        "notes": notes,
    }


def associate(rows: list[dict[str, Any]], roles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """G2b-2: link each completion candidate to the nearest preceding non-posted request with the same (RequesterId, Tag).

    A request is never closed by a completion, so split completions accumulate on the same request.
    If the same key is issued again before any completion was observed for the earlier request,
    the earlier request is labelled REISSUED instead of being guessed.
    """
    indices = [row["packet_index"] for row in rows]
    if any(later <= earlier for earlier, later in zip(indices, indices[1:])):
        raise G2bError("Rows are not in strictly increasing capture order")
    requests: list[dict[str, Any]] = []
    orphans: list[dict[str, Any]] = []
    latest: dict[tuple[int, int], dict[str, Any]] = {}
    for row, role in zip(rows, roles):
        key = (row["requester_id"], row["tag"])
        if role["role"] == NON_POSTED_REQUEST:
            previous = latest.get(key)
            if previous is not None and not previous["completions"]:
                previous["outcome"] = REISSUED
                previous["reissued_at_packet"] = row["packet_index"]
            request = {
                "row": row["row"],
                "packet_index": row["packet_index"],
                "time_display": row["time_display"],
                "channel": row["channel"],
                "tlp_type_hex": row["tlp_type_hex"],
                "vendor_type_name": role["vendor_type_name"],
                "requester_id": row["requester_id"],
                "requester_bdf": bdf(row["requester_id"]),
                "tag": row["tag"],
                "outcome": NONE_OBSERVED,
                "completions": [],
            }
            requests.append(request)
            latest[key] = request
        elif role["role"] == COMPLETION_CANDIDATE:
            completion = {
                "row": row["row"],
                "packet_index": row["packet_index"],
                "time_display": row["time_display"],
                "channel": row["channel"],
                "tlp_type_hex": row["tlp_type_hex"],
                "vendor_type_name": role["vendor_type_name"],
                "type_evidence": role["type_evidence"],
                "requester_id": row["requester_id"],
                "tag": row["tag"],
                "completer_id": row["completer_id"],
                "completer_bdf": bdf(row["completer_id"]),
                "compl_status": row["compl_status"],
                "compl_status_name": STATUS_NAMES.get(row["compl_status"], "UNKNOWN"),
            }
            request = latest.get(key)
            if request is None:
                orphans.append({**completion, "association": ORPHAN})
                continue
            completion["packet_gap_from_request"] = row["packet_index"] - request["packet_index"]
            completion["direction_relation"] = "opposite" if row["channel"] != request["channel"] else "same"
            request["completions"].append(completion)
            if request["outcome"] != REISSUED:
                request["outcome"] = COMPLETIONS_OBSERVED
    return requests, orphans


def summarize(rows: list[dict[str, Any]], roles: list[dict[str, Any]], requests: list[dict[str, Any]], orphans: list[dict[str, Any]]) -> dict[str, Any]:
    role_by_type = Counter((r["tlp_type_hex"], r["vendor_type_name"], r["type_evidence"], r["role"]) for r in roles)
    outcome_by_type = Counter((q["vendor_type_name"], q["outcome"]) for q in requests)
    associated = [c for q in requests for c in q["completions"]]
    status_counts = Counter((c["vendor_type_name"], c["compl_status_name"]) for c in associated + orphans)
    return {
        "rows": len(rows),
        "roles": [
            {"tlp_type_hex": code, "vendor_type_name": name, "type_evidence": evidence, "role": role, "rows": count}
            for (code, name, evidence, role), count in sorted(role_by_type.items(), key=lambda kv: int(kv[0][0], 16))
        ],
        "role_notes": sorted({note for r in roles for note in r["notes"]}),
        "requests": len(requests),
        "request_outcomes": [
            {"vendor_type_name": name, "outcome": outcome, "requests": count}
            for (name, outcome), count in sorted(outcome_by_type.items())
        ],
        "requests_with_multiple_completions": sum(1 for q in requests if len(q["completions"]) > 1),
        "completion_candidates": len(associated) + len(orphans),
        "completions_associated": len(associated),
        "completions_without_preceding_request": len(orphans),
        "completion_status_observations": [
            {"vendor_type_name": name, "compl_status_name": status, "completions": count}
            for (name, status), count in sorted(status_counts.items())
        ],
        "direction_relation_counts": dict(Counter(c["direction_relation"] for c in associated)),
        "not_established": [
            "transaction completeness (Byte Count / Length / Lower Address not read)",
            "completion timeout: no completion observed before capture end is not a protocol timeout",
            "fault or abnormality: UR/CA/CRS status values are observations only",
            "correctness of nearest-preceding association when Tags are reused",
        ],
    }


def write_outputs(output_dir: Path, roles, requests, orphans, summary) -> dict[str, str]:
    if output_dir.exists():
        raise G2bError(f"Refusing to reuse existing output directory: {output_dir}")
    output_dir.mkdir(parents=True)
    digests: dict[str, str] = {}
    for name, payload in (("roles.json", roles), ("associations.json", requests), ("orphan_completions.json", orphans)):
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        (output_dir / name).write_bytes(data)
        digests[name] = hashlib.sha256(data).hexdigest().upper()
    columns = ("packet_index", "time_display", "vendor_type_name", "requester_bdf", "tag", "outcome", "completions", "completion_packets", "statuses")
    with (output_dir / "associations.tsv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(columns)
        for q in requests:
            writer.writerow([
                q["packet_index"], q["time_display"], q["vendor_type_name"], q["requester_bdf"], q["tag"], q["outcome"],
                len(q["completions"]), ",".join(str(c["packet_index"]) for c in q["completions"]),
                ",".join(c["compl_status_name"] for c in q["completions"]),
            ])
    (output_dir / "summary.json").write_text(json.dumps({**summary, "output_sha256": digests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fields", type=Path, required=True, help="Verified G2a canonical fields.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="New output directory")
    parser.add_argument("--show-request", type=int, action="append", default=[], help="Packet index of a request to print")
    args = parser.parse_args(argv)
    try:
        raw = args.fields.read_bytes()
        rows = json.loads(raw.decode("utf-8"))
        roles = [classify(row) for row in rows]
        requests, orphans = associate(rows, roles)
        summary = summarize(rows, roles, requests, orphans)
        summary["input_fields_sha256"] = hashlib.sha256(raw).hexdigest().upper()
        summary["vendor_constants_source"] = VENDOR_CONSTANTS_SOURCE
        write_outputs(args.output_dir, roles, requests, orphans, summary)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G2bError) as exc:
        print(f"G2b not produced: {exc}", file=sys.stderr)
        return 2
    shown = [q for q in requests if q["packet_index"] in set(args.show_request)]
    print(json.dumps({"summary": summary, "shown_requests": shown}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
