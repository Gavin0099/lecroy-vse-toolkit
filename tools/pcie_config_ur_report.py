"""Publish a bounded Windows projection and portable reports from the same evidence."""
import html
from pathlib import Path

import pcie_large_io as large
from pcie_ui_pages import MAX_BYTES, encoded


SCHEMA = "pcie.config-ur-evidence/v1"
INDEX_SCHEMA = "pcie.config-ur-index/v1"
PAGE_SCHEMA = "pcie.config-ur-page/v1"
IDENTITY = ("analysis_id", "source_trace_sha256", "display_trace_sha256", "packet_namespace")
GROUPS = {
    "writes": "Config Write",
    "reads": "Config Read",
    "memory": "Memory UR／CA",
    "ur_summary": "重複 UR",
    "unmatched": "未配對／狀態未確認的 Completion",
}
COLUMNS = ("Packet", "交易", "目的／回覆端", "位址／暫存器", "寫入值／BE", "Completion", "回讀")
STATES = {
    "NO_COMPLETION_OBSERVED_BEFORE_LINK_DOWN": "Link Down 前未見回覆",
    "NO_COMPLETION_OBSERVED": "未觀察到回覆",
    "DATA_GAP": "資料範圍不足",
    "AMBIGUOUS": "配對不明確",
    "UNKNOWN": "未知",
}
REGISTER_NAMES = {
    "PCI_EXP_CAP_HEADER": "PCI Express Capability 標頭",
    "PCI_EXP_LINK_CONTROL": "PCI Express Link Control",
    "L1SS_EXT_CAP_HEADER": "L1 PM Substates 標頭",
    "VSEC_SECOND_HEADER": "VSEC 次標頭",
}
REASON = {
    "RAW_FRAME_VERIFIED": "原始 frame 核對",
    "NATIVE_TEXT_VERIFIED": "原生文字核對",
    "METADATA_ONLY": "僅有 metadata",
}
INTERVALS = {"same_interval": "同一連線區間", "later_interval": "後續連線區間", "unknown": "區間未知"}
MAX_REPORT_BYTES = 32 * 1024 * 1024


def _hex(value, width=0):
    return "未知" if value is None else f"0x{value:0{width}X}"


def _bdf(value):
    return "未知" if value is None else f"{value >> 8:02X}:{(value >> 3) & 0x1f:02X}.{value & 7}"


def _status(code):
    return STATES.get(code, code or "未知")


def _seconds(ns):
    if ns is None:
        return "時間未知"
    seconds, nanoseconds = divmod(ns, 1_000_000_000)
    return f"{seconds}.{nanoseconds:09d} s"


def _be(event):
    return " / ".join(_hex(event[key]) for key in ("first_be", "last_be"))


def _event_lines(label, event):
    lines = [
        f"{label} Packet {event['packet_index']} · {event['direction']} · "
        f"{event['time_display'] or _seconds(event['time_ns'])}",
        f"{event['kind']} · Requester {_bdf(event['requester_id'])} · "
        f"Tag {event['tag'] if event['tag'] is not None else '未知'}",
    ]
    if event["kind"] in ("Cpl", "CplD"):
        lines.append(
            f"Completer {_bdf(event['device_id'])} · {_status(event['status'])} · "
            f"Byte Count {event['byte_count'] if event['byte_count'] is not None else '未知'} · "
            f"Lower Address {_hex(event['lower_address'])}"
        )
    else:
        count = event["length_dw"]
        lines.append(f"First／Last BE {_be(event)} · {count if count is not None else '未知'} DW")
    for evidence in event["evidence"]:
        lines.append(
            f"{REASON[evidence['kind']]} · {evidence['file']} #{evidence['line']} · "
            f"{', '.join(evidence['fields'])} · SHA-256 {evidence['sha256']}"
        )
    return lines


def _row(row):
    req, cpl = row["request"], row["completion"]
    readback = row["readback"]
    config = req["kind"].startswith("Cfg")
    reg = row["register"]
    expected = reg["identity"] if reg else "UNKNOWN"
    address = _hex(req["register"] if config else req["address"])
    if config and expected != "UNKNOWN":
        address += " " + REGISTER_NAMES.get(expected, expected)
        if reg["scope"] == "later_interval":
            address += "（後段同 BDF，供比對）"
    locations = {"request": req["packet_index"]}
    details = _event_lines("原請求", req)
    if cpl is not None:
        locations["completion"] = cpl["packet_index"]
        details.extend(_event_lines("Completion", cpl))
    observed = "—"
    if readback:
        rq, reply = readback["request"], readback["completion"]
        locations.update(read_request=rq["packet_index"], read_completion=reply["packet_index"])
        observed = _hex(reply["value"], 8) + ("（後續連線區間）" if readback["scope"] == "later_interval" else "")
        details.extend(_event_lines("回讀請求", rq))
        details.extend(_event_lines("回讀 Completion", reply))
        if readback["scope"] == "later_interval":
            details.append("回讀來自後續連線區間，僅可供比對。")
    elif req["kind"].startswith("CfgRd") and cpl is not None and row["completion_status"] == "SC":
        observed = _hex(cpl["value"], 8)
    else:
        observed = "回讀未確認" if config else "—"
    if config:
        if reg and expected != "UNKNOWN":
            basis = "、".join(str(p) for p in reg["evidence_packets"])
            details.append(f"暫存器定位證據 Packet {basis}／{INTERVALS[reg['scope']]}")
            if reg["scope"] == "same_interval":
                for field in reg.get("write_fields", ()):
                    details.append(f"觀察到的寫入欄位 {field['name']} = {_hex(field['value'])}")
            elif reg["scope"] == "later_interval":
                details.append("後段同 BDF 的暫存器定義僅供比對，原區間的暫存器身分尚未核對。")
        else:
            details.append("暫存器身分未知，保留 Config offset。")
    if row["write_effect"] == "NOT_ESTABLISHED":
        details.append("硬體寫入效果尚未建立。")
    if row["bar"] == "BAR_UNKNOWN":
        details.append("BAR 未知，保留 Memory 地址。")
    if row["epoch"] is not None:
        details.append(f"觀察區間 {row['epoch']}")
    result = _status(row["completion_status"])
    if cpl is not None:
        result += f" · {cpl['packet_index']}"
    payload = (_hex(req["value"], 8) + " / " if req["kind"].startswith("CfgWr") else "") + _be(req)
    return dict(id=row["id"], columns=[str(req["packet_index"]), req["kind"],
        _bdf(req["device_id"] if config else cpl["device_id"] if cpl else None),
        address, payload, result, observed], details=details, locations=locations)


def _group(group):
    bursts = group["bursts"]
    return dict(id="", columns=["—", f"{len(bursts)} 個觀察時段", "—",
                    f"{_hex(group['address'])} · {group['byte_length']} B", "—",
                    f"{group['count']} 次 UR", "—"],
                details=[f"時段 {i + 1} · {_seconds(b['start_ns'])}～{_seconds(b['end_ns'])} · {b['count']} 次"
                         for i, b in enumerate(bursts)] + [
                    "原請求 Packet " + "、".join(p[1:] for p in group["row_ids"])
                ], locations={})


def _unmatched(event):
    return dict(id="", columns=[str(event["packet_index"]), event["kind"], _bdf(event["device_id"]), "—",
                    "—", f"{_status(event['status'])} · 未配對", "—"],
                details=_event_lines("未配對的 Completion", event), locations={})


def _coverage(result):
    c = result["coverage"]
    return " · ".join([
        "完整擷取範圍未知",
        "訂閱範圍內資料已保留" if c["stream_complete"] else "訂閱資料部分缺漏",
        "已保留 Link Down 邊界" if c["link_boundaries_complete"] else "Link Down 邊界不完整",
        f"原始 frame 格式未支援 {c['unsupported_frame_rows']} 筆",
        f"省略 {c['omitted_rows']} 筆",
    ])


def _paginate(items, base, output):
    names = []
    chunk = []
    def page_values(rows):
        return dict(base, page=len(names), rows=rows)
    def flush():
        raw = encoded(page_values(chunk))
        if len(raw) > MAX_BYTES:
            raise ValueError("單筆暫存器證據超過分頁大小上限。")
        name = f"{base['group']}-{len(names)}.json"
        _write_bytes(output / name, raw)
        names.append(name)
    for item in items:
        if chunk and (len(chunk) == 20 or len(encoded(page_values(chunk + [item]))) > MAX_BYTES):
            flush()
            chunk.clear()
        chunk.append(item)
    if chunk or not names:
        flush()
    return names


def _write_bytes(path, content):
    large.check_disk(path.parent, len(content))
    with path.open("xb") as stream:
        stream.write(content)


def _projections(result):
    groups = {key: [] for key in GROUPS}
    for row in result["rows"]:
        kind = row["request"]["kind"]
        group = "writes" if kind.startswith("CfgWr") else "reads" if kind.startswith("CfgRd") else "memory"
        groups[group].append(_row(row))
    groups["ur_summary"] = [_group(group) for group in result["ur_groups"]]
    groups["unmatched"] = [_unmatched(event) for event in result["unmatched_completions"]]
    return groups


def _report(index, groups, format):
    web = format == "html"
    title = "PCIe 暫存器與 UR"
    esc = html.escape
    if web:
        yield '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>' + title + "</title>"
        yield "<style>body{font:1rem sans-serif;margin:2rem auto;max-width:88rem;padding:0 1rem}table{border-collapse:collapse;width:100%}th,td{text-align:left;border-bottom:1px solid #ddd;padding:.5rem;overflow-wrap:anywhere}details{padding:.4rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><body>"
        yield f"<h1>{title}</h1><p>{esc(index['coverage_text'])}</p>"
    else:
        yield f"# {title}\n\n{index['coverage_text']}\n"
    for field in IDENTITY:
        label = {
            "analysis_id": "分析識別碼", "source_trace_sha256": "來源 SHA-256",
            "display_trace_sha256": "顯示副本 SHA-256", "packet_namespace": "Packet 索引範圍",
        }[field]
        yield f"<p>{label} <code>{esc(index[field])}</code></p>" if web else f"- {label} {esc(index[field])}"
    for key, items in groups.items():
        heading = GROUPS[key] + f"（{len(items)}）"
        yield f"<h2>{heading}</h2>" if web else f"\n## {heading}\n"
        if not items:
            yield "<p>目前沒有此類證據。</p>" if web else "目前沒有此類證據。"
            continue
        if web:
            yield "<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in COLUMNS) + "</tr></thead><tbody>"
        else:
            yield "| " + " | ".join(COLUMNS) + " |\n|" + "|".join("---" for _ in COLUMNS) + "|"
        for item in items:
            cols = item["columns"]
            if web:
                yield "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in cols) + "</tr>"
            else:
                yield "| " + " | ".join(esc(c).replace("|", "&#124;").replace("\n", " ") for c in cols) + " |"
        if web:
            yield "</tbody></table>"
        else:
            yield ""
        for item in items:
            name = " · ".join(item["columns"][:4])
            details = "\n".join(item["details"])
            if web:
                yield f"<details><summary>{esc(name)}</summary><pre>{esc(details)}</pre></details>"
            else:
                yield f"<details><summary>{esc(name)}</summary><pre>{esc(details)}</pre></details>\n"
    if web:
        yield "</body></html>"


def _write_report(path, lines):
    large.check_disk(path.parent, MAX_REPORT_BYTES)
    size = 0
    with path.open("xb") as f:
        for line in lines:
            chunk = (line + "\n").encode("utf-8")
            size += len(chunk)
            if size > MAX_REPORT_BYTES:
                raise large.ResourceLimit("暫存器／UR 報告超過輸出大小上限。")
            f.write(chunk)


def write(output, result):
    """Create a new evidence generation. A ready index is written only after all files."""
    output = Path(output).resolve()
    if result["schema"] != SCHEMA:
        raise ValueError("不相容的暫存器／UR 證據格式。")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "index.json").exists():
        raise FileExistsError("此證據版本已發布。")

    binding = {key: result[key] for key in IDENTITY}
    groups = _projections(result)
    manifests = {}
    for key, rows in groups.items():
        page = dict(binding, schema=PAGE_SCHEMA, group=key)
        manifests[key] = dict(count=len(rows), pages=_paginate(rows, page, output))
    index = dict(binding, schema=INDEX_SCHEMA, coverage_text=_coverage(result), groups=manifests,
                 row_count=len(result["rows"]), report_html="report.html", report_markdown="report.md")
    for file, fmt in ((index["report_html"], "html"), (index["report_markdown"], "markdown")):
        _write_report(output / file, _report(index, groups, fmt))
    body = encoded(index)
    if len(body) > MAX_BYTES:
        raise ValueError("暫存器／UR 分頁索引超過大小上限。")
    _write_bytes(output / "index.json", body)
    return index
