import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g3d_context as g3d
import g3e_groups as g3e
import g3f_findings as g3f

REISSUED = "SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED"


def pkt(row):
    return 1000 + 2 * row if row < 20 else 200000 + 2 * row


def build_inputs():
    # Row 2: CfgRd0 Tag 3 (first request). Row 24: MRd Tag 3 (repeated request / G3a request).
    # Row 25: its UR completion. Row 26: ERR_COR. Row 10: independent CfgRd0 with no candidate.
    spec = {2: ("0x9", "CfgRd0", "NON_POSTED_REQUEST", 3, None, None),
            24: ("0x1", "MRd(32)", "NON_POSTED_REQUEST", 3, None, None),
            25: ("0x11", "Cpl", "COMPLETION_CANDIDATE", 3, 0x100, 1),
            26: ("0xD", "Msg", "POSTED_OR_OTHER", 0, None, None)}
    fields, roles = [], []
    for n in range(1, 31):
        code, name, role, tag, completer, status = spec.get(n, ("0x3", "MWr(32)", "POSTED_OR_OTHER", 0, None, None))
        fields.append({"row": n, "packet_index": pkt(n), "time_display": "4.848 sec" if n < 20 else "5.880 sec",
                       "channel": "Upstream" if role == "COMPLETION_CANDIDATE" else "Downstream", "tlp_type_hex": code,
                       "tag": tag, "requester_id": 0, "completer_id": completer, "compl_status": status})
        roles.append({"row": n, "packet_index": pkt(n), "role": role, "vendor_type_name": name})
    associations = [
        {"packet_index": pkt(2), "outcome": REISSUED, "reissued_at_packet": pkt(24), "completions": []},
        {"packet_index": pkt(24), "outcome": "COMPLETIONS_OBSERVED", "completions": [{"packet_index": pkt(25)}]},
    ]
    candidates = [
        {"candidate_id": "C001", "detector": g3e.G3B, "anchor_packet": pkt(2), "anchor_time_display": "4.848 sec", "tag": 3,
         "first_request": {"packet_index": pkt(2), "type": "CfgRd0"}, "repeated_request": {"packet_index": pkt(24), "type": "MRd(32)"}},
        {"candidate_id": "C002", "detector": g3e.G3A, "anchor_packet": pkt(25), "anchor_time_display": "5.880 sec",
         "request": {"packet_index": pkt(24), "type": "MRd(32)", "tag": 3},
         "completion": {"packet_index": pkt(25), "compl_status_name": "UR"},
         "gui_crosscheck": {"result": "MATCHED", "lecroy_view": "Split Tra 29 (detail)", "screenshots": []}},
    ]
    message = {"packet": pkt(26), "message_name": "ERR_COR", "display_time": "5.880 sec", "position": "after",
               "gap_reference_packet": pkt(25), "relationship": "temporal_correlation_only"}
    nearby = {"candidates": [
        {"candidate_id": "C001", "nearby_messages": [], "excluded_beyond_packet_bound": []},
        {"candidate_id": "C002", "nearby_messages": [message], "excluded_beyond_packet_bound": []},
    ]}
    contexts = {"candidates": g3d.build(fields, roles, associations, candidates, nearby, context_rows=3)}
    groups = {"groups": g3e.group(candidates, associations, nearby),
              "detectors": {g3e.G3A: {"surfaces": "An associated completion reports a status other than SC."},
                            g3e.G3B: {"surfaces": "Same association key observed again before an associated completion was observed in the captured sequence."}}}
    return groups, candidates, nearby, contexts, fields


class G3fTests(unittest.TestCase):
    def test_message_outside_context_rows_is_placed_by_g3c_reference_anchor(self):
        groups, candidates, nearby, contexts, fields = build_inputs()
        far = dict(nearby["candidates"][1]["nearby_messages"][0], packet=pkt(30))
        nearby["candidates"][1]["nearby_messages"] = [far]
        f = g3f.build(groups, candidates, nearby, contexts, fields)[0]
        segment_b = f["what_was_observed"]["local_segments"][1]
        self.assertEqual([m["packet"] for m in segment_b["nearby_messages"]], [pkt(30)])
        self.assertEqual(f["what_was_observed"]["nearby_messages_outside_segments"], [])

    def test_interior_rows_between_request_and_completion_are_not_anchors(self):
        groups, candidates, nearby, contexts, fields = build_inputs()
        cpl = next(c for c in candidates if c["candidate_id"] == "C002")
        cpl["completion"]["packet_index"] = pkt(27)
        associations = [
            {"packet_index": pkt(2), "outcome": REISSUED, "reissued_at_packet": pkt(24), "completions": []},
            {"packet_index": pkt(24), "outcome": "COMPLETIONS_OBSERVED", "completions": [{"packet_index": pkt(27)}]},
        ]
        roles = [{"row": r["row"], "packet_index": r["packet_index"],
                  "role": "COMPLETION_CANDIDATE" if r["row"] == 27 else ("NON_POSTED_REQUEST" if r["row"] in (2, 24) else "POSTED_OR_OTHER"),
                  "vendor_type_name": "Cpl" if r["row"] == 27 else "MWr(32)"} for r in fields]
        fields[26]["completer_id"], fields[26]["compl_status"] = 0x100, 1
        contexts = {"candidates": g3d.build(fields, roles, associations, candidates, nearby, context_rows=3)}
        groups = {"groups": g3e.group(candidates, associations, nearby), "detectors": groups["detectors"]}
        f = g3f.build(groups, candidates, nearby, contexts, fields)[0]
        packets = [a["packet"] for a in f["what_was_observed"]["local_segments"][1]["anchors"]]
        self.assertEqual(packets, [pkt(24), pkt(27)])

    def test_singleton_with_two_segments_uses_candidate_wording(self):
        groups, candidates, nearby, contexts, fields = build_inputs()
        only = [c for c in candidates if c["candidate_id"] == "C001"]
        associations = [{"packet_index": pkt(2), "outcome": REISSUED, "reissued_at_packet": pkt(24), "completions": []},
                        {"packet_index": pkt(24), "outcome": "NONE_OBSERVED_IN_CAPTURE", "completions": []}]
        nearby_one = {"candidates": [nearby["candidates"][0]]}
        groups_one = {"groups": g3e.group(only, associations, nearby_one), "detectors": groups["detectors"]}
        contexts_one = {"candidates": [c for c in contexts["candidates"] if c["candidate_id"] == "C001"]}
        f = g3f.build(groups_one, only, nearby_one, contexts_one, fields)[0]
        limitation = next(u for u in f["not_known"] if "same failure episode" in u)
        self.assertTrue(limitation.startswith("This candidate's anchors lie in separate local segments"))

    def test_long_lineage_group_is_split_into_local_segments_with_limitation(self):
        findings = g3f.build(*build_inputs())
        self.assertEqual(len(findings), 1)
        f = findings[0]
        segments = f["what_was_observed"]["local_segments"]
        self.assertEqual([s["segment"] for s in segments], ["A", "B"])
        self.assertEqual(segments[0]["display_times"], ["4.848 sec"])
        self.assertEqual([a["packet"] for a in segments[1]["anchors"]], [pkt(24), pkt(25)])
        self.assertIn("C001:repeated_request", segments[1]["anchors"][0]["roles"])
        self.assertIn("C002:request", segments[1]["anchors"][0]["roles"])
        self.assertEqual(segments[1]["nearby_messages"][0]["message"], "ERR_COR")
        self.assertEqual(f["where_to_look"]["primary_go_to_packet"], pkt(2))
        self.assertEqual(f["where_to_look"]["segment_go_to_packets"], [pkt(2), pkt(24)])
        self.assertEqual(f["trace_span_packets"], pkt(25) - pkt(2))
        limitation = next(u for u in f["not_known"] if "same failure episode" in u)
        self.assertIn("same G2b same-key association lineage", limitation)

    def test_five_questions_are_answered_and_wording_is_neutral(self):
        f = g3f.build(*build_inputs())[0]
        for key in ("where_to_look", "what_was_observed", "why_surfaced", "not_known"):
            self.assertTrue(f[key])
        self.assertEqual(f["gui_crosschecks"], [{"candidate_id": "C002", "result": "MATCHED", "lecroy_view": "Split Tra 29"}])
        self.assertEqual(f["interpretation"], "NOT_EVALUATED")
        text = json.dumps(f).lower()
        for banned in ("severity", "confidence", "priority", "root cause", "caused", "fault type"):
            self.assertNotIn(banned, text)

    def test_single_segment_group_has_no_episode_limitation(self):
        groups, candidates, nearby, contexts, fields = build_inputs()
        only = [c for c in candidates if c["candidate_id"] == "C002"]
        groups = {"groups": g3e.group(only, [{"packet_index": pkt(24), "outcome": "COMPLETIONS_OBSERVED", "completions": []}],
                                      {"candidates": [nearby["candidates"][1]]}), "detectors": groups["detectors"]}
        f = g3f.build(groups, only, {"candidates": [nearby["candidates"][1]]},
                      {"candidates": [c for c in contexts["candidates"] if c["candidate_id"] == "C002"]}, fields)[0]
        self.assertEqual(len(f["what_was_observed"]["local_segments"]), 1)
        self.assertFalse(any("same failure episode" in u for u in f["not_known"]))

    def test_missing_candidate_in_contexts_is_rejected(self):
        groups, candidates, nearby, contexts, fields = build_inputs()
        with self.assertRaisesRegex(g3f.G3fError, "differ"):
            g3f.build(groups, candidates, nearby, {"candidates": contexts["candidates"][:1]}, fields)


if __name__ == "__main__":
    unittest.main()
