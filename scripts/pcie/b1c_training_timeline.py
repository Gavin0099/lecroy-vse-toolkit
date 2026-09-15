#!/usr/bin/env python3
"""PCIe-B1c: condense a verified B1b window timeline into a readable link training flow.

Offline and descriptive only. Consecutive segments with the same LTSSM main state become one
phase (sub-states listed in order); consecutive link-condition-only segments become one phase;
a display-time jump of at least --gap-seconds between neighbouring segments becomes an explicit
"no observed events" phase. Unknowns carried from B1a/B1b are always printed. No link rule, no
MUX reading, no health claim; a contract check rejects judgement wording before writing.

B1c-r1 (optional evidence inputs): every phase lists the last LTSSM state of each channel when it
starts, so a channel that keeps its state across a phase started by the other channel stays
visible; `HasErrors` gets a channel only when the B1c-x2 probe shows every flagged event of the
enclosing range on one channel; PETracer GUI observations are attached to their phase strictly as
samples. Per-phase error subtypes stay UNKNOWN.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

PKT_COUNTS = ("tlp", "dllp_ack", "dllp_nak", "dllp_fc", "dllp_pm", "dllp_other",
              "os_ts1", "os_ts2", "os_eios", "os_eieos", "os_skip", "os_other")
ERR_SUBFLAGS = ("disparity", "symbol", "wrong_symbol", "delimiter", "end_bad", "alignment", "idle",
                "ts_data_rate", "ts_format", "ts_parity", "ts_reserved", "tlp_bad_lcrc", "dllp_bad_crc")
COUNT_LABELS = {"tlp": "TLP", "dllp_ack": "ACK DLLP", "dllp_nak": "NAK DLLP", "dllp_fc": "FC DLLP", "dllp_pm": "PM DLLP",
                "dllp_other": "other DLLP", "os_ts1": "TS1", "os_ts2": "TS2", "os_eios": "EIOS", "os_eieos": "EIEOS",
                "os_skip": "SKIP", "os_other": "other ordered set"}
STATE_LABELS = {"DETECT": "Detect", "POLLING": "Polling", "CONFIG": "Configuration", "L0": "L0", "RECOVERY": "Recovery",
                "HOT_RESET": "Hot Reset", "DISABLED": "Disabled", "LOOP_BACK": "Loopback", "L0S": "L0s", "L1": "L1", "L2": "L2",
                "UNDEFINED": "LTSSM undefined"}
TLP_TYPE_NAMES = {1: "MRd(32)", 3: "MWr(32)", 4: "MRd(64)", 6: "MWr(64)", 9: "CfgRd0", 10: "CfgWr0", 11: "CfgRd1",
                  12: "CfgWr1", 13: "Msg", 14: "MsgD", 17: "Cpl", 18: "CplD"}
UNKNOWNS = [
    "`HasErrors` 有計數，但 B1b 讀取的 13 個子旗標全部為 0，error subtype 為 `UNKNOWN`。",
    "各階段的 TS1、TS2、DLLP 等計數沒有按方向拆開；方向只來自階段起點的 LTSSM 或 link condition 紀錄，未逐事件證明。",
    "`LINK_UP` / `LINK_DOWN` 使用 VSE 常數名稱，文字意義尚未在 PETracer GUI 核對。",
    "speed code 的 GT/s 標示來自 VSE 手冊文字，未經 probe 驗證。",
]
UNKNOWNS_R1 = [
    "`HasErrors` 在 GUI 抽樣中對應 analyzer 的 Training Sequence Error，但只看了 3 筆；各階段 `HasErrors` 的子類型分布為 `UNKNOWN`。",
    "單一階段內的 TS1、TS2、DLLP 等計數沒有按方向拆開；方向拆分只到 B1c-x2 的 R1、R2、R3 範圍層級。",
    "speed code 的 GT/s 標示來自 VSE 手冊文字，未經 probe 驗證。",
    "B1c-x2 樣本沒有出現 `_CHANNEL_1` 的名稱，範圍統計以 channel id 列出。",
]
FORBIDDEN = ("異常", "失敗", "錯誤原因", "root cause", "根本原因", "abnormal", "failure", "fail", "mux", "bsod", "導致", "造成", "正常", "嚴重")
SAMPLE_MARK = "僅代表此 sample"
SPEED_MANUAL = {0: "2.5 GT/s", 1: "5.0 GT/s", 2: "8.0 GT/s", 3: "16.0 GT/s", 4: "32.0 GT/s"}
TIME_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*sec\s*$")
DATA_CHANNELS = ("Downstream", "Upstream")


class B1cError(ValueError):
    """Input timeline is unusable or the output contract failed."""


def seconds(display: str) -> Decimal:
    match = TIME_RE.fullmatch(display)
    if not match:
        raise B1cError(f"Unrecognized time display {display!r}")
    return Decimal(match.group(1))


def main_state(record: dict[str, Any]) -> str:
    name = record.get("state_name") or "UNDEFINED"
    return name.split(".")[0] or "UNDEFINED"


def sub_state(record: dict[str, Any]) -> str | None:
    parts = (record.get("state_name") or "").split(".")
    if len(parts) < 2:
        return None
    return re.sub(r"^(RECOVERY_|CFG_|POLLING_|LOOP_BACK_)", "", parts[1])


def segments_with_records(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for row in timeline:
        if row["kind"] == "segment":
            segments.append({"seg": row, "start": [], "inner": []})
            continue
        if not segments:
            raise B1cError(f"Record at packet {row['packet_index']} precedes the first segment")
        current = segments[-1]
        if not current["seg"]["first_index"] <= row["packet_index"] <= current["seg"]["last_index"]:
            raise B1cError(f"Record at packet {row['packet_index']} lies outside segment {current['seg']['seg']}")
        target = "start" if row["packet_index"] == current["seg"]["first_index"] and row["kind"] in ("ltssm", "link_condition") else "inner"
        current[target].append(row)
    if not segments:
        raise B1cError("Timeline has no segments")
    return segments


def phase_key(segment: dict[str, Any]) -> str:
    ltssm = [r for r in segment["start"] if r["kind"] == "ltssm"]
    if ltssm:
        return main_state(ltssm[0])
    if any(r["kind"] == "link_condition" for r in segment["start"]):
        return "LINK_CONDITION"
    return "UNMARKED"


def new_phase(key: str, seg: dict[str, Any], carried: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"kind": key, "first_index": seg["first_index"], "first_time": seg["first_time"], "last_index": seg["last_index"],
            "last_time": seg["last_time"], "segments": [], "events": 0, "counts": {k: 0 for k in PKT_COUNTS},
            "err_any": 0, "err_subflags": {k: 0 for k in ERR_SUBFLAGS}, "steps": [], "inner_records": [],
            "ltssm_at_start": copy.deepcopy(carried)}


def channel_ranges(x2: dict[str, Any]) -> dict[str, tuple[int, int]]:
    head = x2["header"]
    return {"R1": (head["start"], head["r1_end"]), "R2": (head["r1_end"] + 1, head["r2_end"]), "R3": (head["r2_end"] + 1, head["end"])}


def channel_label(x2: dict[str, Any], cid: int) -> str:
    return x2.get("channel_names", {}).get(f"C{cid}") or {1: "_CHANNEL_1", 2: "_CHANNEL_2", 3: "other channel"}[cid]


def build(timeline: list[dict[str, Any]], gap_seconds: Decimal, x2: dict[str, Any] | None = None,
          gui: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    phases: list[dict[str, Any]] = []
    previous = None
    last_state: dict[str, dict[str, Any]] = {}
    for item in segments_with_records(timeline):
        seg = item["seg"]
        key = phase_key(item)
        gap = None
        if previous is not None:
            delta = seconds(seg["first_time"]) - seconds(previous["last_time"])
            if delta >= gap_seconds:
                gap = {"kind": "NO_OBSERVED_EVENTS", "after_index": previous["last_index"], "after_time": previous["last_time"],
                       "before_index": seg["first_index"], "before_time": seg["first_time"], "duration_seconds": str(delta)}
                phases.append(gap)
        if gap is None and phases and phases[-1]["kind"] == key:
            phase = phases[-1]
        else:
            phase = new_phase(key, seg, last_state)
            phases.append(phase)
        phase["segments"].append(seg["seg"])
        phase["last_index"], phase["last_time"] = seg["last_index"], seg["last_time"]
        phase["events"] += seg["events"]
        for k in PKT_COUNTS:
            phase["counts"][k] += seg[k]
        phase["err_any"] += seg["err_any"]
        for k in ERR_SUBFLAGS:
            phase["err_subflags"][k] += seg[k]
        for record in item["start"]:
            step = {"kind": record["kind"], "packet_index": record["packet_index"], "time_display": record["time_display"], "channel": record["channel"]}
            if record["kind"] == "ltssm":
                step.update(state=main_state(record), substate=sub_state(record), state_valid=record["valid"])
                last_state[record["channel"]] = {"state": step["state"], "substate": step["substate"], "state_valid": step["state_valid"],
                                                 "packet_index": record["packet_index"]}
            else:
                step.update(type_name=record.get("type_name") or f"type {record['type']}")
            phase["steps"].append(step)
        phase["inner_records"].extend(item["inner"])
        previous = seg
    for phase in phases:
        if phase["kind"] == "NO_OBSERVED_EVENTS":
            continue
        flagged = [k for k, v in phase["err_subflags"].items() if v]
        phase["error_subtype"] = None if phase["err_any"] == 0 else (flagged if flagged else "UNKNOWN")
        phase["channels"] = sorted({s["channel"] for s in phase["steps"]})
        phase["has_errors_channel"] = None
        phase["gui_samples"] = []
    if x2 is not None:
        attach_channel_evidence(phases, x2)
    if gui is not None:
        for sample in gui.get("ts1_error_samples", []):
            homes = [p for p in phases if p["kind"] != "NO_OBSERVED_EVENTS" and p["first_index"] <= sample["packet_index"] <= p["last_index"]]
            if len(homes) != 1:
                raise B1cError(f"GUI sample packet {sample['packet_index']} does not fall in exactly one phase")
            homes[0]["gui_samples"].append(sample)
    return phases


def attach_channel_evidence(phases: list[dict[str, Any]], x2: dict[str, Any]) -> None:
    ranges = channel_ranges(x2)
    for name, (low, high) in ranges.items():
        inside = [p for p in phases if p["kind"] != "NO_OBSERVED_EVENTS" and low <= p["first_index"] and p["last_index"] <= high]
        straddle = [p for p in phases if p["kind"] != "NO_OBSERVED_EVENTS" and p not in inside and p["first_index"] <= high and p["last_index"] >= low]
        if straddle:
            continue
        range_errors = x2["scopes"][name]["has_errors"]
        if sum(p["err_any"] for p in inside) != range_errors:
            raise B1cError(f"Phase HasErrors inside {name} sum to {sum(p['err_any'] for p in inside)}, B1c-x2 reports {range_errors}")
        by_channel = {cid: x2["cells"][f"{name}C{cid}"]["has_errors"] for cid in (1, 2, 3)}
        carriers = [cid for cid, count in by_channel.items() if count]
        if len(carriers) != 1:
            continue
        label = channel_label(x2, carriers[0])
        for phase in inside:
            if phase["err_any"]:
                phase["has_errors_channel"] = {"channel": label, "range": name, "range_first": low, "range_last": high, "range_has_errors": range_errors}


def fmt(n: int) -> str:
    return f"{n:,}"


def phase_title(phase: dict[str, Any]) -> str:
    if phase["kind"] == "NO_OBSERVED_EVENTS":
        return "沒有觀察到事件"
    if phase["kind"] == "LINK_CONDITION":
        return "link condition 變化"
    return STATE_LABELS.get(phase["kind"], phase["kind"])


def state_text(entry: dict[str, Any]) -> str:
    sub = f".{entry['substate']}" if entry.get("substate") else ""
    valid = "" if entry.get("state_valid", 1) else "，state not valid"
    return f"{STATE_LABELS.get(entry['state'], entry['state'])}{sub}（Packet {entry['packet_index']}{valid}）"


def flow_line(phases: list[dict[str, Any]], r1: bool = False) -> str:
    parts = []
    for phase in phases:
        if phase["kind"] == "NO_OBSERVED_EVENTS":
            parts.append(f"沒有觀察到事件（{phase['duration_seconds']} sec）")
            continue
        label = f"link condition ×{len(phase['steps'])}" if phase["kind"] == "LINK_CONDITION" else phase_title(phase)
        if not r1:
            parts.append(label if phase["kind"] == "LINK_CONDITION" else f"{label}（{'、'.join(phase['channels'])}）")
            continue
        notes = [f"起點 {'、'.join(phase['channels'])}"]
        carrier = (phase.get("has_errors_channel") or {}).get("channel")
        if carrier and carrier not in phase["channels"]:
            carried = phase["ltssm_at_start"].get(carrier)
            notes.append(f"HasErrors 在 {carrier}" + (f"，{carrier} 仍為 {STATE_LABELS.get(carried['state'], carried['state'])}" if carried else ""))
        parts.append(f"{label}（{'；'.join(notes)}）")
    return " → ".join(parts)


def render_markdown(phases: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    r1 = bool(meta.get("r1"))
    lines = ["# PCIe Link Training 流程（B1c" + ("-r1" if r1 else "") + "）", "",
             f"來源 `timeline.json` SHA-256 `{meta['timeline_sha256']}`，packet 範圍 {meta['window']['start']} 至 {meta['window']['end']}。"
             f"本文件只整理 B1b 擷取到的事件，沒有套用任何 link 判斷規則。", "",
             f"相鄰 segment 的顯示時間相差 {meta['gap_seconds']} sec 以上時，列為「沒有觀察到事件」。這是呈現用的門檻，不是 PCIe 規則；時間解析度是 PETracer 顯示值。", ""]
    if r1:
        lines += [f"方向與 GUI 抽樣來自 B1c-x2 `haserrors.json` SHA-256 `{meta['x2_sha256']}` 與 GUI 觀察 `gui-observations.json` SHA-256 `{meta['gui_sha256']}`。"
                  "每個階段列出進入時各方向最後一筆 LTSSM 紀錄；`HasErrors` 的方向只在所屬範圍內全部落在同一方向時標示。", ""]
    lines += ["## 流程總覽", "", flow_line(phases, r1), ""]
    if r1:
        lines += ["## 已核對", ""] + [f"- Packet {e['packet_index']} 在 PETracer GUI 顯示 Link Event「{e['gui_text']}」，與 `{e['vse_constant']}` 一致（B1c-x1）。"
                                      for e in meta["link_events"]] + [""]
        lines += ["## 範圍層級方向統計（B1c-x2）", "", "| 範圍 | Packet | Channel | 事件 | TS1 | `HasErrors` |", "| --- | --- | --- | --- | --- | --- |"]
        for name, (low, high) in meta["ranges"].items():
            for cid in (1, 2, 3):
                cell = meta["cells"][f"{name}C{cid}"]
                if cell["events"]:
                    lines.append(f"| {name} | {low} 至 {high} | {meta['channel_labels'][cid]} | {fmt(cell['events'])} | {fmt(cell['ts1'])} | {fmt(cell['has_errors'])} |")
        lines.append("")
    lines += ["## 尚未確認", ""] + [f"- {u}" for u in (UNKNOWNS_R1 if r1 else UNKNOWNS)] + [""]
    for number, phase in enumerate(phases, start=1):
        lines += [f"## 階段 {number}：{phase_title(phase)}", ""]
        if phase["kind"] == "NO_OBSERVED_EVENTS":
            lines += [f"- 從 {phase['after_time']}（Packet {phase['after_index']}）到 {phase['before_time']}（Packet {phase['before_index']}），相差 {phase['duration_seconds']} sec。",
                      "- 範圍內沒有 TLP、DLLP、ordered set、link condition 或 EIE 事件送達 script；EIE 在整份 trace 都沒有送達，electrical idle 無法用這個方式觀察。", ""]
            continue
        lines.append(f"- 範圍：Packet {phase['first_index']} 至 {phase['last_index']}，{phase['first_time']} 至 {phase['last_time']}，segment {phase['segments'][0]} 至 {phase['segments'][-1]}。")
        if r1:
            carried = [f"{ch} {state_text(phase['ltssm_at_start'][ch])}" for ch in DATA_CHANNELS if ch in phase["ltssm_at_start"]]
            lines.append("- 進入此階段時各方向最後 LTSSM：" + ("、".join(carried) if carried else "尚無紀錄"))
        for step in phase["steps"]:
            if step["kind"] == "ltssm":
                sub = f".{step['substate']}" if step["substate"] else ""
                valid = "" if step["state_valid"] else "（analyzer 標示 state not valid）"
                lines.append(f"- LTSSM {STATE_LABELS.get(step['state'], step['state'])}{sub}，{step['channel']}，Packet {step['packet_index']}，{step['time_display']}{valid}")
            else:
                lines.append(f"- link condition `{step['type_name']}`，{step['channel']}，Packet {step['packet_index']}，{step['time_display']}")
        counts = "、".join(f"{COUNT_LABELS[k]} {fmt(v)}" for k, v in phase["counts"].items() if v)
        lines.append(f"- 事件 {fmt(phase['events'])}" + (f"：{counts}" if counts else ""))
        if phase["err_any"]:
            subtype = "`UNKNOWN`" if phase["error_subtype"] == "UNKNOWN" else "、".join(f"{k} {fmt(phase['err_subflags'][k])}" for k in phase["error_subtype"])
            line = f"- `HasErrors` {fmt(phase['err_any'])}，error subtype：{subtype}"
            carrier = phase.get("has_errors_channel")
            if carrier:
                line += (f"；方向 {carrier['channel']}（依據 B1c-x2 {carrier['range']}：Packet {carrier['range_first']} 至 {carrier['range_last']} 的 "
                         f"{fmt(carrier['range_has_errors'])} 筆 `HasErrors` 全部在 {carrier['channel']}）")
            lines.append(line)
        else:
            lines.append("- `HasErrors` 0")
        for sample in phase.get("gui_samples", []):
            labels = "、".join(f"`{label}`" for label in sample["gui_error_labels"])
            lines.append(f"- GUI 抽樣 Packet {sample['packet_index']}（{sample['direction_arrow']}，{sample['speed']} GT/s {sample['width']}）顯示 Training Sequence Error {labels}，{SAMPLE_MARK}。")
        for record in phase["inner_records"]:
            if record["kind"] == "tlp":
                lines.append(f"- TLP `{TLP_TYPE_NAMES.get(record['tlp_type'], 'type ' + str(record['tlp_type']))}`，{record['channel']}，Packet {record['packet_index']}")
            elif record["kind"] == "nak":
                lines.append(f"- NAK DLLP seq {record['seq']}，{record['channel']}，Packet {record['packet_index']}")
            elif record["kind"] == "speed_width":
                label = SPEED_MANUAL.get(record["speed"], "未列於手冊")
                lines.append(f"- speed code {record['speed']}（手冊標示 {label}），width x{record['width']}，{record['channel']}，Packet {record['packet_index']}")
        lines.append("")
    return "\n".join(lines)


def contract_check(markdown: str, phases: list[dict[str, Any]], r1: bool = False) -> list[str]:
    errors = []
    lowered = markdown.lower()
    for word in FORBIDDEN:
        if word in lowered:
            errors.append(f"judgement wording present: {word}")
    for unknown in (UNKNOWNS_R1 if r1 else UNKNOWNS):
        if unknown not in markdown:
            errors.append("an unknown from B1a/B1b is missing")
    headings = re.findall(r"^## 階段 (\d+)：", markdown, flags=re.MULTILINE)
    if [int(h) for h in headings] != list(range(1, len(phases) + 1)):
        errors.append("phase headings do not match the phases")
    sections = re.split(r"^## 階段 \d+：", markdown, flags=re.MULTILINE)[1:]
    for phase, body in zip(phases, sections):
        if phase.get("error_subtype") == "UNKNOWN" and "`UNKNOWN`" not in body:
            errors.append(f"phase starting at packet {phase['first_index']} hides the UNKNOWN error subtype")
        if phase.get("has_errors_channel") and "依據 B1c-x2" not in body:
            errors.append(f"phase starting at packet {phase['first_index']} states a HasErrors channel without its basis")
    for line in markdown.splitlines():
        if re.search(r"`TS[A-Za-z]+Err`", line) and SAMPLE_MARK not in line:
            errors.append("a GUI error label appears without the sample-only mark")
    if "—" in markdown or "–" in markdown:
        errors.append("dash character present")
    return errors


def load_x2(haserrors_path: Path, summary_path: Path, b1b_summary: dict[str, Any]) -> tuple[dict[str, Any], str]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS_HASERRORS_PROBE_OUTPUT" or summary.get("b1b_totals_crosscheck") != "MATCHED":
        raise B1cError("B1c-x2 summary is not a PASS matched against B1b")
    raw = haserrors_path.read_bytes()
    x2 = json.loads(raw.decode("utf-8"))
    head = x2["header"]
    if (head["start"], head["end"]) != (b1b_summary["window"]["start"], b1b_summary["window"]["end"]):
        raise B1cError("B1c-x2 window differs from the B1b window")
    return x2, hashlib.sha256(raw).hexdigest().upper()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True, help="B1b export timeline.json")
    parser.add_argument("--summary", type=Path, required=True, help="B1b export summary.json (must be PASS_WINDOW_EXPORT)")
    parser.add_argument("--gap-seconds", default="0.1", help="Display-time jump shown as a no-observed-events phase")
    parser.add_argument("--x2-haserrors", type=Path, help="B1c-r1: B1c-x2 export haserrors.json")
    parser.add_argument("--x2-summary", type=Path, help="B1c-r1: B1c-x2 export summary.json")
    parser.add_argument("--gui-observations", type=Path, help="B1c-r1: gui-observations.json from the x1/x3 session")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1cError(f"Refusing to reuse existing output directory: {args.output_dir}")
        raw = args.timeline.read_bytes()
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
        if summary.get("status") != "PASS_WINDOW_EXPORT":
            raise B1cError("B1b summary is not PASS_WINDOW_EXPORT")
        timeline_sha = hashlib.sha256(raw).hexdigest().upper()
        if summary.get("timeline_json_sha256") != timeline_sha:
            raise B1cError("B1b summary does not describe this timeline.json")
        if not summary.get("named_with_constants"):
            raise B1cError("B1b timeline was not named with the probed constants")
        r1_inputs = (args.x2_haserrors, args.x2_summary, args.gui_observations)
        if any(r1_inputs) and not all(r1_inputs):
            raise B1cError("B1c-r1 needs --x2-haserrors, --x2-summary and --gui-observations together")
        r1 = all(r1_inputs)
        gap = Decimal(args.gap_seconds)
        meta: dict[str, Any] = {"timeline_sha256": timeline_sha, "window": summary["window"], "gap_seconds": str(gap), "r1": r1}
        x2 = gui = None
        if r1:
            x2, meta["x2_sha256"] = load_x2(args.x2_haserrors, args.x2_summary, summary)
            gui_raw = args.gui_observations.read_bytes()
            gui = json.loads(gui_raw.decode("utf-8"))
            meta["gui_sha256"] = hashlib.sha256(gui_raw).hexdigest().upper()
            meta.update(link_events=gui.get("link_events", []), ranges=channel_ranges(x2), cells=x2["cells"],
                        channel_labels={cid: channel_label(x2, cid) for cid in (1, 2, 3)})
        phases = build(json.loads(raw.decode("utf-8")), gap, x2, gui)
        markdown = render_markdown(phases, meta)
        errors = contract_check(markdown, phases, r1)
        if errors:
            raise B1cError("contract failed: " + "; ".join(errors))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ArithmeticError, B1cError) as exc:
        print(f"B1c training timeline not produced: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)
    input_meta = {k: v for k, v in meta.items() if k in ("timeline_sha256", "window", "gap_seconds", "x2_sha256", "gui_sha256")}
    document = {"schema": "pcie.b1c-training-timeline/v2" if r1 else "pcie.b1c-training-timeline/v1",
                "input": {**input_meta, "summary_status": summary["status"]},
                "parameters": {"gap_seconds": str(gap), "gap_is": "presentation threshold, not a PCIe rule"},
                "unknowns": UNKNOWNS_R1 if r1 else UNKNOWNS, "phases": phases}
    (args.output_dir / "training.json").write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.output_dir / "training.md").write_text(markdown, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS_TRAINING_TIMELINE", "revision": "r1" if r1 else "base", "phases": len(phases), "flow": flow_line(phases, r1),
                      "training_md_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest().upper()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
