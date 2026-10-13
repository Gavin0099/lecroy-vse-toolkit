"""Generate new S01 sidecars from saved P03 output; never rewrite old evidence."""
import hashlib
import json
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcie_field_probe as p
import pcie_protocol_appendix as a
import s01_contract as s

def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

probes = {}; sources = {}
for profile in ["dllp", "tlp"]:
    probes[profile], sources[profile] = a.load_probe(HERE / "prepared/plan.json", HERE / (profile + "-a"), profile)
sha = probes["dllp"]["trace_sha256"]
runtime = s.read_json(HERE / "runtime-executable.json")
assert a.digest(runtime["path"]) == runtime["sha256"]
catalog = s.read_json(ROOT / "docs/pcie-usb-source-register-20261013.json")
source = next(r for r in catalog["sources"] if r["id"] == "LC-01")
assert a.digest(source["local_path"]) == source["sha256"].lower()
evidence = [{"id": "LC-01-DOC", "kind": "document", "locator": source["local_path"], "sha256": source["sha256"].lower(),
             "note": "LC-01 5.2.2/5.2.3 selected field applicability; not numeric rule qualification."}]
for profile in probes:
    for key in ["observations", "before"]:
        v = sources[profile][key]
        evidence.append({"id": profile + "-" + key, "kind": "saved_output", "locator": v["path"], "sha256": v["sha256"],
                         "trace_sha256": sha, "note": "Bounded sample and protected identity, no capture coverage proof."})
caps = []; events = []
for profile, value in probes.items():
    types = p.DLLP if profile == "dllp" else p.TLP
    for native_type in types:
        rows = [r for r in value["rows"] if r["native_type"] == native_type]
        refs = [profile + "-observations"]
        for field in p.FIELDS[profile]:
            applies = p.applicable(profile, native_type, field)
            available = any(r["fields"][field]["state"] == "available" for r in rows)
            caps.append({"id": f"pcie.{profile}.{native_type}.{field}", "api_support": "supported",
                         "applicability": "applicable" if applies else "not_applicable",
                         "availability": "available" if available else "unknown" if applies else "not_applicable",
                         "evidence_refs": ["LC-01-DOC"] + refs})
        indices = [r["index"] for r in rows]
        events.append({"event": f"pcie.{profile}.{native_type}", "state": "observed" if rows else "unknown",
                       "count": len(rows), "evidence_refs": refs,
                       "coverage": {"selection": "included", "retention": "unknown",
                                    "extraction": "partial" if value["counts"][str(native_type)]["visited"] > len(rows) else "complete",
                                    "start_index": min(indices) if indices else None, "end_index": max(indices) if indices else None}})
before = s.read_json(HERE / "dllp-a/before.json")
p11_path = HERE / "p11-state-points-r3/observations.json"
p11 = s.read_json(p11_path)
assert p11["trace_sha256"] == sha
evidence.append({"id": "P11-POINTS", "kind": "saved_output", "locator": str(p11_path), "sha256": a.digest(p11_path),
                 "trace_sha256": sha, "note": "Saved valid state points, corroborated legacy source; no complete epoch/capture proof."})
caps.append({"id": "pcie.LtssmState", "api_support": "supported", "applicability": "applicable", "availability": "available", "evidence_refs": ["P11-POINTS"]})
recovery_indices = [r["packet_ref"]["index"] for r in p11["points"] if r["feature"] in {"recovery_state", "equalization_state"}]
events.append({"event": "pcie.ltssm.Recovery", "state": "observed", "count": len(recovery_indices), "evidence_refs": ["P11-POINTS"],
               "coverage": {"selection": "included", "retention": "unknown", "extraction": "partial", "start_index": min(recovery_indices), "end_index": max(recovery_indices)}})
p10_path = HERE / "p10-standard-view-r3/observations.json"
p10 = s.read_json(p10_path)
assert p10["queries"][1]["register_view"]["binding"]["trace"]["sha256"].lower() == sha
evidence.append({"id": "P10-VIEW", "kind": "saved_output", "locator": str(p10_path), "sha256": a.digest(p10_path),
                 "trace_sha256": sha, "note": "Three evidence planes; native match on raw bits, not effective state."})
for field in ["ASPMControl", "CommonClockConfig", "EnableClockPowerManagement"]:
    caps.append({"id": "pcie.LinkControl." + field, "api_support": "supported", "applicability": "applicable", "availability": "available", "evidence_refs": ["P10-VIEW"]})
events.append({"event": "pcie.LinkControlSnapshot", "state": "observed", "count": 2, "evidence_refs": ["P10-VIEW"],
               "coverage": {"selection": "included", "retention": "unknown", "extraction": "partial", "start_index": 3300, "end_index": 10360}})
manifest = {"schema_version": "s01.input-manifest/v1", "manifest_id": "P03-CONVERTED-FIELD-SAMPLE", "origin": "recorded",
            "trace": {"trace_id": "PCIE-P03-" + sha[:12], "sha256": sha, "protocol": "pcie", "identity_evidence_refs": ["dllp-before", "tlp-before"],
                      "facts": {key: {"state": "unknown", "value": None, "evidence_refs": []} for key in ["mode", "bidirectional", "capture_start", "capture_end", "epoch", "filters"]}},
            "toolchain": {"software_version": runtime["version"], "extractor_sha256": before["script"]["sha256"],
                          "constants_sha256": before["runtime_sources"]["VS_constants.inc"]["sha256"], "evidence_refs": ["dllp-before", "tlp-before"]},
            "sources": [{"source_id": "LC-01", "revision": source["version"], "locator": source["local_path"], "review_depth": "sections_reviewed",
                         "sections": ["5.2.2", "5.2.3"], "applicability": "applicable", "evidence_refs": ["LC-01-DOC"]}],
            "evidence": evidence, "capabilities": caps, "observations": events, "historical_claims": [], "claim_boundary": "INPUT_METADATA_ONLY"}
assert not s.validate_manifest(manifest), s.validate_manifest(manifest)
profiles = [
    {"slice_id": "P03-SAMPLED-ACK", "protocol": "pcie", "engineer_question": "ACK 序號可否由來源取回？", "expected_observation": "原生 ACK 欄位樣本",
     "modes": ["non_flit", "flit"], "requirements": [{"kind": "field", "id": "pcie.dllp.0.AckNak_SeqNum", "expected": "available"}, {"kind": "event", "id": "pcie.dllp.0", "expected": "observed"}]},
    {"slice_id": "P04", "protocol": "pcie", "engineer_question": "是否足以評估 replay？", "expected_observation": "同 epoch 雙向連續序號觀測",
     "modes": ["non_flit"], "requirements": [{"kind": "field", "id": "pcie.tlp.1.PSN", "expected": "available"}, {"kind": "fact", "id": "epoch", "expected": "known"},
                      {"kind": "fact", "id": "bidirectional", "expected": True}, {"kind": "coverage", "id": "pcie.dllp.0", "expected": "complete"}]},
    {"slice_id": "P05", "protocol": "pcie", "engineer_question": "是否足以重建 credit？", "expected_observation": "初始 credit 與同 epoch 雙向連續更新",
     "modes": ["non_flit"], "requirements": [{"kind": "field", "id": "pcie.dllp.4.HdrFC", "expected": "available"}, {"kind": "fact", "id": "epoch", "expected": "known"},
                      {"kind": "fact", "id": "bidirectional", "expected": True}, {"kind": "coverage", "id": "pcie.dllp.4", "expected": "complete"}]},
    {"slice_id": "P11-STATE-POINTS", "protocol": "pcie", "engineer_question": "是否曾觀測到有效 Recovery state？", "expected_observation": "附 packet source 的有效狀態點",
     "modes": ["non_flit", "flit"], "requirements": [{"kind": "field", "id": "pcie.LtssmState", "expected": "available"}, {"kind": "event", "id": "pcie.ltssm.Recovery", "expected": "observed"}]},
    {"slice_id": "P10-STANDARD-VIEW", "protocol": "pcie", "engineer_question": "能否分開看到原始 ClockPM 設定位元與讀回？", "expected_observation": "有來源的 register evidence planes，不推生效",
     "modes": ["non_flit", "flit"], "requirements": [{"kind": "field", "id": "pcie.LinkControl.EnableClockPowerManagement", "expected": "available"}, {"kind": "event", "id": "pcie.LinkControlSnapshot", "expected": "observed"}]},
]
matrix = s.build_matrix([manifest], profiles)
assert matrix["traces"][0]["assessments"][0]["status"] == "partial"  # mode unknown blocks full eligibility
assert all(r["status"] != "eligible" for r in matrix["traces"][0]["assessments"][1:])
assert all(r["qualification"] == "NOT_EVALUATED" for r in matrix["traces"][0]["assessments"])
save(HERE / "manifest.json", manifest); save(HERE / "eligibility.json", matrix)
print(json.dumps({"manifest": "valid", "eligibility": [(r["slice_id"], r["status"]) for r in matrix["traces"][0]["assessments"]]}))
