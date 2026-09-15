#!/usr/bin/env python3
"""Check a saved PCIe-B1a link-layer field probe log and write records/summary JSON.

Field verification only: which link and data-link fields are populated, how often, and capped
samples. It applies no link rules and makes no health claim about the link.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_g1a_log import DONE_MARKER, RUNTIME_ERROR_RE, G1aLogError, check_log  # noqa: E402

HEADER_RE = re.compile(r"^PCIE_B1A_LINK_FIELDS_V1 caps=ltssm:(?P<ltssm>\d+),linkcond:(?P<linkcond>\d+),"
                       r"speedwidth:(?P<speedwidth>\d+),nak:(?P<nak>\d+),err:(?P<err>\d+)$")
T = r"(?P<index>\d+)\|(?P<time>[^|]+)\|(?P<channel>[^|]+)"
RECORD_RES = {
    "ltssm": re.compile(rf"^PCIE_B1A_LTSSM\|{T}\|(?P<event>\d+)\|(?P<state>\d+)\|(?P<substate>\d+)\|(?P<subsubstate>\d+)\|(?P<valid>\d+)$"),
    "linkcond": re.compile(rf"^PCIE_B1A_LINKCOND\|{T}\|(?P<type>\d+|NA)$"),
    "speedwidth": re.compile(rf"^PCIE_B1A_SPEEDWIDTH\|{T}\|(?P<event>\d+)\|(?P<speed>\d+)\|(?P<width>\d+)$"),
    "nak": re.compile(rf"^PCIE_B1A_NAK\|{T}\|(?P<seq>\d+|NA)$"),
    "err": re.compile(rf"^PCIE_B1A_ERR\|{T}\|(?P<event>\d+)$"),
}
COUNT_RE = re.compile(r"^PCIE_B1A_COUNT\|(?P<name>[a-z0-9_]+)=(?P<value>\d+)$")
END_RE = re.compile(r"^PCIE_B1A_END\|events=(?P<events>\d+)\|reason=trace_end$")
COUNT_NAMES = (
    "tlp", "dllp", "ordered_set", "link_condition", "eie", "other_event",
    "dllp_ack", "dllp_nak", "dllp_fc", "dllp_pm", "dllp_other", "dllp_bad_crc", "tlp_bad_lcrc",
    "os_ts1", "os_ts2", "os_eios", "os_eieos", "os_skip", "os_other", "os_compressed",
    "error_events", "ltssm_present", "ltssm_changes", "speed_present", "width_present", "speed_width_changes",
)
# sampled record kind -> count that is its population
SAMPLE_TOTALS = {"ltssm": "ltssm_changes", "linkcond": "link_condition", "speedwidth": "speed_width_changes",
                 "nak": "dllp_nak", "err": "error_events"}


class B1aLogError(ValueError):
    """The log does not establish a complete B1a field probe."""


def parse_log(text: str, g1a: dict[str, Any] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines()]
    headers = [m for line in lines if (m := HEADER_RE.fullmatch(line))]
    if len(headers) != 1:
        raise B1aLogError("Expected exactly one B1a v1 header")
    caps = {k: int(v) for k, v in headers[0].groupdict().items()}
    if lines.count(DONE_MARKER) != 1:
        raise B1aLogError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise B1aLogError("The log contains a runtime-error marker")

    records: dict[str, list[dict[str, Any]]] = {kind: [] for kind in RECORD_RES}
    counts: dict[str, int] = {}
    ends: list[re.Match[str]] = []
    for line in lines:
        if not line.startswith("PCIE_B1A_") or HEADER_RE.fullmatch(line):
            continue
        if ends:
            raise B1aLogError("B1a line emitted after the END marker")
        if match := COUNT_RE.fullmatch(line):
            if match["name"] not in COUNT_NAMES:
                raise B1aLogError(f"Unknown count {match['name']}")
            if match["name"] in counts:
                raise B1aLogError(f"Duplicate count {match['name']}")
            counts[match["name"]] = int(match["value"])
            continue
        if match := END_RE.fullmatch(line):
            ends.append(match)
            continue
        for kind, regex in RECORD_RES.items():
            if match := regex.fullmatch(line):
                if counts:
                    raise B1aLogError(f"{kind} record after the finish counts")
                row = {k: (v.strip() if k in ("time", "channel") else (v if v == "NA" else int(v))) for k, v in match.groupdict().items()}
                row["packet_index"] = row.pop("index")
                row["time_display"] = row.pop("time")
                records[kind].append(row)
                break
        else:
            raise B1aLogError(f"Unrecognized B1a line: {line[:80]}")

    if len(ends) != 1:
        raise B1aLogError(f"Expected exactly one END marker; found {len(ends)}")
    missing = [name for name in COUNT_NAMES if name not in counts]
    if missing:
        raise B1aLogError(f"Missing counts: {missing}")
    events = int(ends[0]["events"])
    by_event = sum(counts[k] for k in ("tlp", "dllp", "ordered_set", "link_condition", "eie", "other_event"))
    if by_event != events:
        raise B1aLogError(f"Event-type counts sum to {by_event}, END reports {events}")
    if counts["dllp_ack"] + counts["dllp_nak"] + counts["dllp_fc"] + counts["dllp_pm"] + counts["dllp_other"] != counts["dllp"]:
        raise B1aLogError("DLLP type counts do not sum to the DLLP count")
    if sum(counts[k] for k in ("os_ts1", "os_ts2", "os_eios", "os_eieos", "os_skip", "os_other")) != counts["ordered_set"]:
        raise B1aLogError("Ordered set type counts do not sum to the ordered set count")
    for name in ("ltssm_present", "speed_present", "width_present", "error_events"):
        if counts[name] > events:
            raise B1aLogError(f"{name} exceeds the event count")
    for kind, total_name in SAMPLE_TOTALS.items():
        expected = min(counts[total_name], caps[kind])
        if len(records[kind]) != expected:
            raise B1aLogError(f"{kind}: {len(records[kind])} samples, expected min({total_name}={counts[total_name]}, cap={caps[kind]})")
        indices = [row["packet_index"] for row in records[kind]]
        if any(later < earlier for earlier, later in zip(indices, indices[1:])):
            raise B1aLogError(f"{kind} samples are not in trace order")
    if g1a is not None and counts["tlp"] != g1a["tlp_callback_count"]:
        raise B1aLogError(f"B1a TLP count {counts['tlp']} differs from G1a {g1a['tlp_callback_count']}")
    return {"caps": caps, "counts": counts, "events": events, "records": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Saved B1a VSE output (GUI Save Output or COM report lines)")
    parser.add_argument("--g1a-log", type=Path, help="Verified G1a log of the same trace (TLP count cross-check)")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1aLogError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.log.read_bytes()
        g1a = check_log(args.g1a_log.read_text(encoding="utf-8-sig")) if args.g1a_log else None
        result = parse_log(raw.decode("utf-8-sig"), g1a)
    except (OSError, UnicodeDecodeError, G1aLogError, B1aLogError) as exc:
        print(f"B1a log not accepted: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    records_path = args.output_dir / "records.json"
    records_path.write_text(json.dumps(result["records"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = result["counts"]
    summary = {
        "status": "PASS_LINK_FIELD_PROBE_OUTPUT",
        "events": result["events"],
        "counts": counts,
        "caps": result["caps"],
        "samples": {kind: len(rows) for kind, rows in result["records"].items()},
        "sample_truncated": {kind: counts[total] > result["caps"][kind] for kind, total in SAMPLE_TOTALS.items()},
        "g1a_tlp_crosscheck": "MATCHED" if g1a is not None else "NOT_RUN",
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "records_json_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest().upper(),
        "not_established": [
            "link health or any rule result (B1c)",
            "meaning of LTSSM numeric codes against the vendor constants (decoded in B1b)",
            "GUI agreement for sampled records",
            "events outside the subscribed packet types (TLP, DLLP, ordered set, link condition, EIE)",
        ],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
