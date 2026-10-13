"""Guarded P03 runner. Default is preflight; --execute opens a new readonly copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import shutil
import pcie_field_probe as p
import s01_contract as s


def identity(path):
    st = path.stat()
    return {"path": str(path.resolve()), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "readonly": bool(st.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)}


def save(path, value): path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True); ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--profile", choices=list(p.FIELDS), required=True); ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--execute", action="store_true"); a = ap.parse_args()
    plan = s.read_json(a.plan); p.validate_plan(plan)
    script = a.plan.parent / (a.profile + ".pevs"); source_before = identity(a.source)
    if source_before["sha256"] != plan["trace_sha256"]: raise s.ContractError("source hash mismatch")
    if identity(script)["sha256"] != plan["profiles"][a.profile]: raise s.ContractError("script hash mismatch")
    # pywin32 is already present in this interpreter; do not install or convert traces.
    if not a.execute:
        print(json.dumps({"status": "PREFLIGHT", "profile": a.profile, "source": source_before, "execute": False})); return 0
    if a.output.exists(): raise s.ContractError("fresh output directory required")
    a.output.mkdir(parents=True)
    working = a.output / "working.pex"; shutil.copy2(a.source, working); os.chmod(working, stat.S_IREAD)
    before = {"source": source_before, "working": identity(working), "script": identity(script)}
    if not before["working"]["readonly"] or before["working"]["sha256"] != source_before["sha256"]: raise s.ContractError("readonly copy failed")
    root = Path(__file__).resolve().parents[1]; runner = root / "scripts/pcie/com_run_vse.py"
    constants = Path(r"C:\Users\Public\Documents\LeCroy\PCIe Protocol Suite\Scripts\VFScripts")
    before["runtime_sources"] = {name: identity(constants / name) for name in ["VS_constants.inc", "VSTools.inc"]}
    before["runner"] = identity(runner)
    save(a.output / "before.json", before)
    cmd = [sys.executable, "-B", str(runner), "--trace", str(working.resolve()), "--protect", str(a.source.resolve()),
           "--script", str(script.resolve()), "--output-dir", str((a.output / "native").resolve()), "--timeout", "120"]
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (a.output / "runner.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    after = {"source": identity(a.source), "working": identity(working), "script": identity(script),
             "runtime_sources": {name: identity(constants / name) for name in ["VS_constants.inc", "VSTools.inc"]}, "runner": identity(runner)}
    save(a.output / "after.json", after)
    if before != after: raise s.ContractError("source/working/script/runtime identity changed")
    if run.returncode: raise s.ContractError("native runner failed; see saved log")
    value = p.assess(s.read_json(a.output / "native/com-run.json"), s.read_json(a.output / "native/report-lines.json"), plan, a.profile)
    save(a.output / "observations.json", value)
    print(json.dumps({"status": "BOUNDED_FIELDS_COMPLETE", "profile": a.profile, "summary": value["summary"], "identities_unchanged": True}))
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (s.ContractError, OSError) as e:
        print(json.dumps({"status": "FAILED", "error": str(e)})); raise SystemExit(2)
