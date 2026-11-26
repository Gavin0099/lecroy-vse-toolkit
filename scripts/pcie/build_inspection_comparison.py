#!/usr/bin/env python3
"""Render a bounded, descriptive comparison of two PCIe inspection JSON files."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "pcie.trace-inspection-observations/v1"
REPORT_KIND = "SINGLE_TRACE_INSPECTION"
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
TYPE_CODE_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
EXPECTED_COVERAGE = "FIRST_FIVE_TLP_RECORDS_ONLY"
PAGE_TITLE = "PCIe Trace Inspection Comparison"
SAMPLE_BOUNDARY_NOTE = (
    "Counts below describe only the bounded five-TLP observation samples. "
    "They are not full-trace statistics."
)
# Filename tokens that read like a test outcome. They are surfaced only as hints.
OUTCOME_HINT_TOKENS = frozenset({"pass", "passed", "fail", "failed", "hang", "good", "bad", "ng"})


class ComparisonError(ValueError):
    """Comparison inputs are invalid or exceed the bounded report contract."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ComparisonError(f"{label} must be an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonError(f"{label} must be a non-empty string")
    return value


def _sha256(value: Any, label: str) -> str:
    text = _text(value, label)
    if not SHA256_RE.fullmatch(text):
        raise ComparisonError(f"{label} must be a 64-digit SHA-256")
    return text.upper()


def _normalize_type_code(value: str) -> str:
    return "0x" + value[2:].upper()


def filename_outcome_hints(file_name: str) -> list[str]:
    """Return outcome-like filename tokens in original spelling; never a verdict."""
    hints: list[str] = []
    for token in re.split(r"[^0-9A-Za-z]+", Path(file_name).stem):
        if token.casefold() in OUTCOME_HINT_TOKENS and token not in hints:
            hints.append(token)
    return hints


def _sample_shape(data: dict[str, Any]) -> dict[str, Any]:
    """Describe one trace's own five-row sample; nothing here aligns it with the other trace."""
    rows = data["observations"]
    indices = [row["packet_index"] for row in rows]
    return {
        "type_sequence": [_normalize_type_code(row["vendor_type_code_hex"]) for row in rows],
        "gui_subtype_sequence": [row["gui_crosscheck"]["subtype"] for row in rows],
        "index_gaps": [later - earlier for earlier, later in zip(indices, indices[1:])],
        "channels": sorted({row["vendor_channel"] for row in rows}),
        "link_widths": sorted({row["link_width"] for row in rows}),
        "filename_hints": filename_outcome_hints(data["trace"]["file_name"]),
    }


def validate_observation(data: Any, label: str) -> dict[str, Any]:
    """Accept only a completed F0 first-five-TLP inspection, not arbitrary JSON."""
    root = _mapping(data, label)
    if root.get("schema_version") != SCHEMA_VERSION:
        raise ComparisonError(f"{label} is not {SCHEMA_VERSION}")
    if root.get("report_kind") != REPORT_KIND:
        raise ComparisonError(f"{label} is not a single-trace inspection")
    _text(root.get("report_date"), f"{label}.report_date")

    trace = _mapping(root.get("trace"), f"{label}.trace")
    _text(trace.get("file_name"), f"{label}.trace.file_name")
    _text(trace.get("source_path"), f"{label}.trace.source_path")
    if type(trace.get("size_bytes")) is not int or trace["size_bytes"] <= 0:
        raise ComparisonError(f"{label}.trace.size_bytes must be a positive integer")
    _sha256(trace.get("sha256"), f"{label}.trace.sha256")
    _text(trace.get("last_write_utc"), f"{label}.trace.last_write_utc")
    if trace.get("ground_truth") != "UNKNOWN":
        raise ComparisonError(f"{label} must retain UNKNOWN ground truth")

    software = _mapping(root.get("software"), f"{label}.software")
    for key in ("product", "version", "executable_path"):
        _text(software.get(key), f"{label}.software.{key}")
    _sha256(software.get("executable_sha256"), f"{label}.software.executable_sha256")

    extractor = _mapping(root.get("extractor"), f"{label}.extractor")
    for key in ("script_path", "scope", "time_representation"):
        _text(extractor.get(key), f"{label}.extractor.{key}")
    _sha256(extractor.get("script_sha256"), f"{label}.extractor.script_sha256")
    if extractor.get("record_cap") != 5:
        raise ComparisonError(f"{label} is outside the five-record extractor scope")
    fields = extractor.get("fields")
    if not isinstance(fields, list) or not fields or any(not isinstance(item, str) for item in fields):
        raise ComparisonError(f"{label}.extractor.fields must be a non-empty string list")

    status = _mapping(root.get("status"), f"{label}.status")
    if status != {
        "extraction": "PASS_BOUNDED",
        "ground_truth": "UNKNOWN",
        "diagnostic_result": "NOT_EVALUATED",
        "coverage": EXPECTED_COVERAGE,
    }:
        raise ComparisonError(f"{label} must be a completed bounded extraction with no diagnostic verdict")

    evidence = _mapping(root.get("evidence"), f"{label}.evidence")
    for key in ("extractor_log_path", "gui_image_path"):
        _text(evidence.get(key), f"{label}.evidence.{key}")
    for key in ("extractor_log_sha256", "gui_image_sha256"):
        _sha256(evidence.get(key), f"{label}.evidence.{key}")
    if type(evidence.get("gui_rows_checked")) is not int or evidence["gui_rows_checked"] != 5:
        raise ComparisonError(f"{label} must have five GUI-cross-checked rows")

    rows = root.get("observations")
    if not isinstance(rows, list) or len(rows) != 5:
        raise ComparisonError(f"{label} must contain exactly five observations")
    observed_indices: list[int] = []
    for index, raw_row in enumerate(rows, start=1):
        row = _mapping(raw_row, f"{label}.observations[{index}]")
        if type(row.get("packet_index")) is not int or row["packet_index"] < 0:
            raise ComparisonError(f"{label} observation {index} has an invalid packet index")
        observed_indices.append(row["packet_index"])
        if row.get("event_family") != "TLP":
            raise ComparisonError(f"{label} observation {index} is not a TLP")
        _text(row.get("vendor_channel"), f"{label} observation {index} channel")
        type_code = _text(row.get("vendor_type_code_hex"), f"{label} observation {index} type code")
        if not TYPE_CODE_RE.fullmatch(type_code):
            raise ComparisonError(f"{label} observation {index} has an invalid TLP type code")
        if type(row.get("link_width")) is not int or row["link_width"] < 1:
            raise ComparisonError(f"{label} observation {index} has an invalid link width")
        _text(row.get("extractor_time_display"), f"{label} observation {index} time")
        gui = _mapping(row.get("gui_crosscheck"), f"{label} observation {index}.gui_crosscheck")
        if gui.get("status") != "MATCHED":
            raise ComparisonError(f"{label} observation {index} is not GUI cross-checked")
        for key in ("family", "subtype", "time_seconds"):
            _text(gui.get(key), f"{label} observation {index}.gui_crosscheck.{key}")
        if gui.get("link_width") != row["link_width"]:
            raise ComparisonError(f"{label} observation {index} GUI link width does not match")

    context = _mapping(root.get("gui_context"), f"{label}.gui_context")
    for key in ("visible_packet_indices", "intervening_non_extracted_indices"):
        values = context.get(key)
        if not isinstance(values, list) or any(type(value) is not int for value in values):
            raise ComparisonError(f"{label}.gui_context.{key} must be an integer list")
    if type(context.get("next_tlp_visible_beyond_cap")) is not int:
        raise ComparisonError(f"{label}.gui_context.next_tlp_visible_beyond_cap must be an integer")
    _text(context.get("interpretation"), f"{label}.gui_context.interpretation")
    visible_indices = set(context["visible_packet_indices"])
    interleaved_indices = set(context["intervening_non_extracted_indices"])
    if len(set(observed_indices)) != 5:
        raise ComparisonError(f"{label} contains duplicate packet indices")
    if not set(observed_indices).issubset(visible_indices):
        raise ComparisonError(f"{label} GUI context omits an extracted packet index")
    if not interleaved_indices.issubset(visible_indices) or interleaved_indices.intersection(observed_indices):
        raise ComparisonError(f"{label} GUI context has inconsistent intervening packet indices")
    limitations = root.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(
        not isinstance(item, str) or not item.strip() for item in limitations
    ):
        raise ComparisonError(f"{label}.limitations must be a non-empty string list")

    return root


def load_observation(path: Path, label: str) -> tuple[dict[str, Any], Path, str]:
    try:
        resolved = path.resolve(strict=True)
        raw = resolved.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"Cannot read {label} observation JSON: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ComparisonError(f"{label} observation JSON is not UTF-8: {path}") from exc
    digest = hashlib.sha256(raw).hexdigest().upper()
    return validate_observation(data, label), resolved, digest


def compare_observations(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left = validate_observation(left, "Trace A")
    right = validate_observation(right, "Trace B")

    if left["trace"]["sha256"].casefold() == right["trace"]["sha256"].casefold():
        raise ComparisonError("Trace A and Trace B have the same source SHA-256")
    for section, keys in (
        ("software", ("product", "version", "executable_sha256")),
        ("extractor", ("script_sha256", "record_cap", "scope", "fields", "time_representation")),
    ):
        for key in keys:
            left_value = left[section][key]
            right_value = right[section][key]
            equal = (
                left_value.casefold() == right_value.casefold()
                if key in ("executable_sha256", "script_sha256")
                else left_value == right_value
            )
            if not equal:
                raise ComparisonError(f"Trace A and Trace B differ in {section}.{key}")

    left_counts = Counter(_normalize_type_code(row["vendor_type_code_hex"]) for row in left["observations"])
    right_counts = Counter(_normalize_type_code(row["vendor_type_code_hex"]) for row in right["observations"])
    codes = sorted(set(left_counts) | set(right_counts), key=lambda value: int(value[2:], 16))
    type_counts = [
        {"type_code": code, "trace_a": left_counts[code], "trace_b": right_counts[code]}
        for code in codes
    ]
    return {
        "trace_a": left,
        "trace_b": right,
        "type_counts": type_counts,
        "shape_a": _sample_shape(left),
        "shape_b": _sample_shape(right),
    }


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_rows(data: dict[str, Any]) -> str:
    rows = []
    for index, row in enumerate(data["observations"], start=1):
        gui = row["gui_crosscheck"]
        rows.append(
            "<tr>"
            f"<td>{index}</td><td>{row['packet_index']}</td>"
            f"<td>{_esc(gui['family'])} / {_esc(gui['subtype'])}</td>"
            f"<td><code>{_esc(_normalize_type_code(row['vendor_type_code_hex']))}</code></td>"
            f"<td>{_esc(row['vendor_channel'])}</td><td>x{row['link_width']}</td>"
            f"<td>{_esc(row['extractor_time_display'])}</td></tr>"
        )
    return "".join(rows)


def _render_trace_card(label: str, data: dict[str, Any], observation_sha256: str) -> str:
    trace = data["trace"]
    limitations = "".join(f"<li>{_esc(item)}</li>" for item in data["limitations"])
    return f"""<section class="trace-card" aria-labelledby="{label.lower()}-title">
<h2 id="{label.lower()}-title">{label} <span class="unknown">測試結果未確認</span></h2>
<p class="filename">{_esc(trace['file_name'])}</p>
<p>抽取範圍：此 trace 中前五筆 TLP；每筆均有 GUI 抽樣核對。</p>
<div class="table-wrap"><table><thead><tr><th>本檔樣本序</th><th>Packet index</th><th>GUI 類別 / 子類</th><th>Type code</th><th>Channel</th><th>Link width</th><th>VSE 顯示時間</th></tr></thead>
<tbody>{_render_rows(data)}</tbody></table></div>
<details><summary>Trace 與執行身份</summary><dl>
<dt>來源路徑</dt><dd><code>{_esc(trace['source_path'])}</code></dd>
<dt>檔案大小</dt><dd>{trace['size_bytes']:,} bytes</dd>
<dt>Trace SHA-256</dt><dd><code>{_esc(trace['sha256'])}</code></dd>
<dt>最後修改時間 (UTC)</dt><dd><code>{_esc(trace['last_write_utc'])}</code></dd>
<dt>Observation JSON SHA-256</dt><dd><code>{_esc(observation_sha256)}</code></dd>
<dt>VSE 輸出 SHA-256</dt><dd><code>{_esc(data['evidence']['extractor_log_sha256'])}</code></dd>
<dt>Extractor SHA-256</dt><dd><code>{_esc(data['extractor']['script_sha256'])}</code></dd>
<dt>PETracer</dt><dd>{_esc(data['software']['product'])} {_esc(data['software']['version'])}</dd>
<dt>PETracer SHA-256</dt><dd><code>{_esc(data['software']['executable_sha256'])}</code></dd>
<dt>GUI 證據 SHA-256</dt><dd><code>{_esc(data['evidence']['gui_image_sha256'])}</code></dd>
<dt>來源限制</dt><dd><ul>{limitations}</ul></dd>
</dl></details></section>"""


def _render_observed(pair: dict[str, Any]) -> str:
    left, right = pair["shape_a"], pair["shape_b"]

    def trace_item(label: str, shape: dict[str, Any]) -> str:
        gaps = ", ".join(f"{gap:+d}" for gap in shape["index_gaps"])
        widths = ", ".join(f"x{width}" for width in shape["link_widths"])
        return (
            f"<li>{label} 樣本（依本檔輸出順序）：Type code <code>{_esc(' → '.join(shape['type_sequence']))}</code>；"
            f"GUI 子類 {_esc(' → '.join(shape['gui_subtype_sequence']))}；packet index 間隔 {_esc(gaps)}；"
            f"channel {_esc(', '.join(shape['channels']))}；link width {_esc(widths)}。</li>"
        )

    def same(flag: bool) -> str:
        return "相同" if flag else "不同"

    same_counts = all(item["trace_a"] == item["trace_b"] for item in pair["type_counts"])
    return (
        '<section class="panel"><h2>Observed：工具在兩份樣本中看到的</h2><ul>'
        + trace_item("Trace A", left)
        + trace_item("Trace B", right)
        + f"<li>Type code 樣本組成：兩份樣本{same(same_counts)}（見 Sample composition）。</li>"
        + f"<li>Type code 排列順序：兩份樣本{same(left['type_sequence'] == right['type_sequence'])}。</li>"
        + f"<li>Packet index 間隔模式：兩份樣本{same(left['index_gaps'] == right['index_gaps'])}。</li>"
        + '</ul><p class="muted">「相同」只表示兩份樣本各自的排列形狀一致，不表示是同一批事件，也不表示兩份 trace 的行為相同。</p></section>'
    )


def _render_filename_hints(pair: dict[str, Any]) -> str:
    items = [
        f"<li>{label} filename contains <code>{_esc(token)}</code>; this is treated only as a filename hint "
        f"and not as ground truth.（{label} 檔名含 <code>{_esc(token)}</code>，只當作檔名提示，不是已確認的測試結果。）</li>"
        for label, shape in (("Trace A", pair["shape_a"]), ("Trace B", pair["shape_b"]))
        for token in shape["filename_hints"]
    ]
    if not items:
        return ""
    return f'<section class="panel"><h2>Filename hints：檔名提示</h2><ul>{"".join(items)}</ul></section>'


def render_html(pair: dict[str, Any], left_sha256: str, right_sha256: str) -> str:
    left = pair["trace_a"]
    right = pair["trace_b"]
    count_rows = "".join(
        "<tr>"
        f"<td><code>{_esc(item['type_code'])}</code></td>"
        f"<td>{item['trace_a']}</td><td>{item['trace_b']}</td></tr>"
        for item in pair["type_counts"]
    )
    if not count_rows:
        count_rows = '<tr><td colspan="3">樣本中沒有可列出的 type code。</td></tr>'
    observed = _render_observed(pair)
    hints = _render_filename_hints(pair)

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{PAGE_TITLE}</title>
<style>
:root{{color-scheme:light;--ink:#182334;--muted:#546579;--line:#d7e0e8;--panel:#fff;--page:#f3f6f8;--blue:#eaf3fa;--amber:#fff4d6}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 system-ui,"Segoe UI",sans-serif}}
main{{max-width:1320px;margin:auto;padding:28px 22px 48px}}h1{{font-size:clamp(1.6rem,3vw,2.2rem);line-height:1.2;margin:.25em 0}}h2{{font-size:1.25rem;margin:.2em 0 .7em}}
p{{margin:.55em 0}}.lede,.notice,.panel,.trace-card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin:16px 0}}
.notice{{background:var(--amber);border-color:#e6cb79}}.sample-boundary{{background:var(--amber);border-radius:8px;padding:10px 12px}}ul{{margin:.4em 0;padding-left:1.3em}}.muted{{color:var(--muted)}}.unknown{{display:inline-block;font-size:.78rem;font-weight:600;background:#eef1f4;color:#34465a;border-radius:999px;padding:3px 9px;vertical-align:middle}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.trace-card{{margin:0;min-width:0}}.filename{{font-weight:700;overflow-wrap:anywhere}}.table-wrap{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.91rem}}th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{background:var(--blue);white-space:nowrap}}td code,dd code{{overflow-wrap:anywhere}}
dl{{display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:5px 12px}}dt{{color:var(--muted)}}dd{{margin:0;overflow-wrap:anywhere}}code{{font-family:ui-monospace,Consolas,monospace;font-size:.9em}}
footer{{margin-top:24px;color:var(--muted);font-size:.9rem}}@media(max-width:850px){{.grid{{grid-template-columns:1fr}}main{{padding:18px 12px 32px}}}}
</style></head><body><main>
<h1>{PAGE_TITLE}</h1><p class="muted filename">Trace A：{_esc(left['trace']['file_name'])} ／ Trace B：{_esc(right['trace']['file_name'])}</p>
<section class="lede"><h2>這頁能回答什麼？</h2>
<p>它列出兩份記錄各自最前面的五筆 TLP（PCIe 協定資料封包），並分別描述兩份樣本的組成。兩邊使用相同的 PETracer 與 extractor；表中的五筆也各自有 GUI 抽樣核對。</p>
<p>Type code 是 LeCroy 顯示的封包類別代碼。時間與封包 index 各自屬於原本那份記錄；A 的第 1 筆不代表和 B 的第 1 筆是同一個封包。</p></section>
{hints}{observed}
<section class="notice"><h2>Not established：這頁無法確立的事</h2><p>這不是故障診斷。每份 trace 只看前五筆 TLP。</p><ul>
<li>哪一份 trace 是正常的（which trace is normal）</li>
<li>哪一份 trace 是異常的（which trace is abnormal）</li>
<li>觀察到的差異或相同之處是否代表故障（whether observed differences indicate a fault）</li>
<li>五筆樣本能否代表整份 trace 的行為（whether samples represent full-trace behavior）</li>
<li>兩邊同序號樣本是否為對應事件（whether same-position samples are corresponding events）</li>
<li>故障原因（root cause）</li></ul></section>
<section class="panel"><h2>Sample composition：有界樣本中觀察到的 TLP type</h2>
<p class="sample-boundary"><strong>{SAMPLE_BOUNDARY_NOTE}</strong><br>下表只描述各自前五筆 TLP 樣本的組成，不是整份 trace 的統計，也不用來判斷差異是否異常。</p>
<div class="table-wrap"><table><thead><tr><th>TLP Type code</th><th>Trace A 樣本筆數</th><th>Trace B 樣本筆數</th></tr></thead><tbody>{count_rows}</tbody></table></div></section>
<div class="grid">{_render_trace_card('Trace A', left, left_sha256)}{_render_trace_card('Trace B', right, right_sha256)}</div>
<footer>本頁只讀兩份單 trace observation JSON，不重新解析 `.pex`，也不重新驗證來源 trace 或 VSE 證據檔。實際測試結果尚未確認，工具沒有判斷故障；每份 trace 只涵蓋前五筆 TLP。</footer>
</main></body></html>"""


def build_comparison(
    trace_a_path: Path,
    trace_b_path: Path,
    output_path: Path,
    repo_root: Path = REPO_ROOT,
) -> Path:
    repo_root = repo_root.resolve()
    left, _, left_sha = load_observation(trace_a_path, "Trace A")
    right, _, right_sha = load_observation(trace_b_path, "Trace B")
    pair = compare_observations(left, right)

    target = output_path if output_path.is_absolute() else repo_root / output_path
    target = target.resolve()
    try:
        target.relative_to(repo_root)
    except ValueError as exc:
        raise ComparisonError("HTML output must stay inside the repository") from exc
    if target.exists():
        raise ComparisonError(f"Refusing to overwrite existing HTML: {target}")
    if target.suffix.casefold() != ".html":
        raise ComparisonError("Output path must end in .html")

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(render_html(pair, left_sha, right_sha))
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-a", type=Path, required=True, help="Trace A observations.json")
    parser.add_argument("--trace-b", type=Path, required=True, help="Trace B observations.json")
    parser.add_argument("--output", type=Path, required=True, help="New HTML path inside this repository")
    args = parser.parse_args(argv)
    try:
        path = build_comparison(args.trace_a, args.trace_b, args.output)
    except (ComparisonError, OSError) as exc:
        print(f"PCIe comparison HTML not generated: {exc}", file=sys.stderr)
        return 2
    print(path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
