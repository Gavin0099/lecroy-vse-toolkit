"""PCIE-02A replayable COM selection qualification. Never claims GUI landing.

Run with --request request.json --output NEW_DIRECTORY [--timeout 120].
An existing PETracer process causes a restricted-mode refusal before Dispatch.
Timeout terminates only our Python worker; native cancellation is UNKNOWN.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/pcie"))
import native_navigation as nav

METHODS = ("SelectDisplayUnit", "GetSelectedDispUnit", "GetFirstVisibleDispUnit",
           "GetPacketStartTime", "GetPacketByTime", "SetClosePolicy")


def read_json(path, *, retry_seconds=2):
    """Read one complete receipt, tolerating brief Windows sharing denials.

    Antivirus/indexers can still deny reads briefly. Retry only sharing/access
    errors, with a deadline; malformed JSON and persistent denial remain errors.
    A failed read must never be replaced with a fabricated completion receipt.
    """
    path = Path(path)
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            return json.loads(path.read_text(encoding='utf-8-sig'))
        except OSError as exc:
            retryable = (getattr(exc, 'winerror', None) in (2, 5, 32, 33)
                or isinstance(exc, (PermissionError, FileNotFoundError)))
            if not retryable or time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    # Windows readers can temporarily deny DELETE sharing, which is required
    # for atomic replacement. Keep the old complete JSON until a bounded retry
    # succeeds; never truncate it or turn a persistent denial into success.
    deadline = time.monotonic() + 2
    while True:
        try:
            temporary.replace(path)
            return
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(.05)


def processes():
    # Process inventory only. No GUI automation or termination of PETracer.
    value = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PETracer.exe", "/FO", "CSV", "/NH"],
                           check=True, capture_output=True, text=True, encoding="mbcs", errors="replace",
                           timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return [int(row.split(",")[1].strip('"')) for row in value.stdout.splitlines()
            if row.lower().startswith('"petracer.exe"')]


def capabilities():
    import pythoncom
    import win32api
    import winreg
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "CATC.PETracer\\CLSID") as key:
        clsid = winreg.QueryValueEx(key, None)[0]
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "CLSID\\" + clsid + "\\LocalServer32") as key:
        command = winreg.QueryValueEx(key, None)[0]
    # Registered EXE may be quoted or have an Automation suffix.
    end = command.lower().find(".exe")
    executable = Path(command[:end + 4].strip('" '))
    library = executable.parent / "PEAutomation.tlb"
    info = win32api.GetFileVersionInfo(str(executable), "\\")
    ms, ls = info["FileVersionMS"], info["FileVersionLS"]
    version = ".".join(str(x) for x in (ms >> 16, ms & 65535, ls >> 16, ls & 65535))
    tlb = pythoncom.LoadTypeLib(str(library))
    interfaces = []
    for i in range(tlb.GetTypeInfoCount()):
        name = tlb.GetDocumentation(i)[0]
        if not name.startswith("IPETraceForScript"):
            continue
        interface = tlb.GetTypeInfo(i)
        found = {}
        for j in range(interface.GetTypeAttr().cFuncs):
            function = interface.GetFuncDesc(j)
            method = interface.GetDocumentation(function.memid)[0]
            if method in METHODS:
                found[method] = function.memid
        if found:
            interfaces.append({"name": name, "iid": str(interface.GetTypeAttr().iid), "methods": found})
    return {"executable": str(executable), "file_version": version, "typelib": str(library),
            "typelib_sha256": nav.digest(library), "interfaces": interfaces}


def worker(request_path, output):
    receipt = {"started_utc": datetime.now(timezone.utc).isoformat(), "stage": "preflight",
               "status": "RUNNING", "open_file_count": 0, "anchors": [],
               "gui_navigation": "NOT_VERIFIED", "set_close_policy_used": False,
               "coexistence": "RESTRICTED_NO_EXISTING_SESSION"}
    target = output / "worker.json"
    def save(): write(target, receipt)
    trace = analyzer = selector = None
    initialized = False
    before = None
    save()
    try:
        request = nav.validate_request(json.loads(request_path.read_text(encoding="utf-8-sig")))
        before = nav.verify_files(request)
        receipt["before"] = before
        receipt["existing_pids"] = processes()
        if receipt["existing_pids"]:
            receipt["status"] = "EXISTING_SESSION_BLOCKED"
            return 2
        receipt["capabilities"] = capabilities()
        work = output / "display-working.pex"
        shutil.copyfile(request["display_trace"]["path"], work)
        work.chmod(0o444)
        receipt["working_before"] = nav.identity(work)
        if receipt["working_before"]["sha256"] != request["display_trace"]["sha256"].lower():
            raise nav.NavigationError("working copy hash mismatch")
        if processes():
            receipt["status"] = "EXISTING_SESSION_BLOCKED"
            return 2
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        initialized = True
        receipt["stage"] = "create_com"; save()
        analyzer = win32com.client.Dispatch("CATC.PETracer")
        receipt["created_pids"] = processes()
        if len(receipt["created_pids"]) != 1:
            raise nav.NavigationError("ambiguous native process ownership; no file opened")
        receipt["stage"] = "open_working_copy"; save()
        trace = analyzer.OpenFile(str(work.resolve()))
        receipt["open_file_count"] += 1
        receipt["native_trace_name"] = trace.GetName()
        selector = win32com.client.CastTo(trace, "IPETraceForScript15")
        receipt["runtime_methods"] = {}
        for method in METHODS:
            row = nav.invoke(selector._oleobj_, "GetIDsOfNames", method)
            receipt["runtime_methods"][method] = row
        count = int(selector.GetPacketsCountEx())
        receipt["packet_count"] = count
        for anchor in request["anchors"]:
            receipt["stage"] = "select_packet_" + str(anchor["packet_index"]); save()
            try:
                row = nav.select_packet(selector, anchor, count)
            except nav.NavigationError as exc:
                row = {"locator": anchor, "status": "INVALID_PACKET", "error": str(exc), "calls": []}
            row["manual_fallback"] = nav.manual_instructions(work, anchor)
            receipt["anchors"].append(row); save()
        receipt["status"] = ("SELECTION_ONLY_COMPLETE" if all(row["status"] == "SELECTION_VERIFIED"
                             for row in receipt["anchors"]) else "SELECTION_INCOMPLETE")
    except Exception as exc:
        receipt.update(status="FAILED", error=str(exc), exception_type=type(exc).__name__,
                       hresult=getattr(exc, "hresult", None), excepinfo=getattr(exc, "excepinfo", None))
    finally:
        if trace is not None:
            receipt["stage"] = "close_owned_trace"; save()
            receipt["close"] = nav.invoke(trace, "Close")
        selector = trace = analyzer = None
        if initialized:
            pythoncom.CoUninitialize()
        if receipt.get("created_pids"):
            deadline = time.monotonic() + 10
            while processes() and time.monotonic() < deadline:
                time.sleep(0.2)
        receipt["remaining_pids"] = processes()
        try:
            if before is not None:
                receipt["after"] = nav.verify_files(request)
                receipt["inputs_unchanged"] = before == receipt["after"]
            if "working_before" in receipt:
                receipt["working_after"] = nav.identity(work)
                receipt["working_unchanged"] = receipt["working_before"] == receipt["working_after"]
        except Exception as exc:
            receipt["integrity_error"] = str(exc)
            receipt["inputs_unchanged"] = False
        if receipt.get("inputs_unchanged") is False or receipt.get("working_unchanged") is False:
            receipt["status"] = "INTEGRITY_FAILED"
        if receipt.get("created_pids") and (receipt["remaining_pids"] or not receipt.get("close", {}).get("ok")):
            receipt["status"] = "NATIVE_CLEANUP_UNCONFIRMED"
        receipt["stage"] = "finished"; save()
    return 0 if receipt["status"] == "SELECTION_ONLY_COMPLETE" else 2


def supervise(command, output, timeout):
    if not math_is_positive(timeout):
        raise nav.NavigationError("timeout must be a positive finite number")
    started = time.monotonic()
    with (output / "worker.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            code = process.wait(timeout=timeout)
            result = {"status": "WORKER_EXITED", "worker_exit_code": code}
        except subprocess.TimeoutExpired:
            process.kill()  # The exact Python worker we created, never PETracer.
            process.wait(timeout=10)
            result = {"status": "WORKER_TIMED_OUT", "worker_exit_code": process.returncode,
                      "native_cancelled": "UNKNOWN", "native_process_terminated": False,
                      "recovery": "Inspect PETracer and worker.json; do not restart while its session remains open."}
    result["elapsed_seconds"] = time.monotonic() - started
    return result


def math_is_positive(value):
    import math
    return math.isfinite(value) and value > 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if args.worker:
        return worker(args.request.resolve(), output)
    if output.exists():
        parser.error("fresh output directory required")
    request = nav.validate_request(json.loads(args.request.read_text(encoding="utf-8-sig")))
    before = nav.verify_files(request)
    if not math_is_positive(args.timeout):
        parser.error("positive finite timeout required")
    output.mkdir(parents=True)
    write(output / "request.json", request)
    result = supervise([sys.executable, str(Path(__file__).resolve()), "--worker", "--request",
                        str(output / "request.json"), "--output", str(output)], output, args.timeout)
    result["before"] = before
    try:
        result["after"] = nav.verify_files(request)
        result["inputs_unchanged"] = before == result["after"]
    except Exception as exc:
        result.update(inputs_unchanged=False, integrity_error=str(exc))
    result["remaining_native_pids"] = processes()
    write(output / "supervisor.json", result)
    print(json.dumps(result, ensure_ascii=False))
    if not result["inputs_unchanged"]:
        return 3
    return result["worker_exit_code"] if result["status"] == "WORKER_EXITED" else 4


if __name__ == "__main__":
    raise SystemExit(main())
