"""Single-trace USB2 control-transfer inspection guidance; no labels or markers."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

MAX_RECORDS = 100_000
PREFIX_BYTES = 64
LOOKBACK_RECORDS = 256
LOOKBACK_NS = 10_000_000_000
DESCRIPTORS = {1: "Device", 2: "Configuration", 3: "String", 6: "Device Qualifier",
               7: "Other-Speed Configuration", 15: "BOS"}
FIELDS = ("index", "seconds", "nanoseconds", "duration_seconds", "duration_nanoseconds",
          "channel", "speed", "address", "endpoint", "completed", "halted", "error",
          "direction", "request_type", "recipient", "request", "value", "request_index",
          "requested_length", "native_payload_length")
RULE_VERSION = "usb2-control-guidance-3"


class InputError(ValueError):
    pass


def ns_text(ns):
    return f"{ns // 1_000_000_000}.{ns % 1_000_000_000:09d}"


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise InputError(f"Invalid {name}")
    return value


def normalize(raw):
    """Whitelist the fixed extractor protocol. Other report text cannot drive rules."""
    for key in ("trace_sha256", "script_sha256"):
        if not isinstance(raw.get(key), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", raw[key]):
            raise InputError(f"Missing {key}")
    if type(raw.get("run_result")) is not int or raw["run_result"] != 2 or type(raw.get("finished_result")) is not int or raw["finished_result"] != 2 or raw.get("error") != "":
        raise InputError("Native run did not finish cleanly")
    integrity = raw.get("integrity", {})
    if any(integrity.get(k) is not True for k in ("source_unchanged", "working_copy_unchanged", "working_copy_readonly", "script_unchanged")):
        raise InputError("Protected input integrity not established")
    summary = raw.get("summary")
    if not isinstance(summary, list) or len(summary) != 5:
        raise InputError("Missing extractor summary")
    for v in summary:
        integer(v, 0, 2**63 - 1, "summary count")
    visited, controls, emitted, unsupported, level = summary
    if level != 3 or emitted != min(controls, MAX_RECORDS) or visited < controls + unsupported:
        raise InputError("Extractor counts do not reconcile")
    reports = raw.get("reports")
    if not isinstance(reports, list) or any(not isinstance(r, str) for r in reports):
        raise InputError("Invalid report transport")
    events = []
    for report in reports:
        for line in report.splitlines():
            if not line.startswith("UCT|"):
                continue
            parts = line.split("|")
            if len(parts) != 22:
                raise InputError("Truncated control record")
            try:
                values = [int(p) for p in parts[1:21]]
            except ValueError as exc:
                raise InputError("Non-integer control field") from exc
            e = dict(zip(FIELDS, values))
            for k, v in e.items():
                integer(v, 0, 2**63 - 1, k)
            for k in ("nanoseconds", "duration_nanoseconds"):
                integer(e[k], 0, 999_999_999, k)
            for k in ("completed", "halted", "direction"):
                integer(e[k], 0, 1, k)
            for k, hi in (("address", 127), ("endpoint", 15), ("request_type", 3),
                          ("recipient", 31), ("request", 255), ("value", 65535),
                          ("request_index", 65535), ("requested_length", 65535)):
                integer(e[k], 0, hi, k)
            if e["channel"] != 1 or e["speed"] not in (0, 1, 2):
                raise InputError("Record is outside USB2 extractor scope")
            prefix = parts[21]
            if not re.fullmatch(r"(?:[0-9A-Fa-f]{2})*", prefix) or len(prefix) // 2 != min(e["native_payload_length"], PREFIX_BYTES):
                raise InputError("Payload prefix length does not reconcile")
            buf = bytes.fromhex(prefix)
            setup = bytes([(e["direction"] << 7) | (e["request_type"] << 5) | e["recipient"], e["request"]])
            for k in ("value", "request_index", "requested_length"):
                setup += e[k].to_bytes(2, "little")
            # Actual native payloads include SETUP. Only subtract after byte equality.
            setup_matches = len(buf) >= 8 and buf[:8] == setup
            e.update(timestamp_ns=e["seconds"] * 1_000_000_000 + e["nanoseconds"],
                     duration_ns=e["duration_seconds"] * 1_000_000_000 + e["duration_nanoseconds"],
                     native_prefix_hex=prefix.upper(), setup_bytes_match=setup_matches,
                     data_length=e["native_payload_length"] - 8 if setup_matches else None,
                     data_prefix_hex=buf[8:].hex().upper() if setup_matches else None,
                     packet_refs=None)
            if events and (e["index"] <= events[-1]["index"] or e["timestamp_ns"] < events[-1]["timestamp_ns"]):
                raise InputError("Duplicate/out-of-order native transfer identity")
            events.append(e)
    if len(events) != emitted:
        raise InputError("Missing or duplicate emitted records")
    return {"trace_sha256": raw["trace_sha256"].lower(), "extractor_sha256": raw["script_sha256"].lower(),
            "visited_transfers": visited, "eligible_controls": controls, "unsupported_controls": unsupported,
            "truncated": emitted < controls, "events": events}


def request_key(e, exact=False):
    keys = ("channel", "speed", "address", "endpoint", "direction", "request_type",
            "recipient", "request", "value", "request_index")
    return tuple(e[k] for k in keys) + ((e["requested_length"],) if exact else ())


def successful(e):
    return e["completed"] == 1 and e["halted"] == 0 and e["error"] == 0


def descriptor(e):
    return e["endpoint"] == 0 and e["request_type"] == 0 and e["direction"] == 1 and e["request"] == 6


def request_name(e):
    if descriptor(e):
        dtype, index = e["value"] >> 8, e["value"] & 255
        return f"{DESCRIPTORS.get(dtype, f'Descriptor 0x{dtype:02X}')} descriptor（index {index}）"
    return f"Control request 0x{e['request']:02X}" if e['request'] is not None else "Control request（原生欄位未知）"


def boundary(e):
    # Observed logical boundaries only. No physical-device continuity is asserted.
    return e["request_type"] == 0 and (e["request"] == 5 or (e["request"] == 9 and e["value"] == 0))


def history(events, pos):
    e = events[pos]
    result = []
    for j in range(pos - 1, max(-1, pos - LOOKBACK_RECORDS - 1), -1):
        p = events[j]
        if e["timestamp_ns"] - p["timestamp_ns"] > LOOKBACK_NS:
            break
        same_bus = (p["channel"], p["speed"]) == (e["channel"], e["speed"])
        if same_bus and p["request_type"] == 0:
            if p["request"] == 5 and e["address"] in (p["address"], p["value"]):
                break
            if p["address"] == e["address"] and p["request"] == 9 and p["value"] == 0:
                break
        result.append(p)
    return result


def nearby_prior(events, pos):
    return [p for p in history(events, pos) if request_key(p) == request_key(events[pos])]


def timing_context(events, pos):
    e = events[pos]
    pool = [p for p in history(events, pos) if descriptor(p) and successful(p)
            and (p['channel'], p['speed'], p['address'], p['endpoint']) ==
                (e['channel'], e['speed'], e['address'], e['endpoint'])
            and (p['data_length'] or 0) > 0 and p['duration_ns'] > 0]
    if len(pool) < 5:
        return None
    ordered = sorted(pool, key=lambda p:p['duration_ns'])
    reference = ordered[(95 * len(ordered) + 99) // 100 - 1]
    return {"count":len(pool), "p95_ns":reference['duration_ns'],
            "references":list(dict.fromkeys([reference['index']] + [p['index'] for p in pool[:3]]))}


def descriptor_issues(e):
    """Only compare declared content after actual SETUP prefix verification."""
    if not descriptor(e) or not successful(e) or e["data_length"] is None or e["data_length"] < 2:
        return []
    b = bytes.fromhex(e["data_prefix_hex"])
    if len(b) < 2:
        return []
    dtype = e["value"] >> 8
    issues = []
    if b[1] != dtype:
        issues.append(f"回傳 descriptor type 0x{b[1]:02X}，請求的是 0x{dtype:02X}")
    if b[0] < 2:
        issues.append(f"回傳 bLength={b[0]}，不足以包含 descriptor 的兩個表頭欄位")
    declared = b[0]
    if dtype in (2, 7, 15) and len(b) >= 4 and b[1] == dtype:
        declared = int.from_bytes(b[2:4], "little")
    if declared > 0 and e["data_length"] < min(e["requested_length"], declared):
        issues.append(f"回傳內容宣告長度 {declared}，本次要求 {e['requested_length']}，native 資料只有 {e['data_length']} bytes")
    return issues


def declared_followup(previous, current):
    if not previous or not descriptor(current) or current["data_length"] != 0:
        return None
    prefix = bytes.fromhex(previous["data_prefix_hex"] or "")
    dtype = current["value"] >> 8
    # These descriptors explicitly declare a total response length in bytes 2..3.
    if (dtype not in (2, 7, 15) or len(prefix) < 4 or prefix[1] != dtype
            or current["requested_length"] <= previous["requested_length"]):
        return None
    total = int.from_bytes(prefix[2:4], "little")
    if total > previous["data_length"] >= 4:
        return total
    return None


def discover(data):
    events = data["events"]
    hits = []
    for pos, e in enumerate(events):
        # Restrict first release to standard Chapter 9 device/interface/endpoint control.
        if e["endpoint"] != 0 or e["request_type"] != 0:
            continue
        prior = nearby_prior(events, pos)
        supported = next((p for p in prior if successful(p) and (p["data_length"] or 0) > 0), None)
        repeat = next((p for p in prior if request_key(p, True) == request_key(e, True)
                       and not successful(p)), None)
        rules, facts, reasons = [], [], []
        strength = 0
        if e["completed"] == 0:
            rules.append("incomplete")
            facts.append("LeCroy native Completed=0，未將這筆控制傳輸標為完成。")
            reasons.append("先釐清這筆請求在哪個階段停止，才能解釋後續請求。")
            strength = 90
        if (e["halted"] or e["error"]) and (supported or repeat):
            rules.append("response_change" if supported else "repeated_stop")
            facts.append(f"native Halted={e['halted']}、Error={e['error']}。")
            if supported:
                facts.append(f"相同地址／請求欄位的 transfer {supported['index']} 曾完成並有 {supported['data_length']} bytes 資料；兩次 wLength 為 {supported['requested_length']}／{e['requested_length']}。")
                reasons.append("這次回應與附近曾取得資料的同類請求不同，值得先比較參數與裝置回應。")
            else:
                facts.append(f"附近 transfer {repeat['index']} 也有相同完整請求且未正常完成。")
                reasons.append("同一組請求參數附近反覆停止，應從第一次停止展開檢查。")
            strength = max(strength, 70 if supported else 55)
        timing = timing_context(events, pos) if descriptor(e) else None
        declared = declared_followup(supported, e)
        if declared is not None and not e["halted"] and not e["error"]:
            rules.append("empty_descriptor_followup")
            facts.append(f"transfer {supported['index']} 已回傳同一 descriptor 的表頭，wTotalLength={declared}；接著這筆把 wLength 從 {supported['requested_length']} 增至 {e['requested_length']}，native 資料卻為 0 bytes。")
            reasons.append("先取得表頭再要求更多內容的流程在此失去資料；比孤立的資料不足旗標更值得先檢查。")
            strength = max(strength, 85)
        if (descriptor(e) and e["requested_length"] is not None and e["requested_length"] > 0 and e["data_length"] == 0
                and not e["halted"] and not e["error"] and timing
                and e["duration_ns"] > 10 * timing["p95_ns"]):
            rules.append("no_data_delay")
            facts.append(f"這筆要求 {e['requested_length']} bytes，native 資料階段為 0 bytes，耗時 {ns_text(e['duration_ns'])} 秒；native Completed={e['completed']}。")
            facts.append(f"附近同地址有 {timing['count']} 筆已完成且有資料的 descriptor 請求，耗時 P95 為 {ns_text(timing['p95_ns'])} 秒。")
            reasons.append("沒有資料與相對長等待同時出現，超過這份 trace 內附近參考耗時的 10 倍；這是檢查優先線索，並非 USB timeout 判定。")
            strength = max(strength, 80)
        issues = descriptor_issues(e)
        if issues:
            rules.append("descriptor_content")
            facts.extend(issues)
            reasons.append("native 傳輸完成後，內容仍有可核對的不一致；先查回傳欄位。")
            strength = max(strength, 65)
        if not rules:
            continue
        if e["data_length"] is not None:
            facts.append(f"已核對 native payload 前 8 bytes 與 SETUP 欄位相符；其後有 {e['data_length']} bytes 資料。")
        gaps = ["尚無已核實的 child packet 對應；Transfer ID 不等於 Packet ID。",
                "未由逐筆 handshake 證明 SETUP 已接受或 status stage 是否完成。",
                "相同地址不保證同一實體裝置；未觀察到的 reset 與預期負向測試仍需排除。"]
        tail = pos >= len(events) - 3
        if tail:
            gaps.append("位置接近本次控制傳輸觀測尾端；請先確認 capture 是否涵蓋後續回應。")
            strength -= 20
        if not e["setup_bytes_match"]:
            gaps.append("native payload 未確認為 SETUP 前綴表示，資料階段長度保持未知。")
        if e["duration_ns"] is None:
            gaps.append("此資料來源未提供完整 transfer duration；區段結尾只保留已知的時間點。")
        if "incomplete" in rules:
            if e["data_length"] == 0:
                guidance = f"先在 LeCroy 展開 transfer {e['index']} 的 SETUP，確認是否被 ACK；若已接受，再看裝置 IN 回應是持續 NAK、STALL 或無可見回應。若 capture 在此截斷，先補後段資料，不先改 descriptor 內容。"
            elif e["data_length"] is not None and e["data_length"] > 0:
                guidance = f"先展開 transfer {e['index']} 最後一筆資料之後的反向 status 交換；若 status 正常，再核對 native 完成旗標與擷取範圍；若沒有可見交換，檢查 host 是否繼續送出請求。"
            else:
                guidance = f"先展開 transfer {e['index']}，核對 SETUP 是否接受，再確認有無 DATA；有資料則查最後的 status 交換，缺後段擷取則先補 capture。"
        elif "empty_descriptor_followup" in rules:
            guidance = f"先對照 transfer {supported['index']} 表頭的 wTotalLength 與 transfer {e['index']} 的 wLength，再展開後一筆的第一個 IN 回應；若裝置拒絕，核對該長度是否應支援；若持續等待，追查第一個不同回應；若已有 DATA，先核對 native grouping／擷取完整性。"
        elif "no_data_delay" in rules:
            guidance = f"先展開 transfer {e['index']} 的第一筆 IN，確認是持續 NAK、STALL、無可見回應，還是 native grouping 未保留 DATA；若真的只有 SETUP 後長等待，再核對 host 是否送出後續交易與測試是否刻意等待。不要只憑 Completed=1 就把 descriptor 內容當成已取得。"
        elif "descriptor_content" in rules:
            guidance = f"先展開 transfer {e['index']} 的回傳 descriptor，逐項核對上列 type／length 欄位與本次 wLength；若內容符合測試預期，再核對測試條件，不把它當成傳輸未完成。"
        else:
            reference = supported["index"] if supported else repeat["index"]
            guidance = f"先比較 transfer {reference} 與 {e['index']} 的 wValue、wIndex、wLength 及資料／停止狀態；若看到 STALL，先核對這是否為預期拒絕的負向請求；若應支援，再查第一個不同回應，勿從最後一次重送開始。"
        hits.append({"position": pos, "event": e, "rules": rules, "facts": facts, "reasons": reasons,
                     "guidance": guidance, "gaps": gaps, "strength": strength,
                     "support_index": supported["index"] if supported else None,
                     "timing_references": timing["references"] if timing and "no_data_delay" in rules else []})
    episodes = []
    for hit in hits:
        e = hit["event"]
        match = None
        for ep in reversed(episodes):
            last = ep["hits"][-1]
            if request_key(last["event"], True) != request_key(e, True):
                continue
            middle = events[last["position"] + 1:hit["position"]]
            if (hit["position"] - last["position"] <= LOOKBACK_RECORDS
                    and e["timestamp_ns"] - last["event"]["timestamp_ns"] <= LOOKBACK_NS
                    and not any(boundary(x) or (request_key(x, True) == request_key(e, True) and successful(x)) for x in middle)):
                match = ep
            break
        if match is None:
            match = {"hits": []}
            episodes.append(match)
        match["hits"].append(hit)
    episodes.sort(key=lambda ep: (-max(h["strength"] for h in ep["hits"]), ep["hits"][0]["event"]["timestamp_ns"]))
    cards = []
    for rank, ep in enumerate(episodes[:3], 1):
        first, last = ep["hits"][0], ep["hits"][-1]
        e = first["event"]
        context = events[max(0, first["position"] - 3):last["position"] + 4]
        support_ids = {h["support_index"] for h in ep["hits"] if h["support_index"] is not None}
        support_ids.update(i for h in ep["hits"] for i in h["timing_references"])
        context = sorted({x["index"]: x for x in context + [x for x in events if x["index"] in support_ids]}.values(), key=lambda x:x["index"])
        cards.append({"rank": rank, "title": request_name(e) + "讀取流程" if descriptor(e) else request_name(e),
            "start_ns": e["timestamp_ns"], "end_ns": max(h["event"]["timestamp_ns"] + (h["event"]["duration_ns"] or 0) for h in ep["hits"]),
            "transfer_indices": [h["event"]["index"] for h in ep["hits"]], "address": e["address"], "endpoint": e["endpoint"],
            "facts": list(dict.fromkeys(f for h in ep["hits"] for f in h["facts"])),
            "reasons": list(dict.fromkeys(f for h in ep["hits"] for f in h["reasons"])),
            "next_step": first["guidance"], "evidence_gaps": list(dict.fromkeys(g for h in ep["hits"] for g in h["gaps"])),
            "rules": sorted({r for h in ep["hits"] for r in h["rules"]}), "context": context,
            "evidence_completeness": "partial", "packet_refs": None})
    return {"format": "usb-control-inspection/v1", "rule_version": RULE_VERSION,
            "trace_sha256": data["trace_sha256"], "extractor_sha256": data["extractor_sha256"],
            "scope": "USB2 standard EP0 control transfers / Chapter 9 inspection only",
            "status": "candidates_found" if cards else "no_supported_candidate", "candidates": cards,
            "episode_count": len(episodes), "omitted_episodes": max(0, len(episodes) - 3),
            "coverage": {k:data[k] for k in ("visited_transfers", "eligible_controls", "unsupported_controls", "truncated")},
            "analysis_inputs": ["native_control_records"], "labels_used": False, "markers_used": False,
            "known_failure_time_used": False, "verdict": "NOT_EVALUATED",
            "limitations": ["非 USB PASS／FAIL 或根因判定；NAK、short response、停止旗標本身不等於故障。",
                "原生 grouping 與 display／capture 完整性未獨立資格化；控制傳輸以外的 USB 行為不在分析範圍。",
                "排序是檢查優先順序，不是根因機率；無候選不代表整份 trace 正常。"]}


def render(model):
    esc = lambda s: html.escape(str(s), quote=True)
    shown = lambda v: "未知" if v is None else esc(v)
    def lis(values):
        return "<ul>" + "".join(f"<li>{esc(v)}</li>" for v in values) + "</ul>"
    def card(c):
        stamp = ns_text(c["start_ns"])
        ids = ", ".join(map(str, c["transfer_indices"]))
        table = "".join(f"<tr><td>{x['index']}</td><td>{ns_text(x['timestamp_ns'])}</td><td>{x['address']}/{x['endpoint']}</td><td>{esc(request_name(x))}</td><td>{shown(x['requested_length'])}</td><td>{shown(x['data_length'])}</td><td>{shown(x['completed'])}/{shown(x['halted'])}/{shown(x['error'])}</td></tr>" for x in c["context"])
        return f'''<article class="card" id="candidate-{c['rank']}"><div class="eyebrow">{'優先檢查' if c['rank']==1 else '次要線索'} · 證據部分缺漏</div>
<h2>{esc(c['title'])}</h2><div class="position"><strong>{stamp} 秒</strong> · Address {c['address']} / EP {c['endpoint']}<br>LeCroy Transfer {ids} <button data-copy="{stamp}" aria-label="複製時間">複製時間</button><button data-copy="{esc(ids)}" aria-label="複製 Transfer 編號">複製 Transfer 編號</button></div>
<h3>發生什麼事</h3>{lis(c['facts'])}<h3>為什麼先看這裡</h3>{lis(c['reasons'])}<div class="next"><h3>工程師下一步</h3><p>{esc(c['next_step'])}</p></div>
<details><summary>前後事件與證據缺口</summary><p>區段 {stamp}–{ns_text(c['end_ns'])} 秒；從第一筆候選展開。以下編號屬於 Transfer 層。</p><div class="scroll"><table><thead><tr><th>Transfer</th><th>時間（秒）</th><th>Ad/EP</th><th>請求</th><th>wLength</th><th>資料 bytes</th><th>完成/停止/錯誤</th></tr></thead><tbody>{table}</tbody></table></div>{lis(c['evidence_gaps'])}</details></article>'''
    cards = model["candidates"]
    content = card(cards[0]) if cards else '<article class="card empty"><h2>本次分析範圍內未找到足夠可疑的區段</h2><p>這表示目前證據不足以提出候選，並不是 USB PASS。若問題在其他 USB 類型、內容語意或未擷取的部分，本版無法排除。</p></article>'
    if len(cards) > 1:
        content += '<details class="secondary"><summary>另外 ' + str(len(cards)-1) + ' 個候選區段</summary>' + ''.join(card(c) for c in cards[1:]) + '</details>'
    coverage = model["coverage"]
    if coverage["truncated"]:
        content = '<p class="warning">擷取已達 100,000 筆上限，結果僅涵蓋保留的前段資料。</p>' + content
    return f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>USB 控制傳輸檢查導引</title><style>
:root{{color-scheme:light;--ink:#203243;--muted:#607184;--line:#dae3eb;--amber:#a8630b}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f7;color:var(--ink);font:16px/1.7 system-ui,"Microsoft JhengHei",sans-serif}}main{{max-width:1040px;margin:auto;padding:34px 22px 70px}}header{{margin-bottom:24px}}h1{{font-size:28px;line-height:1.35;margin:6px 0}}header p,.meta{{color:var(--muted)}}.eyebrow{{font-size:13px;font-weight:700;color:var(--amber);letter-spacing:.08em}}.card{{background:white;border:1px solid var(--line);border-top:4px solid #df9d40;border-radius:12px;padding:28px;margin:18px 0;box-shadow:0 4px 18px #20324308}}h2{{font-size:23px;line-height:1.45;margin:8px 0 18px}}h3{{font-size:16px;margin:24px 0 8px}}p,ul{{margin:8px 0}}li{{margin:6px 0}}.position{{border-left:3px solid #6c95b5;padding-left:16px;font-variant-numeric:tabular-nums}}button{{border:1px solid #c4d1dd;border-radius:5px;background:#f6f9fc;color:#244e70;padding:5px 9px;margin:7px 6px 0 0;cursor:pointer}}button:focus-visible,summary:focus-visible{{outline:3px solid #327cba;outline-offset:3px}}.next{{background:#edf4f9;border-radius:8px;padding:1px 20px 16px;margin-top:22px}}details{{border-top:1px solid var(--line);padding-top:16px;margin-top:22px}}summary{{cursor:pointer;font-weight:650;color:#365d7c}}.secondary{{border:0}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}th,td{{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left}}th{{background:#f4f7fa}}.warning{{background:#fff2d9;padding:16px;border-radius:8px}}.empty{{border-top-color:#7799b6}}footer{{margin-top:24px;font-size:14px;color:var(--muted)}}.hash{{word-break:break-all;font:12px ui-monospace,monospace}}@media(max-width:600px){{main{{padding:20px 12px}}.card{{padding:20px}}h1{{font-size:23px}}h2{{font-size:20px}}}}
</style></head><body><main><header><div class="eyebrow">單一 TRACE · USB2 CONTROL</div><h1>先看值得檢查的請求，再沿證據往下查</h1><p>分析範圍為 Chapter 9 標準 EP0 控制傳輸。搜尋不使用檔名標籤、失敗註記或已知時間。</p></header>{content}<p id="copy-status" role="status" aria-live="polite"></p><footer><details><summary>分析範圍與限制</summary>{lis(model['limitations'])}<p>可見 transfer callbacks：{coverage['visited_transfers']:,}；USB2 control records：{coverage['eligible_controls']:,}；略過的其他 control：{coverage['unsupported_controls']:,}。未顯示候選區段：{model['omitted_episodes']}。</p><p class="hash">Trace SHA-256: {esc(model['trace_sha256'])}</p><p>原始結果見同目錄 inspection.json；native 完成旗標並非本工具的測試合規判定。</p></details></footer></main><script>
document.querySelectorAll('[data-copy]').forEach(b=>b.addEventListener('click',async()=>{{let ok=false;try{{await navigator.clipboard.writeText(b.dataset.copy);ok=true}}catch(e){{let t=document.createElement('textarea');t.value=b.dataset.copy;document.body.appendChild(t);t.select();ok=document.execCommand('copy');t.remove()}}document.getElementById('copy-status').textContent=ok?'已複製，可貼到 LeCroy 定位。':'複製未完成，請選取畫面上的時間或編號。'}}));
</script></body></html>'''


def analyze_file(source, output):
    raw = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    data = normalize(raw)
    model = discover(data)
    model["analysis_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    model["raw_result_sha256"] = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    targets = [output / "inspection.json", output / "report.html"]
    if any(p.exists() for p in targets):
        raise InputError("Refusing to overwrite inspection/report")
    targets[0].write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    targets[1].write_text(render(model), encoding="utf-8")
    return model


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--input", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        model = analyze_file(args.input, args.output)
        print(json.dumps({"status": model["status"], "candidates": len(model["candidates"]), "report": str(args.output / "report.html")}, ensure_ascii=False))
    except (InputError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
