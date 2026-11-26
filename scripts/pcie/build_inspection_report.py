#!/usr/bin/env python3
"""Build an offline single-trace PCIe inspection bundle from verified evidence."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "pcie.trace-inspection-observations/v1"
HEADER = "PCIE_D1_TLP_SPIKE_V1 cap=5 time=vendor_display_text"
DONE_MARKER = "------- D O N E !!! -------"
RECORD_RE = re.compile(
    r"^PCIE_D1_TLP\|(?P<index>\d+)\|(?P<time>[^|]+)\|(?P<family>[^|]+)\|"
    r"(?P<channel>[^|]+)\|(?P<type>0x[0-9A-Fa-f]+)\|(?P<width>\d+)$"
)
RUNTIME_ERROR_RE = re.compile(
    r"No channels found to be sent|No events found to be sent|runtime error|script error",
    re.IGNORECASE,
)


class InspectionError(ValueError):
    """Input evidence is missing, inconsistent, or outside this report's scope."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def format_mtime_utc(path: Path) -> str:
    nanoseconds = path.stat().st_mtime_ns
    seconds, fraction = divmod(nanoseconds, 1_000_000_000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    # Windows timestamps have 100 ns resolution; preserve the recorded 7 digits.
    return f"{stamp}.{fraction // 100:07d}Z"


def resolve_repo_file(repo_root: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise InspectionError(f"{label} is unavailable: {value}") from exc
    return resolved


def verify_file_identity(
    path: Path, expected_sha256: str, label: str, expected_size: int | None = None
) -> str:
    if not path.is_file():
        raise InspectionError(f"{label} is not a file: {path}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise InspectionError(f"{label} size differs from the evidence manifest")
    observed = sha256_file(path)
    if observed.casefold() != expected_sha256.casefold():
        raise InspectionError(f"{label} SHA-256 differs from the evidence manifest")
    return observed


def parse_vendor_log(text: str, expected_count: int = 5) -> list[dict[str, Any]]:
    lines = text.splitlines()
    if lines.count(HEADER) != 1:
        raise InspectionError("Expected exactly one recognized D1 projection header")
    if lines.count(DONE_MARKER) != 1:
        raise InspectionError("Expected exactly one normal VSE completion marker")
    if any(RUNTIME_ERROR_RE.search(line) for line in lines):
        raise InspectionError("The retained VSE output contains a runtime-error marker")

    records: list[dict[str, Any]] = []
    for line in lines:
        match = RECORD_RE.fullmatch(line)
        if not match:
            continue
        row = match.groupdict()
        if row["family"] != "TLP":
            raise InspectionError("The projection contains a non-TLP event family")
        try:
            width = int(row["width"])
            index = int(row["index"])
        except ValueError as exc:
            raise InspectionError("Invalid numeric field in VSE output") from exc
        if width < 1:
            raise InspectionError("Invalid link width in VSE output")
        records.append(
            {
                "packet_index": index,
                "event_family": row["family"],
                "vendor_channel": row["channel"].strip(),
                "vendor_type_code_hex": "0x" + row["type"][2:].upper(),
                "link_width": width,
                "extractor_time_display": row["time"].strip(),
            }
        )
    if len(records) != expected_count:
        raise InspectionError(
            f"Expected {expected_count} bounded TLP records; found {len(records)}"
        )
    indices = [row["packet_index"] for row in records]
    if len(set(indices)) != len(indices):
        raise InspectionError("Duplicate packet index in VSE output")
    return records


def seconds_as_display_millis(value: str) -> Decimal:
    cleaned = value.strip()
    if cleaned.lower().endswith("sec"):
        cleaned = cleaned[:-3].strip()
    try:
        return Decimal(cleaned).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise InspectionError(f"Unparseable time value: {value}") from exc


def build_observations(manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    trace_meta = manifest["source_trace"]
    trace_path = resolve_repo_file(repo_root, trace_meta["path"], "Source trace")
    if trace_path.name != trace_meta["file_name"]:
        raise InspectionError("Trace filename differs from the evidence manifest")
    if trace_path.stat().st_size != trace_meta["size_bytes"]:
        raise InspectionError("Trace size differs from the evidence manifest")
    if sha256_file(trace_path).casefold() != trace_meta["sha256"].casefold():
        raise InspectionError("Trace SHA-256 differs from the evidence manifest")
    if format_mtime_utc(trace_path) != trace_meta["last_write_utc"]:
        raise InspectionError("Trace UTC modification time differs from the evidence manifest")

    software = manifest["software"]
    executable = resolve_repo_file(repo_root, software["executable_path"], "PETracer executable")
    executable_hash = verify_file_identity(
        executable, software["executable_sha256"], "PETracer executable"
    )
    extractor_meta = manifest["extractor"]
    extractor_path = resolve_repo_file(repo_root, extractor_meta["script_path"], "VSE extractor")
    extractor_hash = verify_file_identity(
        extractor_path, extractor_meta["script_sha256"], "VSE extractor"
    )
    execution = manifest["execution"]
    log_path = resolve_repo_file(repo_root, execution["output_log_path"], "VSE output log")
    log_hash = verify_file_identity(log_path, execution["output_log_sha256"], "VSE output log")
    log_text = log_path.read_text(encoding="utf-8-sig")
    records = parse_vendor_log(log_text, expected_count=extractor_meta["record_cap"])
    if log_text.count(execution["completion_marker"]) != 1:
        raise InspectionError("Manifest completion marker does not match the retained log")

    gui_meta = manifest["gui_crosscheck"]
    gui_path = resolve_repo_file(repo_root, gui_meta["image_path"], "GUI cross-check image")
    gui_hash = verify_file_identity(gui_path, gui_meta["image_sha256"], "GUI cross-check image")
    gui_rows = gui_meta["rows"]
    if len(gui_rows) != len(records):
        raise InspectionError("GUI cross-check row count differs from the extracted projection")

    joined: list[dict[str, Any]] = []
    for record, gui in zip(records, gui_rows, strict=True):
        if record["packet_index"] != gui["packet_index"]:
            raise InspectionError("GUI packet index does not match the VSE output order")
        if record["vendor_type_code_hex"].casefold() != gui["vendor_type_code_hex"].casefold():
            raise InspectionError(f"GUI type-code cross-check differs at {record['packet_index']}")
        if record["link_width"] != gui["link_width"]:
            raise InspectionError(f"GUI link-width cross-check differs at {record['packet_index']}")
        api_time = seconds_as_display_millis(record["extractor_time_display"])
        gui_time = seconds_as_display_millis(gui["time_seconds"])
        if api_time != gui_time:
            raise InspectionError(f"GUI rounded-time cross-check differs at {record['packet_index']}")
        joined.append(
            {
                **record,
                "gui_crosscheck": {
                    "status": "MATCHED",
                    "family": gui["family"],
                    "subtype": gui["subtype"],
                    "time_seconds": gui["time_seconds"],
                    "link_width": gui["link_width"],
                },
            }
        )

    context = gui_meta
    observed_indices = {row["packet_index"] for row in joined}
    if not observed_indices.issubset(set(context["visible_packet_indices"])):
        raise InspectionError("GUI context does not include every cross-checked record")
    if not set(context["intervening_non_extracted_indices"]).issubset(
        set(context["visible_packet_indices"])
    ):
        raise InspectionError("GUI context contains an index not visible in the evidence image")

    repo_relative = lambda value: Path(value).as_posix()
    return {
        "schema_version": SCHEMA_VERSION,
        "report_kind": "SINGLE_TRACE_INSPECTION",
        "report_date": manifest["report_date"],
        "trace": {
            "file_name": trace_path.name,
            "source_path": str(trace_path),
            "size_bytes": trace_path.stat().st_size,
            "sha256": sha256_file(trace_path),
            "last_write_utc": format_mtime_utc(trace_path),
            "ground_truth": "UNKNOWN",
        },
        "software": {
            "product": software["product"],
            "version": software["version"],
            "executable_path": str(executable),
            "executable_sha256": executable_hash,
        },
        "extractor": {
            "script_path": repo_relative(extractor_meta["script_path"]),
            "script_sha256": extractor_hash,
            "scope": extractor_meta["scope"],
            "record_cap": extractor_meta["record_cap"],
            "fields": extractor_meta["fields"],
            "time_representation": extractor_meta["time_representation"],
        },
        "status": {
            "extraction": "PASS_BOUNDED",
            "ground_truth": "UNKNOWN",
            "diagnostic_result": "NOT_EVALUATED",
            "coverage": "FIRST_FIVE_TLP_RECORDS_ONLY",
        },
        "evidence": {
            "extractor_log_path": repo_relative(execution["output_log_path"]),
            "extractor_log_sha256": log_hash,
            "gui_image_path": repo_relative(gui_meta["image_path"]),
            "gui_image_sha256": gui_hash,
            "gui_rows_checked": len(joined),
        },
        "observations": joined,
        "gui_context": {
            "visible_packet_indices": context["visible_packet_indices"],
            "intervening_non_extracted_indices": context["intervening_non_extracted_indices"],
            "next_tlp_visible_beyond_cap": context["next_tlp_visible_beyond_cap"],
            "interpretation": (
                "GUI screenshot context only. Intervening packet indices and the next visible TLP "
                "were not added to the bounded extractor output."
            ),
        },
        "limitations": [
            "This is a single-trace inspection report, not PASS/FAIL triage.",
            "Ground truth is UNKNOWN; diagnostic result is NOT EVALUATED.",
            "Only the first five TLP callbacks emitted by this bounded script are represented; this is not full-trace coverage or a total TLP count.",
            "Extractor time is coarse vendor display text. More precise values shown are separate GUI cross-check observations.",
            "The extractor reports the vendor channel label Downstream; physical endpoint mapping is not established.",
            "No TLP payload, request/completion semantics, suspicious region, or root cause was analyzed.",
            "The GUI Errors detected! indicator is not interpreted as a device PASS/FAIL result.",
            "The source capture remains external to this report bundle; its identity is bound by size, modification time, and SHA-256.",
        ],
    }


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def relative_url(repo_root: Path, output_dir: Path, repo_path: str) -> str:
    target = repo_root / Path(repo_path)
    return Path(os.path.relpath(target, output_dir)).as_posix()


def render_markdown(data: dict[str, Any], log_url: str, gui_url: str) -> str:
    trace = data["trace"]
    rows = []
    technical_rows = []
    for item in data["observations"]:
        gui = item["gui_crosscheck"]
        rows.append(
            "| {index} | {name} | {gui_time} | {api_time} |".format(
                index=item["packet_index"],
                name=markdown_escape(f"{gui['family']} / {gui['subtype']}"),
                gui_time=markdown_escape(gui["time_seconds"]),
                api_time=markdown_escape(item["extractor_time_display"]),
            )
        )
        technical_rows.append(
            "| {index} | {code} | {channel} | x{width} |".format(
                index=item["packet_index"],
                code=markdown_escape(item["vendor_type_code_hex"]),
                channel=markdown_escape(item["vendor_channel"]),
                width=item["link_width"],
            )
        )
    context = data["gui_context"]
    visible = ", ".join(str(index) for index in context["visible_packet_indices"])
    interleaved = ", ".join(str(index) for index in context["intervening_non_extracted_indices"])
    count = len(data["observations"])
    fields = ", ".join(f"`{markdown_escape(field)}`" for field in data["extractor"]["fields"])
    return f"""# PCIe Trace 檢視報告

## 先看重點

這份報告檢查 PCIe 擷取檔（trace）`{markdown_escape(trace['file_name'])}`：只讀取工具輸出的前 {count} 筆 TLP（PCIe 封包），再抽樣與 LeCroy 畫面核對。

- **讀到了什麼：** {count} 筆資料；這只是前五筆，不是整份 trace 的統計。
- **畫面核對：** {data['evidence']['gui_rows_checked']} 筆都能依封包編號及顯示內容，在 LeCroy GUI 找到相符資料。
- **測試結果：** 不知道這份 trace 對應的測試是正常或異常；本報告沒有做故障判斷。

> **簡單說：** 這證明目前工具能讀出並核對這幾筆資料，不代表裝置測試 PASS，也不代表已找出問題。

## 封包清單

| 封包編號 | LeCroy 顯示名稱 | LeCroy 畫面時間 | 工具讀取時間 |
| ---: | --- | ---: | ---: |
{chr(10).join(rows)}

封包編號可用來在 LeCroy 中找到該列。LeCroy 畫面時間比工具輸出的時間精確；工具時間只顯示到千分之一秒（1 毫秒），因此五筆都顯示 `4.848 sec`，**不代表它們發生在同一個時間點**。

## 回看證據

- [先看 LeCroy 畫面核對]({gui_url})：可依上方封包編號找到對應資料。
- [查看工具原始輸出]({log_url})：核對工具實際印出的五筆資料。
- [查看資料底稿](observations.json)：機器可讀的記錄與來源身份。

## 本報告沒有判斷的事

- 哪份測試是 PASS 或 FAIL、裝置是否正常、或故障原因。
- 整份 trace 有多少 TLP；目前只處理工具輸出的前五筆。
- 封包 payload、request/completion 關係或可疑區段。
- LeCroy 的 `Errors detected!` 指示器不等同產品測試結果。

## 技術附錄（需要重現或核對身份時再看）

### Trace 與軟體身份

| 項目 | 值 |
| --- | --- |
| Trace 原始檔 | `{markdown_escape(trace['file_name'])}` |
| 本機來源路徑 | `{markdown_escape(trace['source_path'])}` |
| 檔案大小 | {trace['size_bytes']:,} bytes |
| Trace SHA-256 | `{trace['sha256']}` |
| Trace 最後修改時間 (UTC) | `{trace['last_write_utc']}` |
| 分析軟體 | {markdown_escape(data['software']['product'])} {markdown_escape(data['software']['version'])} |
| PETracer SHA-256 | `{data['software']['executable_sha256']}` |
| VSE script | `{markdown_escape(data['extractor']['script_path'])}` |
| Script SHA-256 | `{data['extractor']['script_sha256']}` |

### 原始欄位與核對方式

| 封包編號 | VSE 原始類型碼 | VSE channel 標籤 | Link width |
| ---: | --- | --- | ---: |
{chr(10).join(technical_rows)}

- 工具實際輸出欄位：{fields}
- 工具時間來源：{markdown_escape(data['extractor']['time_representation'])}
- GUI 另顯示封包編號 {visible}；其中 {interleaved} 是畫面上可見、但不在工具五筆輸出中的封包。下一筆畫面可見 TLP 是 {context['next_tlp_visible_beyond_cap']}，只作畫面脈絡。
- VSE 原始輸出 SHA-256：`{data['evidence']['extractor_log_sha256']}`
- GUI 截圖 SHA-256：`{data['evidence']['gui_image_sha256']}`
- 機器狀態碼：`{data['status']['extraction']}` / ground truth `{data['status']['ground_truth']}` / diagnostic `{data['status']['diagnostic_result']}` / coverage `{data['status']['coverage']}`
- Schema：`{data['schema_version']}`。這是單 trace 檢視資料，不是 finding contract、PCIe normalized event model 或 USB/PCIe 共用 schema。
"""


def render_html(data: dict[str, Any], log_url: str, gui_url: str) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    trace = data["trace"]
    rows = []
    technical_rows = []
    for item in data["observations"]:
        gui = item["gui_crosscheck"]
        rows.append(
            "<tr><td><code>{}</code></td><td>{} / {}</td><td>{}</td><td>{}</td></tr>".format(
                item["packet_index"], esc(gui["family"]), esc(gui["subtype"]),
                esc(gui["time_seconds"]), esc(item["extractor_time_display"]),
            )
        )
        technical_rows.append(
            "<tr><td>{}</td><td><code>{}</code></td><td>{}</td><td>x{}</td></tr>".format(
                item["packet_index"], esc(item["vendor_type_code_hex"]),
                esc(item["vendor_channel"]), item["link_width"],
            )
        )
    limits = "".join(f"<li>{esc(item)}</li>" for item in data["limitations"])
    context = data["gui_context"]
    visible = ", ".join(str(index) for index in context["visible_packet_indices"])
    interleaved = ", ".join(str(index) for index in context["intervening_non_extracted_indices"])
    fields = " ".join(f"<code>{esc(field)}</code>" for field in data["extractor"]["fields"])
    count = len(data["observations"])
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline';">
<title>PCIe Trace 檢視報告 — {esc(trace['file_name'])}</title>
<style>
:root {{ color-scheme: light; --ink:#172b3a; --muted:#536777; --line:#d7e0e7; --paper:#fff; --wash:#f2f6f8; --accent:#24516b; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--wash); color:var(--ink); font:16px/1.55 "Segoe UI", "Noto Sans TC", sans-serif; }}
main {{ max-width:1040px; margin:0 auto; padding:30px 20px 52px; }} h1 {{ margin:0 0 6px; font-size:2rem; }} h2 {{ margin:0 0 14px; font-size:1.25rem; }} h3 {{ margin:18px 0 8px; font-size:1.05rem; }} p {{ margin:8px 0; }}
.intro {{ color:var(--muted); margin:0 0 20px; }} section {{ background:var(--paper); border:1px solid var(--line); padding:22px; margin:16px 0; }}
.summary-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:16px 0; }} .summary-card {{ border:1px solid var(--line); background:var(--paper); padding:13px; }} .summary-card span {{ display:block; color:var(--muted); font-size:.88rem; }} .summary-card strong {{ display:block; margin-top:4px; }}
.plain-note {{ background:var(--wash); border-left:4px solid var(--accent); padding:12px 15px; margin:12px 0; }} .table-wrap {{ overflow-x:auto; }} table {{ width:100%; border-collapse:collapse; min-width:600px; }} th,td {{ border-bottom:1px solid var(--line); text-align:left; padding:10px 9px; vertical-align:top; }} th {{ color:var(--muted); font-size:.9rem; }}
.glossary {{ display:grid; grid-template-columns:190px 1fr; gap:7px 14px; }} .term {{ color:var(--muted); }} code {{ overflow-wrap:anywhere; font:.92em/1.45 Consolas,monospace; }} ul,ol {{ padding-left:22px; }} li {{ margin:7px 0; }} a {{ color:var(--accent); }} img {{ display:block; width:100%; height:auto; border:1px solid var(--line); }} details {{ margin-top:12px; border-top:1px solid var(--line); padding-top:12px; }} summary {{ cursor:pointer; color:var(--accent); font-weight:600; }} footer {{ color:var(--muted); font-size:.9rem; margin-top:20px; }}
@media(max-width:760px) {{ main {{ padding:18px 12px 34px; }} .summary-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} section {{ padding:16px; }} .glossary {{ grid-template-columns:1fr; gap:2px; }} .term:not(:first-child) {{ margin-top:9px; }} }}
</style>
</head>
<body><main>
<header><h1>PCIe Trace 檢視報告</h1><p class="intro">{esc(trace['file_name'])}。先看摘要即可理解本報告結果；檔案與程式身份資料放在頁面下方。</p></header>
<section><h2>先看重點</h2>
<p><strong>這份報告檢查什麼？</strong>從 PCIe 擷取檔（trace）讀出前 {count} 筆 TLP（PCIe 封包），再抽樣與 LeCroy 畫面核對。</p>
<div class="summary-grid">
<div class="summary-card"><span>讀到資料</span><strong>{count} 筆（僅前五筆）</strong></div>
<div class="summary-card"><span>畫面核對</span><strong>{data['evidence']['gui_rows_checked']} / {count} 筆相符</strong></div>
<div class="summary-card"><span>測試正常或異常</span><strong>未知</strong></div>
<div class="summary-card"><span>故障判斷</span><strong>未進行</strong></div>
</div>
<p class="plain-note"><strong>簡單說：</strong>工具讀到並核對了這幾筆資料；這不代表裝置測試 PASS，也不代表已找出問題。整份 trace 尚未分析。</p>
</section>
<section><h2>封包清單</h2>
<div class="glossary"><div class="term">封包編號</div><div>用這個編號在 LeCroy 畫面找到同一筆資料。</div>
<div class="term">LeCroy 顯示名稱</div><div>分析軟體對封包顯示的名稱。</div>
<div class="term">兩種時間</div><div>LeCroy 時間較精確；工具時間只到千分之一秒（1 毫秒），因此五筆都顯示 4.848 秒，不代表它們同時發生。</div></div>
<div class="table-wrap"><table><thead><tr><th>封包編號</th><th>LeCroy 顯示名稱</th><th>LeCroy 畫面時間</th><th>工具讀取時間</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</section>
<section><h2>回看證據</h2><ol>
<li><a href="{esc(gui_url)}">先看 LeCroy 畫面核對</a>：可用上方封包編號定位。</li>
<li><a href="{esc(log_url)}">看工具原始輸出</a>：確認工具實際列出的資料。</li>
<li><a href="observations.json">看資料底稿（JSON）</a>：供程式或追查身份使用。</li>
</ol><details><summary>展開 LeCroy 核對畫面</summary><p><img src="{esc(gui_url)}" alt="LeCroy 畫面中與工具輸出核對的五筆 TLP"></p></details></section>
<section><h2>本報告沒有判斷的事</h2><ul>
<li>這份 trace 對應的裝置測試是 PASS 還是 FAIL。</li><li>整份 trace 的封包總數；目前只讀取前五筆。</li>
<li>封包內容、可疑區段或故障原因。</li><li>LeCroy 的「Errors detected!」提示不等同產品測試結果。</li>
</ul></section>
<section><details><summary>技術附錄：檔案、軟體與原始欄位（需要重現或追查時再展開）</summary>
<h3>Trace 與軟體身份</h3><div class="glossary">
<div class="term">Trace 原始檔</div><div>{esc(trace['file_name'])}</div><div class="term">本機來源路徑</div><div><code>{esc(trace['source_path'])}</code></div>
<div class="term">檔案大小</div><div>{trace['size_bytes']:,} bytes</div><div class="term">Trace SHA-256</div><div><code>{esc(trace['sha256'])}</code></div>
<div class="term">最後修改時間 (UTC)</div><div><code>{esc(trace['last_write_utc'])}</code></div><div class="term">分析軟體</div><div>{esc(data['software']['product'])} {esc(data['software']['version'])}</div>
<div class="term">PETracer SHA-256</div><div><code>{esc(data['software']['executable_sha256'])}</code></div><div class="term">VSE script</div><div><code>{esc(data['extractor']['script_path'])}</code></div>
<div class="term">Script SHA-256</div><div><code>{esc(data['extractor']['script_sha256'])}</code></div><div class="term">工具範圍</div><div>{esc(data['extractor']['scope'])}</div>
<div class="term">實際輸出欄位</div><div>{fields}</div><div class="term">工具時間來源</div><div>{esc(data['extractor']['time_representation'])}</div>
</div>
<h3>VSE 原始值</h3><div class="table-wrap"><table><thead><tr><th>封包編號</th><th>原始類型碼</th><th>Channel 標籤</th><th>Link width</th></tr></thead><tbody>{''.join(technical_rows)}</tbody></table></div>
<p>這些是工具與分析軟體提供的技術欄位，不表示嚴重度或錯誤分類。</p>
<p>畫面可見的封包編號：{esc(visible)}。其中 {esc(interleaved)} 沒有出現在這支工具的五筆輸出中。下一筆畫面可見 TLP 是 {context['next_tlp_visible_beyond_cap']}，只作畫面脈絡。</p>
<ul><li>VSE 原始輸出 SHA-256：<code>{esc(data['evidence']['extractor_log_sha256'])}</code></li><li>GUI 截圖 SHA-256：<code>{esc(data['evidence']['gui_image_sha256'])}</code></li>
<li>機器狀態碼：<code>{esc(data['status']['extraction'])}</code>；ground truth <code>{esc(data['status']['ground_truth'])}</code>；diagnostic <code>{esc(data['status']['diagnostic_result'])}</code>；coverage <code>{esc(data['status']['coverage'])}</code>。</li>
</ul><p>Schema {esc(data['schema_version'])}。這是單 trace 檢視資料，不是 PCIe finding contract、normalized event model 或 USB/PCIe 共用 schema。</p>
<h3>來源中記錄的限制</h3><ul>{limits}</ul>
</details></section>
<footer>本頁呈現資料讀取與 GUI 抽樣核對，不代表完整 trace 分析，也不提供裝置 PASS/FAIL 或故障診斷。</footer>
</main></body></html>
"""


def build_bundle(manifest_path: Path, output_dir: Path, repo_root: Path = REPO_ROOT) -> tuple[Path, Path, Path]:
    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve(strict=True)
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(repo_root)
    except ValueError as exc:
        raise InspectionError("Report output must stay inside the repository") from exc
    if output_dir.exists():
        raise InspectionError(f"Refusing to overwrite existing report directory: {output_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InspectionError(f"Cannot read evidence manifest: {manifest_path}") from exc
    data = build_observations(manifest, repo_root)
    log_url = relative_url(repo_root, output_dir, data["evidence"]["extractor_log_path"])
    gui_url = relative_url(repo_root, output_dir, data["evidence"]["gui_image_path"])
    output_dir.mkdir(parents=True, exist_ok=False)
    json_path = output_dir / "observations.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Reload JSON so both renderers consume exactly the saved structured source.
    saved_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown_path = output_dir / "report.md"
    html_path = output_dir / "report.html"
    markdown_path.write_text(render_markdown(saved_data, log_url, gui_url), encoding="utf-8")
    html_path.write_text(render_html(saved_data, log_url, gui_url), encoding="utf-8")
    return json_path, markdown_path, html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="Evidence identity/cross-check JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="New report directory inside the repository")
    args = parser.parse_args(argv)
    try:
        paths = build_bundle(args.manifest, args.output_dir)
    except (InspectionError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"inspection report not generated: {exc}", file=sys.stderr)
        return 2
    for path in paths:
        print(path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
