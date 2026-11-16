#!/usr/bin/env python3
"""Build scoped link findings from an accepted B1d evaluation, without new rules."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import b1d_mux_rules as b1d

SCHEMA = "pcie.b1e-link-findings/v1"
TITLES = {
    "SWITCH_LINK_DOWN": "切換起點 Link Down", "DISCONNECT_ACTIVITY": "接通前的 link 行為",
    "MUX_CONNECTIVITY": "MUX 接通證據", "BIDIRECTIONAL_L0": "雙向 L0 觀察里程碑",
    "LINK_WIDTH_SAMPLES": "連線 width 樣本", "INITIAL_GEN1_SAMPLE": "首次 L0 前速率樣本",
    "TARGET_SPEED_OBSERVED": "目標 Gen3 樣本", "MUX_DISCONNECT_DURATION": "切換事件時間差",
    "TRAINING_TIMEOUT": "Training 時限", "TS_ERROR_TOLERANCE": "TS-error 接受度",
    "HOTPLUG_INIT_ACTIVITY": "L0 後初始化活動", "DEVICE_INITIALIZATION_COMPLETED": "裝置初始化完成條件",
}


class B1eError(ValueError):
    """Accepted evidence is missing or inconsistent."""


def build(evaluation: dict[str, Any], training: dict[str, Any]) -> dict[str, Any]:
    if evaluation.get("schema") != b1d.SCHEMA:
        raise B1eError("Unsupported B1d evaluation schema")
    expected = b1d.evaluate(training, evaluation["product_context"])
    if expected != {k: v for k, v in evaluation.items() if k != "input"}:
        raise B1eError("B1d evaluation differs from its rules, context or evidence")
    findings = []
    for i, r in enumerate(evaluation["evaluations"]):
        if r.get("assessment_kind") == "observation_only":
            category = "OBSERVATION_ONLY"
        elif r["status"] == "FAIL":
            category = "RULE_MISMATCH"
        elif r["status"] == "INCONCLUSIVE":
            category = "EVIDENCE_GAP"
        elif r["status"] == "NOT_EVALUATED":
            category = "UNEVALUATED_RULE"
        elif r["rule_id"] in ("SWITCH_LINK_DOWN", "DISCONNECT_ACTIVITY"):
            category = "EXPECTED_CONTEXT"
        else:
            category = "SUPPORTED_MILESTONE"
        findings.append({"finding_id": f"B1E-{i+1:03}", "title": TITLES[r["rule_id"]],
                         "category": category, "is_rule_mismatch": category == "RULE_MISMATCH",
                         "source_evaluation": f"/evaluations/{i}", **copy.deepcopy(r)})

    observed = [p for p in training["phases"] if p["kind"] != "NO_OBSERVED_EVENTS"]
    crc = {}
    for flag in ("tlp_bad_lcrc", "dllp_bad_crc"):
        values = [p.get("err_subflags", {}).get(flag) for p in observed]
        for p, value in zip(observed, values):
            if value is not None and b1d.natural(value, flag) > p["events"]:
                raise B1eError("CRC flag count exceeds phase events")
        crc[flag] = {"count": None if any(v is None for v in values) else sum(values),
                     "coverage": "input window only; analyzer flag counts; missing is UNKNOWN"}
    rows = b1d.records(training, "steps") + b1d.records(training, "inner_records")
    states = copy.deepcopy(evaluation["states"])
    if states["mux_switch"]["status"] == "PASS" and states["link_l0"]["status"] == "PASS":
        focus = {"stage": "AFTER_BIDIRECTIONAL_L0", "question": "L0 建立後，是否完成目標升速與新 SDE 裝置初始化？",
                 "next_evidence": ["speed change / Gen3 convergence", "CfgRd/CfgWr and completions", "VID/DID, BAR and Command state", "device enable / driver-emulation interaction"],
                 "limitation": "目前 capture 尾端不足，沒有判定哪一步造成裝置不可見；不重開已有支持的 MUX 接通。"}
    elif states["mux_switch"]["status"] == "PASS":
        focus = {"stage": "LINK_ESTABLISHMENT_EVIDENCE_GAP", "question": "已有雙向 training 支持，仍需取得雙向有效 L0 證據。",
                 "next_evidence": ["explicit valid L0 records in both directions"], "limitation": "不能把缺 L0 改成 MUX 失敗。"}
    else:
        focus = {"stage": "CONNECTIVITY_EVIDENCE_GAP", "question": "本輸入尚缺工程師 Q7 所要求的雙向有效 training 證據。",
                 "next_evidence": ["explicit valid bidirectional training after the reconnect anchor"], "limitation": "缺觀察不等同物理切換失敗。"}
    return {"schema": SCHEMA, "overall_verdict": "NOT_CLAIMED", "states": states, "findings": findings,
            "observations": {"nak_records": [r for r in rows if r["kind"] == "nak"],
                             "recovery_state_records": [r for r in rows if r["kind"] == "ltssm" and r["state"] == "RECOVERY"],
                             "raw_speed_width_records": [r for r in rows if r["kind"] == "speed_width"], "crc_flags": crc,
                             "window": training["input"]["window"], "last_observed_time": evaluation["observations"]["last_observed_time"]},
            "investigation_focus": focus, "case_report": copy.deepcopy(evaluation["product_context"]["case"]),
            "validation_debt": copy.deepcopy(evaluation["validation_debt"]),
            "input_unknowns": copy.deepcopy(evaluation["input_unknowns"]),
            "not_established": copy.deepcopy(evaluation["not_established"])}


def render_markdown(doc: dict[str, Any]) -> str:
    safe = lambda text: str(text).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    focus = doc["investigation_focus"]
    lines = ["# PCIe-B1e：Link findings", "", focus["question"], "", focus["limitation"], "",
             "此報告保留 B1d 各項狀態與限制；EXPECTED_CONTEXT 不作異常，證據不足不改成 FAIL，缺門檻不改成 PASS。", "",
             "| Finding | 項目 | 類別 | 狀態 | 觀察與解讀 |", "| --- | --- | --- | --- | --- |"]
    for f in doc["findings"]:
        lines.append(f"| {f['finding_id']} | {f['title']} | {f['category']} | {f['status']} | {safe(f['summary'])} |")
    lines += ["", "## 後續需要的證據", ""] + [f"- {n}" for n in focus["next_evidence"]]
    for f in doc["findings"]:
        lines += ["", f"## {f['finding_id']}：{f['title']}", "", f["summary"], "", f"限制：{f['limitation']}", "",
                  f"B1d evaluation.json：`{f['source_evaluation']}`；rule `{f['rule_id']}`。", ""]
        for e in f["evidence"]:
            if "packet_index" in e:
                lines.append(f"- Packet {e['packet_index']}：training.json `{e['source']}`。")
            elif "count" in e:
                lines.append(f"- Packet {e['first_index']}-{e['last_index']}：HasErrors {e['count']:,}，subtype {safe(e['error_subtype'])}；`{e['source']}`。")
            else:
                lines.append(f"- Packet {e['after_index']}-{e['before_index']} 之間沒有觀察到事件，{e['duration_seconds']} sec；`{e['source']}`。")
    obs = doc["observations"]
    lines += ["", "## 其他原始觀察", "", "NAK 只作 NAK 觀察，不推定 replay；Recovery state 紀錄不當作完整 entry 次數。", ""]
    for r in obs["nak_records"]:
        lines.append(f"- NAK Packet {r['packet_index']}，{r['time_display']}，seq {r['seq']}，{r['channel']}；`{r['source']}`。")
    for flag, result in obs["crc_flags"].items():
        lines.append(f"- {flag}：{result['count'] if result['count'] is not None else 'UNKNOWN'}，僅限 window 內 analyzer flag。")
    lines += [f"- Recovery state 紀錄 {len(obs['recovery_state_records'])} 筆，raw speed/width 紀錄 {len(obs['raw_speed_width_records'])} 筆；詳細 packet 保留在 JSON，不作規範違反判定。",
              "", "## Case 來源與未完成驗證", "", f"使用者轉述：{safe(doc['case_report']['reported_symptom'])}；不作前段根因推定。", ""]
    lines += [f"- {d['id']}：{d['reason']}（不阻擋本版）" for d in doc["validation_debt"]]
    lines += ["", "## 重播來源", ""] + [f"- {k}：`{v}`" for k, v in doc["input"].items()]
    lines += ["", "本版未建立整體產品 PASS/FAIL、電氣量測、規範完整性或 root cause。", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--source-document", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output_dir.exists():
            raise B1eError("Refusing to reuse existing output directory")
        raw, training_raw, source_raw = args.evaluation.read_bytes(), args.training.read_bytes(), args.source_document.read_bytes()
        sha = lambda data: hashlib.sha256(data).hexdigest().upper()
        evaluation, training = json.loads(raw.decode("utf-8")), json.loads(training_raw.decode("utf-8"))
        if sha(training_raw) != evaluation["input"]["training_sha256"] or sha(training_raw) != evaluation["product_context"]["training_sha256"]:
            raise B1eError("Evaluation and training identity differ")
        if sha(source_raw) != evaluation["input"]["source_document_sha256"] or sha(source_raw) != evaluation["product_context"]["provenance"]["document_sha256"]:
            raise B1eError("Evaluation and engineer source identity differ")
        doc = build(evaluation, training)
        doc["input"] = {"evaluation_sha256": sha(raw), "training_sha256": sha(training_raw), "source_document_sha256": sha(source_raw)}
        markdown = render_markdown(doc)
        args.output_dir.mkdir(parents=True)
        (args.output_dir / "findings.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (args.output_dir / "findings.md").write_text(markdown, encoding="utf-8", newline="\n")
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, AttributeError) as exc:
        print(f"B1e findings not produced: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS_B1E_FINDINGS_BUILD", "findings": len(doc["findings"]), "rule_mismatches": sum(f["is_rule_mismatch"] for f in doc["findings"]), "focus": doc["investigation_focus"]["stage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
