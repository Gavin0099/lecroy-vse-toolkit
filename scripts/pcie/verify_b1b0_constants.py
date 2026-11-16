#!/usr/bin/env python3
"""Check the PCIe-B1b-0 VSE constant probe output and write constants.json (name -> value)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_g1a_log import DONE_MARKER, RUNTIME_ERROR_RE  # noqa: E402

HEADER = "PCIE_B1B0_CONSTANTS_V1"
CONST_RE = re.compile(r"^PCIE_B1B0_CONST\|(?P<name>[A-Z0-9_]+)=(?P<value>-?\d+)$")
END = "PCIE_B1B0_END|reason=trace_end"
REQUIRED = ("_PKT_TLP", "_PKT_DLLP", "_PKT_ORDERED_SET", "_PKT_LINK_CONDITION", "_CHANNEL_1", "_CHANNEL_2",
            "LINK_CONDITION_LINK_DOWN", "LINK_CONDITION_LINK_UP", "LTSSM_STATE_DETECT", "LTSSM_STATE_POLLING",
            "LTSSM_STATE_CONFIG", "LTSSM_STATE_L0", "LTSSM_STATE_RECOVERY")


class B1b0Error(ValueError):
    """The constant probe output is incomplete or inconsistent."""


def parse(text: str) -> dict[str, int]:
    lines = [line.strip() for line in text.splitlines()]
    if lines.count(HEADER) != 1 or lines.count(END) != 1 or lines.count(DONE_MARKER) != 1:
        raise B1b0Error("Expected exactly one header, END marker and VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise B1b0Error("The output contains a runtime-error marker")
    constants: dict[str, int] = {}
    for line in lines:
        if not line.startswith("PCIE_B1B0_") or line in (HEADER, END):
            continue
        match = CONST_RE.fullmatch(line)
        if not match:
            raise B1b0Error(f"Unrecognized line: {line[:80]}")
        if match["name"] in constants:
            raise B1b0Error(f"Duplicate constant {match['name']}")
        constants[match["name"]] = int(match["value"])
    missing = [name for name in REQUIRED if name not in constants]
    if missing:
        raise B1b0Error(f"Missing constants: {missing}")
    packet_events = [constants[k] for k in constants if k.startswith("_PKT_")]
    if len(set(packet_events)) != len(packet_events):
        raise B1b0Error("Packet event constants are not distinct")
    return constants


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1b0Error(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.log.read_bytes()
        constants = parse(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, B1b0Error) as exc:
        print(f"B1b-0 output not accepted: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "constants.json").write_text(json.dumps(constants, indent=1) + "\n", encoding="utf-8")
    summary = {"status": "PASS_CONSTANT_PROBE_OUTPUT", "constants": len(constants), "log_sha256": hashlib.sha256(raw).hexdigest().upper()}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "values": constants}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
