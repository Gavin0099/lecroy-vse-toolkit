#!/usr/bin/env python3
"""P01 PCIe-only selection plan and saved report reconciliation."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import s01_contract as s

PROFILES={"packet-all":("_PACKET",None),"packet-empty-window":("_PACKET",None),
          "packet-tlp":("_PACKET","_PKT_TLP"),"packet-dllp":("_PACKET","_PKT_DLLP"),
          "link-all":("_LINK",None),"split-all":("_SPLIT",None)}


def script(profile):
    if profile not in PROFILES:raise s.ContractError("unknown PCIe selection")
    level,event=PROFILES[profile]
    start,end=(1_000_000_000,1_000_000_001) if profile=="packet-empty-window" else (0,200)
    selection=f"SendTraceEventOnly({event});" if event else "SendAllTraceEvents();"
    return f'''# P01: LC-01 input context / selection, LC-13/14/15 named constants.
set ModuleType = "Verification Script";
set OutputType = "VS";
set InputType = "VS";
set DecoderDesc = "P01 bounded PCIe selection observation";
set Visited = 0;
set Selected = 0;
set Emitted = 0;
set Mismatches = 0;
%include "VSTools.inc"
OnStartScript()
{{
    ScriptForDisplayOnly();
    EnableOutput();
    SendAllChannels();
    SendLevelOnly({level});
    {selection}
}}
ProcessEvent()
{{
    Visited++;
    if (in.Level != {level}) Mismatches++;
    if (in.Index >= {start} && in.Index <= {end})
    {{
        Selected++;
        if (Emitted < 256)
        {{
            ReportText(FormatEx("{{\\"kind\\":\\"p01-row\\",\\"index\\":%d,\\"level\\":%d,\\"channel\\":%d,\\"event_raw\\":%d,\\"time2\\":[%d,%d,%d]}}",
                in.Index,in.Level,in.Channel,in.TraceEvent,in.Time2[0],in.Time2[1],in.Time2[2]));
            Emitted++;
        }}
    }}
    return Complete();
}}
OnFinishScript()
{{
    ReportText(FormatEx("{{\\"kind\\":\\"p01-end\\",\\"visited\\":%d,\\"selected\\":%d,\\"emitted\\":%d,\\"mismatches\\":%d,\\"native_level\\":%d}}",
        Visited,Selected,Emitted,Mismatches,{level}));
}}
'''


def prepare(output, trace_sha):
    if type(trace_sha) is not str or not re.fullmatch(r"[0-9a-f]{64}",trace_sha):raise s.ContractError("trace identity required")
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    profiles=[]
    for name,(level,event) in PROFILES.items():
        text=script(name);path=out/(name+".pevs");path.write_text(text,encoding="utf-8",newline="\n")
        profiles.append({"id":name,"level":level,"event":event,"script":path.name,"sha256":hashlib.sha256(text.encode()).hexdigest(),
                         "requested_index_window":[1_000_000_000,1_000_000_001] if name=="packet-empty-window" else [0,200]})
    plan={"schema_version":"pcie.selection-plan/v1","trace_sha256":trace_sha,"profiles":profiles,
          "range_application":"post_dispatch_level_local_guard","qualification":"NOT_EVALUATED"}
    (out/"plan.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
    return plan


def validate_plan(plan):
    if (type(plan) is not dict or set(plan)!={"schema_version","trace_sha256","profiles","range_application","qualification"}
            or plan["schema_version"]!="pcie.selection-plan/v1" or plan["range_application"]!="post_dispatch_level_local_guard"
            or plan["qualification"]!="NOT_EVALUATED" or type(plan["trace_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}",plan["trace_sha256"])
            or type(plan["profiles"]) is not list or len(plan["profiles"])!=len(PROFILES)):
        raise s.ContractError("unsupported PCIe plan")
    for row,(name,(level,event)) in zip(plan["profiles"],PROFILES.items()):
        expected={"id":name,"level":level,"event":event,"script":name+".pevs","sha256":hashlib.sha256(script(name).encode()).hexdigest(),
                  "requested_index_window":[1_000_000_000,1_000_000_001] if name=="packet-empty-window" else [0,200]}
        if row!=expected:raise s.ContractError("PCIe profile/namespace/script binding mismatch")


def assess(run, lines, profile):
    if run.get("status")!="COM_RUN_COMPLETE" or run.get("identities_unchanged") is not True or run.get("steps",{}).get("finish_event",{}).get("result_name")!="DONE":
        raise s.ContractError("PCIe transport/completion/integrity failed")
    if type(lines) is not list or any(type(x) is not str for x in lines):raise s.ContractError("invalid report lines")
    rows=[];ends=[]
    for line in lines:
        if line.strip().startswith('{"kind":"p01-'):
            try:record=json.loads(line.strip(),object_pairs_hook=s._pairs,parse_constant=s._bad_constant)
            except ValueError as e:raise s.ContractError("bad PCIe report JSON") from e
            if record.get("kind")=="p01-row":rows.append(record)
            elif record.get("kind")=="p01-end":ends.append(record)
            else:raise s.ContractError("unknown PCIe marker")
    if len(ends)!=1:raise s.ContractError("one end marker required")
    end=ends[0]
    if set(end)!={"kind","visited","selected","emitted","mismatches","native_level"} or any(type(end[k]) is not int or end[k]<0 for k in end if k!="kind"):
        raise s.ContractError("invalid end counters")
    if not end["visited"]>=end["selected"]>=end["emitted"] or end["emitted"]!=min(end["selected"],256) or end["emitted"]!=len(rows) or end["mismatches"]:
        raise s.ContractError("PCIe row/level denominator mismatch")
    start,stop=profile["requested_index_window"]
    for r in rows:
        if (set(r)!={"kind","index","level","channel","event_raw","time2"}
                or any(type(r[k]) is not int or r[k]<0 for k in ["index","level","channel","event_raw"])
                or r["level"]!=end["native_level"] or not start<=r["index"]<=stop
                or type(r["time2"]) is not list or len(r["time2"])!=3 or any(type(x) is not int or x<0 for x in r["time2"])
                or r["time2"][1]>=1_000_000_000 or r["time2"][2]>=1000):raise s.ContractError("invalid PCIe context/range/time components")
    return {"schema_version":"pcie.selection-observation/v1","profile":profile["id"],"counts":end,"rows":rows,
            "empty_observation":"unknown" if not rows else None,"sample_truncated":end["selected"]>end["emitted"],
            "index_namespace":profile["level"],"effective_native_range":"unknown","display_filters":"unknown",
            "measurement_resolution":"unknown","qualification":"NOT_EVALUATED"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind",choices=["prepare","assess"]);p.add_argument("--output",type=Path);p.add_argument("--trace-sha256")
    p.add_argument("--plan",type=Path);p.add_argument("--profile");p.add_argument("--run-directory",type=Path)
    a=p.parse_args()
    try:
        if a.kind=="prepare":
            if a.output is None:raise s.ContractError("output required")
            value=prepare(a.output,a.trace_sha256)
        else:
            if a.plan is None or a.run_directory is None:raise s.ContractError("saved plan/run required")
            plan=s.read_json(a.plan);validate_plan(plan);profile=next((r for r in plan["profiles"] if r["id"]==a.profile),None)
            if profile is None:raise s.ContractError("profile not present")
            run=s.read_json(a.run_directory/"com-run.json")
            pre=run.get("pre",{})
            if pre.get("script",{}).get("sha256","").lower()!=profile["sha256"] or not pre.get("files") or pre["files"][0].get("sha256","").lower()!=plan["trace_sha256"]:
                raise s.ContractError("saved run bound to a different source/script")
            value=assess(run,s.read_json(a.run_directory/"report-lines.json"),profile)
        print(json.dumps(value,indent=2,allow_nan=False));return 0
    except (s.ContractError,OSError) as e:print(json.dumps({"status":"invalid","error":str(e)}));return 2


if __name__=="__main__":raise SystemExit(main())
