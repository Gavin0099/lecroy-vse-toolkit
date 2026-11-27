"""Run the PCIe event probe against an isolated PETracer working copy."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

SCRIPT = Path(__file__).with_name("protocol-events.pevs")
MAX_PACKET_INDEX = 2_147_483_647


def identity(path: Path) -> dict:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    info = path.stat()
    return {"sha256": digest, "bytes": info.st_size, "mtime_ns": info.st_mtime_ns, "mode": info.st_mode}


def render_probe(template: str, first: int, last: int) -> str:
    if not 0 <= first <= last <= MAX_PACKET_INDEX:
        raise ValueError("invalid inclusive packet window")
    for name, value in (("FIRST_PACKET", first), ("LAST_PACKET", last)):
        template, count = re.subn(rf"(?m)^const {name} = [0-9]+;$", f"const {name} = {value};", template)
        if count != 1:
            raise ValueError(f"expected exactly one {name} declaration")
    return template


def verify_conversion(source: dict, display: dict, manifest: Path | None) -> str | None:
    if source["sha256"] == display["sha256"]:
        return None
    if manifest is None:
        raise ValueError("a sealed conversion manifest is required for a different display copy")
    raw = manifest.read_bytes()
    data = json.loads(raw)
    binding = data.get("binding", {})
    if (data.get("status") != "SEALED_CONVERSION" or data.get("cleanup_confirmed") is not True
            or binding.get("schema") != "pcie.converted-copy/v1"
            or binding.get("source_sha256") != source["sha256"]
            or data.get("display_sha256") != display["sha256"] or data.get("bytes") != display["bytes"]):
        raise ValueError("conversion manifest does not bind these two inputs")
    return hashlib.sha256(raw).hexdigest()


def analyzer_pids() -> set[int]:
    process = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq PETracer.exe", "/FO", "CSV", "/NH"],
        check=True, capture_output=True, text=True, encoding="mbcs", errors="replace",
    )
    return {
        int(row[1]) for row in csv.reader(process.stdout.splitlines())
        if len(row) >= 2 and row[0].casefold() == "petracer.exe"
    }


def peak_working_set(pid: int) -> int | None:
    import pywintypes
    import win32api
    import win32con
    import win32process

    try:
        access = win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ
        process = win32api.OpenProcess(access, False, pid)
        try:
            return win32process.GetProcessMemoryInfo(process)["PeakWorkingSetSize"]
        finally:
            process.Close()
    except (OSError, pywintypes.error):
        return None


def collect(working: Path, script: Path, log: Path, timeout: float, receipt: dict) -> None:
    import pythoncom
    import win32com.client

    class Events:
        def OnVScriptReportUpdated(self, line, tag):
            try:
                stream.write(str(line).rstrip("\r\n") + "\n")
            except (OSError, UnicodeError) as exc:
                data["error"] = exc

        def OnVScriptFinished(self, name, result, tag):
            data["result"] = int(result)

    data = {}
    analyzer = trace = engine = events = None
    owned = set()
    started = time.monotonic()
    pythoncom.CoInitialize()
    try:
        if analyzer_pids():
            raise RuntimeError("PETracer already has a session")
        analyzer = win32com.client.Dispatch("CATC.PETracer")
        owned = analyzer_pids()
        if len(owned) != 1:
            raise RuntimeError("ambiguous analyzer ownership; no trace opened")
        receipt["analyzer_pid"] = pid = next(iter(owned))
        trace = analyzer.OpenFile(str(working))
        receipt["native_packet_count"] = int(trace.GetPacketsCountEx())
        if receipt["window"][1] >= receipt["native_packet_count"]:
            raise ValueError("window exceeds the native packet range")
        receipt["open_seconds"] = round(time.monotonic() - started, 3)
        started = time.monotonic()
        with log.open("x", encoding="utf-8", newline="\n") as stream:
            engine = trace.GetVScriptEngine(str(script))
            events = win32com.client.WithEvents(engine, Events)
            engine.LaunchVScript()
            while "result" not in data:
                pythoncom.PumpWaitingMessages()
                if "error" in data:
                    raise data["error"]
                if time.monotonic() - started >= timeout:
                    raise TimeoutError("VSE completion callback timed out")
                time.sleep(0.001)
            for _ in range(20):
                pythoncom.PumpWaitingMessages()
                time.sleep(0.05)
            if "error" in data:
                raise data["error"]
        receipt["script_result"] = data["result"]
        receipt["script_seconds"] = round(time.monotonic() - started, 3)
        receipt["analyzer_peak_working_set_bytes"] = peak_working_set(pid)
        if data["result"] != 2:
            raise RuntimeError(f"VSE did not report DONE: {data['result']}")
    finally:
        try:
            if events is not None:
                events.close()
        finally:
            try:
                if trace is not None:
                    trace.Close()
            finally:
                events = engine = trace = analyzer = None
                pythoncom.CoUninitialize()
                deadline = time.monotonic() + 45
                remaining = owned & analyzer_pids()
                while remaining and time.monotonic() < deadline:
                    time.sleep(0.25)
                    remaining = owned & analyzer_pids()
                receipt["owned_analyzer_pids_remaining"] = sorted(remaining)


def run(source: Path, display: Path, expected_display: str, output: Path,
        first: int, last: int, timeout: float, conversion_manifest: Path | None = None) -> dict:
    source = source.resolve(strict=True)
    display = display.resolve(strict=True)
    if any(path.suffix.lower() != ".pex" or not path.is_file() for path in (source, display)):
        raise ValueError("source and display must be .pex files")
    if not 0 < timeout < float("inf"):
        raise ValueError("positive finite timeout required")
    before = {"source": identity(source), "display": identity(display)}
    if before["display"]["sha256"] != expected_display.lower():
        raise ValueError("display input does not match the supplied SHA-256")
    conversion_sha256 = verify_conversion(before["source"], before["display"], conversion_manifest)
    rendered = render_probe(SCRIPT.read_text(encoding="utf-8"), first, last)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    script = output / SCRIPT.name
    script.write_text(rendered, encoding="utf-8", newline="\n")
    working = output / "display-working.pex"
    shutil.copyfile(display, working)
    working.chmod(stat.S_IREAD)
    before["working"] = identity(working)
    before["script"] = identity(script)
    log = output / "protocol-events.txt"
    receipt = {
        "schema": "pcie.protocol-events-acquisition/v1",
        "window": [first, last],
        "packet_namespace": ("source_packet" if before["source"]["sha256"] == expected_display.lower()
                             else "display_copy_packet"),
        "filter_status": "UNKNOWN",
        "conversion_manifest_sha256": conversion_sha256,
        "before": before,
        "status": "FAILED",
    }
    try:
        if before["working"]["sha256"] != expected_display.lower():
            raise ValueError("working copy does not match the verified display input")
        collect(working, script, log, timeout, receipt)
        if receipt["owned_analyzer_pids_remaining"]:
            raise RuntimeError("owned analyzer cleanup could not be verified")
        receipt["status"] = "VSE_DONE"
    except Exception as exc:
        # pywin32 failures are platform-specific; preserve the failed receipt.
        receipt["error"] = str(exc)
    finally:
        receipt["after"] = {key: identity(path) for key, path in (
            ("source", source), ("display", display), ("working", working), ("script", script)
        )}
        receipt["inputs_unchanged"] = before == receipt["after"]
        if not receipt["inputs_unchanged"]:
            receipt["status"] = "INTEGRITY_FAILED"
        if log.is_file():
            receipt["report"] = identity(log)
        (output / "acquisition.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--display", required=True, type=Path, help="Same source or a previously verified conversion")
    parser.add_argument("--display-sha256", required=True)
    parser.add_argument("--conversion-manifest", type=Path, help="Sealed source/display conversion receipt")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--first", type=int, required=True)
    parser.add_argument("--last", type=int, required=True)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()
    try:
        receipt = run(args.source, args.display, args.display_sha256, args.output_dir,
                      args.first, args.last, args.timeout, args.conversion_manifest)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: receipt[key] for key in ("status", "inputs_unchanged", "window")}, ensure_ascii=False))
    return 0 if receipt["status"] == "VSE_DONE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
