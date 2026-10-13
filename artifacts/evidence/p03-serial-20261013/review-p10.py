import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcie_aspm_register_view as p
OUT = HERE / "p10-standard-view-r3"
value = json.loads((OUT / "observations.json").read_bytes())
for source in value["sources"].values(): assert p.digest(source["path"]) == source["sha256"]
for dep in value["dependencies"].values(): assert p.digest(dep["path"]) == dep["sha256"]
snapshot, log, caps = [json.loads(Path(value["sources"][key]["path"]).read_bytes()) for key in ["snapshot", "accesses", "capabilities"]]
definition = p.rd.load(p.DEFINITION)
for i, packet in enumerate([3300, 10360]):
    assert value["queries"][i] == p.build(snapshot, log, caps, definition, packet)
    rows = value["queries"][i]["register_view"]["rows"]
    # Independent real-field oracle: saved GetData query10360 DWORD0x90
    # holds raw0x42 with those bits valid; actual write request10354 has42.
    expected = [None, None, None] if packet == 3300 else [2, 1, 0]
    assert [r["catc_merged"]["value"] for r in rows] == expected
    assert [r["last_write_intent"]["value"] for r in rows] == expected
    assert all(r["last_read_back"]["value"] is None for r in rows)
    if packet == 10360:
        space = snapshot["packets"][str(packet)]
        data, mask = space["GetData"]
        assert data[0x90 // 4] & 0xffff == 0x42
        assert mask[0x90 // 4] & 0x143 == 0x143
        assert all(r["native_comparison"] == "MATCH" for r in rows)
        assert all(10354 in r["last_write_intent"]["evidence_request_packets"] for r in rows)
    assert value["queries"][i]["effective_state"] == "UNKNOWN"
    assert value["queries"][i]["policy_result"] == "NOT_EVALUATED"
review = {"slice": "P10", "review": "APPROVE_BOUNDED_STANDARD_REGISTER_VIEW", "report_directory": str(OUT),
          "queries": [3300, 10360], "fields": ["ASPM Control", "CommonClockConfig", "EnableClockPowerManagement"],
          "real_query10360_merged_and_write_values": [2, 1, 0], "write_request": 10354,
          "real_query3300_fields": "all unknown", "readback": "unknown at both queries", "native_catc_matches": 3,
          "source_id": "PCI-45", "layout_source_notes": str(ROOT / "docs/pcie-register-defs/linkcontrol-observation.source.json"),
          "scope": "one trace/BDF001:00.0/before_disconnect/case capability offset0x90; standard raw bit view only",
          "limits": ["device role/RC counterpart/wire state unknown; not full P10 qualification", "L1SS named fields not qualified",
                     "CATC merged state and write intent are not effective state or hardware readback",
                     "CLKREQ/electrical clock/L1 entry unverified; no product policy verdict"],
          "next_gate": "P07/P08 need applicable named capability inputs; U06 needs further command samples; other evaluators retain input/normative/engineer gates"}
(HERE / "p10-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review": review["review"], "fields": 3, "native_matches": 3, "readback": "unknown"}))
