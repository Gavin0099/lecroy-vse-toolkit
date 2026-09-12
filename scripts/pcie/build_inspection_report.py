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
    status = data["status"]
    rows = []
    for item in data["observations"]:
        gui = item["gui_crosscheck"]
        rows.append(
            "| {index} | {api_time} | {code} | {channel} | x{width} | {family} / {subtype} | {gui_time} |".format(
                index=item["packet_index"],
                api_time=markdown_escape(item["extractor_time_display"]),
                code=markdown_escape(item["vendor_type_code_hex"]),
                channel=markdown_escape(item["vendor_channel"]),
                width=item["link_width"],
                family=markdown_escape(gui["family"]),
                subtype=markdown_escape(gui["subtype"]),
                gui_time=markdown_escape(gui["time_seconds"]),
            )
        )
    limits = "\n".join(f"- {markdown_escape(item)}" for item in data["limitations"])
    context = data["gui_context"]
    visible = ", ".join(str(index) for index in context["visible_packet_indices"])
    interleaved = ", ".join(str(index) for index in context["intervening_non_extracted_indices"])
    return f"""# PCIe Trace Inspection

單一 trace 的有限範圍檢視。這份報告不判斷正常／異常，也不提出故障原因。

| 狀態 | 值 |
| --- | --- |
| Extraction | **PASS — bounded first five TLP records** |
| Ground truth | **{status['ground_truth']}** |
| Diagnostic result | **{status['diagnostic_result']}** |
| Coverage | **{status['coverage']}** |

## Trace identity

| 欄位 | 值 |
| --- | --- |
| File | `{markdown_escape(trace['file_name'])}` |
| Local source path | `{markdown_escape(trace['source_path'])}` |
| Size | {trace['size_bytes']:,} bytes |
| SHA-256 | `{trace['sha256']}` |
| Last write (UTC) | `{trace['last_write_utc']}` |

## Runtime and extraction scope

- Software: {markdown_escape(data['software']['product'])} {markdown_escape(data['software']['version'])}
- Executable SHA-256: `{data['software']['executable_sha256']}`
- VSE script: `{markdown_escape(data['extractor']['script_path'])}`
- Script SHA-256: `{data['extractor']['script_sha256']}`
- Scope: {markdown_escape(data['extractor']['scope'])}
- Fields actually emitted: {', '.join(f'`{markdown_escape(field)}`' for field in data['extractor']['fields'])}
- Time source: {markdown_escape(data['extractor']['time_representation'])}

## Extracted TLP observations

API display time and GUI timestamp are separate measurements. The GUI column is a cross-check observation, not a higher-precision value emitted by the VSE script.

| Packet index | Extractor time | Raw vendor type | Vendor channel | Width | GUI family / subtype | GUI time (sec) |
| ---: | --- | --- | --- | ---: | --- | ---: |
{chr(10).join(rows)}

Five of five emitted records matched the GUI sample by packet index, raw vendor type, displayed-time rounding, and link width. The visible GUI sequence covers indices {visible}; intervening non-extracted packet indices are {interleaved}. The next TLP visible beyond the script cap is {context['next_tlp_visible_beyond_cap']}; it is context only and is not included in the extraction result.

## Evidence

- [Original VSE extraction output]({log_url}) — SHA-256 `{data['evidence']['extractor_log_sha256']}`
- [LeCroy GUI cross-check]({gui_url}) — SHA-256 `{data['evidence']['gui_image_sha256']}`
- Structured observations: `observations.json`

## Limitations

{limits}

Schema: `{data['schema_version']}`. This inspection-only observation document is not the later F1 finding contract, a normalized PCIe event model, or a USB/PCIe shared schema.
"""


def render_html(data: dict[str, Any], log_url: str, gui_url: str) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    trace = data["trace"]
    rows = []
    for item in data["observations"]:
        gui = item["gui_crosscheck"]
        rows.append(
            "<tr><td>{}</td><td>{}</td><td><code>{}</code></td><td>{}</td>"
            "<td>x{}</td><td>{} / {}</td><td>{}</td></tr>".format(
                item["packet_index"], esc(item["extractor_time_display"]),
                esc(item["vendor_type_code_hex"]), esc(item["vendor_channel"]),
                item["link_width"], esc(gui["family"]), esc(gui["subtype"]),
                esc(gui["time_seconds"]),
            )
        )
    limits = "".join(f"<li>{esc(item)}</li>" for item in data["limitations"])
    context = data["gui_context"]
    visible = ", ".join(str(index) for index in context["visible_packet_indices"])
    interleaved = ", ".join(str(index) for index in context["intervening_non_extracted_indices"])
    fields = " ".join(f"<code>{esc(field)}</code>" for field in data["extractor"]["fields"])
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline';">
<title>PCIe Trace Inspection — {esc(trace['file_name'])}</title>
<style>
:root {{ color-scheme: light; --ink:#172b3a; --muted:#536777; --line:#d7e0e7; --paper:#fff; --wash:#f2f6f8; --accent:#24516b; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--wash); color:var(--ink); font:16px/1.55 "Segoe UI", "Noto Sans TC", sans-serif; }}
main {{ max-width:1120px; margin:0 auto; padding:32px 22px 56px; }} h1 {{ margin:0 0 6px; font-size:2rem; }} h2 {{ margin:0 0 16px; font-size:1.25rem; }} p {{ margin:8px 0; }}
.intro {{ color:var(--muted); margin:0 0 22px; }} .status-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:18px 0 24px; }}
.status {{ border:1px solid var(--line); border-left:4px solid var(--accent); background:var(--paper); padding:14px 16px; }} .status span {{ display:block; color:var(--muted); font-size:.88rem; }} .status strong {{ display:block; margin-top:3px; }}
section {{ background:var(--paper); border:1px solid var(--line); padding:22px; margin:16px 0; }} .grid {{ display:grid; grid-template-columns:190px 1fr; gap:8px 16px; }} .label {{ color:var(--muted); }} code {{ overflow-wrap:anywhere; font: .92em/1.45 Consolas, monospace; }}
.table-wrap {{ overflow-x:auto; }} table {{ width:100%; border-collapse:collapse; min-width:850px; }} th,td {{ border-bottom:1px solid var(--line); text-align:left; padding:10px 9px; vertical-align:top; }} th {{ color:var(--muted); font-size:.9rem; }}
.note {{ background:var(--wash); border-left:3px solid var(--line); padding:12px 14px; }} ul {{ padding-left:22px; }} li {{ margin:7px 0; }} a {{ color:var(--accent); }} img {{ display:block; width:100%; height:auto; border:1px solid var(--line); }} details {{ margin-top:14px; }} summary {{ cursor:pointer; color:var(--accent); }} footer {{ color:var(--muted); font-size:.9rem; margin-top:20px; }}
@media(max-width:700px) {{ main {{ padding:20px 12px 36px; }} .status-grid {{ grid-template-columns:1fr; }} section {{ padding:16px; }} .grid {{ grid-template-columns:1fr; gap:2px; }} .label:not(:first-child) {{ margin-top:10px; }} }}
</style>
</head>
<body><main>
<header><h1>PCIe Trace Inspection</h1><p class="intro">單一 trace 的有限範圍檢視。報告呈現可回查的封包觀察，不判斷正常／異常，也不推測故障原因。</p></header>
<div class="status-grid">
<div class="status"><span>Extraction</span><strong>PASS — 前五筆 TLP 範圍</strong></div>
<div class="status"><span>Ground truth</span><strong>{esc(data['status']['ground_truth'])}</strong></div>
<div class="status"><span>Diagnostic result</span><strong>{esc(data['status']['diagnostic_result'])}</strong></div>
</div>
<section><h2>Trace identity</h2><div class="grid">
<div class="label">檔案</div><div>{esc(trace['file_name'])}</div>
<div class="label">本機來源路徑</div><div><code>{esc(trace['source_path'])}</code></div>
<div class="label">大小</div><div>{trace['size_bytes']:,} bytes</div>
<div class="label">SHA-256</div><div><code>{esc(trace['sha256'])}</code></div>
<div class="label">最後修改時間 (UTC)</div><div><code>{esc(trace['last_write_utc'])}</code></div>
</div></section>
<section><h2>Runtime and extraction scope</h2><div class="grid">
<div class="label">分析軟體</div><div>{esc(data['software']['product'])} {esc(data['software']['version'])}</div>
<div class="label">Executable SHA-256</div><div><code>{esc(data['software']['executable_sha256'])}</code></div>
<div class="label">VSE script</div><div><code>{esc(data['extractor']['script_path'])}</code></div>
<div class="label">Script SHA-256</div><div><code>{esc(data['extractor']['script_sha256'])}</code></div>
<div class="label">範圍</div><div>{esc(data['extractor']['scope'])}</div>
<div class="label">實際輸出欄位</div><div>{fields}</div>
<div class="label">時間來源</div><div>{esc(data['extractor']['time_representation'])}</div>
</div></section>
<section><h2>Extracted TLP observations</h2><p class="note">Extractor 輸出的顯示時間與 GUI 時間分欄呈現。GUI 時間只作核對，並非 VSE script 輸出的高精度時間。</p>
<div class="table-wrap"><table><thead><tr><th>Packet index</th><th>Extractor time</th><th>Raw vendor type</th><th>Vendor channel</th><th>Width</th><th>GUI family / subtype</th><th>GUI time (sec)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>五筆輸出均依 packet index、raw vendor type、顯示時間四捨五入值及 link width 與 GUI 抽樣相符。GUI 畫面顯示的封包 index 範圍為 {esc(visible)}；其中未輸出的插入封包 index 為 {esc(interleaved)}。下一筆可見 TLP 是 {context['next_tlp_visible_beyond_cap']}，位於 script 上限之外，只作畫面脈絡。</p>
</section>
<section><h2>Evidence</h2><ul>
<li><a href="{esc(log_url)}">原始 VSE extraction output</a> — SHA-256 <code>{esc(data['evidence']['extractor_log_sha256'])}</code></li>
<li><a href="{esc(gui_url)}">LeCroy GUI cross-check</a> — SHA-256 <code>{esc(data['evidence']['gui_image_sha256'])}</code></li>
<li><a href="observations.json">Structured observations</a></li>
</ul><details><summary>查看 GUI cross-check 畫面</summary><p><img src="{esc(gui_url)}" alt="LeCroy GUI showing the five TLP packets checked against the extractor output"></p></details></section>
<section><h2>Limitations</h2><ul>{limits}</ul></section>
<footer>Schema {esc(data['schema_version'])}. 此 inspection observation 僅供單 trace 檢視，並非 F1 finding contract、PCIe normalized event model 或 USB/PCIe 共用 schema。</footer>
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
