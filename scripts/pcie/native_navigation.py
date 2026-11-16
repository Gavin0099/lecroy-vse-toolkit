"""Packet identity and selection checks; no COM/UI side effects on import.

Selection is deliberately weaker than GUI navigation. PETracer 13.26 b43 can
return an out-of-range selection and a plausible timestamp without an error.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re
import time


class NavigationError(ValueError):
    pass


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def identity(path):
    path = Path(path).resolve()
    info = path.stat()
    return {"path": str(path), "sha256": digest(path), "bytes": info.st_size,
            "mtime_ns": info.st_mtime_ns, "readonly": not bool(info.st_mode & 0o222)}


def validate_request(request):
    if request.get("schema") != "pcie.navigation-probe/v1":
        raise NavigationError("unsupported request schema")
    for key in ("source_trace", "display_trace"):
        item = request.get(key, {})
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise NavigationError(key + " path required")
        if not Path(item["path"]).is_absolute():
            raise NavigationError(key + " requires an absolute path")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", str(item.get("sha256", ""))):
            raise NavigationError(key + " SHA-256 required")
        if Path(item["path"]).suffix.lower() != ".pex":
            raise NavigationError("only .pex display/source files are supported")
    anchors = request.get("anchors")
    if not isinstance(anchors, list) or not 1 <= len(anchors) <= 32:
        raise NavigationError("1..32 explicit anchors required")
    source_sha = request["source_trace"]["sha256"].lower()
    display_sha = request["display_trace"]["sha256"].lower()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise NavigationError("anchor must be an object")
        for key, expected in (("source_trace_sha256", source_sha), ("display_trace_sha256", display_sha)):
            if str(anchor.get(key, "")).lower() != expected:
                raise NavigationError("anchor trace identity mismatch: " + key)
        # A converted trace has its own numbering. No original-to-converted map
        # is inferred from matching timestamps, lengths or file names.
        namespace = anchor.get("packet_namespace")
        if namespace not in ("native_trace_packet_zero_based", "converted_trace_packet_zero_based"):
            raise NavigationError("unqualified Packet namespace")
        if source_sha != display_sha and namespace != "converted_trace_packet_zero_based":
            raise NavigationError("different source/display hashes require converted namespace")
        if type(anchor.get("display_level")) is not int or anchor["display_level"] != 0:
            raise NavigationError("only Packet level 0 is qualified")
        if type(anchor.get("packet_index")) is not int or anchor["packet_index"] < 0:
            raise NavigationError("Packet index must be a nonnegative integer")
        if "channel" not in anchor or anchor.get("direction") not in ("Upstream", "Downstream", "UNKNOWN"):
            raise NavigationError("channel and direction (or explicit UNKNOWN) required")
        if "timestamp" not in anchor:
            raise NavigationError("timestamp required; use null when precision is unknown")
        timestamp = anchor.get("timestamp")
        if timestamp is not None:
            if not isinstance(timestamp, dict) or timestamp.get("unit") != "ns":
                raise NavigationError("timestamp must use native nanoseconds or null")
            value = timestamp.get("value")
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise NavigationError("invalid native timestamp")
    return request


def verify_files(request):
    identities = {}
    for key in ("source_trace", "display_trace"):
        identities[key] = identity(request[key]["path"])
        if identities[key]["sha256"] != request[key]["sha256"].lower():
            raise NavigationError(key + " hash mismatch")
    return identities


def validate_index(index, packet_count):
    if type(packet_count) is not int or packet_count <= 0:
        raise NavigationError("native Packet count unavailable")
    if type(index) is not int or not 0 <= index < packet_count:
        raise NavigationError("Packet outside native range 0.." + str(packet_count - 1))


def invoke(target, method, *args):
    started = time.monotonic()
    try:
        value = getattr(target, method)(*args)
        return {"method": method, "args": list(args), "ok": True, "value": value,
                "elapsed_seconds": time.monotonic() - started, "hresult": None,
                "hresult_note": "successful HRESULT is not exposed by pywin32 dispatch"}
    except Exception as exc:
        return {"method": method, "args": list(args), "ok": False,
                "elapsed_seconds": time.monotonic() - started, "error": str(exc),
                "exception_type": type(exc).__name__, "hresult": getattr(exc, "hresult", None),
                "excepinfo": getattr(exc, "excepinfo", None)}


def select_packet(target, anchor, packet_count):
    validate_index(anchor["packet_index"], packet_count)
    result = {"locator": anchor, "gui_navigation": "NOT_VERIFIED", "calls": [],
              "direction_verification": "GUI_OR_NATIVE_EXPORT_REQUIRED"}
    started = time.monotonic()
    def call(method, *args):
        row = invoke(target, method, *args)
        result["calls"].append(row)
        return row
    selected = call("SelectDisplayUnit", 0, anchor["packet_index"])
    if not selected["ok"]:
        result["status"] = "API_FAILED"
    else:
        readback = call("GetSelectedDispUnit")
        visible = call("GetFirstVisibleDispUnit")
        timestamp = call("GetPacketStartTime", 0, anchor["packet_index"])
        actual = readback.get("value")
        matches = (readback["ok"] and isinstance(actual, (tuple, list))
                   and list(actual) == [0, anchor["packet_index"]])
        result["selection_matches"] = matches
        result["first_visible"] = visible.get("value") if visible["ok"] else None
        result["timestamp_ns"] = timestamp.get("value") if timestamp["ok"] else None
        expected = anchor["timestamp"]
        result["timestamp_matches"] = (timestamp["ok"] and timestamp.get("value") == expected["value"]) if expected else None
        result["status"] = "SELECTION_VERIFIED" if matches else "SELECTION_NOT_VERIFIED"
        if result["timestamp_matches"] is False:
            result["status"] = "TIMESTAMP_MISMATCH"
        # Neither first_visible == index nor a correct readback proves that
        # the intended file/view/direction was actually visible to an engineer.
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def manual_instructions(work_path, anchor):
    return {"file": str(work_path), "sha256": anchor["display_trace_sha256"],
            "steps": ["在 PETracer 確認此工作副本。", "按 Ctrl+G（Search → Go to Packet）。",
                      "輸入 Packet " + str(anchor["packet_index"]) + " 並按 Enter。",
                      "核對 Packet、時間與方向；API 已選取不代表主視圖已定位。"]}
