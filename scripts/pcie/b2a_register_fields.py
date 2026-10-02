#!/usr/bin/env python3
"""Validate the qualified non-Flit probe against existing G2a metadata and bytes."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "pcie.b2a-register-fields/v1"
FIELDS = "packet_index time_display channel tlp_type requester_id tag device_id register address register_data first_be last_be payload_length payload_prefix completer_id compl_status byte_count lower_addr frame_prefix".split()
TEXT = {"time_display", "channel", "payload_prefix", "frame_prefix"}
CFG = {9, 10, 11, 12}
HEADER = 'B2A_BEGIN|v1|index|time|channel|type|requester|tag|device|register|address|data|first_be|last_be|payload_len|payload_prefix|completer|status|byte_count|lower_addr|frame_prefix'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def parse(text):
    rows, end, begun = [], None, False
    for line in text.splitlines():
        if line.startswith("B2A_BEGIN|"):
            if begun or rows or line != HEADER: raise ValueError("Duplicate/misplaced/unsupported begin")
            begun = True
        elif line.startswith("B2A_ROW|"):
            if not begun or end: raise ValueError("Row outside probe markers")
            parts = line.split("|")[1:]
            if len(parts) != len(FIELDS): raise ValueError("Malformed probe row")
            row = {}
            for key, value in zip(FIELDS, parts):
                value = value.strip()
                if key in TEXT: row[key] = None if value == "NA" else value
                elif value == "NA": row[key] = None
                elif key == "packet_index" and value.isdecimal(): row[key] = int(value)
                elif re.fullmatch(r"0x[0-9A-F]+", value): row[key] = int(value, 16)
                else: raise ValueError(f"Invalid numeric field {key}")
            if row["packet_index"] is None or (rows and row["packet_index"] <= rows[-1]["packet_index"]): raise ValueError("Non-increasing packets")
            rows.append(row)
        elif line.startswith("B2A_END|"):
            m = re.fullmatch(r"B2A_END\|tlps=(\d+)\|rows=(\d+)\|reason=trace_end", line)
            if not begun or end or not m: raise ValueError("Invalid end marker")
            end = {"tlps": int(m[1]), "rows": int(m[2])}
    if not end or not rows or end["rows"] != len(rows): raise ValueError("Incomplete probe")
    return rows, end


def verify(rows, end, metadata, *, require_full_payload=False):
    """Check fields; legacy 16-byte inputs get consistency checks only.

    Fresh CLI qualification requires independent raw bytes for the first DWORD.
    Historical downstream replay may retain the narrower legacy evidence scope.
    """
    if any(r.get('row')!=i+1 for i,r in enumerate(metadata)) or any(b['packet_index']<=a['packet_index'] for a,b in zip(metadata,metadata[1:])): raise ValueError('Invalid G2a row order')
    wanted = [r for r in metadata if int(r["tlp_type_hex"], 16) in CFG | {17, 18}]
    if end["tlps"] != len(metadata) or len(rows) != len(wanted): raise ValueError("Coverage differs from G2a")
    counts = {"config_reads": 0, "config_writes": 0, "completions": 0, "payload_dwords_checked": 0}
    for r, old in zip(rows, wanted):
        for key in ("packet_index", "time_display", "channel", "requester_id", "tag", "completer_id", "compl_status"):
            if r[key] != old[key]: raise ValueError(f"G2a mismatch {key} at {r['packet_index']}")
        typ = r["tlp_type"]
        if typ != int(old["tlp_type_hex"], 16): raise ValueError("Type mismatch")
        if r["frame_prefix"] is None or not re.fullmatch(r"(?:[0-9A-F]{32}|[0-9A-F]{38})", r["frame_prefix"]): raise ValueError("Missing frame prefix")
        f = bytes.fromhex(r["frame_prefix"])
        # Qualified on this capture only: FB + two sequence bytes + 3-DW header.
        # Unsupported framing is rejected, not decoded using this layout.
        if f[0] != 0xFB or f[3] != {9: 4, 10: 0x44, 11: 5, 12: 0x45, 17: 0xA, 18: 0x4A}[typ]: raise ValueError("Unsupported frame layout")
        plen = r["payload_length"]
        if plen is None or plen < 0: raise ValueError("Missing payload length")
        p = bytes.fromhex(r["payload_prefix"]) if r["payload_prefix"] else b""
        if len(p) != min(plen, 16): raise ValueError("Payload prefix length mismatch")
        if plen:
            needed=min(plen,4)
            if require_full_payload and len(f)<15+needed: raise ValueError("Full raw DWORD/payload bytes required for qualification")
            available=min(needed,len(f)-15)
            if f[15:15+available] != p[:available]: raise ValueError("Frame/payload mismatch")
            if plen >= 4 and r["register_data"] is not None:
                if r["register_data"] != int.from_bytes(p[:4], "little"): raise ValueError("RegisterData/payload mismatch")
                counts["payload_dwords_checked"] += 1
        if typ in CFG:
            for key, value in (("requester_id", int.from_bytes(f[7:9], "big")), ("tag", f[9]), ("first_be", f[10] & 15), ("last_be", f[10] >> 4), ("device_id", int.from_bytes(f[11:13], "big")), ("register", int.from_bytes(f[13:15], "big") & 0xFFC)):
                if r[key] != value: raise ValueError(f"Config header mismatch {key}")
            if typ in (9, 11):
                if plen != 0 or r["register_data"] is not None: raise ValueError("Read request contains inferred data")
                counts["config_reads"] += 1
            else:
                if plen != 4 or r["register_data"] is None: raise ValueError("Missing write DWORD")
                counts["config_writes"] += 1
        else:
            for key, value in (("completer_id", int.from_bytes(f[7:9], "big")), ("compl_status", f[9] >> 5), ("byte_count", int.from_bytes(f[9:11], "big") & 0xFFF), ("requester_id", int.from_bytes(f[11:13], "big")), ("tag", f[13]), ("lower_addr", f[14] & 0x7F)):
                if r[key] != value: raise ValueError(f"Completion header mismatch {key}")
            counts["completions"] += 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("com-run", "metadata", "output-dir"): ap.add_argument("--" + name, type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.output_dir.exists(): raise ValueError("Refusing existing output")
        run = json.loads((a.com_run / "com-run.json").read_text(encoding="utf-8"))
        raw = a.com_run / "vse-output.txt"
        if run["status"] != "COM_RUN_COMPLETE" or run.get('steps',{}).get('finish_event',{}).get('result_name')!='DONE' or not run["identities_unchanged"] or sha(raw) != run["output"]["vse_output_sha256"]: raise ValueError("Unqualified COM evidence")
        rows, end = parse(raw.read_text(encoding="utf-8")); counts = verify(rows, end, json.loads(a.metadata.read_text(encoding="utf-8")), require_full_payload=True)
        out = {"schema": SCHEMA, "status": "PASS_REGISTER_FIELD_PROBE", "input": {"com_run_sha256": sha(a.com_run / "com-run.json"), "vse_output_sha256": sha(raw), "metadata_sha256": sha(a.metadata), "trace": run["pre"]["files"][0]}, "units": {"register": "byte offset (qualified on this capture)", "register_data": "little-endian DWORD from payload; not a CfgRd request value", "byte_enable": "first/last DWORD byte mask", "payload_length": "bytes"}, "counts": counts, "tlps": end["tlps"], "rows": rows, "not_established": ["all versions/framing modes", "CplD is config data without request association", "vendor register meaning", "post-switch initialization beyond capture end"]}
        a.output_dir.mkdir(parents=True)
        out['validation_basis']={'frame_prefix_bytes':19,'payload_proof':'first payload DWORD compared independently with raw frame bytes 15..18',
                                 'legacy_16_byte_prefix':'historical consistency checks only; cannot qualify a new payload DWORD'}
        (a.output_dir / "fields.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": out["status"], **counts}))
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(str(e), file=sys.stderr); return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
