import json
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/"tools"))
import s01_contract as s
import pcie_selection_probe as p
plan=s.read_json(here/"p01-prepared/plan.json")
p.validate_plan(plan)
rows=[]
for profile in plan["profiles"]:
    runs=[]
    for prefix in ["p01-","p01-repeat-"]:
        d=here/(prefix+profile["id"])
        r=s.read_json(d/"com-run.json")
        a=p.assess(r,s.read_json(d/"report-lines.json"),profile)
        assert r["pre"]["files"][0]["sha256"].lower()==plan["trace_sha256"]
        runs.append(a)
    assert runs[0]==runs[1]
    rows.append({"profile":profile["id"],"counts":runs[0]["counts"],"reproducible":True})
record={"slice":"P01","review":"APPROVE_BOUNDED_SELECTION_TRANSPORT","profiles":rows,
    "source_sha256":plan["trace_sha256"],"scope":"installed named constants / converted trace / level-local 0-200 and empty window",
    "split_native_level":next(r["counts"]["native_level"] for r in rows if r["profile"]=="split-all"),
    "limits":["TLP/DLLP exist outside tested0-200 window; zero selected rows not event absence",
              "split named constant resolved to4 despite an installed manual context table listing2",
              "display filters and native effective range unknown; no absence/compliance verdict",
              "no complete grouping/packet reference qualification or legacy PASS expansion"],
    "next_allowed":"P02 native group status/metrics; explicit packet references still required before complete qualification"}
(here/"p01-review.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
