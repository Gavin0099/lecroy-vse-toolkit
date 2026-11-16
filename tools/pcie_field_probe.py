"""P03: PCIe-only, bounded native fields. No replay/credit/compliance evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s01_contract as s

CAP = 8  # first eight callbacks per native type, not an inclusive packet window
DLLP = {0: "ACK", 1: "NAK", 4: "INIT_FC1_P", 5: "INIT_FC1_NP", 6: "INIT_FC1_CPL",
        12: "INIT_FC2_P", 13: "INIT_FC2_NP", 14: "INIT_FC2_CPL",
        8: "UPDATE_FC_P", 9: "UPDATE_FC_NP", 10: "UPDATE_FC_CPL"}
TLP = {1: "MRD32", 3: "MWR32", 4: "MRD64", 6: "MWR64", 7: "IORD", 8: "IOWR",
       9: "CFGRD_0", 10: "CFGWR_0", 11: "CFGRD_1", 12: "CFGWR_1",
       13: "MSG", 14: "MSGD", 17: "CPL", 18: "CPLD", 19: "CPLLK", 20: "CPLDLK"}
FC = set(DLLP) - {0, 1}
COMPLETION = {17, 18, 19, 20}
FIELDS = {
    "dllp": ["AckNak_SeqNum", "VC_ID", "HdrFC", "DataFC", "HdrScale", "DataScale", "BadCRC", "InvalidEncoding", "FCError"],
    "tlp": ["Type", "Fmt", "PSN", "Length", "ByteCount", "LowerAddr", "ComplStatus", "BadLCRC", "BadECRC", "ErrorLengthField"],
}


def applicable(profile, native_type, field):
    # LC-01 §§5.2.2–3; no mode/epoch is inferred from a non-null field.
    if profile == "dllp":
        if field == "AckNak_SeqNum": return native_type in {0, 1}
        if field in {"VC_ID", "HdrFC", "DataFC", "HdrScale", "DataScale"}: return native_type in FC
    elif field in {"ByteCount", "LowerAddr", "ComplStatus"}:
        return native_type in COMPLETION
    return True


def script(profile):
    if profile not in FIELDS: raise s.ContractError("unknown P03 profile")
    types = DLLP if profile == "dllp" else TLP
    prefix = "DLLP_TYPE_" if profile == "dllp" else "TLP_TYPE_ID_"
    member = "DLLPType" if profile == "dllp" else "TLPType"
    event = "_PKT_DLLP" if profile == "dllp" else "_PKT_TLP"
    counters = "\n".join(f"set Count_{name} = 0;" for name in types.values())
    branches = []
    for number, name in types.items():
        fields = []
        for field in FIELDS[profile]:
            value = f"NativeField(in.{field})" if applicable(profile, number, field) else '"{\\\"state\\\":\\\"not_applicable\\\",\\\"value\\\":null}"'
            fields.append(f'        f_{field} = {value};')
        fmt = '{"kind":"p03-row","profile":"' + profile + '","index":%d,"level":%d,"channel":%d,"native_type":%d,"time2":[%d,%d,%d],"fields":{' + ','.join('"' + field + '":%s' for field in FIELDS[profile]) + '}}'
        args = "in.Index,in.Level,in.Channel,in." + member + ",in.Time2[0],in.Time2[1],in.Time2[2]," + ",".join("f_" + field for field in FIELDS[profile])
        branches.append(f'''    if (in.{member} == {prefix}{name})
    {{
        Known++;
        Count_{name}++;
        if (Count_{name} <= {CAP})
        {{
{chr(10).join(fields)}
            ReportText(FormatEx({json.dumps(fmt)}, {args}));
            Emitted++;
        }}
    }}''')
    counts = "\n".join('    ReportText(FormatEx("' + '{\\"kind\\":\\"p03-count\\",\\"native_type\\":%d,\\"visited\\":%d}' + '", ' + prefix + name + ', Count_' + name + '));' for name in types.values())
    return f'''# P03 LC-01 5.2.2/5.2.3: native raw fields; no rule evaluation.
set ModuleType = "Verification Script";
set OutputType = "VS";
set InputType = "VS";
set DecoderDesc = "P03 {profile} raw fields";
set Visited = 0;
set Known = 0;
set Emitted = 0;
set Mismatches = 0;
{counters}
%include "VSTools.inc"
NativeField(v)
{{
    if (v == null) return "{{\\"state\\":\\"unknown\\",\\"value\\":null}}";
    return FormatEx("{{\\"state\\":\\"available\\",\\"value\\":%d}}", v);
}}
OnStartScript()
{{
    ScriptForDisplayOnly();
    EnableOutput();
    SendAllChannels();
    SendLevelOnly(_PACKET);
    SendTraceEventOnly({event});
    {'SendDllpType(_ANY_TYPE);' if profile == 'dllp' else 'SendTlpType(_ANY_TYPE);'}
}}
ProcessEvent()
{{
    Visited++;
    if (in.Level != _PACKET || in.TraceEvent != {event}) Mismatches++;
{chr(10).join(branches)}
    return Complete();
}}
OnFinishScript()
{{
{counts}
    ReportText(FormatEx("{{\\"kind\\":\\"p03-end\\",\\"visited\\":%d,\\"known\\":%d,\\"emitted\\":%d,\\"mismatches\\":%d,\\"native_level\\":%d}}", Visited,Known,Emitted,Mismatches,_PACKET));
}}
'''


def prepare(output, trace_sha):
    if type(trace_sha) is not str or not re.fullmatch(r"[0-9a-f]{64}", trace_sha): raise s.ContractError("trace SHA-256 required")
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    plan = {"schema_version": "pcie.field-plan/v1", "trace_sha256": trace_sha, "cap_per_type": CAP,
            "selection": "first_callbacks_per_native_type", "profiles": {}}
    for profile in FIELDS:
        text = script(profile); (out / (profile + ".pevs")).write_text(text, encoding="utf-8", newline="\n")
        plan["profiles"][profile] = hashlib.sha256(text.encode()).hexdigest()
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def validate_plan(plan):
    if (type(plan) is not dict or set(plan) != {"schema_version", "trace_sha256", "cap_per_type", "selection", "profiles"}
            or plan["schema_version"] != "pcie.field-plan/v1" or type(plan["cap_per_type"]) is not int or plan["cap_per_type"] != CAP
            or plan["selection"] != "first_callbacks_per_native_type" or type(plan["trace_sha256"]) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", plan["trace_sha256"])
            or plan["profiles"] != {p: hashlib.sha256(script(p).encode()).hexdigest() for p in FIELDS}):
        raise s.ContractError("P03 plan/template mismatch")


def _nat(value): return type(value) is int and value >= 0


def assess(run, lines, plan, profile):
    validate_plan(plan)
    if profile not in FIELDS: raise s.ContractError("unknown profile")
    if (run.get("status") != "COM_RUN_COMPLETE" or run.get("identities_unchanged") is not True
            or run.get("steps", {}).get("finish_event", {}).get("result_name") != "DONE"
            or not run.get("steps", {}).get("close", {}).get("ok")
            or not run.get("steps", {}).get("process_exit", {}).get("ok")):
        raise s.ContractError("runtime/completion/integrity failure")
    pre = run.get("pre", {})
    if (pre.get("script", {}).get("sha256", "").lower() != plan["profiles"][profile]
            or not pre.get("files") or pre["files"][0].get("sha256", "").lower() != plan["trace_sha256"]):
        raise s.ContractError("run is bound to a different trace/script")
    if type(lines) is not list or any(type(x) is not str for x in lines): raise s.ContractError("invalid report lines")
    records = []
    for line in lines:
        if line.strip().startswith('{"kind":"p03-'):
            try: records.append(json.loads(line.strip(), object_pairs_hook=s._pairs, parse_constant=s._bad_constant))
            except ValueError as e: raise s.ContractError("invalid P03 JSON") from e
    if not records or records[-1].get("kind") != "p03-end": raise s.ContractError("terminal end required")
    ends = [r for r in records if r.get("kind") == "p03-end"]
    if len(ends) != 1: raise s.ContractError("one end required")
    end = ends[0]
    if (set(end) != {"kind", "visited", "known", "emitted", "mismatches", "native_level"}
            or any(not _nat(end[k]) for k in end if k != "kind")
            or end["mismatches"] or end["native_level"] != 0 or not end["visited"] >= end["known"] >= end["emitted"]):
        raise s.ContractError("invalid end counters/packet namespace")
    types = DLLP if profile == "dllp" else TLP
    counts = {}; rows = []; seen = set(); per_type = dict.fromkeys(types, 0); counts_started = False
    for r in records[:-1]:
        if r.get("kind") == "p03-count":
            counts_started = True
            if (set(r) != {"kind", "native_type", "visited"} or not _nat(r["native_type"])
                    or r["native_type"] not in types or r["native_type"] in counts or not _nat(r["visited"])):
                raise s.ContractError("invalid/duplicate type count")
            counts[r["native_type"]] = r["visited"]
        elif r.get("kind") == "p03-row":
            if counts_started: raise s.ContractError("row after summary")
            if (set(r) != {"kind", "profile", "index", "level", "channel", "native_type", "time2", "fields"}
                    or r["profile"] != profile or any(not _nat(r[k]) for k in ["index", "level", "channel", "native_type"])
                    or r["level"] != 0 or r["native_type"] not in types or r["index"] in seen
                    or (rows and r["index"] <= rows[-1]["index"])
                    or type(r["time2"]) is not list or len(r["time2"]) != 3 or any(not _nat(v) for v in r["time2"])
                    or r["time2"][1] >= 1_000_000_000 or r["time2"][2] >= 1000
                    or type(r["fields"]) is not dict or set(r["fields"]) != set(FIELDS[profile])):
                raise s.ContractError("invalid row context/time/field set")
            seen.add(r["index"]); per_type[r["native_type"]] += 1
            for field, cell in r["fields"].items():
                applies = applicable(profile, r["native_type"], field)
                if type(cell) is not dict or set(cell) != {"state", "value"}: raise s.ContractError("invalid field cell")
                state, value = cell["state"], cell["value"]
                if not applies:
                    if state != "not_applicable" or value is not None: raise s.ContractError("inapplicable field value")
                elif state == "available":
                    if not _nat(value): raise s.ContractError("available field needs raw integer")
                elif state != "unknown" or value is not None:
                    raise s.ContractError("null runtime field is unknown, not unsupported or absent")
            rows.append(r)
        else: raise s.ContractError("unknown P03 record")
    if (set(counts) != set(types) or sum(counts.values()) != end["known"] or len(rows) != end["emitted"]
            or any(per_type[t] != min(CAP, counts[t]) for t in types)):
        raise s.ContractError("sample/type count mismatch")
    return {"schema_version": "pcie.field-observation/v1", "trace_sha256": plan["trace_sha256"], "profile": profile,
            "rows": rows, "counts": {str(t): {"label": types[t], "visited": counts[t], "sampled": per_type[t],
                       "observation": "observed" if counts[t] else "unknown"} for t in types}, "summary": end,
            "coverage": {"selection": "explicit_type_subscription", "sample": "first_8_per_type", "retention": "unknown",
                         "display_filters": "unknown", "capture_bounds": "unknown", "mode": "unknown", "epoch": "unknown"},
            "scale_semantics": "raw_vendor_encoding_only", "length_semantics": "raw_vendor_field_no_zero_normalization",
            "qualification": "NOT_EVALUATED"}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("kind", choices=["prepare", "assess"])
    p.add_argument("--output", type=Path); p.add_argument("--trace-sha256"); p.add_argument("--plan", type=Path)
    p.add_argument("--profile"); p.add_argument("--run-directory", type=Path); a = p.parse_args()
    try:
        if a.kind == "prepare":
            if a.output is None: raise s.ContractError("output required")
            value = prepare(a.output, a.trace_sha256)
        else:
            if a.plan is None or a.run_directory is None: raise s.ContractError("saved plan and run directory required")
            value = assess(s.read_json(a.run_directory / "com-run.json"), s.read_json(a.run_directory / "report-lines.json"), s.read_json(a.plan), a.profile)
        print(json.dumps(value, indent=2, allow_nan=False)); return 0
    except (s.ContractError, OSError) as e:
        print(json.dumps({"status": "invalid", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
