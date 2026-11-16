#!/usr/bin/env python3
"""Check a saved PCIe-G3c-0 message field probe log against the verified G1a count and G2a field export."""

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

HEADER = "PCIE_G3C0_MSG_FIELDS_V1 fields=requester_id,message_code,message_route"
ROW_RE = re.compile(
    r"^PCIE_G3C0_MSG\|(?P<index>\d+)\|(?P<time>[^|]+)\|(?P<channel>[^|]+)\|(?P<type>0x[0-9A-Fa-f]+)\|"
    r"(?P<requester>NA|0x[0-9A-Fa-f]{4})\|(?P<code>NA|0x[0-9A-Fa-f]{2})\|(?P<route>NA|0x[0-9A-Fa-f])$"
)
END_RE = re.compile(r"^PCIE_G3C0_END\|tlps=(?P<tlps>\d+)\|messages=(?P<messages>\d+)\|reason=trace_end$")
MESSAGE_TYPE_CODES = {"0xD", "0xE", "0xF", "0x10"}

# Installed Scripts/VFScripts/VS_constants.inc (SHA-256 799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D).
VENDOR_CONSTANTS_SOURCE = "Scripts/VFScripts/VS_constants.inc SHA-256 799311B51894B31B1B35B99294227D3CB770D28758B0EEE4D915CAD09E6A2E6D"
MESSAGE_CODE_NAMES = {
    0x20: "ASSERT_INTA", 0x21: "ASSERT_INTB", 0x22: "ASSERT_INTC", 0x23: "ASSERT_INTD",
    0x24: "DEASSERT_INTA", 0x25: "DEASSERT_INTB", 0x26: "DEASSERT_INTC", 0x27: "DEASSERT_INTD",
    0x14: "PM_ACTIVESTATENAK", 0x18: "PM_PME", 0x19: "PM_TURNOFF", 0x1B: "PM_TOACK",
    0x30: "ERR_COR", 0x31: "ERR_NONFATAL", 0x33: "ERR_FATAL", 0x03: "UNLOCK", 0x50: "SLOTPOWERLIMIT",
    0x7E: "VENDOR0", 0x7F: "VENDOR1", 0x52: "PTM_REQUEST", 0x53: "PTM_RESPONSE",
    0x41: "HP_ATTN_IND_ON", 0x43: "HP_ATTN_IND_BLINK", 0x40: "HP_ATTN_IND_OFF", 0x45: "HP_POWER_IND_ON",
    0x47: "HP_POWER_IND_BLINK", 0x44: "HP_POWER_IND_OFF", 0x48: "HP_ATTN_BTN_PRESSED",
}
MESSAGE_ROUTE_NAMES = {
    0x0: "TOROOTCOMPLEX", 0x1: "BYADDRESS", 0x2: "BYID", 0x3: "FROMROOTCOMPLEX",
    0x4: "LOCALTERMRECEIVER", 0x5: "GATHERTOROOTCOMPLEX", 0x6: "RESERVED1TERMRECEIVER", 0x7: "RESERVED2TERMRECEIVER",
}


class G3c0Error(ValueError):
    """The log does not establish a complete message field probe."""


def parse_messages(text: str, g1a_total: int, g2a_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines()]
    if lines.count(HEADER) != 1:
        raise G3c0Error("Expected exactly one G3c-0 header")
    if lines.count(DONE_MARKER) != 1:
        raise G3c0Error("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise G3c0Error("The log contains a runtime-error marker")
    rows: list[dict[str, Any]] = []
    ends: list[re.Match[str]] = []
    for line in lines:
        if not line.startswith("PCIE_G3C0_") or line == HEADER:
            continue
        if match := ROW_RE.fullmatch(line):
            if ends:
                raise G3c0Error("Message row after END")
            code = None if match["code"] == "NA" else int(match["code"], 16)
            route = None if match["route"] == "NA" else int(match["route"], 16)
            rows.append({
                "packet_index": int(match["index"]),
                "time_display": match["time"].strip(),
                "channel": match["channel"].strip(),
                "tlp_type_hex": "0x" + match["type"][2:].upper(),
                "requester_id": None if match["requester"] == "NA" else int(match["requester"], 16),
                "message_code": code,
                "message_code_name": None if code is None else MESSAGE_CODE_NAMES.get(code, "UNMAPPED"),
                "message_route": route,
                "message_route_name": None if route is None else MESSAGE_ROUTE_NAMES.get(route, "UNMAPPED"),
            })
        elif match := END_RE.fullmatch(line):
            ends.append(match)
        else:
            raise G3c0Error(f"Unrecognized G3c-0 line: {line[:80]}")
    if len(ends) != 1:
        raise G3c0Error(f"Expected exactly one END; found {len(ends)}")
    if int(ends[0]["tlps"]) != g1a_total:
        raise G3c0Error(f"END reports {ends[0]['tlps']} TLPs; G1a verified {g1a_total}")
    expected = [r for r in g2a_rows if r["tlp_type_hex"] in MESSAGE_TYPE_CODES]
    if int(ends[0]["messages"]) != len(rows) or len(rows) != len(expected):
        raise G3c0Error(f"Expected {len(expected)} message rows from G2a; log has {len(rows)}, END says {ends[0]['messages']}")
    for row, ref in zip(rows, expected):
        for key in ("packet_index", "time_display", "channel", "tlp_type_hex", "requester_id"):
            if row[key] != ref[key]:
                raise G3c0Error(f"Message {row['packet_index']} {key} differs from the verified G2a export")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--g1a-log", type=Path, required=True)
    parser.add_argument("--g2a-fields", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise G3c0Error(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.log.read_bytes()
        g1a = check_log(args.g1a_log.read_bytes().decode("utf-8-sig"))
        g2a_raw = args.g2a_fields.read_bytes()
        rows = parse_messages(raw.decode("utf-8-sig"), g1a["tlp_callback_count"], json.loads(g2a_raw.decode("utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, G1aLogError, G3c0Error) as exc:
        print(f"G3c-0 log not accepted: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    data = (json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    (args.output_dir / "messages.json").write_bytes(data)
    summary = {
        "status": "PASS_MESSAGE_FIELD_PROBE_OUTPUT",
        "messages": rows,
        "log_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "g2a_fields_sha256": hashlib.sha256(g2a_raw).hexdigest().upper(),
        "messages_json_sha256": hashlib.sha256(data).hexdigest().upper(),
        "name_source": VENDOR_CONSTANTS_SOURCE,
        "not_established": [
            "GUI agreement (compared separately against retained GUI screenshots)",
            "any causal relation between a message and a candidate",
        ],
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
