#!/usr/bin/env python3
"""U01 offline selection preparation and saved-result assessment. No COM imports."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import s01_contract as s01

# LC-04 PDF19/89/152/157/161/168/170. Names are resolved by installed VSE.
SELECTIONS = {
    "packet-default": ("_PKT", ["SendAllTraceEvents();"]),
    "packet-crc-off": ("_PKT", ["SendAllTraceEvents();", "SendPktsWithBadCRC(0);"]),
    "packet-crc-on": ("_PKT", ["SendAllTraceEvents();", "SendPktsWithBadCRC(1);"]),
    "transaction-all": ("_TRA", ["SendAllTraceEvents();"]),
    "transfer-default": ("_XFER", ["SendTransfer(_ANY, _ANY, _ANY);"]),
    "transfer-complete": ("_XFER", ["SendTransfer(_ANY, _ANY, _ANY, 1, 0);"]),
    "transfer-incomplete": ("_XFER", ["SendTransfer(_ANY, _ANY, _ANY, 0, 0);"]),
}
SOURCE_SECTIONS = ["PDF19: input context", "PDF89: in.Completed", "PDF152: SendLevelOnly",
                   "PDF157: SendAllChannels", "PDF161: SendAllTraceEvents",
                   "PDF168: SendTransfer", "PDF170: SendPktsWithBadCRC"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_script(selection, start, end):
    if selection not in SELECTIONS or type(start) is not int or type(end) is not int or not 0 <= start <= end <= 1_000_000_000:
        raise s01.ContractError("invalid named selection or inclusive level-local index window")
    level, calls = SELECTIONS[selection]
    # Use an explicit wire token: the installed CSL rejects unary -1 here.
    # The host decodes NOT_APPLICABLE to its internal -1 sentinel, never zero.
    completion = "in.Completed" if level == "_XFER" else '"NOT_APPLICABLE"'
    settings = "\n    ".join(calls)
    return f'''# U01 selection observation only. LC-04 PDF19/89/152/157/161/168/170.
# Index window is a post-dispatch level-local guard, NOT a native capture range.
set Visited = 0;
set Selected = 0;
set Emitted = 0;
set LevelMismatches = 0;
%include "VSTools.inc"
OnStartScript()
{{
    SendAllChannels();
    SendLevelOnly({level});
    {settings}
    ScriptForDisplayOnly();
}}
ProcessEvent()
{{
    Visited++;
    if (in.Level != {level}) LevelMismatches++;
    if (in.Index >= {start} && in.Index <= {end})
    {{
        Selected++;
        if (Emitted < 512)
        {{
            NotifyClient(2501, ["U01-ROW", in.Index, in.Level, in.Channel,
                in.Speed, in.TraceEvent, in.Time[0], in.Time[1], {completion}]);
            Emitted++;
        }}
    }}
    return Complete();
}}
OnFinishScript()
{{
    NotifyClient(2502, ["U01-END", Visited, Selected, Emitted, LevelMismatches, {level}]);
    return 0;
}}
'''


def prepare(output, trace_sha, trace_id, start=0, end=200):
    if type(trace_sha) is not str or re.fullmatch(r"[0-9A-Fa-f]{64}", trace_sha) is None:
        raise s01.ContractError("a declared trace SHA-256 is required")
    if type(trace_id) is not str or not trace_id.strip():
        raise s01.ContractError("a trace ID is required")
    # Validate before creating an output directory; never overwrite evidence.
    scripts = {k: render_script(k, start, end) for k in SELECTIONS}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for name, text in scripts.items():
        path = output / (name + ".vse")
        path.write_text(text, encoding="utf-8", newline="\n")
        rows.append({"id": name, "level": SELECTIONS[name][0], "script": path.name,
                     "script_sha256": sha256(path), "calls": SELECTIONS[name][1]})
    plan = {"schema_version": "u01.selection-plan/v3", "trace_id": trace_id,
            "trace_sha256": trace_sha.lower(), "protocol": "usb", "profiles": rows,
            "requested_range": {"namespace": "level_local_event_index", "start": start, "end": end},
            "range_application": "post_dispatch_guard", "max_exported_rows": 512,
            "source_sections": SOURCE_SECTIONS, "qualification": "NOT_EVALUATED"}
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def validate_plan(plan):
    expected_keys = {"schema_version", "trace_id", "trace_sha256", "protocol", "profiles", "requested_range",
                     "range_application", "max_exported_rows", "source_sections", "qualification"}
    if type(plan) is not dict or set(plan) != expected_keys:
        raise s01.ContractError("invalid plan shape")
    if (plan["schema_version"] != "u01.selection-plan/v3" or plan["protocol"] != "usb"
            or plan["qualification"] != "NOT_EVALUATED" or plan["range_application"] != "post_dispatch_guard"
            or type(plan["max_exported_rows"]) is not int or plan["max_exported_rows"] != 512
            or type(plan["trace_sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", plan["trace_sha256"])
            or type(plan["trace_id"]) is not str or not plan["trace_id"].strip()
            or plan["source_sections"] != SOURCE_SECTIONS):
        raise s01.ContractError("unsupported or altered plan semantics")
    window = plan["requested_range"]
    if type(window) is not dict or set(window) != {"namespace", "start", "end"} or window["namespace"] != "level_local_event_index":
        raise s01.ContractError("invalid index namespace")
    if type(plan["profiles"]) is not list or len(plan["profiles"]) != len(SELECTIONS):
        raise s01.ContractError("all seven named selections must be present")
    for row, name in zip(plan["profiles"], SELECTIONS):
        text = render_script(name, window["start"], window["end"])
        expected = {"id": name, "level": SELECTIONS[name][0], "script": name + ".vse",
                    "script_sha256": hashlib.sha256(text.encode()).hexdigest(), "calls": SELECTIONS[name][1]}
        if row != expected:
            raise s01.ContractError("named selection or script identity was altered")


def validate_result(result, plan, selection):
    """Validate a saved host payload. Success means transport consistency only."""
    validate_plan(plan)
    profile = next((p for p in plan["profiles"] if p["id"] == selection), None)
    if profile is None or type(result) is not dict:
        raise s01.ContractError("unknown selection or invalid result")
    required = {"selection", "trace_sha256", "script_sha256", "integrity", "run_result", "finished_result",
                "error", "rows", "summary", "software_version", "constants_sha256", "manual_sha256"}
    if set(result) != required:
        raise s01.ContractError("result must contain only the declared payload fields")
    if (result["selection"] != selection or result["trace_sha256"] != plan["trace_sha256"]
            or result["script_sha256"] != profile["script_sha256"]):
        raise s01.ContractError("result is bound to another trace, script or selection")
    for key in ["constants_sha256", "manual_sha256"]:
        if type(result[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", result[key]):
            raise s01.ContractError("missing installed source identity")
    if type(result["software_version"]) is not str or not result["software_version"].strip():
        raise s01.ContractError("missing installed software version")
    integrity = result["integrity"]
    if type(integrity) is not dict or set(integrity) != {"source_unchanged", "working_copy_unchanged", "working_copy_readonly"} or any(v is not True for v in integrity.values()):
        raise s01.ContractError("source/working-copy integrity gate failed")
    if (type(result["run_result"]) is not int or result["run_result"] != 2
            or type(result["finished_result"]) is not int or result["finished_result"] != 2 or result["error"] != ""):
        raise s01.ContractError("run/finished markers or host error gate failed")
    summary, rows = result["summary"], result["rows"]
    if type(summary) is not list or len(summary) != 5 or any(type(v) is not int or v < 0 for v in summary):
        raise s01.ContractError("one valid U01-END summary is required")
    visited, selected, emitted, mismatches, native_level = summary
    if (type(rows) is not list or mismatches != 0 or not visited >= selected >= emitted
            or emitted != min(selected, 512) or len(rows) != emitted):
        raise s01.ContractError("callback/sample denominator or level reconciliation failed")
    window = plan["requested_range"]
    for row in rows:
        if type(row) is not list or len(row) != 8 or any(type(v) is not int for v in row):
            raise s01.ContractError("invalid numeric callback row")
        index, level, channel, speed, event, sec, ns, completed = row
        if (not window["start"] <= index <= window["end"] or level != native_level
                or min(channel, speed, event, sec, ns) < 0 or ns >= 1_000_000_000
                or (profile["level"] != "_XFER" and completed != -1)
                or (profile["level"] == "_XFER" and completed not in (0, 1))):
            raise s01.ContractError("callback field, namespace, range or completion mismatch")
        if selection in {"transfer-complete", "transfer-incomplete"} and completed != (1 if selection == "transfer-complete" else 0):
            raise s01.ContractError("explicit completion selection disagrees with observed callback")
    return {"selection": selection, "transport": "consistent", "callback_count": visited,
            "window_callback_count": selected, "exported_row_count": emitted,
            "sample_truncated": selected > emitted, "native_level": native_level,
            "delivered_index_bounds": [min(r[0] for r in rows), max(r[0] for r in rows)] if rows else None,
            "effective_capture_range": "unknown", "bad_crc_coverage": "unknown",
            "incomplete_transfer_coverage": "unknown", "qualification": "NOT_EVALUATED"}


def manifest_from_result(result, plan, selection, locator, artifact_sha):
    assessment = validate_result(result, plan, selection)
    unknown = {"state": "unknown", "value": None, "evidence_refs": []}
    obs_ref = "U01-OUTPUT"
    facts = {k: dict(unknown) for k in ["mode", "bidirectional", "capture_start", "capture_end", "epoch", "filters"]}
    facts["filters"] = {"state": "known", "value": json.dumps({"selection": selection, "range": plan["requested_range"],
                              "range_application": "post_dispatch_guard"}, sort_keys=True), "evidence_refs": [obs_ref]}
    # A successfully reconciled empty sample does not establish event absence.
    count = assessment["window_callback_count"]
    bounds = assessment["delivered_index_bounds"]
    manifest = {"schema_version": "s01.input-manifest/v1", "manifest_id": "U01-" + plan["trace_id"] + "-" + selection,
        "origin": "recorded", "trace": {"trace_id": plan["trace_id"] + ":" + selection,
            "sha256": plan["trace_sha256"], "protocol": "usb", "identity_evidence_refs": [obs_ref], "facts": facts},
        "toolchain": {"software_version": result["software_version"], "extractor_sha256": result["script_sha256"],
                      "constants_sha256": result["constants_sha256"], "evidence_refs": [obs_ref]},
        "sources": [{"source_id": "LC-04", "revision": "Manual 9.12, July 2025, Suite 10.13+", "locator": "installed:USBProtocolSuiteVSEManual.pdf",
                     "review_depth": "sections_reviewed", "sections": SOURCE_SECTIONS, "applicability": "applicable", "evidence_refs": ["LC-04-DOC"]}],
        "evidence": [{"id": obs_ref, "kind": "saved_output", "locator": str(locator), "sha256": artifact_sha,
            "trace_sha256": plan["trace_sha256"], "note": "Reconciled protected-copy callback sample, not independently qualified coverage."},
            {"id": "LC-04-DOC", "kind": "document", "locator": "installed:USBProtocolSuiteVSEManual.pdf", "sha256": result["manual_sha256"], "note": "Selected installed manual sections only."}],
        "capabilities": [], "observations": [{"event": "usb.u01." + selection + ".callbacks",
            "state": "observed" if count > 0 else "unknown", "count": count,
            "coverage": {"selection": "included", "retention": "unknown", "extraction": "partial" if assessment["sample_truncated"] else "complete",
                         "start_index": bounds[0] if bounds else None, "end_index": bounds[1] if bounds else None}, "evidence_refs": [obs_ref]}],
        "historical_claims": [], "claim_boundary": "INPUT_METADATA_ONLY"}
    errors = s01.validate_manifest(manifest)
    if errors:
        raise s01.ContractError(json.dumps(errors))
    return manifest


def compare_results(results, plan):
    """Compare like-level callback samples, without interpreting CRC/root cause."""
    if type(results) is not dict or set(results) != set(SELECTIONS):
        raise s01.ContractError("a complete set of seven saved selections is required")
    assessments = {name: validate_result(results[name], plan, name) for name in SELECTIONS}
    identities = {(r["software_version"], r["constants_sha256"], r["manual_sha256"]) for r in results.values()}
    if len(identities) != 1:
        raise s01.ContractError("installed source identities changed between selections")
    comparisons = []
    for left, right in [("packet-default", "packet-crc-off"), ("packet-crc-off", "packet-crc-on"),
                        ("transfer-default", "transfer-complete"), ("transfer-complete", "transfer-incomplete")]:
        a, b = results[left], results[right]
        if a["summary"][-1] != b["summary"][-1]:
            raise s01.ContractError("like-level comparison has different native index namespaces")
        comparisons.append({"left": left, "right": right,
            "window_callback_count_delta": b["summary"][1] - a["summary"][1],
            "exported_samples_equal": a["rows"] == b["rows"],
            "interpretation": "callback comparison only; neither equality nor difference establishes event-class coverage"})
    return {"schema_version": "u01.selection-comparison/v1", "trace_sha256": plan["trace_sha256"],
            "assessments": list(assessments.values()), "comparisons": comparisons,
            "engineer_observation": "Selection settings and callback/sample denominators are explicit; bad-CRC and incomplete coverage still need independent known examples.",
            "qualification": "NOT_EVALUATED"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="kind", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--trace-sha256", required=True)
    prep.add_argument("--trace-id", required=True)
    prep.add_argument("--start", type=int, default=0)
    prep.add_argument("--end", type=int, default=200)
    assess = sub.add_parser("assess")
    assess.add_argument("--plan", type=Path, required=True)
    assess.add_argument("--result", type=Path, required=True)
    assess.add_argument("--selection", required=True)
    check = sub.add_parser("check-plan")
    check.add_argument("--plan", type=Path, required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--plan", type=Path, required=True)
    compare.add_argument("--results-directory", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.kind == "prepare":
            value = prepare(args.output, args.trace_sha256, args.trace_id, args.start, args.end)
        elif args.kind == "check-plan":
            validate_plan(s01.read_json(args.plan))
            value = {"status": "valid", "qualification": "NOT_EVALUATED"}
        elif args.kind == "compare":
            plan = s01.read_json(args.plan)
            results = {name: s01.read_json(args.results_directory / name / "result.json") for name in SELECTIONS}
            value = compare_results(results, plan)
        else:
            plan, result = s01.read_json(args.plan), s01.read_json(args.result)
            value = {"assessment": validate_result(result, plan, args.selection),
                     "manifest": manifest_from_result(result, plan, args.selection, str(args.result), sha256(args.result))}
        print(json.dumps(value, indent=2, allow_nan=False))
        return 0
    except (s01.ContractError, OSError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc), "qualification": "NOT_EVALUATED"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
