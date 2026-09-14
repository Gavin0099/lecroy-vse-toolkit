#!/usr/bin/env python3
"""PCIe-G8: render G3f findings.json as a layered, offline HTML report.

Wording comes from the G7 `finding_parts` so Markdown and HTML say the same thing. Layout only:
a fixed warning panel, a scan table, and one card per finding whose first layer shows the
navigation anchor, observations and segments, with full evidence inside <details>.
No scripts, no external resources, all text escaped. A contract check fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import g7_render_markdown as g7  # noqa: E402

WARNINGS = [
    "Ground truth `UNKNOWN`，這份 trace 的測試結果還沒確認。",
    "工具沒有判斷故障原因，每一組都只是候選檢查位置（`NOT_EVALUATED`）。",
    "判斷附近與否用的 64 packets 範圍是 prototype heuristic，看過資料後才訂。",
    "各組依主要定位點在 trace 裡出現的先後排列，順序不代表嚴重程度。",
    g7.NAVIGATION_NOTE,
]

PROVENANCE_LABEL = "Trace 來源與轉換"

CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1d2433;--muted:#5b6475;--line:#d9dee7;--warn-bg:#fff4d6;--warn-line:#e6c36a;
--ur:#b3261e;--ur-bg:#fde8e7;--msg:#8a4b00;--msg-bg:#fff0dc;--key:#1f4e8c;--key-bg:#e6eefb;--seg:#4a4f5c;--seg-bg:#eceef2}
@media (prefers-color-scheme: dark){:root{--bg:#14171c;--panel:#1d2129;--ink:#e6e9ef;--muted:#a3abba;--line:#343a46;--warn-bg:#3a3020;
--warn-line:#8c7336;--ur:#ff9b94;--ur-bg:#46211f;--msg:#ffc680;--msg-bg:#3d2c14;--key:#9cc3ff;--key-bg:#1d2d45;--seg:#c9ced8;--seg-bg:#2b303a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,"Segoe UI","Microsoft JhengHei",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}h1{font-size:1.5rem;margin:.2em 0 .6em}h2{font-size:1.15rem;margin:1.6em 0 .6em}
p{margin:.5em 0}code{font-family:ui-monospace,Consolas,monospace;font-size:.92em;background:var(--seg-bg);padding:0 .25em;border-radius:3px;overflow-wrap:anywhere}
.warn{background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:10px;padding:12px 16px;margin:16px 0}.warn ul{margin:.3em 0;padding-left:1.2em}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;background:var(--panel);font-size:.9rem}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--seg-bg);white-space:nowrap}
.badge{display:inline-block;font-size:.78rem;font-weight:600;border-radius:999px;padding:1px 8px;margin:1px 4px 1px 0;white-space:nowrap}
.b-ur{color:var(--ur);background:var(--ur-bg)}.b-msg{color:var(--msg);background:var(--msg-bg)}.b-key{color:var(--key);background:var(--key-bg)}.b-seg{color:var(--seg);background:var(--seg-bg)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:14px 0}
.card h3{margin:0 0 .4em;font-size:1.05rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px 18px}
.label{color:var(--muted);font-size:.82rem}.card ul{margin:.2em 0;padding-left:1.2em}details{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
summary{cursor:pointer;font-weight:600}details h4{margin:.9em 0 .3em;font-size:.95rem}.muted{color:var(--muted);font-size:.85rem}
"""


class G8Error(ValueError):
    """Rendering input is unusable or the HTML contract failed."""


def inline(text: str) -> str:
    """Escape text, then turn `identity` spans into <code>."""
    escaped = html.escape(text, quote=True)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def _badges(facts: dict[str, Any]) -> str:
    out = []
    for status in facts["statuses"]:
        out.append(f'<span class="badge b-ur">{html.escape(status)}</span>')
    for message in facts["messages"]:
        out.append(f'<span class="badge b-msg">{html.escape(message)}</span>')
    if facts["same_key"]:
        out.append('<span class="badge b-key">同 key 再次出現</span>')
    out.append(f'<span class="badge b-seg">{facts["segments"]} Segments，跨 {facts["span"]:,} packets</span>')
    return "".join(out)


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>" if items else ""


def render_card(finding: dict[str, Any]) -> str:
    parts = g7.finding_parts(finding)
    facts = parts["facts"]
    fid = html.escape(parts["finding_id"])
    segments_first = "".join(f"<li>{inline(s['title'])}，定位 {inline('`Packet ' + str(s['go_to_packet']) + '`')}</li>" for s in parts["segments"])
    why = "<ul>" + "".join(
        f"<li>{inline(text)}" + (_list(subs) if subs else "") + "</li>" for text, subs in parts["why"]
    ) + "</ul>"
    segment_detail = "".join(f"<h4>{inline(s['title'])}</h4>{_list(s['lines'])}" for s in parts["segments"])
    crosschecks = "".join(f"<p>{inline(x)}</p>" for x in parts["crosschecks"])
    observations = "".join(f"<p>{inline(x)}</p>" for x in parts["observations"])
    nearby = f"<p class=\"label\">附近也觀察到</p>{_list(parts['nearby'])}" if parts["nearby"] else ""
    return f"""<section class="card" id="finding-{fid.lower()}" data-finding="{fid}">
<h3>Finding {fid} {_badges(facts)}</h3>
<div class="grid">
<div><div class="label">主要定位點</div><div>{inline('`Packet ' + str(parts['primary_packet']) + '`')}</div><div class="muted">依固定規則選出，只用來跳轉</div></div>
<div><div class="label">觀察</div>{_list(parts['summary'])}</div>
<div><div class="label">Segments</div><ul>{segments_first}</ul></div>
</div>
<details>
<summary>展開完整證據</summary>
<h4>主要定位點</h4><p>{inline(parts['primary_sentence'])}</p>{('<p class="label">其他位置</p>' + _list(parts['other_locations'])) if parts['other_locations'] else ''}
<h4>觀察到什麼</h4>{observations}{nearby}
<h4>相關位置</h4>{segment_detail}{crosschecks}
<h4>為什麼列出這一項</h4>{why}
<h4>目前還不能確定</h4>{_list(parts['unknown'])}
<h4>追溯</h4><p>{inline(parts['trace'])}</p>
</details>
</section>"""


def render(findings_doc: dict[str, Any], trace_name: str, trace_sha256: str | None, tlp_count: int | None, findings_sha256: str,
           provenance: dict[str, str] | None = None) -> str:
    findings = findings_doc["findings"]
    rows = []
    for f in findings:
        parts = g7.finding_parts(f)
        facts = parts["facts"]
        rows.append(
            f"<tr><td><a href=\"#finding-{html.escape(f['finding_id'].lower())}\">{html.escape(f['finding_id'])}</a></td>"
            f"<td>{inline('`Packet ' + str(parts['primary_packet']) + '`')}</td>"
            f"<td>{html.escape('、'.join(facts['times']))}</td><td>{_badges(facts)}</td><td>{inline('；'.join(parts['summary']))}</td></tr>"
        )
    intro = "".join(f"<p>{inline(p)}</p>" for p in g7.intro_paragraphs(trace_name, tlp_count, len(findings))[:1])
    glossary = _list(g7.glossary_lines(findings))
    sources = _list(g7.source_lines(trace_name, trace_sha256, tlp_count, findings_sha256, bool(provenance)))
    origin = ""
    if provenance:
        origin = (f'<section class="warn" aria-label="{PROVENANCE_LABEL}"><strong>{PROVENANCE_LABEL}</strong>'
                  f"{_list(g7.provenance_lines(trace_sha256, provenance))}</section>")
    cards = "\n".join(render_card(f) for f in findings)
    title = html.escape(f"{g7.REPORT_TITLE}（{trace_name}）")
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><main>
<h1>{title}</h1>
{origin}{intro}
<section class="warn" aria-label="閱讀前須知"><strong>閱讀前須知</strong>{_list(WARNINGS)}</section>
<h2>{len(findings)} 組候選檢查位置一覽</h2>
<div class="table-wrap"><table><thead><tr><th>Finding</th><th>主要定位點</th><th>時間</th><th>標記</th><th>內容</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>
<h2>Findings</h2>
{cards}
<h2>報告用到的 PCIe 名詞</h2>{glossary}
<h2>資料來源</h2>{sources}
</main></body></html>
"""


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.cards: list[str] = []
        self.external: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs = dict(attrs)
        if tag == "section" and "data-finding" in attrs:
            self.cards.append(attrs["data-finding"])
        for key in ("src", "href"):
            value = attrs.get(key) or ""
            if value and not value.startswith("#"):
                self.external.append(value)


def contract_check(document: str, findings_doc: dict[str, Any], provenance: dict[str, str] | None = None) -> list[str]:
    errors: list[str] = []
    if provenance:
        head = document.split('<section class="card" ')[0]
        marker = f'aria-label="{PROVENANCE_LABEL}"'
        block = html.unescape(re.sub(r"<[^>]+>", "", head.split(marker)[-1])) if marker in head else ""
        for needed in (f"Original trace SHA-256 {provenance.get('original_sha256')}", "Converted analysis copy SHA-256", g7.PACKET_INDEX_NOTE):
            if needed not in block:
                errors.append(f"conversion provenance before the findings lacks: {needed}")
    collector = _Collector()
    collector.feed(document)
    if "script" in collector.tags:
        errors.append("script element present")
    if collector.external:
        errors.append(f"external references present: {collector.external}")
    findings = findings_doc["findings"]
    expected = [f["finding_id"] for f in findings]
    if collector.cards != expected:
        errors.append(f"cards {collector.cards} differ from findings.json order {expected}")
    text = html.unescape(re.sub(r"<[^>]+>", "", document))
    if g7.NAVIGATION_NOTE not in text or "Ground truth UNKNOWN" not in text:
        errors.append("warning panel incomplete")
    cards = re.split(r'<section class="card" ', document)[1:]
    for f, card in zip(findings, cards):
        fid = f["finding_id"]
        first, _, details = card.partition("<details>")
        if f"Packet {f['where_to_look']['primary_go_to_packet']}" not in first:
            errors.append(f"{fid} first layer lacks the navigation anchor")
        if not details:
            errors.append(f"{fid} has no expandable evidence")
            continue
        detail_text = html.unescape(re.sub(r"<[^>]+>", "", details))
        for seg in f["what_was_observed"]["local_segments"]:
            for a in seg["anchors"]:
                if f"Packet {a['packet']}" not in detail_text:
                    errors.append(f"{fid} evidence omits anchor packet {a['packet']}")
        if "UNKNOWN" not in detail_text or f"{fid}" not in detail_text.split("追溯")[-1]:
            errors.append(f"{fid} evidence lacks UNKNOWN or traceability")
    lowered = text.lower()
    for phrase in g7.FORBIDDEN_PHRASES:
        if phrase in lowered:
            errors.append(f"forbidden phrase present: {phrase}")
    if "—" in text or "–" in text:
        errors.append("dash character present")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--trace-file-name", required=True)
    parser.add_argument("--trace-sha256")
    parser.add_argument("--tlp-count", type=int)
    g7.add_provenance_arguments(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise G8Error(f"Refusing to overwrite existing report: {args.output}")
        raw = args.findings.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        provenance = g7.provenance_from_args(args)
        document = render(doc, args.trace_file_name, args.trace_sha256, args.tlp_count, hashlib.sha256(raw).hexdigest().upper(), provenance)
        errors = contract_check(document, doc, provenance)
        if errors:
            raise G8Error("HTML contract failed: " + "; ".join(errors))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, g7.G7Error, G8Error) as exc:
        print(f"G8 report not produced: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(document)
    print(json.dumps({"output": args.output.as_posix(), "findings": len(doc["findings"]), "contract_errors": 0,
                      "sha256": hashlib.sha256(document.encode("utf-8")).hexdigest().upper()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
