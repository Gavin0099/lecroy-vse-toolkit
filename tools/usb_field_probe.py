#!/usr/bin/env python3
"""Bounded USB field observations. Never runs COM or evaluates protocol policy."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import s01_contract as s01


def script(slice_id, limit=128):
    if slice_id not in {"U02", "U03"} or type(limit) is not int or not 1 <= limit <= 512:
        raise s01.ContractError("unsupported slice or sample limit")
    if slice_id == "U03":
        # Same documented raw members already qualified by M2; only add the
        # installed name function. No duration-based classification.
        return f'''# U03: LC-04 PDF30-31, LC-09 GetLfpsDesc, existing M2 raw contract.
set Visited = 0;
set KnownModeCount = 0;
set UnknownModeCount = 0;
set Emitted = 0;
set Mismatches = 0;
%include "VSTools.inc"
OnStartScript()
{{
    SendAllChannels();
    SendLevelOnly(_PKT);
    SendTraceEventOnly(_USB3_LFPS);
    SendPktsWithBadCRC(1);
    ScriptForDisplayOnly();
}}
ProcessEvent()
{{
    Visited++;
    if (in.Level != _PKT || in.TraceEvent != _USB3_LFPS) Mismatches++;
    if (in.Speed == _SS || in.Speed == _SSP)
    {{
        KnownModeCount++;
        if (Emitted < {limit})
        {{
            ModeName = "SS";
            if (in.Speed == _SSP) ModeName = "SSP";
            ReportText(FormatEx("U03|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%s|%s",
                in.Index, in.Time[0], in.Time[1], in.Channel, in.Speed, in.Type,
                in.Duration, in.DurationSec, in.DurationNS, in.PatternType, in.StartsPattern,
                GetLfpsDesc(in.Type), ModeName));
            Emitted++;
        }}
    }}
    else UnknownModeCount++;
    return Complete();
}}
OnFinishScript()
{{
    ReportText(FormatEx("U03-UNSUPPORTED-MODE|%d", UnknownModeCount));
    NotifyClient(2502, ["U01-END", Visited, KnownModeCount, Emitted, Mismatches, _PKT]);
    return 0;
}}
'''
    return f'''# U02: LC-04 PDF19/20/32; LC-09/12; USB-01 7.2.2.1-.2 / 7.3.5.
set Visited = 0;
set KnownModeCount = 0;
set UnknownModeCount = 0;
set Emitted = 0;
set Mismatches = 0;
%include "VSTools.inc"
OnStartScript()
{{
    SendAllChannels();
    SendLevelOnly(_PKT);
    SendTraceEventOnly(_USB3_LINK_CMD);
    SendPktsWithBadCRC(1);
    ScriptForDisplayOnly();
}}
ProcessEvent()
{{
    Visited++;
    if (in.Level != _PKT || in.TraceEvent != _USB3_LINK_CMD) Mismatches++;
    if (in.Speed == _SS || in.Speed == _SSP)
    {{
        KnownModeCount++;
        if (Emitted < {limit})
        {{
            ModeName = "SS";
            if (in.Speed == _SSP) ModeName = "SSP";
            ReportText(FormatEx("U02|%d|%d|%d|%d|%d|%d|%d|%d|%d|%d|%s|%s",
                in.Index, in.Time[0], in.Time[1], in.Channel, in.Speed,
                in.LnkCmd, in.LinkCmdInfo, in.CRC5, in.LinkCmdInfo_2, in.CRC5_2,
                GetUsb3LnkCmdDesc(in.LnkCmd), ModeName));
            Emitted++;
        }}
    }}
    else UnknownModeCount++;
    return Complete();
}}
OnFinishScript()
{{
    ReportText(FormatEx("U02-UNSUPPORTED-MODE|%d", UnknownModeCount));
    NotifyClient(2502, ["U01-END", Visited, KnownModeCount, Emitted, Mismatches, _PKT]);
    return 0;
}}
'''


def prepare(output, slice_id, trace_sha, limit=128):
    text = script(slice_id, limit)
    if type(trace_sha) is not str or not re.fullmatch(r"[0-9a-f]{64}", trace_sha):
        raise s01.ContractError("explicit lowercase trace identity required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    path = output / (slice_id.lower() + ".vse")
    path.write_text(text, encoding="utf-8", newline="\n")
    plan = {"schema_version": "usb.field-plan/v1", "slice": slice_id, "trace_sha256": trace_sha,
            "script": path.name, "script_sha256": hashlib.sha256(text.encode()).hexdigest(), "sample_limit": limit,
            "qualification": "NOT_EVALUATED"}
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def validate_plan(plan):
    if type(plan) is not dict or set(plan) != {"schema_version", "slice", "trace_sha256", "script", "script_sha256", "sample_limit", "qualification"}:
        raise s01.ContractError("invalid field plan shape")
    text = script(plan["slice"], plan["sample_limit"])
    if (plan["schema_version"] != "usb.field-plan/v1" or plan["qualification"] != "NOT_EVALUATED"
            or type(plan["trace_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", plan["trace_sha256"])
            or plan["script"] != plan["slice"].lower() + ".vse"
            or plan["script_sha256"] != hashlib.sha256(text.encode()).hexdigest()):
        raise s01.ContractError("field plan binding or template mismatch")


def assess(result, plan):
    validate_plan(plan)
    keys = {"slice", "trace_sha256", "script_sha256", "integrity", "run_result", "finished_result", "error", "summary", "reports"}
    if type(result) is not dict or set(result) != keys:
        raise s01.ContractError("invalid saved field-result shape")
    if (result["slice"] != plan["slice"] or result["trace_sha256"] != plan["trace_sha256"] or result["script_sha256"] != plan["script_sha256"]):
        raise s01.ContractError("field result bound to another input")
    integrity = result["integrity"]
    if type(integrity) is not dict or set(integrity) != {"source_unchanged", "working_copy_unchanged", "working_copy_readonly"} or any(x is not True for x in integrity.values()):
        raise s01.ContractError("field probe integrity failed")
    if type(result["run_result"]) is not int or result["run_result"] != 2 or type(result["finished_result"]) is not int or result["finished_result"] != 2 or result["error"] != "":
        raise s01.ContractError("field probe completion failed")
    summary = result["summary"]
    if type(summary) is not list or len(summary) != 5 or any(type(x) is not int or x < 0 for x in summary):
        raise s01.ContractError("field probe end marker missing")
    visited, known, emitted, mismatches, level = summary
    if not visited >= known >= emitted or emitted != min(known, plan["sample_limit"]) or mismatches:
        raise s01.ContractError("field probe counts do not reconcile")
    if type(result["reports"]) is not list or any(type(x) is not str for x in result["reports"]):
        raise s01.ContractError("invalid report rows")
    records = []
    mode_markers = []
    prefix = plan["slice"]
    fields = (["index", "time_sec", "time_ns", "channel_raw", "speed_raw", "lnkcmd_raw", "info_raw", "crc5_raw", "replica_info_raw", "replica_crc5_raw"]
              if prefix == "U02" else ["index", "time_sec", "time_ns", "channel_raw", "speed_raw", "type_raw", "duration_raw_ns", "duration_sec", "duration_remainder_ns", "pattern_type_raw", "starts_pattern"])
    for line in result["reports"]:
        if line.startswith(prefix + "-UNSUPPORTED-MODE|"):
            token = line.split("|")
            if len(token) != 2 or not re.fullmatch(r"[0-9]+", token[1]):
                raise s01.ContractError("invalid unknown mode count")
            mode_markers.append(int(token[1]))
        elif line.startswith(prefix + "|"):
            values = line.split("|")
            if len(values) != len(fields)+3 or any(not re.fullmatch(r"[0-9]+", x) for x in values[1:1+len(fields)]):
                raise s01.ContractError("invalid numeric field row")
            row = dict(zip(fields, map(int, values[1:1+len(fields)])))
            if row["time_ns"] >= 1_000_000_000:
                raise s01.ContractError("timestamp component outside nanosecond range")
            if prefix == "U02" and (row["info_raw"] > 0x7ff or row["replica_info_raw"] > 0x7ff or row["crc5_raw"] > 31 or row["replica_crc5_raw"] > 31):
                raise s01.ContractError("field value outside independent documented width")
            if prefix == "U03" and (row["duration_remainder_ns"] >= 1_000_000_000 or row["starts_pattern"] not in {0,1}):
                raise s01.ContractError("invalid LFPS duration component or pattern flag")
            if values[-1] not in {"SS", "SSP"} or not re.fullmatch(r"[A-Z0-9_]+|UNK\([0-9]+\)", values[-2]):
                raise s01.ContractError("unknown/corrupt mode or native name encoding")
            row.update(level_raw=level, mode_observed=values[-1], name_vendor=values[-2], name_state="unknown" if values[-2].startswith("UNK(") else "named",
                       origin="vendor_decoded", packet_ref={"trace_sha256": plan["trace_sha256"], "index": row["index"], "level": "_PKT", "channel_raw": row["channel_raw"]})
            if prefix == "U02": row["replica_applicability"] = "applicable"
            else: row.update(duration_unit="ns", measurement_resolution="unknown", wake_reset_success="NOT_EVALUATED")
            records.append(row)
    if len(mode_markers) != 1 or known + mode_markers[0] != visited or len(records) != emitted:
        raise s01.ContractError("report rows or supported-mode accounting incomplete")
    identities = {(r["index"], r["channel_raw"], r["time_sec"], r["time_ns"]) for r in records}
    if len(identities) != len(records):
        raise s01.ContractError("duplicate packet source reference")
    return {"schema_version": "usb.field-observation/v1", "slice": plan["slice"], "records": records,
            "callback_count": visited, "supported_mode_callback_count": known, "exported_count": emitted,
            "sample_truncated": known > emitted, "unsupported_mode_count": mode_markers[0],
            "observed_native_names": sorted({r["name_vendor"] for r in records}),
            "crc_correctness": "NOT_EVALUATED", "other_command_types": "not_qualified",
            "capture_completeness": "unknown", "qualification": "NOT_EVALUATED"}


def manifest(result, plan, before, result_path, result_sha, before_path, before_sha):
    a=assess(result,plan)
    if (type(before) is not dict or type(before.get("source")) is not dict or type(before.get("toolchain")) is not dict
            or type(before["toolchain"].get("software_version")) is not str or not before["toolchain"]["software_version"].strip()
            or type(before["toolchain"].get("constants")) is not dict
            or type(before["toolchain"]["constants"].get("sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}",before["toolchain"]["constants"]["sha256"])
            or ("vstools" in before["toolchain"] and type(before["toolchain"]["vstools"]) is not dict)):
        raise s01.ContractError("invalid before/toolchain metadata")
    if before["source"].get("sha256") != plan["trace_sha256"]:
        raise s01.ContractError("before metadata belongs to another source")
    unknown={"state":"unknown","value":None,"evidence_refs":[]}
    refs=["NATIVE-OUTPUT"]
    facts={key:dict(unknown) for key in ["mode","bidirectional","capture_start","capture_end","epoch","filters"]}
    facts["filters"]={"state":"known","value":json.dumps({"level":"_PKT","slice":plan["slice"],"sample_limit":plan["sample_limit"],"mode_guard":["_SS","_SSP"],"bad_crc_flag":1},sort_keys=True),"evidence_refs":refs}
    caps=["in.Index","in.Time","in.Channel","in.Speed"]
    caps += (["in.LnkCmd","in.LinkCmdInfo","in.CRC5","in.LinkCmdInfo_2","in.CRC5_2","GetUsb3LnkCmdDesc"] if plan["slice"]=="U02"
             else ["in.Type","in.Duration","in.DurationSec","in.DurationNS","in.PatternType","in.StartsPattern","GetLfpsDesc"])
    indices=[r["index"] for r in a["records"]]
    m={"schema_version":"s01.input-manifest/v1","manifest_id":plan["slice"]+"-FIELD-SAMPLE","origin":"recorded",
       "trace":{"trace_id":plan["slice"]+"-"+plan["trace_sha256"][:12],"sha256":plan["trace_sha256"],"protocol":"usb","identity_evidence_refs":refs,"facts":facts},
       "toolchain":{"software_version":before["toolchain"]["software_version"],"extractor_sha256":plan["script_sha256"],"constants_sha256":before["toolchain"]["constants"]["sha256"],"evidence_refs":["BEFORE"]},
       "sources":[{"source_id":"LC-04","revision":"VSE Manual9.12, July2025, Suite10.13+","locator":"installed:USBProtocolSuiteVSEManual.pdf",
                   "review_depth":"sections_reviewed","sections":["PDF19/20/30/31/32"],"applicability":"applicable","evidence_refs":["LC-04-DOC"]},
                  {"source_id":"LC-09","revision":"Installed VSTools SHA in before.json","locator":"installed:VSTools.inc",
                   "review_depth":"sections_reviewed","sections":["GetLfpsDesc","GetUsb3LnkCmdDesc"],"applicability":"applicable","evidence_refs":["LC-09-DOC"]}],
       "evidence":[{"id":"NATIVE-OUTPUT","kind":"saved_output","locator":str(result_path),"sha256":result_sha,"trace_sha256":plan["trace_sha256"],"note":"Native field sample only; no wire correctness or complete capture claim."},
                   {"id":"BEFORE","kind":"saved_output","locator":str(before_path),"sha256":before_sha,"trace_sha256":plan["trace_sha256"],"note":"Source/script/toolchain preflight identity; not coverage proof."},
                   {"id":"LC-04-DOC","kind":"document","locator":"installed:USBProtocolSuiteVSEManual.pdf","sha256":None,"note":"Manual9.12 selected input/member sections read; not a runtime availability proof."},
                   {"id":"LC-09-DOC","kind":"document","locator":"installed:VSTools.inc","sha256":before["toolchain"].get("vstools",{}).get("sha256"),"note":"Installed vendor name functions; native classifier origin retained."}],
       "capabilities":[{"id":"usb."+key,"api_support":"supported" if indices else "unknown","applicability":"applicable" if indices else "unknown","availability":"available" if indices else "unknown","evidence_refs":refs if indices else []} for key in caps],
       "observations":[{"event":"usb."+("LINK_CMD" if plan["slice"]=="U02" else "LFPS"),"state":"observed" if indices else "unknown","count":len(indices),
                        "coverage":{"selection":"included","retention":"unknown","extraction":"partial" if a["sample_truncated"] else "complete","start_index":min(indices) if indices else None,"end_index":max(indices) if indices else None},"evidence_refs":refs}],
       "historical_claims":[],"claim_boundary":"INPUT_METADATA_ONLY"}
    errors=s01.validate_manifest(m)
    if errors:raise s01.ContractError(json.dumps(errors))
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=["prepare", "check-plan", "assess", "manifest"])
    p.add_argument("--output", type=Path)
    p.add_argument("--slice", default="U02")
    p.add_argument("--trace-sha256")
    p.add_argument("--limit", type=int, default=128)
    p.add_argument("--plan", type=Path)
    p.add_argument("--result", type=Path)
    p.add_argument("--before", type=Path)
    a = p.parse_args()
    try:
        if a.kind == "prepare":
            if a.output is None: raise s01.ContractError("output required")
            value = prepare(a.output, a.slice, a.trace_sha256, a.limit)
        else:
            if a.plan is None: raise s01.ContractError("plan required")
            plan = s01.read_json(a.plan)
            if a.kind == "check-plan":
                validate_plan(plan); value = {"status": "valid"}
            else:
                if a.result is None: raise s01.ContractError("result required")
                result=s01.read_json(a.result)
                if a.kind=="manifest":
                    if a.before is None:raise s01.ContractError("before metadata required")
                    value=manifest(result,plan,s01.read_json(a.before),a.result,hashlib.sha256(a.result.read_bytes()).hexdigest(),a.before,hashlib.sha256(a.before.read_bytes()).hexdigest())
                else:value = assess(result, plan)
        print(json.dumps(value, indent=2, allow_nan=False)); return 0
    except (s01.ContractError, OSError) as e:
        print(json.dumps({"status": "invalid", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
