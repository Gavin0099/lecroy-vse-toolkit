import hashlib
import json
from pathlib import Path
import sys

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root / "tools"))
import s01_contract as s
import usb_field_probe as f

plan=s.read_json(here / "u02-prepared/plan.json")
results=[f.assess(s.read_json(here / name / "result.json"),plan) for name in ["u02-run-a","u02-run-b"]]
assert results[0]==results[1]
raw=s.read_json(here / "u02-raw-packets/raw.json")
assert raw["trace_sha256"].lower()==plan["trace_sha256"]
assert raw["source_unchanged"] and raw["working_unchanged"] and raw["working_readonly"]
checks=[]
for p in raw["packet_records"]:
    assert p["number_of_bits"]==64 and len(p["bytes"])==8
    native=next(r for r in results[0]["records"] if r["index"]==p["index"])
    # USB-01 Figure7-13: byte0/LSB first, info b10:0, CRC b15:11.
    # Table7-3: words at symbols4-5 and6-7. No CRC polynomial check.
    b=p["bytes"]
    first=b[4] | (b[5]<<8); second=b[6] | (b[7]<<8)
    expected=(first&0x7ff,first>>11,second&0x7ff,second>>11)
    actual=(native["info_raw"],native["crc5_raw"],native["replica_info_raw"],native["replica_crc5_raw"])
    assert actual==expected
    checks.append({"index":p["index"],"raw_hex":p["hex"],"word_fields":list(actual),"native_name":native["name_vendor"],"match":True})
record={"slice":"U02","review":"APPROVE_SAMPLED_NATIVE_FIELDS","two_runs_semantically_identical":True,
    "native_callbacks":results[0]["callback_count"],"sampled_rows":results[0]["exported_count"],
    "observed_names":results[0]["observed_native_names"],"raw_packet_field_checks":checks,
    "sources":["LC-04 PDF19/20/32", "LC-09/12", "USB-01 Revision1.1 7.2.2.1-.2 Figure7-13 / 7.3.5"],
    "limits":["observed sample is SSP only; SS has offline fixtures but no real sample qualification",
              "LGOOD/LCRD1 observed; LBAD/LRTY/LGO and other names not qualified",
              "CRC bit values match two raw packets; CRC correctness NOT_EVALUATED",
              "sample128 is partial, epoch/capture completeness remain unknown"],
    "next_allowed":"U03 LFPS raw/vendor-name mapping using independently qualified historical raw observations"}
(here / "u02-review.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
