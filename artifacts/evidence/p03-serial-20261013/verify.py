import hashlib
import json
import re
from pathlib import Path
import stat
import subprocess
import sys
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
FROZEN = Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
sys.path.insert(0, str(ROOT / "tools"))
import pcie_field_probe as p
import pcie_protocol_appendix as a
import s01_contract as s


def git(*args, root=ROOT): return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


baseline = s.read_json(HERE / "baseline.json")
allowed = {"docs/pcie-usb-spec-slices-20261013.md", "docs/serial-slice-checkpoint-20261013.md"}
unchanged = []; changed = []; appends = []
for row in baseline["files"]:
    path = ROOT / row["path"]
    if row["path"] in {"PLAN.md", "artifacts/session-closeout.txt"}:
        raw = path.read_bytes(); assert hashlib.sha256(raw[:row["size"]]).hexdigest() == row["sha256"]
        appends.append({"path": row["path"], "prefix_preserved": True, "prefix_bytes": row["size"], "append_bytes": len(raw) - row["size"]})
    elif a.digest(path) != row["sha256"]:
        assert row["path"] in allowed, row["path"]
        changed.append(row["path"])
    else: unchanged.append(row["path"])
assert git("rev-parse", "HEAD") == baseline["head"]
assert git("rev-parse", "HEAD", root=FROZEN) == a.FROZEN_HEAD
assert git("status", "--porcelain", root=FROZEN) == ""
assert not s.validate_manifest(s.read_json(HERE / "manifest.json"))
assert not s.validate_matrix(s.read_json(HERE / "eligibility.json"))
assert all(r["qualification"] == "NOT_EVALUATED" and r["status"] == "partial" for r in s.read_json(HERE / "eligibility.json")["traces"][0]["assessments"])
source = Path(r"C:\Users\reiko\AppData\Local\Temp\pcie-p4a-hang-20260914-dcea0027\Disable ASPM--Insert SD7-hang.pex")
assert a.digest(source) == "c6e9646be0624b3efdd2a31796edcfc9e3a517c1429491a8101c7e48f96e15ad"
assert a.digest(ROOT / "dp1 hub detect SSD fail-2.usb") == "a5568248d1c3d04f3cc16d6d3649f1303be0d15ffa1a734e2057d73564836cae"
for profile in ["dllp", "tlp"]:
    for suffix in ["a", "b"]:
        directory = HERE / (profile + "-" + suffix); before = s.read_json(directory / "before.json")
        working = directory / "working.pex"
        assert a.digest(working) == before["working"]["sha256"]
        assert working.stat().st_size == before["working"]["bytes"] and working.stat().st_mtime_ns == before["working"]["mtime_ns"]
        assert bool(working.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
tests = {}
for group in ["s01", "u01", "usb_fields", "selection_pcie", "pcie_fields", "pcie_report_appendix", "usb_report_appendix", "pcie_recovery", "pcie_aspm_view"]:
    command = [sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", "tests/" + group, "-p", "test_*.py", "-v"]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    (HERE / (group + "-tests.txt")).write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    count = int(re.search(r"Ran (\d+) tests", run.stderr)[1]); tests[group] = {"count": count, "status": "PASS", "command": command}
frozen_checks = {}
for module in ["b3a", "b3b", "b3d"]:
    command = [sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", "tests/pcie", "-p", "test_" + module + "*.py", "-v"]
    run = subprocess.run(command, cwd=FROZEN, capture_output=True, text=True, encoding="utf-8")
    (HERE / ("frozen-" + module + "-tests.txt")).write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    frozen_checks[module] = {"status": "PASS", "count": int(re.search(r"Ran (\d+) tests", run.stderr)[1]), "command": command}
sidecar_command = [sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", "tests/pcie", "-p", "test_b2h2*.py", "-v"]
sidecar_run = subprocess.run(sidecar_command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
(HERE / "existing-sidecar-tests.txt").write_text(sidecar_run.stdout + sidecar_run.stderr, encoding="utf-8")
assert sidecar_run.returncode == 0, sidecar_run.stdout + sidecar_run.stderr
sidecar_count = int(re.search(r"Ran (\d+) tests", sidecar_run.stderr)[1])
host = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "tests/u01/test-u01-host.ps1"], cwd=ROOT, capture_output=True, text=True)
(HERE / "host-tests.txt").write_text(host.stdout + host.stderr, encoding="utf-8")
assert host.returncode == 0, host.stdout + host.stderr
for script in ["review-p03.py", "review-i01.py", "review-i02.py", "review-p11.py", "review-p10.py", "make-metadata.py"]:
    run = subprocess.run([sys.executable, "-X", "utf8", "-B", str(HERE / script)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    (HERE / (script + ".log")).write_text(run.stdout + run.stderr, encoding="utf-8")
reviews = {name: s.read_json(HERE / (name + "-review.json")) for name in ["p03", "i01", "i02", "p11", "p10"]}
assert all(r["review"].startswith("APPROVE_") for r in reviews.values())
native_pids = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq PETracer.exe", "/FO", "CSV", "/NH"], text=True, encoding="mbcs", errors="replace").strip()
failed_attempt = {"status": "FAILED_PATH_ARGUMENT_BEFORE_TRACE_OPEN", "trace_opened": False,
                  "error": "CATC.PETracer OpenFile rejected relative artifacts/evidence/p03-serial-20261013/tlp-b/working.pex as incorrect path",
                  "successful_absolute_path_retry": "p11-constants-native-b/com-run.json", "intermediate_repeat_refused_by_guard": "PETracer is already running; a COM run needs a clean start",
                  "owned_main_pid": 20984, "owned_client_pid": 55764, "owned_child_pid": 9464,
                  "cleanup": "main/client stopped after exact ownership checks; child Stop-Process access denied then exited; no remaining owned PETracer process",
                  "current_tasklist": native_pids, "source_sha256_preserved": a.digest(source),
                  "working_sha256_preserved": a.digest(HERE / "tlp-b/working.pex"), "p11_implementation": "BOUNDED_STATE_POINTS_COMPLETE", "p11_qualification": "NOT_EVALUATED"}
(HERE / "p11-native-failure.json").write_text(json.dumps(failed_attempt, indent=2) + "\n", encoding="utf-8")
assert subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True).returncode == 0
record = {"status": "LOCAL_BOUNDED_P03_I01_I02_P11_P10_COMPLETE", "reviews": reviews,
          "python_tests": tests, "python_total": sum(r["count"] for r in tests.values()),
          "frozen_W1_W5_tests": frozen_checks, "frozen_total": sum(r["count"] for r in frozen_checks.values()),
          "existing_sidecar_tests": {"status": "PASS", "count": sidecar_count, "command": sidecar_command},
          "managed_callbacks": 8, "managed_activation": 2, "existing_files_unchanged": len(unchanged), "modified_existing_paths": changed,
          "append_only_evidence": appends, "original_head_preserved": baseline["head"], "frozen_head_preserved": a.FROZEN_HEAD,
          "delivery_clean": True, "source_traces_preserved": True, "p11_failure": failed_attempt,
          "limits": ["bounded field/report scopes only; no all29 qualification", "mode/epoch/retention/bounds unknown", "no new policy/compliance/root-cause verdict"],
          "not_done": ["remaining14 candidates and full slice qualification", "P04/P05 normative/continuous-epoch gates", "U04/U05/P02 data prerequisites", "G01/G02 engineer prerequisites",
                       "hardware/capture, contact engineers, commit/push/PR/merge/reset, or checkout transfer"],
          "code_sha256": {name: a.digest(ROOT / name) for name in ["tools/pcie_field_probe.py", "tools/run-pcie-field-probe.py", "tools/pcie_protocol_appendix.py", "tools/usb_report_appendix.py", "tools/pcie_recovery_observations.py", "tools/pcie_aspm_register_view.py"]}}
(HERE / "verification.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": record["status"], "python_tests": record["python_total"], "frozen_tests": record["frozen_total"],
                  "existing_files_unchanged": len(unchanged), "remaining_processes": native_pids}))
