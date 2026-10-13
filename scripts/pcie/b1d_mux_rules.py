#!/usr/bin/env python3
"""Evaluate one engineer-defined MUX switch window offline (PCIe-B1d v1).

PASS is a scoped evidence match, not physical MUX proof or product success.
Unknown numerical limits never become FAIL. No raw trace access or root-cause inference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from b1c_training_timeline import seconds

SCHEMA = "pcie.b1d-mux-rule-evaluation/v1"
STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_EVALUATED")
RULE_QUESTIONS = {
    "SWITCH_LINK_DOWN": [1], "DISCONNECT_ACTIVITY": [1, 2, 3],
    "MUX_CONNECTIVITY": [7], "BIDIRECTIONAL_L0": [2], "LINK_WIDTH_SAMPLES": [4],
    "INITIAL_GEN1_SAMPLE": [], "TARGET_SPEED_OBSERVED": [4],
    "MUX_DISCONNECT_DURATION": [1, 3], "TRAINING_TIMEOUT": [2, 3],
    "TS_ERROR_TOLERANCE": [5], "HOTPLUG_INIT_ACTIVITY": [2, 6],
    "DEVICE_INITIALIZATION_COMPLETED": [2, 6],
}
DEBT = {
    "training_timeout": "適用 spec、training 起算條件及 timeout 上限未提供。",
    "ts_error_tolerance": "TS-error 容許筆數、持續時間、起點與適用階段未提供。",
    "gen3_convergence": "Gen3 升速完成的 milestone／觀察時限未提供。",
    "hotplug_completion": "初始化／enumeration 完成事件、register 清單與時限未提供。",
}


class B1dError(ValueError):
    """Context or evidence cannot support this bounded evaluation."""


def natural(value: Any, name: str, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise B1dError(f"{name} must be a {'positive' if positive else 'nonnegative'} integer")
    return value


def rate(value: Any) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise B1dError("Speed/reference duration must be a positive decimal string")
    result = Decimal(value)
    if result <= 0:
        raise B1dError("Speed/reference duration must be positive")
    return result


def validate(training: dict[str, Any], context: dict[str, Any]) -> None:
    if training.get("schema") != "pcie.b1c-training-timeline/v2":
        raise B1dError("B1d requires B1c-r1 schema v2")
    if training["input"].get("summary_status") != "PASS_WINDOW_EXPORT":
        raise B1dError("Input window export is not PASS_WINDOW_EXPORT")
    if context.get("schema") != "pcie.b1d-product-context/v1":
        raise B1dError("Unsupported product context schema")
    provenance = context["provenance"]
    if provenance.get("source_kind") != "owner_relayed_engineer_answers":
        raise B1dError("Explicit owner-relayed engineer provenance required")
    for key in ("document", "received_date"):
        if not isinstance(provenance.get(key), str) or not provenance[key].strip():
            raise B1dError(f"Missing provenance {key}")
    for rule, questions in RULE_QUESTIONS.items():
        if context["rule_questions"].get(rule) != questions:
            raise B1dError(f"Missing or different engineer source for {rule}")
    operation = context["operation"]
    if (operation.get("kind"), operation.get("interposer"), operation.get("to_device")) != (
            "sde_insert_mux_switch", "between_rc_and_mux", "SDE"):
        raise B1dError("Context is outside this SDE MUX-switch contract")
    start = natural(operation["disconnect_packet"], "disconnect packet", True)
    reconnect = natural(operation["reconnect_packet"], "reconnect packet", True)
    window = training["input"]["window"]
    if not natural(window["start"], "window start", True) <= start < reconnect <= natural(window["end"], "window end", True):
        raise B1dError("Switch anchors are outside the window or out of order")
    expect = context["expectations"]
    if natural(expect["width"], "expected width", True) != 1 or rate(expect["target_speed_gt_s"]) != Decimal("8.0"):
        raise B1dError("This first contract requires engineer-defined SDE Gen3 x1")
    rate(operation["approx_disconnect_seconds"])
    if not all(expect.get(k) is True for k in (
            "link_down_expected", "disconnect_recovery_polling_or_silence_allowed", "new_device_initialization_required")):
        raise B1dError("Product expectations must be explicitly supplied")
    if "initial_gen1_allowed" in expect:
        raise B1dError("No engineer acceptance rule for initial Gen1 was supplied")

    phases = training["phases"]
    if not isinstance(phases, list) or not phases:
        raise B1dError("Empty phase list")
    previous = None
    gap = None
    for phase in phases:
        if phase["kind"] == "NO_OBSERVED_EVENTS":
            if previous is None or gap is not None:
                raise B1dError("Gap is not between two observed phases")
            if phase["after_index"] != previous["last_index"] or phase["after_time"] != previous["last_time"]:
                raise B1dError("Gap does not describe the preceding phase")
            gap = phase
            continue
        first = natural(phase["first_index"], "phase first packet", True)
        last = natural(phase["last_index"], "phase last packet", True)
        t0, t1 = seconds(phase["first_time"]), seconds(phase["last_time"])
        if last < first or t1 < t0:
            raise B1dError("Phase packet/time bounds are reversed")
        if previous is None and first != window["start"]:
            raise B1dError("First phase differs from window start")
        if previous is not None:
            if first != previous["last_index"] + 1 or t0 < seconds(previous["last_time"]):
                raise B1dError("Phases overlap, skip packets or reverse time")
        if gap is not None:
            duration = t0 - seconds(gap["after_time"])
            if (gap["before_index"], gap["before_time"]) != (first, phase["first_time"]) or duration <= 0 or Decimal(gap["duration_seconds"]) != duration:
                raise B1dError("Gap duration/endpoints disagree with observed phases")
            gap = None
        events = natural(phase["events"], "event count", True)
        if natural(phase["err_any"], "HasErrors count") > events:
            raise B1dError("HasErrors exceeds event count")
        for name, count in phase["counts"].items():
            if natural(count, name) > events:
                raise B1dError("Packet count exceeds event count")
        for section in ("steps", "inner_records", "gui_samples"):
            for record in phase[section]:
                if not first <= natural(record["packet_index"], "record packet", True) <= last:
                    raise B1dError("Record lies outside its phase")
                if section == "gui_samples":
                    rate(record["speed"])
                    if not isinstance(record["width"], str) or not re.fullmatch(r"x[1-9]\d*", record["width"]):
                        raise B1dError("Invalid GUI width")
                else:
                    if not t0 <= seconds(record["time_display"]) <= t1:
                        raise B1dError("Record time lies outside its phase")
                    if record["kind"] == "ltssm" and (type(record["state_valid"]) is not int or record["state_valid"] not in (0, 1)):
                        raise B1dError("Invalid LTSSM validity flag")
                    if record["kind"] == "speed_width":
                        natural(record["width"], "observed width", True)
        previous = phase
    if gap is not None or previous["last_index"] != window["end"]:
        raise B1dError("Final phase differs from window end")


def records(training: dict[str, Any], section: str) -> list[dict[str, Any]]:
    rows = []
    for i, phase in enumerate(training["phases"]):
        for j, record in enumerate(phase.get(section, [])):
            rows.append({**record, "source": f"/phases/{i}/{section}/{j}"})
    return sorted(rows, key=lambda r: r["packet_index"])


def evaluate(training: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    validate(training, context)
    rows = sorted(records(training, "steps") + records(training, "inner_records"), key=lambda r: r["packet_index"])
    gui = records(training, "gui_samples")
    op, expect = context["operation"], context["expectations"]
    start, reconnect = op["disconnect_packet"], op["reconnect_packet"]

    def anchor(packet: int, kind: str) -> dict[str, Any]:
        matches = [r for r in rows if r["packet_index"] == packet and r["kind"] == "link_condition" and r["type_name"] == kind]
        if len(matches) != 1:
            raise B1dError(f"Anchor {packet} is not one observed {kind}")
        return matches[0]

    down, up = anchor(start, "LINK_DOWN"), anchor(reconnect, "LINK_UP")
    duration = seconds(up["time_display"]) - seconds(down["time_display"])
    after = [r for r in rows if r["packet_index"] >= reconnect]
    training_rows = [r for r in after if r["kind"] == "ltssm" and r["state_valid"] == 1 and r["state"] in ("POLLING", "CONFIG", "RECOVERY")]
    l0_rows = [r for r in after if r["kind"] == "ltssm" and r["state_valid"] == 1 and r["state"] == "L0"]

    def both(rows: list[dict[str, Any]]) -> bool:
        return {"Upstream", "Downstream"} <= {r.get("channel") for r in rows}

    # Q7 connectivity uses observed training, independently of the L0 milestone.
    connected = both(training_rows)
    l0 = both(l0_rows)
    first_l0 = {c: next((r for r in l0_rows if r["channel"] == c), None) for c in ("Upstream", "Downstream")}
    l0_complete_packet = max(r["packet_index"] for r in first_l0.values()) if l0 else None
    first_l0_packet = min(r["packet_index"] for r in l0_rows) if l0_rows else None
    post_gui = [r for r in gui if r["packet_index"] >= reconnect]
    widths = [{"value": r["width"], "evidence": r} for r in after if r["kind"] == "speed_width"]
    widths += [{"value": int(r["width"][1:]), "evidence": r} for r in post_gui]
    width_status = "INCONCLUSIVE" if not widths else ("PASS" if all(w["value"] == expect["width"] for w in widths) else "FAIL")
    initial_samples = [r for r in post_gui if first_l0_packet is not None and r["packet_index"] < first_l0_packet]
    target_samples = [r for r in post_gui if rate(r["speed"]) == rate(expect["target_speed_gt_s"])]
    config = [r for r in after if l0_complete_packet is not None and r["packet_index"] > l0_complete_packet
              and r["kind"] == "tlp" and r["channel"] == "Downstream" and r["tlp_type"] in (9, 10, 11, 12)]
    disconnected = [r for r in rows if start <= r["packet_index"] < reconnect and r["kind"] == "ltssm" and r["state"] in ("RECOVERY", "POLLING")]
    gaps = [{**p, "source": f"/phases/{i}"} for i, p in enumerate(training["phases"])
            if p["kind"] == "NO_OBSERVED_EVENTS" and start <= p["after_index"] < p["before_index"] <= reconnect]
    errors = [{"source": f"/phases/{i}", "first_index": p["first_index"], "last_index": p["last_index"],
               "first_time": p["first_time"], "last_time": p["last_time"], "count": p["err_any"],
               "error_subtype": p["error_subtype"], "channel_evidence": p.get("has_errors_channel"),
               "gui_samples": p["gui_samples"]}
              for i, p in enumerate(training["phases"]) if p["kind"] != "NO_OBSERVED_EVENTS" and p["err_any"]]
    results = []

    def add(rule: str, status: str, summary: str, evidence: list[dict[str, Any]], limit: str) -> None:
        results.append({"rule_id": rule, "status": status, "summary": summary, "evidence": evidence,
                        "engineer_questions": context["rule_questions"][rule], "limitation": limit})

    add("SWITCH_LINK_DOWN", "PASS", "指定切換起點出現 Link Down，符合工程師描述的切換情境。", [down], "此事件本身不證明後續接通或初始化成功。")
    add("DISCONNECT_ACTIVITY", "PASS" if disconnected or gaps else "INCONCLUSIVE",
        "接通前已觀察的 Recovery／Polling／無事件區間，屬產品允許出現的現象。" if disconnected or gaps else "未觀察到可套用這條情境規則的紀錄。",
        disconnected + gaps, "不驗證整段 LTSSM 的規範合法性或時間；invalid-state 標記原樣保留。")
    add("MUX_CONNECTIVITY", "PASS" if connected else "INCONCLUSIVE",
        "接通 anchor 後有雙向有效 training，支持工程師的 MUX 已接通判斷。" if connected else "未取得接通 anchor 後的雙向有效 training 證據。",
        training_rows, "Q7 的依據是雙向有效 training，不要求雙向 L0；未直接量測 MUX 電氣狀態，未證明裝置初始化。")
    add("BIDIRECTIONAL_L0", "PASS" if l0 else "INCONCLUSIVE",
        "接通後兩方向均有有效 L0 紀錄。" if l0 else "缺少接通後任一方向的有效 L0 紀錄。",
        l0_rows, "本項是兩方向明確有效 L0 的觀察里程碑；Q2 提供後續初始化情境，不取代 Q7 的 training 接通依據。缺少 L0 不自動判 FAIL，沒有 timeout 上限。")
    add("LINK_WIDTH_SAMPLES", width_status,
        "接通後已觀察的 width 樣本符合 x1。" if width_status == "PASS" else ("接通後有 width 樣本不符合 x1。" if width_status == "FAIL" else "接通後没有 width 樣本。"),
        [w["evidence"] for w in widths], "僅限已記錄的 speed_width／GUI 樣本，未確認完整後續連線。")
    add("INITIAL_GEN1_SAMPLE", "INCONCLUSIVE",
        f"首次有效 L0 前的 GUI 樣本觀察到 {initial_samples[0]['speed']} GT/s {initial_samples[0]['width']}；本項只記錄觀察。" if initial_samples else "沒有首次有效 L0 前的 GUI speed 樣本可供記錄。",
        initial_samples[:1], "工程師只定義 target Gen3 x1 與持續停留 Gen1 不符合預期，未提供初始 Gen1 接受規則；本版未驗證 PCIe spec，不判本項 PASS／FAIL。")
    results[-1]["assessment_kind"] = "observation_only"
    add("TARGET_SPEED_OBSERVED", "PASS" if target_samples else "INCONCLUSIVE",
        "接通後 GUI 樣本曾到達目標 8.0 GT/s。" if target_samples else "目前僅確認未在既有 GUI speed 樣本中觀察到 target 8.0 GT/s；window 缺少後續升速證據，不能判定後續是否完成升速。",
        target_samples, "只確認樣本曾觀察到 target rate，不證明升速流程完成；升速完成終點／時限未提供。" if target_samples else "樣本未見 target rate 不等同後續未升速或持續停在 Gen1；升速完成終點／時限未提供，raw speed code 的標示尚未 probe。")
    add("MUX_DISCONNECT_DURATION", "NOT_EVALUATED", f"切換 Link Down 到 reconnect Link Up 的 display-time 差為 {duration} sec，工程師參考值約 {op['approx_disconnect_seconds']} sec。",
        [down, up], "這是兩個事件間的時間，非直接量測 MUX dead-time；約 1.4 sec 不作 timeout 或接受門檻。")
    add("TRAINING_TIMEOUT", "NOT_EVALUATED", DEBT["training_timeout"], l0_rows, "不自訂 Recovery 次數或 training 上限。")
    add("TS_ERROR_TOLERANCE", "NOT_EVALUATED", f"輸入 window 共 {sum(e['count'] for e in errors):,} 筆 HasErrors，保留各段供檢查；容許門檻未定。",
        errors, "未自訂 transient／persistent 數值分類；GUI subtype 僅代表已抽樣的紀錄。")
    add("HOTPLUG_INIT_ACTIVITY", "PASS" if config else "INCONCLUSIVE",
        "雙向 L0 後觀察到 Downstream config request，支持初始化活動已開始。" if config else (
            "雙向 L0 後在輸入 window 未觀察到 config request，後續初始化仍不確定。" if l0 else "尚無雙向 L0，無法建立本版的初始化觀察起點。"),
        config, "看到 request 不證明 Completion、BAR 寫入或 enumeration 完成；未看到也不推定 window 外不存在。")
    add("DEVICE_INITIALIZATION_COMPLETED", "NOT_EVALUATED", DEBT["hotplug_completion"], config,
        "與 MUX 接通狀態獨立；單一 config request 不構成初始化完成。")
    return {
        "schema": SCHEMA, "overall_verdict": "NOT_CLAIMED",
        "scope": "one context-selected MUX switch in the B1c-r1 window",
        "product_context": context,
        "states": {
            "mux_switch": {"state": "MUX_SWITCH_COMPLETED" if connected else "MUX_SWITCH_COMPLETION_NOT_ESTABLISHED", "status": "PASS" if connected else "INCONCLUSIVE", "basis": "engineer Q7 bidirectional-training evidence criterion"},
            "link_l0": {"state": "BIDIRECTIONAL_L0_OBSERVED" if l0 else "BIDIRECTIONAL_L0_NOT_ESTABLISHED", "status": "PASS" if l0 else "INCONCLUSIVE", "basis": "explicit valid L0 records on both directions; independent of Q7 connectivity"},
            "hotplug_activity": {"state": "HOTPLUG_INIT_OBSERVED" if config else "HOTPLUG_INIT_NOT_OBSERVED", "status": "PASS" if config else "INCONCLUSIVE"},
            "device_initialization": {"state": "DEVICE_INITIALIZATION_COMPLETION_NOT_ESTABLISHED", "status": "NOT_EVALUATED", "value": None},
        },
        "observations": {"initial_speed_sample": initial_samples[0] if initial_samples else None,
                         "switch_link_down_to_reconnect_seconds": str(duration), "has_errors": sum(e["count"] for e in errors),
                         "last_observed_packet": training["input"]["window"]["end"], "last_observed_time": training["phases"][-1]["last_time"],
                         "post_l0_observed_seconds": str(seconds(training["phases"][-1]["last_time"]) - max(seconds(r["time_display"]) for r in first_l0.values())) if l0 else None,
                         "time_basis": "PETracer display time; 0 elapsed display seconds does not mean zero physical duration"},
        "evaluations": results,
        "validation_debt": [{"id": k, "status": "NOT_EVALUATED", "reason": v, "blocks_this_version": False} for k, v in DEBT.items()],
        "input_unknowns": training["unknowns"],
        "not_established": ["overall product PASS/FAIL", "direct physical MUX measurement", "persistent Gen1", "enumeration completion", "BSOD root cause", "full-trace or multi-case coverage"],
    }


def render_markdown(doc: dict[str, Any]) -> str:
    def safe(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    context = doc["product_context"]
    lines = ["# PCIe-B1d：MUX 切換產品規則評估", "",
             "本報告逐項比對工程師預期與既有 trace 觀察。PASS 只限各項所列證據，沒有整體產品成功判定。", "",
             f"工程師回答來源：`{safe(context['provenance']['document'])}`，收錄日期 {safe(context['provenance']['received_date'])}；由使用者轉述，回答人／實際日期未提供。", "",
             f"故障描述（使用者轉述）：{safe(context['case']['reported_symptom'])}。其他測試的 0xA0 不套用到本 case。", "",
             "判讀順序是 MUX 接通 → 雙向 L0 → 目標升速 → 新裝置初始化。各階段獨立；雙向 training 支持接通，不能證明後續裝置可見。", "",
             "| 項目 | 狀態 | 觀察與解讀 | 工程師來源 |", "| --- | --- | --- | --- |"]
    for r in doc["evaluations"]:
        source = ', '.join('Q'+str(q) for q in r['engineer_questions']) if r['engineer_questions'] else 'trace 觀察；無工程師接受規則'
        if r['rule_id'] == 'BIDIRECTIONAL_L0':
            source = 'trace observation；Q2 提供後續初始化情境'
        lines.append(f"| {r['rule_id']} | {r['status']} | {safe(r['summary'])} | {source} |")
    lines += ["", "PASS 表示此項觀察符合預期；FAIL 表示已觀察數值違反明確預期；INCONCLUSIVE 表示證據不足；NOT_EVALUATED 表示判定条件未定。", "",
              f"本 window 的最後觀察為 Packet {doc['observations']['last_observed_packet']}（{doc['observations']['last_observed_time']}）。",
              f"雙向 L0 到 window 尾端的 display-time 差為 {doc['observations']['post_l0_observed_seconds']} sec（None 表示尚無雙向 L0）；顯示時間無差不代表物理時間為零。", ""]
    for r in doc["evaluations"]:
        lines += [f"## {r['rule_id']}：{r['status']}", "", r["summary"], "", f"限制：{r['limitation']}", ""]
        for e in r["evidence"]:
            if "packet_index" in e:
                detail = e.get("time_display", "GUI sample")
                if e.get("kind") == "ltssm":
                    detail += f" {e.get('channel')} {e['state']} valid={e['state_valid']}"
                if "gui_error_labels" in e:
                    detail += f" {e['speed']} GT/s {e['width']} subtype={','.join(e['gui_error_labels'])}（僅代表此 sample）"
                lines.append(f"- Packet {e['packet_index']}：{safe(detail)}；training.json `{e['source']}`。")
            elif "count" in e:
                lines.append(f"- Packet {e['first_index']}-{e['last_index']}，{e['first_time']}-{e['last_time']}：HasErrors {e['count']:,}，subtype {safe(e['error_subtype'])}；`{e['source']}`。")
                for sample in e["gui_samples"]:
                    lines.append(f"  - GUI Packet {sample['packet_index']}：{safe(','.join(sample['gui_error_labels']))}（僅代表此 sample）。")
            else:
                lines.append(f"- 沒有觀察到事件：{e['after_time']}-{e['before_time']}（{e['duration_seconds']} sec），Packet {e['after_index']} 與 {e['before_index']} 之間；`{e['source']}`。")
        lines.append("")
    lines += ["## 待補驗證條件", "", "下列項目限制相應規則，沒有阻擋本版建立與重播。", ""]
    lines += [f"- {d['id']}：{d['reason']}" for d in doc["validation_debt"]]
    lines += ["", "## 輸入保留的未知項", ""] + [f"- {u}" for u in doc["input_unknowns"]]
    lines += ["", "## 重播來源", "", f"training.json SHA-256：`{doc['input']['training_sha256']}`",
              f"context SHA-256：`{doc['input']['context_sha256']}`", f"工程師問答 SHA-256：`{doc['input']['source_document_sha256']}`", "",
              "未建立 BSOD 根因、初始化完成、持續 Gen1、整體 PASS／FAIL 或跨 case 正確性。", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--source-document", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1dError("Refusing to reuse existing output directory")
        raw, context_raw, source_raw = args.training.read_bytes(), args.context.read_bytes(), args.source_document.read_bytes()
        sha = lambda value: hashlib.sha256(value).hexdigest().upper()
        training, context = json.loads(raw.decode("utf-8")), json.loads(context_raw.decode("utf-8"))
        if context["training_sha256"] != sha(raw):
            raise B1dError("Product context does not describe this training.json")
        if context["provenance"]["document_sha256"] != sha(source_raw):
            raise B1dError("Engineer source document differs from context provenance")
        doc = evaluate(training, context)
        doc["input"] = {"training_sha256": sha(raw), "context_sha256": sha(context_raw), "source_document_sha256": sha(source_raw), "b1c_input": training["input"]}
        markdown = render_markdown(doc)
        args.output_dir.mkdir(parents=True)
        (args.output_dir / "evaluation.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (args.output_dir / "evaluation.md").write_text(markdown, encoding="utf-8", newline="\n")
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, AttributeError) as exc:
        print(f"B1d evaluation not produced: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS_B1D_RULE_EVALUATION_BUILD", "overall_verdict": "NOT_CLAIMED", "states": doc["states"],
                      "evaluation_md_sha256": sha(markdown.encode("utf-8"))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
