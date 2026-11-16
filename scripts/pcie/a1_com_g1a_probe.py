#!/usr/bin/env python3
"""PCIe-A1: COM automation qualification probe (G1a on a known trace only).

Question: can COM, without any mouse/keyboard input to the PETracer GUI, run the existing
g1a-tlp-count VSE script on a known-good trace and reach the same semantic result as the
verified GUI route? This is a qualification probe, not part of the triage flow.

Route: CATC.PETracer -> OpenFile -> GetVScriptEngine(full script path) -> event sink ->
LaunchVScript -> wait for OnVScriptFinished while collecting OnVScriptReportUpdated lines ->
trace Close -> wait for the PETracer process to exit. No window is hidden and no input is sent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from verify_g1a_log import HEADER, RUNTIME_ERROR_RE, SUMMARY_RE, G1aLogError, check_log  # noqa: E402

VS_RESULT = {-3: "FEATURE_NOT_LICENSED", -2: "SCRIPT_RUNNING", -1: "SCRIPT_NOT_FOUND", 0: "FAILED", 1: "PASSED", 2: "DONE"}
EVENTS: dict = {"lines": [], "finished": None}


def now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(message: str) -> None:
    print(f"{now()} {message}", flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def identity(path: Path) -> dict:
    stat = path.stat()
    return {"path": str(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256(path)}


def petracer_pids() -> list[int]:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PETracer.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, encoding="mbcs", errors="replace").stdout
    return [int(row.split(",")[1].strip('"')) for row in out.splitlines() if row.startswith('"PETracer.exe"')]


class VseEvents:
    def OnVScriptReportUpdated(self, newLine, Tag):  # noqa: N802 - COM event name
        EVENTS["lines"].append(str(newLine))

    def OnVScriptFinished(self, script_name, result, Tag):  # noqa: N802 - COM event name
        EVENTS["finished"] = {"script_name": str(script_name), "result": int(result), "tag": int(Tag), "at": now()}


def semantic(text: str, expected: dict) -> dict:
    lines = [line.strip() for piece in text.splitlines() for line in [piece]]
    summaries = [m for line in lines if (m := SUMMARY_RE.fullmatch(line))]
    result = {
        "header_lines": lines.count(HEADER),
        "summary_lines": len(summaries),
        "runtime_error_marker": any(RUNTIME_ERROR_RE.search(line) for line in lines),
    }
    if len(summaries) == 1:
        s = summaries[0]
        result.update(tlp_count=int(s["count"]), first_index=int(s["first_index"]), first_time=s["first_time"].strip(),
                      last_index=int(s["last_index"]))
    result["matches_gui"] = (result["header_lines"] == 1 and len(summaries) == 1 and not result["runtime_error_marker"]
                             and all(result.get(k) == v for k, v in expected.items()))
    try:
        check_log(text)
        result["full_gui_log_verifier"] = "ACCEPTED"
    except G1aLogError as exc:
        result["full_gui_log_verifier"] = f"NOT_ACCEPTED (informational): {exc}"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True, help="Read-only working copy of the known trace")
    parser.add_argument("--source", type=Path, required=True, help="Original trace; hashed only, never opened")
    parser.add_argument("--script", type=Path, required=True, help="Full path of the deployed g1a-tlp-count.pevs")
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--expected-first", type=int, required=True)
    parser.add_argument("--expected-last", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print(f"Refusing to reuse existing output directory: {args.output_dir}", file=sys.stderr)
        return 2
    if petracer_pids():
        print("PETracer is already running; A1 needs a clean start", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True)

    record: dict = {"schema": "pcie.a1-com-probe/v1", "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "route": "CATC.PETracer.OpenFile -> GetVScriptEngine -> LaunchVScript + events -> Close",
                    "input_sent_to_gui": "none", "window_hidden": False, "steps": {}}
    record["pre"] = {"source": identity(args.source), "trace": identity(args.trace), "script": identity(args.script)}
    steps = record["steps"]
    analyzer = trace = engine = None
    t0 = time.monotonic()
    try:
        pythoncom.CoInitialize()
        analyzer = win32com.client.Dispatch("CATC.PETracer")
        steps["create"] = {"ok": True, "seconds": round(time.monotonic() - t0, 1), "pids": petracer_pids()}
        log(f"CATC.PETracer created, PETracer pids {steps['create']['pids']}")

        t = time.monotonic()
        trace = analyzer.OpenFile(str(args.trace))
        steps["open_file"] = {"ok": trace is not None, "seconds": round(time.monotonic() - t, 1)}
        log(f"OpenFile returned after {steps['open_file']['seconds']} s")

        engine_disp = trace.GetVScriptEngine(str(args.script))
        engine = win32com.client.WithEvents(engine_disp, VseEvents)
        engine_disp.Tag = 0xA1
        steps["get_engine"] = {"ok": True, "vscript_name": str(engine_disp.VScriptName)}
        log(f"engine ready, VScriptName {steps['get_engine']['vscript_name']}")

        t = time.monotonic()
        launch = engine_disp.LaunchVScript()
        steps["launch"] = {"ok": True, "return": None if launch is None else str(launch)}
        log("LaunchVScript returned; waiting for OnVScriptFinished")
        while EVENTS["finished"] is None and time.monotonic() - t < args.timeout:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.05)
        for _ in range(20):  # let trailing report events drain
            pythoncom.PumpWaitingMessages()
            time.sleep(0.05)
        finished = EVENTS["finished"]
        steps["finish_event"] = {"ok": finished is not None, "seconds": round(time.monotonic() - t, 1), "event": finished,
                                 "result_name": VS_RESULT.get(finished["result"]) if finished else None}
        log(f"finish event: {finished}")
    except pythoncom.com_error as exc:
        record["com_error"] = repr(exc)
        log(f"COM error: {exc!r}")
    finally:
        # Each event is one ReportText call without its line break; the GUI shows one event per line.
        text = "\n".join(EVENTS["lines"])
        raw = args.output_dir / "com-vse-report-lines.txt"
        raw.write_text(text, encoding="utf-8", newline="")
        (args.output_dir / "com-vse-report-lines.json").write_text(json.dumps(EVENTS["lines"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        record["report_events"] = {"count": len(EVENTS["lines"]), "text_sha256": sha256(raw)}
        try:
            if trace is not None:
                trace.Close()
                steps["close"] = {"ok": True}
        except pythoncom.com_error as exc:
            steps["close"] = {"ok": False, "error": repr(exc)}
        engine = trace = analyzer = None
        pythoncom.CoUninitialize()
        deadline = time.monotonic() + 90
        while petracer_pids() and time.monotonic() < deadline:
            time.sleep(1)
        steps["process_exit"] = {"ok": not petracer_pids(), "remaining_pids": petracer_pids()}
        log(f"PETracer remaining pids after release: {steps['process_exit']['remaining_pids']}")

    expected = {"tlp_count": args.expected_count, "first_index": args.expected_first, "last_index": args.expected_last}
    record["expected_from_gui_route"] = expected
    record["semantic"] = semantic(text, expected)
    record["post"] = {"source": identity(args.source), "trace": identity(args.trace)}
    unchanged = all(record["pre"][k] == record["post"][k] for k in ("source", "trace"))
    record["identities_unchanged"] = unchanged

    control = [steps.get(k, {}).get("ok") for k in ("create", "open_file", "get_engine", "launch", "finish_event")]
    if all(control) and record["semantic"]["matches_gui"] and unchanged and steps["process_exit"]["ok"] and "com_error" not in record:
        record["status"] = "A1_PASS"
    elif steps.get("open_file", {}).get("ok") and steps.get("launch", {}).get("ok"):
        record["status"] = "A1_PARTIAL"
    else:
        record["status"] = "A1_FAIL"
    record["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (args.output_dir / "a1-probe-result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("status", "semantic", "identities_unchanged", "steps", "report_events")}, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "A1_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
