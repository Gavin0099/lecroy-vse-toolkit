#!/usr/bin/env python3
"""Check the PCIe-B1c-x2 HasErrors subtype probe output and summarize which error members were set.

Descriptive only: counts per range (R1 Recovery phases, R2 Downstream Polling, R3 after the gap) and per
channel, cross-checked against the verified B1b window totals. No rule, no interpretation.
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

FLAGS = ("ErrorDisparity", "ErrorSymbol", "ErrorWrongSymbol", "ErrorDelimiter", "ErrorEndBad", "ErrorAlignment", "ErrorAllignment",
         "ErrorLength", "BadLCRC", "BadECRC", "BadCRC", "MsgErrorG3LenCheck", "TsErrorDataRate", "TsErrorFormat", "TsErrorParity",
         "TsErrorRsrvField", "G3ErrorFraming", "InvalidEncoding", "RsvdField", "ErrorRsvdFld", "HasIdleErrors", "IdleErrorDisparity",
         "IdleErrorSymbol", "IdleErrorSkip", "IdleErrorData", "FCError")
RANGES = ("R1", "R2", "R3")
CHANNELS = ("C1", "C2", "C3")
HEADER_RE = re.compile(r"^PCIE_B1CX2_HASERRORS_V1 start=(?P<start>\d+) end=(?P<end>\d+) r1_end=(?P<r1_end>\d+) r2_end=(?P<r2_end>\d+) cap=(?P<cap>\d+)$")
SAMPLE_RE = re.compile(r"^PCIE_B1CX2_SAMPLE\|(?P<packet_index>\d+)\|(?P<time_display>[^|]+)\|(?P<channel>[^|]+)\|(?P<c>[123])\|(?P<r>[123])\|"
                       r"(?P<event>\d+)\|(?P<ordset>\d+|NA)\|(?P<state>\d+\.\d+|NA)\|(?P<flags>NONE|(?:[A-Za-z0-9]+,)+)$")
PRESENT_RE = re.compile(r"^PCIE_B1CX2_PRESENT\|(?P<flag>[A-Za-z0-9]+)=(?P<n>\d+)$")
SCOPE_RE = re.compile(r"^PCIE_B1CX2_SCOPE\|(?P<scope>[RC][123])\|(?P<events>\d+)\|(?P<ts1>\d+)\|(?P<ts2>\d+)\|(?P<has_errors>\d+)\|(?P<unexplained>\d+)$")
FLAGSET_RE = re.compile(r"^PCIE_B1CX2_FLAGSET\|(?P<scope>[RC][123])\|(?P<flag>[A-Za-z0-9]+)=(?P<n>\d+)$")
CELL_RE = re.compile(r"^PCIE_B1CX2_CELL\|(?P<r>[123])\|(?P<c>[123])\|(?P<events>\d+)\|(?P<ts1>\d+)\|(?P<has_errors>\d+)$")
HEEVENT_RE = re.compile(r"^PCIE_B1CX2_HEEVENT\|tlp=(?P<tlp>\d+)\|dllp=(?P<dllp>\d+)\|ordered_set=(?P<ordered_set>\d+)\|other=(?P<other>\d+)$")
END_RE = re.compile(r"^PCIE_B1CX2_END\|events=(?P<events>\d+)\|has_errors=(?P<has_errors>\d+)\|unexplained=(?P<unexplained>\d+)\|reason=trace_end$")


class B1cx2Error(ValueError):
    """The probe output is incomplete or inconsistent."""


def _ints(match: re.Match[str], skip: tuple[str, ...] = ()) -> dict[str, Any]:
    return {k: (v if k in skip else int(v)) for k, v in match.groupdict().items()}


def parse(text: str, b1b_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines()]
    headers = [m for line in lines if (m := HEADER_RE.fullmatch(line))]
    if len(headers) != 1 or lines.count(DONE_MARKER) != 1:
        raise B1cx2Error("Expected exactly one x2 header and one VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise B1cx2Error("The output contains a runtime-error marker")
    head = {k: int(v) for k, v in headers[0].groupdict().items()}
    samples: list[dict[str, Any]] = []
    present: dict[str, int] = {}
    scopes: dict[str, dict[str, int]] = {}
    flagset: dict[tuple[str, str], int] = {}
    cells: dict[tuple[int, int], dict[str, int]] = {}
    heevent: list[dict[str, int]] = []
    ends: list[dict[str, Any]] = []
    for line in lines:
        if not line.startswith("PCIE_B1CX2_") or HEADER_RE.fullmatch(line):
            continue
        if ends:
            raise B1cx2Error("Line emitted after the END marker")
        if m := SAMPLE_RE.fullmatch(line):
            row = _ints(m, skip=("time_display", "channel", "ordset", "state", "flags"))
            row["time_display"], row["channel"] = row["time_display"].strip(), row["channel"].strip()
            row["flags"] = [] if row["flags"] == "NONE" else row["flags"].rstrip(",").split(",")
            samples.append(row)
        elif m := PRESENT_RE.fullmatch(line):
            if m["flag"] in present:
                raise B1cx2Error(f"Duplicate presence count {m['flag']}")
            present[m["flag"]] = int(m["n"])
        elif m := SCOPE_RE.fullmatch(line):
            if m["scope"] in scopes:
                raise B1cx2Error(f"Duplicate scope {m['scope']}")
            scopes[m["scope"]] = _ints(m, skip=("scope",))
            scopes[m["scope"]].pop("scope")
        elif m := FLAGSET_RE.fullmatch(line):
            key = (m["scope"], m["flag"])
            if key in flagset:
                raise B1cx2Error(f"Duplicate flag count {key}")
            flagset[key] = int(m["n"])
        elif m := CELL_RE.fullmatch(line):
            key = (int(m["r"]), int(m["c"]))
            if key in cells:
                raise B1cx2Error(f"Duplicate cell {key}")
            cells[key] = {k: int(m[k]) for k in ("events", "ts1", "has_errors")}
        elif m := HEEVENT_RE.fullmatch(line):
            heevent.append(_ints(m))
        elif m := END_RE.fullmatch(line):
            ends.append(_ints(m))
        else:
            raise B1cx2Error(f"Unrecognized line: {line[:80]}")

    if len(ends) != 1 or len(heevent) != 1:
        raise B1cx2Error("Expected exactly one END and one HEEVENT line")
    end, he = ends[0], heevent[0]
    if set(present) != set(FLAGS):
        raise B1cx2Error("Presence counts do not cover exactly the flag list")
    if set(scopes) != set(RANGES + CHANNELS):
        raise B1cx2Error("Scopes are not exactly R1-R3 and C1-C3")
    if set(flagset) != {(s, f) for s in RANGES + CHANNELS for f in FLAGS}:
        raise B1cx2Error("Flag counts do not cover every scope and flag")
    if set(cells) != {(r, c) for r in (1, 2, 3) for c in (1, 2, 3)}:
        raise B1cx2Error("Cells are not exactly 3 x 3")
    for field in ("events", "has_errors", "unexplained"):
        for group in (RANGES, CHANNELS):
            if sum(scopes[s][field] for s in group) != end[field]:
                raise B1cx2Error(f"{field} over {group[0][0]} scopes does not equal END")
    for field in ("ts1", "ts2"):
        if sum(scopes[s][field] for s in RANGES) != sum(scopes[s][field] for s in CHANNELS):
            raise B1cx2Error(f"{field} range and channel totals differ")
    for flag in FLAGS:
        if sum(flagset[(s, flag)] for s in RANGES) != sum(flagset[(s, flag)] for s in CHANNELS):
            raise B1cx2Error(f"{flag} range and channel totals differ")
        for s in RANGES + CHANNELS:
            if flagset[(s, flag)] > scopes[s]["has_errors"]:
                raise B1cx2Error(f"{flag} in {s} exceeds its HasErrors count")
    for r in (1, 2, 3):
        for field in ("events", "ts1", "has_errors"):
            if sum(cells[(r, c)][field] for c in (1, 2, 3)) != scopes[f"R{r}"][field]:
                raise B1cx2Error(f"cell row R{r} {field} differs from the range scope")
    for c in (1, 2, 3):
        for field in ("events", "ts1", "has_errors"):
            if sum(cells[(r, c)][field] for r in (1, 2, 3)) != scopes[f"C{c}"][field]:
                raise B1cx2Error(f"cell column C{c} {field} differs from the channel scope")
    if sum(he.values()) != end["has_errors"]:
        raise B1cx2Error("HasErrors by event type does not sum to END")
    bounds = {1: (head["start"], head["r1_end"]), 2: (head["r1_end"] + 1, head["r2_end"]), 3: (head["r2_end"] + 1, head["end"])}
    channel_names: dict[int, set[str]] = {}
    for r in (1, 2, 3):
        in_range = [s for s in samples if s["r"] == r]
        if len(in_range) != min(head["cap"], scopes[f"R{r}"]["has_errors"]):
            raise B1cx2Error(f"R{r} has {len(in_range)} samples, expected min(cap, HasErrors)")
    for s in samples:
        low, high = bounds[s["r"]]
        if not low <= s["packet_index"] <= high:
            raise B1cx2Error(f"Sample {s['packet_index']} lies outside range R{s['r']}")
        if any(f not in FLAGS for f in s["flags"]):
            raise B1cx2Error(f"Sample {s['packet_index']} names an unknown flag")
        channel_names.setdefault(s["c"], set()).add(s["channel"])
    if any(len(names) != 1 for names in channel_names.values()):
        raise B1cx2Error("A channel id maps to more than one channel name in the samples")
    if b1b_summary is not None:
        window, totals = b1b_summary["window"], b1b_summary["totals"]
        if (window["start"], window["end"]) != (head["start"], head["end"]):
            raise B1cx2Error("Window differs from the B1b export")
        if (end["events"], end["has_errors"]) != (totals["events"], totals["err_any"]):
            raise B1cx2Error(f"END events/has_errors {end['events']}/{end['has_errors']} differ from B1b {totals['events']}/{totals['err_any']}")
    return {"header": head, "end": end, "has_errors_by_event": he, "present": present, "scopes": scopes,
            "flags_set": {f: {s: flagset[(s, f)] for s in RANGES + CHANNELS} for f in FLAGS},
            "cells": {f"R{r}C{c}": cells[(r, c)] for r, c in sorted(cells)},
            "channel_names": {f"C{c}": sorted(n)[0] for c, n in sorted(channel_names.items())}, "samples": samples}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--b1b-summary", type=Path, help="B1b window export summary.json for the totals cross-check")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1cx2Error(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.log.read_bytes()
        b1b = json.loads(args.b1b_summary.read_text(encoding="utf-8")) if args.b1b_summary else None
        result = parse(raw.decode("utf-8-sig"), b1b)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, B1cx2Error) as exc:
        print(f"B1c-x2 output not accepted: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "haserrors.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    set_flags = {f: v for f, v in result["flags_set"].items() if any(v.values())}
    summary = {
        "status": "PASS_HASERRORS_PROBE_OUTPUT",
        "b1b_totals_crosscheck": "MATCHED" if b1b is not None else "NOT_RUN",
        "end": result["end"],
        "has_errors_by_event": result["has_errors_by_event"],
        "scopes": result["scopes"],
        "channel_names_from_samples": result["channel_names"],
        "flags_set_nonzero": set_flags,
        "members_never_present": [f for f, n in result["present"].items() if n == 0],
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "not_established": ["meaning of a set member beyond the VSE manual text", "link health or any rule result"],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
