import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g3e_groups as g3e

REISSUED = g3e.REISSUED


def req(packet, outcome="COMPLETIONS_OBSERVED", reissued_at=None):
    q = {"packet_index": packet, "outcome": outcome, "completions": []}
    if reissued_at is not None:
        q["reissued_at_packet"] = reissued_at
    return q


def g3a(cid, request, completion, tag=1, time="4.853 sec"):
    return {"candidate_id": cid, "detector": g3e.G3A, "anchor_time_display": time,
            "request": {"packet_index": request, "type": "MRd(32)", "tag": tag},
            "completion": {"packet_index": completion, "compl_status_name": "UR"}}


def g3b(cid, first, repeated, tag=1, time="4.848 sec"):
    return {"candidate_id": cid, "detector": g3e.G3B, "anchor_time_display": time, "tag": tag,
            "first_request": {"packet_index": first, "type": "CfgRd0"},
            "repeated_request": {"packet_index": repeated, "type": "MRd(32)"}}


def nearby_for(ids, message_ids=()):
    msg = {"packet": 500, "message_name": "ERR_COR", "display_time": "4.853 sec"}
    return {"candidates": [{"candidate_id": cid, "nearby_messages": [msg] if cid in message_ids else []} for cid in ids]}


class G3eTests(unittest.TestCase):
    def test_lineage_and_shared_anchor_merge_g3b_into_g3a(self):
        associations = [req(10, REISSUED, 20), req(20, REISSUED, 30), req(30), req(40)]
        candidates = [g3b("C001", 10, 20), g3b("C002", 20, 30), g3a("C003", 30, 31), g3a("C004", 40, 41)]
        groups = g3e.group(candidates, associations, nearby_for(["C001", "C002", "C003", "C004"]))
        self.assertEqual([g["members"] for g in groups], [["C001", "C002", "C003"], ["C004"]])
        self.assertEqual(groups[0]["grouping_basis"],
                         ["request_or_completion_is_other_candidate_anchor", "shared_anchor_packet", "shared_association_lineage"])
        self.assertEqual(groups[0]["primary_go_to_packet"], 10)
        self.assertEqual(groups[0]["lineage"], {"request_packets": [10, 20, 30], "packet_span": 20})
        self.assertEqual(groups[1]["relationship"], "singleton_no_strong_relationship")
        self.assertEqual(groups[1]["grouping_basis"], ["none_singleton"])

    def test_weak_relations_never_merge(self):
        associations = [req(10), req(20)]
        candidates = [g3a("C001", 10, 11, tag=3, time="4.853 sec"), g3a("C002", 20, 21, tag=3, time="4.853 sec")]
        groups = g3e.group(candidates, associations, nearby_for(["C001", "C002"], message_ids=("C001", "C002")))
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["auxiliary_descriptors_not_used_for_grouping"]["nearby_messages_from_g3c"][0]["message_name"], "ERR_COR")

    def test_every_candidate_exactly_once_and_ids_follow_primary_packet(self):
        associations = [req(50), req(10, REISSUED, 50), req(70)]
        candidates = [g3a("C001", 70, 71), g3b("C002", 10, 50), g3a("C003", 50, 52)]
        groups = g3e.group(candidates, associations, nearby_for(["C001", "C002", "C003"]))
        members = [cid for g in groups for cid in g["members"]]
        self.assertEqual(sorted(members), ["C001", "C002", "C003"])
        self.assertEqual([g["group_id"] for g in groups], ["G001", "G002"])
        self.assertEqual(groups[0]["primary_go_to_packet"], 10)

    def test_no_scores_or_interpretation_fields(self):
        associations = [req(10)]
        groups = g3e.group([g3a("C001", 10, 11)], associations, nearby_for(["C001"]))
        text = json.dumps(groups).lower()
        for banned in ("severity", "confidence", "priority", "score", "root cause", "fault"):
            self.assertNotIn(banned, text)
        self.assertEqual(groups[0]["interpretation"], "NOT_EVALUATED")

    def test_inconsistent_inputs_rejected(self):
        with self.assertRaisesRegex(g3e.G3eError, "missing from G2b"):
            g3e.group([g3a("C001", 10, 11)], [], nearby_for(["C001"]))
        with self.assertRaisesRegex(g3e.G3eError, "do not match"):
            g3e.group([g3a("C001", 10, 11)], [req(10)], nearby_for(["C009"]))
        with self.assertRaisesRegex(g3e.G3eError, "Broken reissue chain"):
            g3e.group([g3b("C001", 10, 99)], [req(10, REISSUED, 99)], nearby_for(["C001"]))


if __name__ == "__main__":
    unittest.main()
