"""P10 bounded standard-register view; reuse B2h2's three evidence planes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/pcie"))
import b2h2_sidecar as sidecar
import b2d_observed_state as state
import catc_regdef as rd

DEFINITION = ROOT / "docs/pcie-register-defs/linkcontrol-observation.regdef.json"


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(snapshot, accesses, capabilities, definition, packet):
    # This first profile is intentionally one saved device/epoch/layout.
    if (capabilities.get("device_id") != 256 or capabilities.get("epoch") != "before_disconnect"
            or capabilities.get("registers", {}).get("LinkControl", {}).get("byte_offset") != 0x90
            or snapshot.get("bdf") != 256):
        raise ValueError("P10 case device/epoch/LinkControl offset not established")
    evidence = capabilities["registers"]["LinkControl"]["capability_evidence"]
    if not evidence or any(e.get("completion_packet", packet + 1) > packet for e in evidence):
        raise ValueError("capability pointer must be read before query packet")
    expected = [("ASPM Control", 0, 2), ("CommonClockConfig", 6, 1), ("EnableClockPowerManagement", 8, 1)]
    registers = definition.get("registers", [])
    if (len(registers) != 1 or registers[0]["name"] != "LinkControl" or registers[0]["offset"] != 0x90
            or [(f["name"], f["lsb"], f["width"]) for f in registers[0]["fields"]] != expected):
        raise ValueError("P10 selected source layout differs from the reviewed bit positions")
    result = sidecar.build(snapshot, accesses, definition, packet, 256)
    if result["binding"]["epoch"] != "before_disconnect": raise ValueError("P10 first profile excludes other epochs")
    return {"schema": "pcie.aspm-register-observations/v1", "slice": "P10", "device_id": 256,
            "register_view": result, "source_ids": ["PCI-45", "LC-02", "Linux-v6.12-pci_regs"],
            "device_role": "unknown", "rc_observations": "unknown", "wire_ltssm_pm_observations": "unknown",
            "wire_scope_reason": "saved LTSSM window starts at225041; queries here precede disconnect and have no eligible state-point source",
            "l1ss_named_fields": "not_qualified", "clkreq_electrical_action": "unknown", "effective_state": "UNKNOWN",
            "expected_state": "UNKNOWN", "policy_result": "NOT_EVALUATED", "qualification": "NOT_EVALUATED",
            "claim_boundary": "standard register bit observations only; no applied state, L1 entry, clock/sideband or Disable-ASPM policy verdict"}


def generate(snapshot_path, log_path, capabilities_path, output):
    output = Path(output)
    if output.exists(): raise ValueError("fresh output required")
    paths = {"snapshot": Path(snapshot_path), "accesses": Path(log_path), "capabilities": Path(capabilities_path), "definition": DEFINITION}
    paths["register_reference"] = ROOT / "docs/pcie-register-reference.json"
    paths["layout_source_notes"] = DEFINITION.with_name("linkcontrol-observation.source.json")
    hashes = {k: digest(v) for k, v in paths.items()}
    snapshot, log, caps = [json.loads(paths[k].read_bytes()) for k in ["snapshot", "accesses", "capabilities"]]
    if (caps.get("input", {}).get("log_sha256", "").lower() != hashes["accesses"]
            or caps.get("input", {}).get("reference_sha256", "").lower() != hashes["register_reference"]):
        raise ValueError("capability source/log/reference binding mismatch")
    definition = rd.load(DEFINITION)
    result = {"schema": "pcie.aspm-register-profile/v1", "slice": "P10", "queries": [],
              "sources": {k: {"path": str(v.resolve()), "sha256": hashes[k]} for k, v in paths.items()},
              "dependencies": {m.__name__: {"path": str(Path(m.__file__).resolve()), "sha256": digest(m.__file__), "state": "existing_current_checkout_working_file"} for m in [sidecar, state, rd]}}
    for module in [sidecar, state, rd]:
        if Path(module.__file__).resolve().parent != ROOT / "scripts/pcie": raise ValueError("mixed-checkout dependency rejected")
    markdown = ["# PCIe LinkControl 原始設定觀測", "", "CATC 合併值、送出的 write intent 與實際 Completion 讀回分開；不能把 enable 視為已進 L1。", "",
                "RC、device role、這些查詢位置的 LTSSM／PM 訊號、L1SS named fields、CLKREQ# 電氣動作仍未知或未資格化。", ""]
    for packet in [3300, 10360]:
        value = build(snapshot, log, caps, definition, packet)
        result["queries"].append(value)
        markdown += [f"## Query packet {packet}", "", sidecar.render(value["register_view"]), ""]
    if any(digest(path) != hashes[key] for key, path in paths.items()): raise ValueError("source changed during render")
    output.mkdir(parents=True)
    (output / "observations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "report.md").write_text("\n".join(markdown), encoding="utf-8")
    return {"status": "LOCAL_P10_STANDARD_VIEW_COMPLETE", "queries": 2, "fields": 3, "qualification": "NOT_EVALUATED"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ["snapshot", "log", "capabilities", "output"]: ap.add_argument("--" + arg, type=Path, required=True)
    a = ap.parse_args()
    try: print(json.dumps(generate(a.snapshot, a.log, a.capabilities, a.output))); return 0
    except (ValueError, OSError, KeyError) as e:
        print(json.dumps({"status": "INVALID", "error": str(e)})); return 2


if __name__ == "__main__": raise SystemExit(main())
