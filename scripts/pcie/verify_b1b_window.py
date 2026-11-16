#!/usr/bin/env python3
"""Check a PCIe-B1b case window export and write an ordered raw link-layer timeline.

Reconstruction only: records and per-segment counts exactly as captured, optionally named with the
probed B1b-0 constants. No link rule, no MUX interpretation, no health claim.
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

from verify_g1a_log import DONE_MARKER, RUNTIME_ERROR_RE  # noqa: E402

HEADER_RE = re.compile(r"^PCIE_B1B_WINDOW_V1 start=(?P<start>\d+) end=(?P<end>\d+)$")
END_RE = re.compile(r"^PCIE_B1B_END\|events=(?P<events>\d+)\|tlp=(?P<tlp>\d+)\|err_any=(?P<err_any>\d+)\|segments=(?P<segments>\d+)\|reason=trace_end$")
T = r"(?P<packet_index>\d+)\|(?P<time_display>[^|]+)\|(?P<channel>[^|]+)"
RECORD_RES = {
    "tlp": re.compile(rf"^PCIE_B1B_TLP\|{T}\|(?P<tlp_type>\d+)$"),
    "nak": re.compile(rf"^PCIE_B1B_NAK\|{T}\|(?P<seq>\d+|NA)$"),
    "pm": re.compile(rf"^PCIE_B1B_PM\|{T}\|(?P<dllp_type>\d+)$"),
    "link_condition": re.compile(rf"^PCIE_B1B_LINKCOND\|{T}\|(?P<type>\d+|NA)$"),
    "ltssm": re.compile(rf"^PCIE_B1B_LTSSM\|{T}\|(?P<event>\d+)\|(?P<state>\d+)\|(?P<substate>\d+)\|(?P<subsubstate>\d+)\|(?P<valid>\d+)$"),
    "speed_width": re.compile(rf"^PCIE_B1B_SPEEDWIDTH\|{T}\|(?P<event>\d+)\|(?P<speed>\d+)\|(?P<width>\d+)$"),
}
SEG_FIELDS = ("seg", "first_index", "first_time", "last_index", "last_time", "events", "tlp")
PKT_FIELDS = ("seg", "dllp_ack", "dllp_nak", "dllp_fc", "dllp_pm", "dllp_other", "os_ts1", "os_ts2", "os_eios", "os_eieos", "os_skip", "os_other")
ERR_FIELDS = ("seg", "err_any", "disparity", "symbol", "wrong_symbol", "delimiter", "end_bad", "alignment", "idle",
              "ts_data_rate", "ts_format", "ts_parity", "ts_reserved", "tlp_bad_lcrc", "dllp_bad_crc")
SEG_RES = {
    "SEG": (re.compile(r"^PCIE_B1B_SEG\|(\d+)\|(\d+)\|([^|]+)\|(\d+)\|([^|]+)\|(\d+)\|(\d+)$"), SEG_FIELDS),
    "SEGPKT": (re.compile(r"^PCIE_B1B_SEGPKT" + r"\|(\d+)" * len(PKT_FIELDS) + "$"), PKT_FIELDS),
    "SEGERR": (re.compile(r"^PCIE_B1B_SEGERR" + r"\|(\d+)" * len(ERR_FIELDS) + "$"), ERR_FIELDS),
}


class B1bWindowError(ValueError):
    """The export does not establish a complete, consistent window reconstruction."""


def _typed(groups: dict[str, str]) -> dict[str, Any]:
    return {k: (v.strip() if k in ("time_display", "channel", "first_time", "last_time") else (v if v == "NA" else int(v))) for k, v in groups.items()}


def parse_export(text: str, g1_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines()]
    headers = [m for line in lines if (m := HEADER_RE.fullmatch(line))]
    if len(headers) != 1:
        raise B1bWindowError("Expected exactly one B1b v1 header")
    start, end = int(headers[0]["start"]), int(headers[0]["end"])
    if lines.count(DONE_MARKER) != 1:
        raise B1bWindowError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise B1bWindowError("The export contains a runtime-error marker")

    records: list[dict[str, Any]] = []
    segments: dict[int, dict[str, Any]] = {}
    seg_order: list[tuple[str, int]] = []
    ends: list[re.Match[str]] = []
    for line in lines:
        if not line.startswith("PCIE_B1B_") or HEADER_RE.fullmatch(line):
            continue
        if ends:
            raise B1bWindowError("B1b line emitted after the END marker")
        if match := END_RE.fullmatch(line):
            ends.append(match)
            continue
        for kind, regex in RECORD_RES.items():
            if match := regex.fullmatch(line):
                records.append({"kind": kind, **_typed(match.groupdict())})
                break
        else:
            for tag, (regex, fields) in SEG_RES.items():
                if match := regex.fullmatch(line):
                    values = _typed(dict(zip(fields, match.groups())))
                    seg = values.pop("seg")
                    segment = segments.setdefault(seg, {})
                    if any(k in segment for k in values):
                        raise B1bWindowError(f"Segment {seg} {tag} line repeated")
                    segment.update(values)
                    seg_order.append((tag, seg))
                    break
            else:
                raise B1bWindowError(f"Unrecognized B1b line: {line[:80]}")

    if len(ends) != 1:
        raise B1bWindowError(f"Expected exactly one END marker; found {len(ends)}")
    total = {k: int(v) for k, v in ends[0].groupdict().items()}
    numbers = sorted(segments)
    if numbers != list(range(1, len(numbers) + 1)) or len(numbers) != total["segments"]:
        raise B1bWindowError(f"Segments {numbers[:5]}... are not 1..{total['segments']}")
    expected_order = [(tag, n) for n in numbers for tag in ("SEG", "SEGPKT", "SEGERR")]
    if seg_order != expected_order:
        raise B1bWindowError("Segment lines are not complete SEG/SEGPKT/SEGERR triples in order")
    seg_list = [{"seg": n, **segments[n]} for n in numbers]
    if sum(s["events"] for s in seg_list) != total["events"]:
        raise B1bWindowError("Segment events do not sum to the END event count")
    if sum(s["tlp"] for s in seg_list) != total["tlp"] or sum(s["err_any"] for s in seg_list) != total["err_any"]:
        raise B1bWindowError("Segment TLP or error counts do not sum to the END totals")
    previous_last = start
    for s in seg_list:
        if not (start <= s["first_index"] <= s["last_index"] <= end) or s["first_index"] < previous_last:
            raise B1bWindowError(f"Segment {s['seg']} range {s['first_index']}-{s['last_index']} is outside or out of order")
        previous_last = s["last_index"]
        counted = sum(s[k] for k in PKT_FIELDS[1:]) + s["tlp"]
        if counted > s["events"] or any(s[k] > s["events"] for k in ERR_FIELDS[1:]):
            raise B1bWindowError(f"Segment {s['seg']} counts exceed its event count")
    indices = [r["packet_index"] for r in records]
    if any(not start <= i <= end for i in indices) or any(b < a for a, b in zip(indices, indices[1:])):
        raise B1bWindowError("Records are outside the window or not in trace order")
    tlp_records = [r["packet_index"] for r in records if r["kind"] == "tlp"]
    if len(tlp_records) != total["tlp"]:
        raise B1bWindowError(f"{len(tlp_records)} TLP records but END reports {total['tlp']}")
    if g1_rows is not None:
        g1 = [row["packet_index"] for row in g1_rows if start <= row["packet_index"] <= end]
        if tlp_records != g1:
            raise B1bWindowError(f"TLP records in the window {tlp_records[:6]} differ from the G1 export {g1[:6]}")
    return {"window": {"start": start, "end": end}, "totals": total, "records": records, "segments": seg_list}


def name_maps(constants: dict[str, int]) -> dict[str, dict[int, str]]:
    def by_prefix(prefix: str) -> dict[int, str]:
        out: dict[int, str] = {}
        for name, value in constants.items():
            if name.startswith(prefix):
                out.setdefault(value, name[len(prefix):])
        return out
    ltssm = by_prefix("LTSSM_STATE_")
    if "LTSSM_NO_STATE" in constants:
        ltssm[constants["LTSSM_NO_STATE"]] = "-"
    return {"event": by_prefix("_PKT_"), "ltssm": ltssm, "link_condition": by_prefix("LINK_CONDITION_")}


def build_timeline(result: dict[str, Any], constants: dict[str, int] | None) -> list[dict[str, Any]]:
    names = name_maps(constants) if constants else None
    rows: list[dict[str, Any]] = []
    for record in result["records"]:
        row = dict(record)
        if names:
            if "event" in row:
                row["event_name"] = names["event"].get(row["event"])
            if row["kind"] == "ltssm":
                row["state_name"] = ".".join(n for n in (names["ltssm"].get(row["state"]), names["ltssm"].get(row["substate"])) if n and n not in ("UNDEFINED", "-"))
            if row["kind"] == "link_condition" and row["type"] != "NA":
                row["type_name"] = names["link_condition"].get(row["type"])
        rows.append(row)
    for segment in result["segments"]:
        rows.append({"kind": "segment", "packet_index": segment["first_index"], "time_display": segment["first_time"], **segment})
    order = {"segment": 0}
    rows.sort(key=lambda r: (r["packet_index"], order.get(r["kind"], 1)))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="B1b VSE output (COM vse-output.txt or GUI saved log)")
    parser.add_argument("--g1-rows", type=Path, help="Verified G1 rows.json of the same trace (TLP cross-check)")
    parser.add_argument("--constants", type=Path, help="B1b-0 constants.json for naming codes")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1bWindowError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.log.read_bytes()
        g1_rows = json.loads(args.g1_rows.read_text(encoding="utf-8")) if args.g1_rows else None
        constants = json.loads(args.constants.read_text(encoding="utf-8")) if args.constants else None
        result = parse_export(raw.decode("utf-8-sig"), g1_rows)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, B1bWindowError) as exc:
        print(f"B1b export not accepted: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    timeline = build_timeline(result, constants)
    timeline_path = args.output_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kinds: dict[str, int] = {}
    for record in result["records"]:
        kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
    summary = {
        "status": "PASS_WINDOW_EXPORT",
        "window": result["window"],
        "totals": result["totals"],
        "records_by_kind": kinds,
        "g1_tlp_crosscheck": "MATCHED" if g1_rows is not None else "NOT_RUN",
        "named_with_constants": constants is not None,
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "timeline_json_sha256": hashlib.sha256(timeline_path.read_bytes()).hexdigest().upper(),
        "not_established": [
            "link health, expected MUX behaviour or any rule result (B1c-B1e)",
            "GUI agreement of link-condition Up/Down wording",
            "speed code labels (not probed)",
        ],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
