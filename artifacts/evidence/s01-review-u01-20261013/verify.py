"""Replay local evidence and preservation checks; no COM/runtime activation."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import s01_contract as s
import u01_selection as u


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


baseline = s.read_json(HERE / "baseline.json")
preserved, prefixes = [], []
for old in baseline["files"]:
    p = ROOT / old["path"]
    if old["path"] in {"PLAN.md", "artifacts/session-closeout.txt"}:
        raw = p.read_bytes()
        assert hashlib.sha256(raw[:old["size"]]).hexdigest() == old["sha256"].lower(), old["path"]
        prefixes.append({"path": old["path"], "original_bytes": old["size"], "append_bytes": len(raw) - old["size"], "original_prefix_preserved": True})
    else:
        assert digest(p) == old["sha256"].lower(), old["path"]
        preserved.append(old["path"])
assert git("rev-parse", "HEAD") == baseline["head"]
delivery = Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
assert git("status", "--porcelain", root=delivery) == ""
assert git("rev-parse", "HEAD", root=delivery) == "f417eecb340f56d09d6e4c0ca0b86f81e2977181"

preflight = s.read_json(HERE / "preflight/preflight.json")
assert preflight["execute_requested"] is False and preflight["raw_trace_opened"] is False
trace_path = Path(preflight["source"])
assert digest(trace_path) == preflight["source_before"]["sha256"]
assert trace_path.stat().st_size == preflight["source_before"]["size"]
plan = s.read_json(HERE / "prepared/plan.json")
u.validate_plan(plan)
for p in plan["profiles"]:
    assert digest(HERE / "prepared" / p["script"]) == p["script_sha256"]

# A current preflight proves file identity, not capture mode/coverage. Never
# transform the historical PASS/FAIL role into a qualification result.
unknown = {"state": "unknown", "value": None, "evidence_refs": []}
manifest = {"schema_version": "s01.input-manifest/v1", "manifest_id": "U01-PREFLIGHT-ONLY",
    "origin": "recorded", "trace": {"trace_id": plan["trace_id"], "sha256": plan["trace_sha256"], "protocol": "usb",
        "identity_evidence_refs": ["PREFLIGHT"], "facts": {key: dict(unknown) for key in ["mode", "bidirectional", "capture_start", "capture_end", "epoch", "filters"]}},
    "toolchain": {"software_version": preflight["software_version"], "extractor_sha256": None,
        "constants_sha256": preflight["constants_sha256"], "evidence_refs": ["PREFLIGHT"]},
    "sources": [], "evidence": [{"id": "PREFLIGHT", "kind": "saved_output", "locator": "preflight/preflight.json",
        "sha256": digest(HERE / "preflight/preflight.json"), "trace_sha256": plan["trace_sha256"],
        "note": "Current file hash inventory of a previously documented USB input; no mode, event, capture completeness or runtime claim."}],
    "capabilities": [], "observations": [], "historical_claims": [], "claim_boundary": "INPUT_METADATA_ONLY"}
profile = {"slice_id": "U01", "engineer_question": "Do independent known bad-CRC and incomplete examples establish selection coverage?",
    "expected_observation": "Explicit flags, reconciled rows and independent event examples; unknown stays unknown.",
    "protocol": "usb", "modes": ["USB2-LS", "USB2-FS", "USB2-HS", "USB3-SS", "USB3-SSP", "USB2-and-USB3"],
    "requirements": [{"kind": "fact", "id": "filters", "expected": "known"},
                     {"kind": "event", "id": "usb.BAD_CRC", "expected": "observed"},
                     {"kind": "event", "id": "usb.INCOMPLETE_TRANSFER", "expected": "observed"}]}
matrix = s.build_matrix([manifest], [profile])
assert matrix["traces"][0]["assessments"][0]["status"] == "partial"
(HERE / "candidate-eligibility.json").write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

counts = {}
for name, expected in [("s01-tests.txt", 42), ("u01-tests.txt", 13)]:
    t = (HERE / name).read_text(encoding="utf-8")
    assert re.search(rf"Ran {expected} tests", t) and t.rstrip().endswith("OK"), name
    counts[name] = {"tests": expected, "sha256": digest(HERE / name), "result": "PASS"}
assert "6 managed callback cases" in (HERE / "host-tests.txt").read_text(encoding="utf-8")
assert "no COM activation" in (HERE / "host-tests.txt").read_text(encoding="utf-8")
git("diff", "--check")

new_files = [str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.glob("tests/u01/*") if p.is_file()]
new_files += ["tools/u01_selection.py", "tools/u01-selection-host.cs", "tools/run-u01-selection.ps1",
              "docs/u01-selection-coverage.md", "docs/s01-review-20261013.md"]
links = []
for name in ["docs/u01-selection-coverage.md", "docs/s01-review-20261013.md", "tests/u01/fixture-oracles.md"]:
    text = (ROOT / name).read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        path = (ROOT / name).parent / target.split("#")[0]
        if path.name == "verification.json":
            continue  # Written below, after all validation succeeds.
        assert path.exists(), (name, target)
        links.append({"document": name, "target": target})
record = {"status": "S01_REVIEW_APPROVE_U01_OFFLINE_READY", "s01_blocking_findings": [],
    "review_scope": "offline manifest/schema/validator/oracles/legacy/CLI, no protocol qualification",
    "checks": counts, "host_checks": {"csharp_compile": "PASS", "managed_callback_cases": 6,
        "powershell_51_parser": "PASS", "com_activation": False},
    "u01_execution": "NOT_RUN_PENDING_RUNTIME_SCOPE_CONFIRMATION", "u01_qualification": "NOT_EVALUATED",
    "u01_trace_input_readiness": "partial", "candidate_matrix": "candidate-eligibility.json",
    "prepared_profiles": 7, "preflight": "preflight/preflight.json", "source_sha256": plan["trace_sha256"],
    "source_sha256_preserved": True, "baseline_file_count": len(baseline["files"]),
    "existing_files_unchanged_count": len(preserved), "append_only_prefixes": prefixes,
    "current_head": git("rev-parse", "HEAD"), "delivery_head": git("rev-parse", "HEAD", root=delivery),
    "delivery_worktree_clean": True, "s01_code_schemas_tests_unchanged": True,
    "new_file_sha256": {name: digest(ROOT / name) for name in new_files},
    "local_links_checked": links, "diff_check": "PASS", "commit_push_merge_reset": "NOT_RUN",
    "limits": ["no decoded raw trace access or VSE syntax/runtime validation", "no independent known bad-CRC/incomplete sample in selected window",
               "delivered bounds are not native effective capture range", "S01 consistency does not authenticate evidence contents",
               "other slices and historical PASS scope unchanged"]}
(HERE / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": record["status"], "tests": 55, "managed_cases": 6, "unchanged_existing_files": len(preserved), "runtime": record["u01_execution"]}))
