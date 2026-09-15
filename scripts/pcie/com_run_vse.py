#!/usr/bin/env python3
"""Run one deployed VSE script on one trace through COM and save its report text.

Uses the COM control path qualified in PCIe-A1 (CATC.PETracer -> OpenFile -> GetVScriptEngine ->
LaunchVScript with OnVScriptFinished/OnVScriptReportUpdated). It sends no GUI input except one
cleanup BM_CLICK on a PETracer error dialog (e.g. a VSE parse error, which otherwise blocks the run
forever; recorded in com-run.json). It applies no semantic checks (each probe keeps its own
verifier) and fails closed on a missing finish event, an error dialog, a changed protected file or
a PETracer process that does not exit.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ctypes
from ctypes import wintypes

import pythoncom
import win32com.client

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from a1_com_g1a_probe import EVENTS, VS_RESULT, VseEvents, identity, log, petracer_pids, sha256  # noqa: E402


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_ENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _window_text(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(2048)
    result = ctypes.c_size_t()
    _user32.SendMessageTimeoutW(hwnd, 0x000D, 2048, buffer, 0x0002, 500, ctypes.byref(result))  # WM_GETTEXT, abort if hung
    return buffer.value


def _class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def error_dialogs(pids: list[int]) -> list[dict]:
    """Visible PETracer #32770 dialogs whose text mentions an error (e.g. a VSE parse error)."""
    found: list[dict] = []

    def on_top(hwnd, _):
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and _user32.IsWindowVisible(hwnd) and _class_name(hwnd) == "#32770":
            children: list[tuple[int, str, str]] = []
            _user32.EnumChildWindows(hwnd, _ENUM(lambda h, __: children.append((h, _class_name(h), _window_text(h))) or True), 0)
            texts = [t for _, _, t in children if t]
            if any("error" in t.lower() for t in texts):
                buttons = [h for h, c, _ in children if c == "Button"]
                found.append({"hwnd": hwnd, "title": _window_text(hwnd), "texts": texts, "button": buttons[0] if buttons else None})
        return True

    _user32.EnumWindows(_ENUM(on_top), 0)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True, help="Working copy to open (should be read-only)")
    parser.add_argument("--protect", type=Path, action="append", default=[], help="Other files that must stay unchanged (hashed only)")
    parser.add_argument("--script", type=Path, required=True, help="Full path of the deployed .pevs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print(f"Refusing to reuse existing output directory: {args.output_dir}", file=sys.stderr)
        return 2
    if petracer_pids():
        print("PETracer is already running; a COM run needs a clean start", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)

    watched = [args.trace, *args.protect]
    run: dict = {"schema": "pcie.com-vse-run/v1", "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "input_sent_to_gui": "none", "window_hidden": False, "steps": {},
                 "pre": {"files": [identity(p) for p in watched], "script": identity(args.script)}}
    steps = run["steps"]
    trace = None
    try:
        pythoncom.CoInitialize()
        t = time.monotonic()
        analyzer = win32com.client.Dispatch("CATC.PETracer")
        steps["create"] = {"ok": True, "seconds": round(time.monotonic() - t, 1)}
        t = time.monotonic()
        trace = analyzer.OpenFile(str(args.trace))
        steps["open_file"] = {"ok": trace is not None, "seconds": round(time.monotonic() - t, 1)}
        log(f"OpenFile returned after {steps['open_file']['seconds']} s")
        engine_disp = trace.GetVScriptEngine(str(args.script))
        engine = win32com.client.WithEvents(engine_disp, VseEvents)
        engine_disp.Tag = 0xB1
        steps["get_engine"] = {"ok": True, "vscript_name": str(engine_disp.VScriptName)}
        t = time.monotonic()
        engine_disp.LaunchVScript()
        log("LaunchVScript returned; waiting for OnVScriptFinished")
        last_report = last_dialog_check = time.monotonic()
        while EVENTS["finished"] is None and time.monotonic() - t < args.timeout:
            pythoncom.PumpWaitingMessages()
            if time.monotonic() - last_dialog_check > 2:
                last_dialog_check = time.monotonic()
                dialogs = error_dialogs(petracer_pids())
                if dialogs:
                    # A modal error dialog blocks the script forever; record it, dismiss it (cleanup input) and stop.
                    run["error_dialogs"] = [{k: d[k] for k in ("title", "texts")} for d in dialogs]
                    for d in dialogs:
                        if d["button"]:
                            _user32.PostMessageW(d["button"], 0x00F5, 0, 0)  # BM_CLICK
                    run["input_sent_to_gui"] = "BM_CLICK on error dialog button (cleanup only)"
                    log(f"error dialog detected, run stopped: {run['error_dialogs']}")
                    break
            if time.monotonic() - last_report > 60:
                log(f"still running, {len(EVENTS['lines'])} report events so far")
                last_report = time.monotonic()
            time.sleep(0.05)
        for _ in range(20):
            pythoncom.PumpWaitingMessages()
            time.sleep(0.05)
        finished = EVENTS["finished"]
        steps["finish_event"] = {"ok": finished is not None, "seconds": round(time.monotonic() - t, 1), "event": finished,
                                 "result_name": VS_RESULT.get(finished["result"]) if finished else None}
        log(f"finish event: {finished}")
        del engine
    except pythoncom.com_error as exc:
        run["com_error"] = repr(exc)
        log(f"COM error: {exc!r}")
    finally:
        # Each event is one ReportText call without its line break; the GUI shows one event per line.
        output = args.output_dir / "vse-output.txt"
        output.write_text("\n".join(EVENTS["lines"]), encoding="utf-8", newline="")
        (args.output_dir / "report-lines.json").write_text(json.dumps(EVENTS["lines"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        run["output"] = {"report_events": len(EVENTS["lines"]), "vse_output_sha256": sha256(output)}
        try:
            if trace is not None:
                trace.Close()
                steps["close"] = {"ok": True}
        except pythoncom.com_error as exc:
            steps["close"] = {"ok": False, "error": repr(exc)}
        trace = analyzer = engine_disp = None
        pythoncom.CoUninitialize()
        deadline = time.monotonic() + 120
        while petracer_pids() and time.monotonic() < deadline:
            time.sleep(1)
        steps["process_exit"] = {"ok": not petracer_pids(), "remaining_pids": petracer_pids()}
        log(f"PETracer remaining pids after release: {steps['process_exit']['remaining_pids']}")

    run["post"] = {"files": [identity(p) for p in watched]}
    run["identities_unchanged"] = run["pre"]["files"] == run["post"]["files"]
    finished = steps.get("finish_event", {})
    ok = (all(steps.get(k, {}).get("ok") for k in ("create", "open_file", "get_engine", "finish_event", "process_exit"))
          and "com_error" not in run and "error_dialogs" not in run and run["identities_unchanged"]
          and finished.get("result_name") not in ("SCRIPT_NOT_FOUND", "FEATURE_NOT_LICENSED", "SCRIPT_RUNNING"))
    run["status"] = "COM_RUN_COMPLETE" if ok else "COM_RUN_FAILED"
    run["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (args.output_dir / "com-run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: run[k] for k in ("status", "identities_unchanged", "steps", "output")}, ensure_ascii=False, indent=2))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
