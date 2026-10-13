"""P11: source-bound Recovery/EQ/reset POINT observations, without timing rules."""
import argparse
from collections import Counter, defaultdict
import html
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote
import pcie_protocol_appendix as dependency
import s01_contract as s


def analyze(records, constants, trace_sha):
    if (type(records) is not list or type(constants) is not dict or type(trace_sha) is not str
            or not re.fullmatch(r"[0-9a-fA-F]{64}", trace_sha)
            or any(type(k) is not str or type(v) is not int for k, v in constants.items())
            or any(k not in constants for k in ["LTSSM_STATE_RECOVERY", "LTSSM_STATE_HOT_RESET", "LTSSM_STATE_L0", "LINK_CONDITION_LINK_UP", "LINK_CONDITION_LINK_DOWN"])):
        raise s.ContractError("P11 requires typed input/verified named constants/trace identity")
    if (len({constants[k] for k in ["LTSSM_STATE_RECOVERY", "LTSSM_STATE_HOT_RESET", "LTSSM_STATE_L0"]}) != 3
            or constants["LINK_CONDITION_LINK_UP"] == constants["LINK_CONDITION_LINK_DOWN"]):
        raise s.ContractError("ambiguous native constants")
    names = {}
    for key, value in constants.items():
        if key.startswith("LTSSM_STATE_"): names.setdefault(value, key[len("LTSSM_STATE_"):])
    points = []; links = []; groups = defaultdict(list); last_index = -1
    for i, row in enumerate(records):
        if type(row) is not dict: raise s.ContractError("invalid source row")
        if row.get("kind") not in {"ltssm", "link_condition"}: continue
        index = row.get("packet_index"); channel = row.get("channel"); time = row.get("time_display")
        if (type(index) is not int or index < 0 or index < last_index or type(channel) is not str or not channel.strip()
                or type(time) is not str or not re.fullmatch(r"\d+(?:\.\d+)? sec", time)):
            raise s.ContractError("invalid packet order/channel/display time")
        last_index = index
        anchor = {"packet_ref": {"trace_sha256": trace_sha.lower(), "index": index, "channel_raw": channel},
                  "time_display": time, "source_pointer": "/" + str(i)}
        if row["kind"] == "link_condition":
            raw = row.get("type")
            if raw != "NA" and (type(raw) is not int or raw < 0): raise s.ContractError("invalid link condition encoding")
            label = "LINK_UP" if raw == constants["LINK_CONDITION_LINK_UP"] else "LINK_DOWN" if raw == constants["LINK_CONDITION_LINK_DOWN"] else "unknown"
            links.append(dict(anchor, raw_type=raw, name_from_constant=label, electrical_link_state="unknown")); continue
        fields = ["state", "substate", "subsubstate", "valid"]
        if any(type(row.get(k)) is not int or row[k] < 0 for k in fields) or row["valid"] not in {0, 1}:
            raise s.ContractError("invalid LTSSM raw vector/validity")
        point = dict(anchor, raw={k: row[k] for k in fields}, state_name_from_constant=names.get(row["state"], "unknown"),
                     substate_name_from_constant=names.get(row["substate"], "unknown"), validity="valid" if row["valid"] else "invalid",
                     duplicate_of=None, feature="unknown")
        points.append(point); groups[(index, channel)].append(len(points) - 1)
    for ids in groups.values():
        vectors = {(json.dumps(points[i]["raw"], sort_keys=True), points[i]["time_display"]) for i in ids}
        if len(vectors) > 1:
            for i in ids: points[i]["validity"] = "ambiguous"
        else:
            for i in ids[1:]: points[i]["duplicate_of"] = ids[0]
    eql_codes = {v for k, v in constants.items() if k.startswith("LTSSM_STATE_RECOVERY_RCVREQL")}
    for point in points:
        if point["validity"] != "valid" or point["duplicate_of"] is not None: continue
        raw = point["raw"]
        if raw["state"] == constants["LTSSM_STATE_RECOVERY"]:
            point["feature"] = "equalization_state" if raw["substate"] in eql_codes else "recovery_state"
        elif raw["state"] == constants["LTSSM_STATE_HOT_RESET"]: point["feature"] = "hot_reset_state"
        elif raw["state"] == constants["LTSSM_STATE_L0"]: point["feature"] = "l0_state"
    channels = sorted({point["packet_ref"]["channel_raw"] for point in points})
    transitions = []; previous = {}
    for i, point in enumerate(points):
        if point["duplicate_of"] is not None: continue
        channel = point["packet_ref"]["channel_raw"]
        if channel in previous:
            transitions.append({"channel_raw": channel, "from_point": previous[channel], "to_point": i,
                                "basis": "successive_saved_same_channel_samples", "continuous_state_interval": "unknown", "elapsed_time": "unknown"})
        previous[channel] = i
    counts = Counter(point["feature"] for point in points if point["duplicate_of"] is None)
    return {"schema": "pcie.recovery-observations/v1", "slice": "P11", "trace_sha256": trace_sha.lower(),
            "origin": "saved_native_state_vector_named_with_probed_constants", "points": points, "link_condition_points": links,
            "channels_observed": channels, "role_mapping": "unknown", "transitions": transitions,
            "observations": {feature: {"state": "observed" if counts[feature] else "unknown", "sample_count": counts[feature]}
                             for feature in ["recovery_state", "equalization_state", "hot_reset_state", "l0_state"]},
            "physical_reset": "unknown", "coverage": {"state_point_export": "change_only", "validity_change_retention": "unknown",
                "capture_start": "unknown", "capture_end": "unknown", "mode": "unknown", "epoch": "unknown", "perst_sideband": "unknown"},
            "entry_exit_qualification": "NOT_EVALUATED", "timing_rules": "NOT_EVALUATED", "qualification": "NOT_EVALUATED",
            "claim_boundary": "positive state-point observations only; no duration/absence/timeout/PHY/EQ electrical verdict"}


def saved_inputs(frozen_root, timeline, constants_run):
    root = Path(frozen_root).resolve(); directory = Path(constants_run).resolve()
    report, _ = dependency.frozen_renderer(root)
    doc = report.adapter.verified_timeline(Path(timeline), root)
    # This historical setup parser is tracked in the current checkout, not in
    # the W1-W5 delivery checkout. Load it in place, never copy it across.
    parser_root = Path(__file__).resolve().parents[1]
    parser_path = parser_root / "scripts/pcie/verify_b1b0_constants.py"
    parser_head = dependency.git(parser_root, "rev-parse", "HEAD").decode().strip()
    relative = parser_path.relative_to(parser_root).as_posix()
    if dependency.git(parser_root, "hash-object", "--path=" + relative, str(parser_path)).strip() != dependency.git(parser_root, "rev-parse", parser_head + ":" + relative).strip():
        raise s.ContractError("constant parser differs from its located commit")
    sys.path.insert(0, str(parser_path.parent))
    from verify_b1b0_constants import parse
    run = s.read_json(directory / "com-run.json")
    if (run["status"] != "COM_RUN_COMPLETE" or run["identities_unchanged"] is not True
            or run["steps"]["finish_event"]["result_name"] != "DONE" or run["steps"]["process_exit"]["ok"] is not True
            or run["pre"]["files"][0]["sha256"].lower() != doc["capture_sha256"].lower()):
        raise s.ContractError("constant probe is not qualified on the same source")
    script = Path(run["pre"]["script"]["path"])
    known_script = parser_root / "scripts/pcie/b1b0-constants.pevs"
    if script.resolve() != known_script.resolve() or dependency.digest(script) != run["pre"]["script"]["sha256"].lower():
        raise s.ContractError("constant script changed or is not the reviewed probe")
    script_relative = known_script.relative_to(parser_root).as_posix()
    if dependency.git(parser_root, "hash-object", "--path=" + script_relative, str(known_script)).strip() != dependency.git(parser_root, "rev-parse", parser_head + ":" + script_relative).strip():
        raise s.ContractError("constant probe differs from located commit")
    if (run["steps"].get("close", {}).get("ok") is not True
            or dependency.digest(directory / "vse-output.txt") != run["output"]["vse_output_sha256"].lower()):
        raise s.ContractError("constant output hash/close mismatch")
    constants = parse((directory / "vse-output.txt").read_text(encoding="utf-8-sig"))
    source = doc["sources"]["link_timeline"]; path = root / source["path"]
    if dependency.digest(path) != source["sha256"].lower(): raise s.ContractError("legacy timeline source hash mismatch")
    value = analyze(s.read_json(path), constants, doc["capture_sha256"])
    value["sources"] = {"state_points": {"path": str(path), "sha256": dependency.digest(path), "binding": source["binding"]},
                        "constant_run": {"path": str(directory / "com-run.json"), "sha256": dependency.digest(directory / "com-run.json")},
                        "constants": {"path": str(directory / "vse-output.txt"), "sha256": dependency.digest(directory / "vse-output.txt")}}
    value["parser_dependency"] = {"path": str(parser_path), "sha256": dependency.digest(parser_path), "checkout_head": parser_head}
    helper = Path(sys.modules["verify_g1a_log"].__file__).resolve()
    helper_root = parser_root if helper.is_relative_to(parser_root) else root
    helper_head = dependency.git(helper_root, "rev-parse", "HEAD").decode().strip()
    helper_relative = helper.relative_to(helper_root).as_posix()
    if dependency.git(helper_root, "hash-object", "--path=" + helper_relative, str(helper)).strip() != dependency.git(helper_root, "rev-parse", helper_head + ":" + helper_relative).strip():
        raise s.ContractError("constant parser helper differs from located commit")
    value["parser_helper_dependency"] = {"path": str(helper), "sha256": dependency.digest(helper), "checkout_head": helper_head}
    value["source_ids"] = ["LC-01:packet input LtssmState validity vector", "LC-16:LTSSM example"]
    value["limitations"] = ["saved change-only extractor did not compare validity bit when deduplicating states; validity-only transitions may be omitted",
                            "state labels use same installed native constants; source remains corroborated legacy, not a new capture",
                            "display time quantum is not hardware timer accuracy; no continuous intervals reconstructed",
                            "no PERST/sideband or physical reset evidence; original B1d four validation debts remain"]
    return value


def render(value, output):
    rec = value["observations"]["recovery_state"]["sample_count"] + value["observations"]["equalization_state"]["sample_count"]
    summary = (f"已觀測到 {rec} 個有效的 Recovery 狀態點；entry／exit、持續期間與 timeout 尚未驗證。"
               if rec else "Recovery 觀測結果未知；沒有適用的有效狀態點，覆蓋範圍尚未驗證。")
    parts = ['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>PCIe Recovery 觀測</title>',
             '<style>body{max-width:1100px;margin:32px auto;padding:16px;font:16px/1.6 system-ui;background:#f3f6fa;color:#182638}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ccd5df;text-align:left}code{overflow-wrap:anywhere}section{overflow:auto}</style><main><h1>PCIe Recovery 狀態觀測</h1>',
             '<p>' + summary + '</p>', '<p>沒有驗證缺席事件、電氣狀態或 root cause。Physical reset、PERST#、mode、epoch 與完整 coverage 皆未知。</p>',
             '<p>來源 SHA-256 <code>' + value["trace_sha256"] + '</code></p>', '<section><table><tr><th>Packet</th><th>channel</th><th>display time</th><th>state／substate</th><th>validity</th><th>來源</th></tr>']
    for point in value["points"]:
        source = value["sources"]["state_points"]; path = Path(source["path"])
        try: url = quote(Path(os.path.relpath(path, output)).as_posix(), safe="/")
        except ValueError: url = path.resolve().as_uri()
        url += "#" + quote(point["source_pointer"], safe="")
        parts.append('<tr><td>' + str(point["packet_ref"]["index"]) + '</td><td>' + html.escape(point["packet_ref"]["channel_raw"]) + '</td><td>' + html.escape(point["time_display"]) + '</td><td>' + html.escape(point["state_name_from_constant"] + ' / ' + point["substate_name_from_constant"]) + '</td><td>' + point["validity"] + '</td><td><a href="' + html.escape(url, quote=True) + '">原生來源</a></td></tr>')
    parts += ['</table></section><h2>限制</h2><ul>'] + ['<li>' + html.escape(text) + '</li>' for text in value["limitations"]]
    return "\n".join(parts + ['</ul></main></html>'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ["frozen-root", "timeline", "constants-run", "output"]: parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists(): raise s.ContractError("fresh output required")
        value = saved_inputs(args.frozen_root, args.timeline, args.constants_run)
        page = render(value, args.output)
        args.output.mkdir(parents=True)
        (args.output / "observations.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output / "report.html").write_text(page, encoding="utf-8")
        print(json.dumps({"status": "LOCAL_P11_STATE_POINTS_COMPLETE", "observations": value["observations"]})); return 0
    except (s.ContractError, ValueError, OSError, KeyError) as e:
        print(json.dumps({"status": "INVALID", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
