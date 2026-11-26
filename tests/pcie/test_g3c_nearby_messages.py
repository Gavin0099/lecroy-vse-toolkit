import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g3c_nearby_messages as g3c

# 40 TLP rows; packet index = 1000 + 3 * row so packet gaps differ from row gaps.
FIELDS = [{"row": n, "packet_index": 1000 + 3 * n} for n in range(1, 41)]


def pkt(row):
    return 1000 + 3 * row


def message(row, name="ERR_COR"):
    return {"packet_index": pkt(row), "time_display": "4.853 sec", "tlp_type_hex": "0xD", "message_code": 0x30,
            "message_code_name": name, "requester_id": 0x100, "message_route_name": "TOROOTCOMPLEX"}


G3A = {"candidate_id": "C001", "detector": "G3A_NON_SUCCESS_COMPLETION", "anchor_packet": pkt(12), "anchor_time_display": "4.853 sec",
       "request": {"packet_index": pkt(10)}, "completion": {"packet_index": pkt(12)}}
G3B = {"candidate_id": "C002", "detector": "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION", "anchor_packet": pkt(2), "anchor_time_display": "4.848 sec",
       "first_request": {"packet_index": pkt(2)}, "repeated_request": {"packet_index": pkt(35)}}


class G3cTests(unittest.TestCase):
    def test_message_after_span_within_window_is_attached_with_gaps(self):
        results, unattached = g3c.attach([G3A], FIELDS, [message(18), message(30, "SLOTPOWERLIMIT")], window=8)
        near = results[0]["nearby_messages"]
        self.assertEqual(len(near), 1)
        self.assertEqual((near[0]["position"], near[0]["tlp_row_gap"], near[0]["packet_gap"]), ("after", 6, 18))
        self.assertEqual(near[0]["gap_reference_packet"], pkt(12))
        self.assertEqual(near[0]["relationship"], "temporal_correlation_only")
        self.assertEqual(results[0]["interpretation"], "NOT_EVALUATED")
        self.assertEqual([u["message_name"] for u in unattached], ["SLOTPOWERLIMIT"])

    def test_window_bounds_are_inclusive_and_exclusive_beyond(self):
        inside, _ = g3c.attach([G3A], FIELDS, [message(2)], window=8)
        self.assertEqual(inside[0]["nearby_messages"][0]["tlp_row_gap"], -8)
        outside, unattached = g3c.attach([G3A], FIELDS, [message(1)], window=8)
        self.assertEqual(outside[0]["nearby_messages"], [])
        self.assertEqual(len(unattached), 1)

    def test_message_between_request_and_completion_is_inside_span(self):
        results, _ = g3c.attach([G3A], FIELDS, [message(11)], window=0)
        self.assertEqual(results[0]["nearby_messages"][0]["position"], "inside_anchor_span")

    def test_g3b_searches_first_and_repeated_request_separately(self):
        results, _ = g3c.attach([G3B], FIELDS, [message(20), message(33)], window=4)
        near = results[0]["nearby_messages"]
        self.assertEqual([(n["span_anchors"], n["packet"]) for n in near], [(["repeated_request"], pkt(33))])
        self.assertEqual(len(results[0]["window"]["spans"]), 2)

    def test_row_adjacent_message_across_capture_gap_is_excluded_not_attached(self):
        gapped = [{"row": n, "packet_index": (1000 + 3 * n) if n <= 15 else (150000 + 3 * n)} for n in range(1, 41)]
        far = {**message(18), "packet_index": 150000 + 3 * 18}
        results, unattached = g3c.attach([G3A], gapped, [far], window=8, max_packet_gap=64)
        self.assertEqual(results[0]["nearby_messages"], [])
        excluded = results[0]["excluded_beyond_packet_bound"]
        self.assertEqual((excluded[0]["tlp_row_gap"], excluded[0]["packet_gap"] > 64), (6, True))
        self.assertEqual(len(unattached), 1)
        self.assertEqual(results[0]["window"]["max_abs_packet_gap"], 64)

    def test_no_causal_wording_and_bad_inputs_rejected(self):
        results, _ = g3c.attach([G3A, G3B], FIELDS, [message(18)], window=8)
        text = json.dumps(results).lower()
        for banned in ("caused", "cause", "root cause", "fault", "anomal"):
            self.assertNotIn(banned, text)
        with self.assertRaisesRegex(g3c.G3cError, "not a TLP row"):
            g3c.attach([G3A], FIELDS, [{**message(18), "packet_index": 5}])
        with self.assertRaisesRegex(g3c.G3cError, "non-negative"):
            g3c.attach([G3A], FIELDS, [], window=-1)


if __name__ == "__main__":
    unittest.main()
