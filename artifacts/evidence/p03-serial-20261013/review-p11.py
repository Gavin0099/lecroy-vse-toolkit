from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
FROZEN = Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
sys.path.insert(0, str(ROOT / "tools"))
import pcie_recovery_observations as p
import s01_contract as s
value = p.saved_inputs(FROZEN, FROZEN / "artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json", HERE / "p11-constants-native-b")
out = HERE / "p11-state-points-r3"
assert value == s.read_json(out / "observations.json")
assert p.render(value, out) == (out / "report.html").read_text(encoding="utf-8")
# Independent packet list reviewed against raw legacy vector/source pointers,
# not obtained by asking the classifier which rows it selected.
expected = [225051, 990789, 990799, 1096915, 1096917, 1484186, 1484200, 1484216, 1484229]
observed = [r["packet_ref"]["index"] for r in value["points"] if r["feature"] == "recovery_state"]
assert observed == expected
assert sum(r["validity"] == "invalid" for r in value["points"]) == 2
assert value["observations"]["equalization_state"] == {"state": "unknown", "sample_count": 0}
assert value["observations"]["hot_reset_state"] == {"state": "unknown", "sample_count": 0}
assert value["physical_reset"] == "unknown" and value["timing_rules"] == "NOT_EVALUATED"
assert all(r["continuous_state_interval"] == "unknown" and r["elapsed_time"] == "unknown" for r in value["transitions"])
raw = s.read_json(Path(value["sources"]["state_points"]["path"]))
for point in value["points"]:
    original = raw[int(point["source_pointer"][1:])]
    assert point["packet_ref"]["index"] == original["packet_index"]
    assert point["raw"] == {k: original[k] for k in ["state", "substate", "subsubstate", "valid"]}

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.links.extend(v for k, v in attrs if k == "href")

links = Links(); links.feed((out / "report.html").read_text(encoding="utf-8"))
assert "script" not in links.tags and len(links.links) == 22
for url in links.links:
    parsed = urlsplit(url); path = Path(unquote(parsed.path).lstrip("/")) if parsed.scheme == "file" else out / unquote(parsed.path)
    assert path.exists(); assert s.read_json(path)[int(unquote(parsed.fragment)[1:])]["kind"] == "ltssm"
review = {"slice": "P11", "review": "APPROVE_SAVED_VALID_STATE_POINTS", "recovery_packets": expected,
          "ltssm_points": 22, "invalid_points": 2, "l0_points": 2, "link_condition_points": 14,
          "native_constants_revalidated": True, "trace_sha256": value["trace_sha256"],
          "constant_run": "p11-constants-native-b/com-run.json", "source_binding": "CORROBORATED_LEGACY",
          "report_directory": str(out), "qualification": "NOT_EVALUATED",
          "limits": value["limitations"] + ["EQ/HotReset absence not established; missing events remain unknown", "partial input eligibility; no capture mode/epoch proof"],
          "early_failure": "relative OpenFile path rejected; owned cleanup preserved; runtime process exited before successful absolute-path retry",
          "next_gate": "remaining candidates require independent input/source evidence; do not rebuild existing PASS views without a true gap"}
(HERE / "p11-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review": review["review"], "recovery_points": 9, "invalid_points": 2, "source_links": 22}))
