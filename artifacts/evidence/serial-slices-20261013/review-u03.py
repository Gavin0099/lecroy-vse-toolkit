import json
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root / "tools"))
import s01_contract as s
import usb_field_probe as f
plan=s.read_json(here / "u03-prepared/plan.json")
a,b=[f.assess(s.read_json(here / name / "result.json"),plan) for name in ["u03-run-a","u03-run-b"]]
assert a==b
legacy_path=root / "c4-demo-regression-20260911/fail-timeline.json"
legacy=s.read_json(legacy_path)
assert legacy["before"]["sha256"].lower()==plan["trace_sha256"]
lfps={(r["Index"],r["TimestampSeconds"],r["TimestampNanoseconds"]):r["Raw"] for r in legacy["events"] if r["EventClass"]=="LFPS"}
for r in a["records"]:
    old=lfps[(r["index"],r["time_sec"],r["time_ns"])]
    expected=(old["LfpsType"],old["DurationNs"],old["DurationSec"],old["DurationRemainderNs"],old["PatternType"],old["StartsPattern"])
    actual=tuple(r[k] for k in ["type_raw","duration_raw_ns","duration_sec","duration_remainder_ns","pattern_type_raw","starts_pattern"])
    assert actual==expected
record={"slice":"U03","review":"APPROVE_SAMPLED_RAW_VENDOR_MAPPING","two_runs_semantically_identical":True,
    "native_callbacks":a["callback_count"],"sampled_rows":a["exported_count"],"historical_raw_rows_matched":len(a["records"]),
    "historical_reference":"c4-demo-regression-20260911/fail-timeline.json", "historical_reference_sha256":f.hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
    "observed_names":a["observed_native_names"],"same_underlying_vendor_decoder_warning":True,
    "limits":["sample128 is partial, unobserved LFPS types unqualified", "name is native classifier output, not observed wake/reset success",
              "event Speed label is not negotiated link mode", "pattern end/capture scope and measurement accuracy unknown"],
    "next_allowed":"U04 exact-field discovery; no guessed in.State. Missing field must not block unrelated P01/U05."}
(here / "u03-review.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
