#!/usr/bin/env python3
"""PCIe-G7: render G3f findings.json as a Traditional Chinese engineering Markdown report.

The renderer performs no analysis. Every sentence is filled from structured fields of
findings.json with fixed templates; PCIe names, packet identities and field names stay in
English. `finding_parts` is shared with the G8 HTML renderer so both carry the same wording.
A report contract check runs before anything is written and fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPORT_TITLE = "PCIe Trace 候選檢查位置報告"
NAVIGATION_NOTE = "主要定位點依固定規則選出，取這一組最早出現的 request。它只用來快速跳轉，不代表該位置比較嚴重、比較可疑，或比較接近故障原因。"
GLOSSARY = {
    "MRd(32)": "32-bit Memory Read request",
    "CfgRd0": "Type 0 Configuration Read request",
    "CfgWr0": "Type 0 Configuration Write request",
    "Cpl": "沒有帶資料的 Completion",
    "CplD": "帶資料的 Completion",
    "UR": "Unsupported Request，Completion status 的一種",
    "SC": "Successful Completion，正常完成的 Completion status",
    "ERR_COR": "Correctable Error Message，裝置回報可更正錯誤的 message",
    "SLOTPOWERLIMIT": "Set Slot Power Limit message",
}
ALWAYS_TERMS = [
    ("Tag", "request 的編號，Completion 會帶回同一個 Tag"),
    ("RequesterId", "送出 request 的裝置位址，格式 `bus:device.function`"),
    ("Go to Packet", "LeCroy PETracer 的 Search > Go to Packet（Ctrl+G）"),
    ("Segment", "同一組候選檢查位置裡位置相近的一段 packet"),
]
BASIS_ZH = {
    "shared_anchor_packet": "它們用到同一個 packet",
    "shared_association_lineage": "它們在同一條 request 關聯鏈上，同一組 `RequesterId` + `Tag` 連續出現",
    "request_or_completion_is_other_candidate_anchor": "其中一項的 request 或 Completion 也是另一項的觀察位置",
}
FORBIDDEN_PHRASES = ("root cause", "根本原因", "confirmed failure", "確認為故障", "導致", "造成了", "severity", "priority", "嚴重度", "建議先看")
SECTION_TITLES = ("### 主要定位點", "### 觀察到什麼", "### 相關位置", "### 為什麼列出這一項", "### 目前還不能確定", "### 追溯")


class G7Error(ValueError):
    """Rendering input is unusable or the report contract failed."""


def _p(packet: int) -> str:
    return f"`Packet {packet}`"


def _codes(values) -> str:
    return "、".join(f"`{v}`" for v in values)


def candidate_view(finding: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per candidate: its anchors by role, taken from local segment anchor roles."""
    view: dict[str, dict[str, Any]] = {}
    for seg in finding["what_was_observed"]["local_segments"]:
        for anchor in seg["anchors"]:
            for role in anchor["roles"]:
                cid, name = role.split(":", 1)
                view.setdefault(cid, {})[name] = {**anchor, "segment": seg["segment"]}
    return view


def messages_of(finding: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for seg in finding["what_was_observed"]["local_segments"] for m in seg["nearby_messages"]]


def finding_facts(finding: dict[str, Any]) -> dict[str, Any]:
    """Flags derived from structure, for summaries and badges."""
    view = candidate_view(finding)
    completions = [v for v in view.values() if "completion" in v]
    return {
        "same_key": any("first_request" in v for v in view.values()),
        "same_key_types": sorted({v["first_request"]["type"] for v in view.values() if "first_request" in v}),
        "request_types": sorted({v["request"]["type"] for v in completions}),
        "statuses": sorted({v["completion"]["status"] for v in completions}),
        "messages": sorted({m["message"] for m in messages_of(finding)}),
        "segments": len(finding["what_was_observed"]["local_segments"]),
        "span": finding["trace_span_packets"],
        "times": sorted({t for seg in finding["what_was_observed"]["local_segments"] for t in seg["display_times"]}),
    }


def summary_parts(finding: dict[str, Any]) -> list[str]:
    facts = finding_facts(finding)
    parts = []
    if facts["same_key"]:
        parts.append(f"{_codes(facts['same_key_types'])} 同一組 key 再次出現")
    if facts["statuses"]:
        parts.append(f"{_codes(facts['request_types'])} 收到 {_codes(facts['statuses'])}")
    if facts["messages"]:
        parts.append(f"附近有 {_codes(facts['messages'])}")
    return parts


def finding_parts(finding: dict[str, Any]) -> dict[str, Any]:
    """All report wording for one finding, as plain strings with backtick-marked identities."""
    view = candidate_view(finding)
    segments = finding["what_was_observed"]["local_segments"]
    primary = finding["where_to_look"]["primary_go_to_packet"]
    members = finding["why_surfaced"]["members"]

    observations = []
    for cid in members:
        roles = view.get(cid, {})
        if "request" in roles and "completion" in roles:
            req, cpl = roles["request"], roles["completion"]
            observations.append((req["packet"], f"{req['display_time']}，{_p(req['packet'])} 的 `{req['type']}` request（`Tag {req['tag']}`）"
                                                 f"收到 {_p(cpl['packet'])} 的 Completion，status 是 `{cpl['status']}`。"))
        elif "first_request" in roles and "repeated_request" in roles:
            first, rep = roles["first_request"], roles["repeated_request"]
            observations.append((first["packet"], f"{first['display_time']}，{_p(first['packet'])} 的 `{first['type']}`（`Tag {first['tag']}`）送出後，"
                                                   f"還沒看到對應的 Completion，同一組 `RequesterId` + `Tag` 就在 {_p(rep['packet'])} 再次出現"
                                                   f"（{rep['display_time']}，`{rep['type']}`）。"))
        else:
            raise G7Error(f"Finding {finding['finding_id']} candidate {cid} has incomplete anchor roles")

    segment_parts = []
    for seg in segments:
        lines = []
        for a in seg["anchors"]:
            parts = [_p(a["packet"]), f"`{a['type']}`", f"`Tag {a['tag']}`", f"Requester `{a['requester']}`"]
            if a["completer"]:
                parts.append(f"Completer `{a['completer']}`")
            if a["status"]:
                parts.append(f"status `{a['status']}`")
            lines.append("，".join(parts))
        lines += [f"{_p(m['packet'])}，`{m['message']}`，附近的 message" for m in seg["nearby_messages"]]
        segment_parts.append({"segment": seg["segment"], "title": f"Segment {seg['segment']}（{'、'.join(seg['display_times'])}）",
                              "go_to_packet": seg["go_to_packet"], "lines": lines})

    crosschecks = []
    for check in finding["gui_crosschecks"]:
        roles = view.get(check["candidate_id"], {})
        if "request" in roles and "completion" in roles:
            crosschecks.append(f"{_p(roles['request']['packet'])} 和 {_p(roles['completion']['packet'])} 的對應，已在 LeCroy Split Transaction 畫面核對一致"
                               f"（`{check['lecroy_view']}`）。")

    facts = finding_facts(finding)
    why: list[tuple[str, list[str]]] = []
    if facts["statuses"]:
        why.append((f"有 request 收到 status 為 {_codes(facts['statuses'])} 的 Completion，工具會列出 status 不是 `SC` 的 Completion。", []))
    if facts["same_key"]:
        why.append(("同一組 `RequesterId` + `Tag` 在看到 Completion 以前再次出現。", []))
    if len(members) > 1:
        why.append(("這幾項觀察放在同一組，原因如下", [BASIS_ZH[b] for b in finding["why_surfaced"]["grouping_basis"]]))

    unknown = ["這份 trace 的 ground truth 還沒確認（`UNKNOWN`），工具沒有判斷這裡是否異常。"]
    if facts["messages"]:
        target = _codes(facts["statuses"]) if facts["statuses"] else "這裡的 request"
        unknown.append(f"{_codes(facts['messages'])} 和 {target} 目前只確認位置接近，沒有證明因果。判斷附近與否用的 64 packets 範圍，是看過資料後才訂的暫定條件。")
    if len(segments) > 1 and len(members) > 1:
        unknown.append(f"這一組的 {len(segments)} 個 Segment 前後相隔約 {facts['span']:,} packets。放在同一組是因為 evidence 有關聯，不代表這幾段屬於同一個故障事件。")
    elif len(segments) > 1:
        unknown.append(f"同一組 `RequesterId` + `Tag` 的兩次出現相隔約 {facts['span']:,} packets，key 相同不代表兩次出現屬於同一個故障事件。")
    checked = {c["candidate_id"] for c in finding["gui_crosschecks"]}
    for cid in members:
        roles = view.get(cid, {})
        if "request" in roles and cid not in checked:
            unknown.append(f"{_p(roles['request']['packet'])} 和 {_p(roles['completion']['packet'])} 的對應是依規則配出來的，還沒在 LeCroy GUI 核對。")
    if facts["same_key"]:
        unknown.append("同一組 key 再次出現，不代表 requester 重送、`Tag` 用法違規，或 Completion 落在 capture 範圍外。")

    return {
        "finding_id": finding["finding_id"],
        "group_id": finding["group_id"],
        "primary_packet": primary,
        "primary_sentence": f"{_p(primary)}，依固定規則選出的主要定位點（這一組最早出現的 request）。在 LeCroy 用 Go to Packet 跳過去。",
        "other_locations": [f"Segment {s['segment']}，{_p(s['go_to_packet'])}" for s in segments if s["go_to_packet"] != primary],
        "summary": summary_parts(finding),
        "observations": [text for _, text in sorted(observations)],
        "nearby": [f"{_p(m['packet'])}，`{m['message']}`（{m['display_time']}）" for m in messages_of(finding)],
        "segments": segment_parts,
        "crosschecks": crosschecks,
        "why": why,
        "unknown": unknown,
        "trace": f"`findings.json` 的 `{finding['finding_id']}`，group `{finding['group_id']}`，candidates {_codes(members)}。",
        "facts": facts,
    }


def glossary_lines(findings: list[dict[str, Any]]) -> list[str]:
    used = {"SC"}
    for f in findings:
        for seg in f["what_was_observed"]["local_segments"]:
            used.update(a["type"] for a in seg["anchors"])
            used.update(a["status"] for a in seg["anchors"] if a["status"])
            used.update(m["message"] for m in seg["nearby_messages"])
    return [f"`{term}`，{GLOSSARY[term]}" for term in GLOSSARY if term in used] + [f"`{t}`，{text}" for t, text in ALWAYS_TERMS]


def intro_paragraphs(trace_name: str, tlp_count: int | None, total: int) -> list[str]:
    count_text = f"{tlp_count} 筆 TLP" if tlp_count is not None else "TLP"
    return [
        f"工具在 `{trace_name}` 的 {count_text} 裡整理出 {total} 組候選檢查位置。每一組都附上主要定位點，也就是 LeCroy 可以直接跳過去的 packet 編號。"
        "各組依主要定位點在 trace 裡出現的先後排列，順序不代表嚴重程度。",
        NAVIGATION_NOTE,
        "這份報告只整理工具觀察到的事。這份 trace 的測試結果還沒確認（ground truth `UNKNOWN`），報告沒有判斷哪一組和故障有關。",
    ]


def source_lines(trace_name: str, trace_sha256: str | None, tlp_count: int | None, findings_sha256: str) -> list[str]:
    lines = [f"`findings.json` SHA-256 `{findings_sha256}`，本報告的所有觀察都來自這個檔案。",
             f"Trace 檔名 `{trace_name}`，由產生報告時的命令列提供。"]
    if trace_sha256:
        lines.append(f"Trace SHA-256 `{trace_sha256}`，由命令列提供。")
    if tlp_count is not None:
        lines.append(f"TLP 總數 {tlp_count}，由命令列提供，來自已驗證的 G1a 計數。")
    return lines


def render_finding(finding: dict[str, Any]) -> str:
    parts = finding_parts(finding)
    out = [f"## Finding {parts['finding_id']}", "", "### 主要定位點", "", parts["primary_sentence"]]
    if parts["other_locations"]:
        out += ["", "其他位置", ""] + [f"- {x}" for x in parts["other_locations"]]
    out += ["", "### 觀察到什麼"]
    for sentence in parts["observations"]:
        out += ["", sentence]
    if parts["nearby"]:
        out += ["", "附近也觀察到", ""] + [f"- {x}" for x in parts["nearby"]]
    out += ["", "### 相關位置"]
    for seg in parts["segments"]:
        out += ["", f"#### {seg['title']}", ""] + [f"- {x}" for x in seg["lines"]]
    for line in parts["crosschecks"]:
        out += ["", line]
    out += ["", "### 為什麼列出這一項", ""]
    for text, subs in parts["why"]:
        out.append(f"- {text}")
        out += [f"  - {s}" for s in subs]
    out += ["", "### 目前還不能確定", ""] + [f"- {x}" for x in parts["unknown"]]
    out += ["", "### 追溯", "", parts["trace"], ""]
    return "\n".join(out)


def render(findings_doc: dict[str, Any], trace_name: str, trace_sha256: str | None, tlp_count: int | None, findings_sha256: str) -> str:
    findings = findings_doc["findings"]
    lines = [f"# {REPORT_TITLE}（{trace_name}）", ""]
    for paragraph in intro_paragraphs(trace_name, tlp_count, len(findings)):
        lines += [paragraph, ""]
    lines += ["## 報告用到的 PCIe 名詞", ""] + [f"- {x}" for x in glossary_lines(findings)]
    lines += ["", f"## {len(findings)} 組候選檢查位置一覽", "", "| Finding | 主要定位點 | 時間 | 內容 |", "| --- | --- | --- | --- |"]
    for f in findings:
        facts = finding_facts(f)
        lines.append(f"| [{f['finding_id']}](#finding-{f['finding_id'].lower()}) | {_p(f['where_to_look']['primary_go_to_packet'])} | {'、'.join(facts['times'])} | {'；'.join(summary_parts(f))} |")
    lines.append("")
    lines += [render_finding(f) for f in findings]
    lines += ["## 資料來源", ""] + [f"- {x}" for x in source_lines(trace_name, trace_sha256, tlp_count, findings_sha256)] + [""]
    return "\n".join(lines)


def contract_check(markdown: str, findings_doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    findings = findings_doc["findings"]
    headings = re.findall(r"^## Finding (F\d{3})$", markdown, flags=re.MULTILINE)
    expected = [f["finding_id"] for f in findings]
    if headings != expected:
        errors.append(f"finding headings {headings} differ from findings.json order {expected}")
    if NAVIGATION_NOTE not in markdown:
        errors.append("global navigation-anchor note missing")
    sections = re.split(r"^## Finding ", markdown, flags=re.MULTILINE)[1:]
    for f, body in zip(findings, sections):
        fid = f["finding_id"]
        for title in SECTION_TITLES:
            if title not in body:
                errors.append(f"{fid} lacks section {title}")
        if f"`Packet {f['where_to_look']['primary_go_to_packet']}`" not in body.split("### 觀察到什麼")[0]:
            errors.append(f"{fid} does not show its primary navigation anchor")
        for seg in f["what_was_observed"]["local_segments"]:
            for a in seg["anchors"]:
                if f"`Packet {a['packet']}`" not in body:
                    errors.append(f"{fid} omits anchor packet {a['packet']}")
        if "`UNKNOWN`" not in body.split("### 目前還不能確定")[-1]:
            errors.append(f"{fid} hides the UNKNOWN ground truth")
        trace = body.split("### 追溯")[-1]
        if f"`{fid}`" not in trace or f"`{f['group_id']}`" not in trace:
            errors.append(f"{fid} lacks traceability to findings.json")
    lowered = markdown.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            errors.append(f"forbidden phrase present: {phrase}")
    if "—" in markdown or "–" in markdown:
        errors.append("dash character present")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--trace-file-name", required=True)
    parser.add_argument("--trace-sha256")
    parser.add_argument("--tlp-count", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise G7Error(f"Refusing to overwrite existing report: {args.output}")
        raw = args.findings.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        markdown = render(doc, args.trace_file_name, args.trace_sha256, args.tlp_count, hashlib.sha256(raw).hexdigest().upper())
        errors = contract_check(markdown, doc)
        if errors:
            raise G7Error("report contract failed: " + "; ".join(errors))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, G7Error) as exc:
        print(f"G7 report not produced: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(markdown)
    print(json.dumps({"output": args.output.as_posix(), "findings": len(doc["findings"]), "contract_errors": 0,
                      "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest().upper()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
