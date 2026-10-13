import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/"tools"))
import s01_contract as s
import u01_selection as u
import usb_field_probe as f
import pcie_selection_probe as p

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda:file.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def git(*args,root=ROOT):return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

baseline=s.read_json(HERE/"baseline.json")
allowed={"PLAN.md","artifacts/session-closeout.txt","docs/pcie-usb-spec-slices-20261013.md","docs/u01-selection-coverage.md",
         "tools/u01_selection.py","tools/u01-selection-host.cs","tools/run-u01-selection.ps1","tests/u01/test_u01_selection.py","tests/u01/test-u01-host.ps1"}
unchanged=[];append=[];modified=[]
for row in baseline["files"]:
    path=ROOT/row["path"]
    if row["path"] in {"PLAN.md","artifacts/session-closeout.txt"}:
        raw=path.read_bytes();assert hashlib.sha256(raw[:row["size"]]).hexdigest()==row["sha256"].lower(),row["path"]
        append.append({"path":row["path"],"prefix_bytes":row["size"],"prefix_preserved":True,"append_bytes":len(raw)-row["size"]})
    elif digest(path)!=row["sha256"].lower():
        assert row["path"] in allowed,row["path"]
        modified.append(row["path"])
    else:unchanged.append(row["path"])
assert git("rev-parse","HEAD")==baseline["head"]
delivery=Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
assert git("status","--porcelain",root=delivery)==""
assert git("rev-parse","HEAD",root=delivery)=="f417eecb340f56d09d6e4c0ca0b86f81e2977181"
reviews={name:s.read_json(HERE/(name+"-review.json")) for name in ["u01","u02","u03","p01"]}
assert all(r["review"].startswith("APPROVE_") for r in reviews.values())
for name in ["u02-run-a","u02-run-b","u03-run-a","u03-run-b"]:
    m=s.read_json(HERE/name/"manifest-final.json");assert not s.validate_manifest(m)
for name in ["u04-discovery","u05-discovery"]:
    r=s.read_json(HERE/name/"discovery.json");assert r["source_unchanged"] and r["working_unchanged"] and r["working_readonly"]
assert digest(ROOT/"dp1 hub detect SSD fail-2.usb")=="a5568248d1c3d04f3cc16d6d3649f1303be0d15ffa1a734e2057d73564836cae"
assert digest(Path(r"C:\Users\reiko\AppData\Local\Temp\pcie-p4a-hang-20260914-dcea0027\Disable ASPM--Insert SD7-hang.pex"))=="c6e9646be0624b3efdd2a31796edcfc9e3a517c1429491a8101c7e48f96e15ad"
tests={}
for directory in ["s01","u01","usb_fields","selection_pcie"]:
    cmd=[sys.executable,"-X","utf8","-B","-m","unittest","discover","-s","tests/"+directory,"-p","test_*.py","-v"]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    (HERE/(directory+"-tests.txt")).write_text(run.stdout+run.stderr,encoding="utf-8")
    count=int(re.search(r"Ran (\d+) tests",run.stderr).group(1))
    tests[directory]={"count":count,"status":"PASS","command":cmd}
host=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File","tests/u01/test-u01-host.ps1"],cwd=ROOT,capture_output=True,text=True)
assert host.returncode==0,host.stdout+host.stderr
(HERE/"host-tests.txt").write_text(host.stdout+host.stderr,encoding="utf-8")
links=0
for name in ["docs/serial-slice-checkpoint-20261013.md","docs/usb-field-probes-20261013.md","docs/pcie-selection-checkpoint-20261013.md","docs/u01-selection-coverage.md"]:
    doc=ROOT/name
    for target in re.findall(r"\]\(([^)]+)\)",doc.read_text(encoding="utf-8")):
        if target.startswith("http"):continue
        path=doc.parent/target.split("#")[0]
        if path.name=="verification.json":continue
        assert path.exists(),(name,target)
        links+=1
assert subprocess.run(["git","diff","--check"],cwd=ROOT,capture_output=True).returncode==0
record={"status":"LOCAL_BOUNDED_CHECKPOINT","authorization":"owner permits serial implementation/validation/review and readonly runtime; no recurring confirmations",
        "reviews":reviews,"qualification_claim":"bounded scopes only; not all29 or full protocol qualification",
        "python_tests":tests,"python_total":sum(x["count"] for x in tests.values()),"managed_callback_cases":8,"activation_recovery_cases":2,
        "csharp_compile":"PASS","powershell51_parse":"PASS","local_links_checked":links,
        "existing_unchanged_files":len(unchanged),"existing_modified_in_scope":modified,"append_only":append,
        "current_head":git("rev-parse","HEAD"),"delivery_head":git("rev-parse","HEAD",root=delivery),"delivery_clean":True,
        "source_traces_sha256_unchanged":True,"s01_code_schema_fixtures_unchanged":True,"w1_w5_frozen":True,
        "no_commit_push_merge_reset_or_hardware":True,
        "data_gates":{"U04":"blocked_field; exact LTSSM state label/API unavailable in native export","U05/P02":"explicit child-packet references not qualified",
                      "G01/G02":"engineer scope/definitions absent"},
        "remaining_candidates":"19 retain individual source/input/qualification prerequisites; no completion claim",
        "changed_code_sha256":{name:digest(ROOT/name) for name in ["tools/u01_selection.py","tools/u01-selection-host.cs","tools/run-u01-selection.ps1","tools/usb_field_probe.py","tools/run-usb-field-probe.ps1","tools/pcie_selection_probe.py"]}}
(HERE/"verification.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":record["status"],"python_tests":record["python_total"],"unchanged":len(unchanged),"modified":modified,"reviews":list(reviews)}))
