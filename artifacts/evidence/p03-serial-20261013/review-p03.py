import hashlib
import json
from pathlib import Path
import re
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcie_field_probe as p
import s01_contract as s

plan = s.read_json(HERE / "prepared/plan.json")
checks = []; repeated = {}; type_counts = {}
for profile in ["dllp", "tlp"]:
    observations = []
    for suffix in ["a", "b"]:
        directory = HERE / (profile + "-" + suffix)
        before = s.read_json(directory / "before.json"); after = s.read_json(directory / "after.json")
        assert before == after and before["working"]["readonly"]
        native = directory / "native"
        value = p.assess(s.read_json(native / "com-run.json"), s.read_json(native / "report-lines.json"), plan, profile)
        assert value == s.read_json(directory / "observations.json")
        observations.append(value)
    assert observations[0] == observations[1]
    repeated[profile] = observations[0]["summary"]
    type_counts[profile] = observations[0]["counts"]
    seen = set()
    for row in observations[0]["rows"]:
        if row["native_type"] in seen: continue
        seen.add(row["native_type"])
        # Separate native API export; known displayed labels are handwritten,
        # never obtained from production applicability or field serialization.
        path = HERE / "packet-text" / f"packets-{row['index']}-{row['index']}.txt"
        text = path.read_text(encoding="utf-8")
        assert f"Packet({row['index']})" in text
        mappings = {"PSN": r"TLP\((\d+)\)", "Length": r"Length\((\d+)\)",
                    "ByteCount": r"Byte Cnt\((\d+)\)", "LowerAddr": r"Lwr Addr\((0x[0-9A-Fa-f]+)\)",
                    "AckNak_SeqNum": r"AckNak_Seq_Num\((\d+)\)", "VC_ID": r"VC ID\((\d+)\)",
                    "HdrFC": r"HdrFC\((\d+)\)", "DataFC": r"DataFC\((\d+)\)",
                    "HdrScale": r"HdrScale\((\d+)\)", "DataScale": r"DataScale\((\d+)\)"}
        matched = []
        for field, pattern in mappings.items():
            cell = row["fields"].get(field)
            if cell is None or cell["state"] != "available": continue
            match = re.search(pattern, text); assert match, (row["index"], field)
            literal = match[1]; expected = int(literal, 16 if literal.startswith("0x") else 10)
            assert cell["value"] == expected, (row["index"], field)
            matched.append(field)
        checks.append({"profile": profile, "native_type": row["native_type"], "packet": row["index"], "fields": matched,
                       "text_file": str(path.relative_to(HERE)), "text_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
export = s.read_json(HERE / "packet-text/com-export.json")
assert export["status"] == "COM_EXPORT_COMPLETE" and export["identities_unchanged"] and export["process_exit_ok"]
assert len(checks) == 18
assert repeated["tlp"]["visited"] == 704  # prior G1/G2a exact converted-source count
assert repeated["dllp"]["visited"] == 2147145  # P01 same source
review = {"slice": "P03", "review": "APPROVE_BOUNDED_NATIVE_FIELDS", "source_sha256": plan["trace_sha256"],
          "repeat_equal": True, "summaries": repeated, "type_counts": type_counts, "packet_crosschecks": checks,
          "crosscheck_authority": "independent API path, same vendor decoder; not an independent protocol compliance oracle",
          "limits": ["first8 per native type; 124 sampled rows total", "zero UpdateFC_Cpl and missing TLP types remain unknown",
                     "ACK/NAK FCError null remains unknown", "raw zero length and scale encodings unchanged; no credit units inferred",
                     "error flags have no positive sample qualification", "capture mode/epoch/retention/display filters unknown",
                     "not all P03 modes/types qualified; no replay, credit, absence or compliance verdict"],
          "next_allowed": "I01 isolated typed P03 source block; W1-W5 stay frozen",
          "blocked_dependents": {"P04": "applicable normative replay text and continuous epoch coverage missing",
                                 "P05": "normative credit rules and initial-credit baseline/direction/epoch missing",
                                 "P06": "P02 packet membership and unique outstanding request identity not qualified"}}
(HERE / "p03-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review": review["review"], "sampled_rows": 124, "packet_crosschecks": len(checks), "repeat_equal": True}))
