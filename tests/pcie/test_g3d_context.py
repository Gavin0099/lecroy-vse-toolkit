import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g3d_context as g3d

# 14 TLP rows. Row 1: first request (G3b); row 6: request, row 8: its UR completion (G3a);
# row 9: ERR_COR; row 12: repeated request (G3b).
SPEC = {
    1: ("0x9", "CfgRd0", "NON_POSTED_REQUEST", 5, None, None),
    6: ("0x1", "MRd(32)", "NON_POSTED_REQUEST", 5, None, None),
    8: ("0x11", "Cpl", "COMPLETION_CANDIDATE", 5, 0x100, 1),
    9: ("0xD", "Msg", "POSTED_OR_OTHER", 0, None, None),
    12: ("0x1", "MRd(32)", "NON_POSTED_REQUEST", 5, None, None),
}


def pkt(row):
    return 100 + 2 * row


def fixtures():
    fields, roles = [], []
    for n in range(1, 15):
        code, name, role, tag, completer, status = SPEC.get(n, ("0x3", "MWr(32)", "POSTED_OR_OTHER", 0, None, None))
        fields.append({"row": n, "packet_index": pkt(n), "time_display": "4.853 sec", "channel": "Upstream" if role == "COMPLETION_CANDIDATE" else "Downstream",
                       "tlp_type_hex": code, "tag": tag, "requester_id": 0x100 if code == "0xD" else 0, "completer_id": completer, "compl_status": status})
        roles.append({"row": n, "packet_index": pkt(n), "role": role, "vendor_type_name": name})
    associations = [
        {"packet_index": pkt(1), "outcome": "SAME_KEY_REISSUED_BEFORE_ANY_COMPLETION_OBSERVED", "completions": [], "reissued_at_packet": pkt(6)},
        {"packet_index": pkt(6), "outcome": "COMPLETIONS_OBSERVED", "completions": [{"packet_index": pkt(8)}]},
        {"packet_index": pkt(12), "outcome": "NONE_OBSERVED_IN_CAPTURE", "completions": []},
    ]
    candidates = [
        {"candidate_id": "C001", "detector": "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION", "anchor_time_display": "4.848 sec",
         "first_request": {"packet_index": pkt(1)}, "repeated_request": {"packet_index": pkt(12)}},
        {"candidate_id": "C002", "detector": "G3A_NON_SUCCESS_COMPLETION", "anchor_time_display": "4.853 sec",
         "request": {"packet_index": pkt(6)}, "completion": {"packet_index": pkt(8)}},
    ]
    message = {"packet": pkt(9), "message_name": "ERR_COR", "relationship": "temporal_correlation_only"}
    nearby = {"candidates": [
        {"candidate_id": "C001", "nearby_messages": [], "excluded_beyond_packet_bound": []},
        {"candidate_id": "C002", "nearby_messages": [message], "excluded_beyond_packet_bound": []},
    ]}
    return fields, roles, associations, candidates, nearby


class G3dTests(unittest.TestCase):
    def test_g3a_block_has_before_anchor_span_after_and_goto(self):
        results = g3d.build(*fixtures(), context_rows=3)
        c = results[1]
        self.assertEqual(c["candidate_anchor"]["primary_goto_packet"], pkt(6))
        block = c["context_blocks"][0]
        self.assertEqual([r["row"] for r in block["before"]["rows"]], [3, 4, 5])
        self.assertEqual([r["row"] for r in block["anchor"]["rows"]], [6, 7, 8])
        self.assertEqual([r["row"] for r in block["after"]["rows"]], [9, 10, 11])
        self.assertEqual(block["anchor"]["rows"][0]["markers"], ["ANCHOR_REQUEST"])
        self.assertEqual(block["anchor"]["rows"][2]["compl_status_name"], "UR")
        self.assertEqual(block["anchor"]["rows"][2]["association"], {"associated_request_packet": pkt(6)})
        self.assertEqual(block["after"]["rows"][0]["markers"], ["NEARBY_MESSAGE_G3C"])
        self.assertEqual(c["nearby_messages_from_g3c"][0]["message_name"], "ERR_COR")
        self.assertEqual(c["interpretation"], "NOT_EVALUATED")

    def test_truncation_is_marked_at_capture_boundaries(self):
        results = g3d.build(*fixtures(), context_rows=3)
        first, repeated = results[0]["context_blocks"]
        self.assertEqual((first["before"]["status"], first["before"]["rows"]), (g3d.TRUNCATED, []))
        self.assertEqual(first["after"]["status"], g3d.COMPLETE)
        self.assertEqual(repeated["after"]["status"], g3d.TRUNCATED)
        self.assertEqual([r["row"] for r in repeated["after"]["rows"]], [13, 14])
        self.assertIsNone(first["anchor"]["rows"][0]["packet_gap_from_previous_tlp_row"])
        self.assertEqual(first["after"]["rows"][0]["packet_gap_from_previous_tlp_row"], 2)

    def test_cross_candidate_anchor_reference_without_new_candidates(self):
        results = g3d.build(*fixtures(), context_rows=6)
        first_block = results[0]["context_blocks"][0]
        row6 = next(r for r in first_block["after"]["rows"] if r["row"] == 6)
        self.assertEqual(row6["also_anchor_of_candidates"], ["C002"])
        self.assertEqual(len(results), 2)

    def test_inputs_must_align_and_wording_stays_neutral(self):
        fields, roles, associations, candidates, nearby = fixtures()
        broken = [dict(r) for r in roles]
        broken[3]["packet_index"] = 9999
        with self.assertRaisesRegex(g3d.G3dError, "not aligned"):
            g3d.build(fields, broken, associations, candidates, nearby)
        with self.assertRaisesRegex(g3d.G3dError, "do not match"):
            g3d.build(fields, roles, associations, candidates, {"candidates": nearby["candidates"][:1]})
        text = json.dumps(g3d.build(*fixtures())).lower()
        for banned in ("caused", "root cause", "fault", "anomal", "timeout"):
            self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
