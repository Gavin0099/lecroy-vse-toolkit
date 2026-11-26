import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "tools"))
import s01_contract as s
import u01_selection as u

here = Path(__file__).resolve().parent
plan = s.read_json(here / "u01-prepared-r3/plan.json")
results = []
for run in ["u01-run-r3a", "u01-run-r3c"]:
    rows = {name: s.read_json(here / run / name / "result.json") for name in u.SELECTIONS}
    u.compare_results(rows, plan)
    for name in rows:
        assessment = s.read_json(here / run / name / "assessment.json")
        assert not s.validate_manifest(assessment["manifest"])
    results.append(rows)
assert results[0] == results[1], "same controlled input did not reproduce the saved callback payload"
record = {"slice": "U01", "review": "APPROVE_BOUNDED_SELECTION_TRANSPORT",
    "runs": ["u01-run-r3a", "u01-run-r3c"], "seven_profiles_semantically_identical": True,
    "counts": {n: {"visited": r["summary"][0], "window": r["summary"][1], "rows": len(r["rows"])} for n, r in results[0].items()},
    "source_and_all_fourteen_working_copies_unchanged": all(all(r["integrity"].values()) for rows in results for r in rows.values()),
    "crc_enabled_total_callback_delta": results[0]["packet-crc-on"]["summary"][0] - results[0]["packet-crc-off"]["summary"][0],
    "scope": "exact trace hash / suite 10.40 / named flags / post-dispatch level-local window 0-200",
    "remaining_limits": ["10 additional callbacks are not independently qualified CRC examples", "incomplete transfer sample absent; coverage remains unknown",
                         "effective native range, capture completeness and epoch unknown", "no protocol correctness or certification verdict"],
    "resolved_findings": ["unary negative literal in CSL payload/scalar prevented execution; v3 explicit NOT_APPLICABLE token retains NA",
                          "transient class-factory RPC failure during repeat; bounded activation-only retry, no automatic replay after trace open"],
    "next_allowed": "U02 positive LINK_CMD fields, then review; unobserved command types remain unqualified"}
(here / "u01-review.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record))
