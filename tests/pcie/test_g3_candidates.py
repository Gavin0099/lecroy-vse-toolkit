import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g3_candidates as g3


def request(packet, tag, outcome, completions=(), reissued_at=None, kind="CfgRd0"):
    q = {
        "packet_index": packet, "time_display": "4.848 sec", "channel": "Downstream", "vendor_type_name": kind,
        "requester_bdf": "000:00.0", "tag": tag, "outcome": outcome, "completions": list(completions),
    }
    if reissued_at is not None:
        q["reissued_at_packet"] = reissued_at
    return q


def completion(packet, status, request_packet):
    return {
        "packet_index": packet, "time_display": "4.853 sec", "channel": "Upstream", "vendor_type_name": "Cpl",
        "type_evidence": "VENDOR_CONSTANT", "completer_bdf": "001:00.0", "compl_status": status,
        "compl_status_name": {0: "SC", 1: "UR", 4: "CA"}[status], "packet_gap_from_request": packet - request_packet,
    }


REQUESTS = [
    request(100, 11, g3.REISSUED, reissued_at=200),
    request(150, 5, "COMPLETIONS_OBSERVED", [completion(152, 0, 150)]),
    request(160, 6, g3.REISSUED, reissued_at=170),
    request(170, 6, "NONE_OBSERVED_IN_CAPTURE"),
    request(200, 11, "COMPLETIONS_OBSERVED", [completion(203, 1, 200)], kind="MRd(32)"),
]


class G3CandidateTests(unittest.TestCase):
    def test_non_success_completion_candidate_is_not_interpreted(self):
        crosscheck = [{"request_packet": 200, "completion_packet": 203, "lecroy_view": "Split Tra 22", "result": "MATCHED", "screenshots": []}]
        candidates = g3.detect(REQUESTS, crosscheck)
        g3a = [c for c in candidates if c["detector"] == "G3A_NON_SUCCESS_COMPLETION"]
        self.assertEqual(len(g3a), 1)
        self.assertEqual((g3a[0]["request"]["packet_index"], g3a[0]["completion"]["compl_status_name"]), (200, "UR"))
        self.assertEqual(g3a[0]["earlier_same_key_requests_reissued_into_this_request"], 1)
        self.assertEqual(g3a[0]["gui_crosscheck"]["result"], "MATCHED")
        self.assertEqual(g3a[0]["interpretation"], "NOT_EVALUATED")
        self.assertNotIn(152, [c["anchor_packet"] for c in candidates])

    def test_reappeared_key_reports_later_completion_without_attributing_it(self):
        candidates = g3.detect(REQUESTS)
        g3b = {c["first_request"]["packet_index"]: c for c in candidates if c["detector"] == "G3B_SAME_KEY_REAPPEARED_BEFORE_COMPLETION"}
        self.assertEqual(sorted(g3b), [100, 160])
        self.assertEqual((g3b[100]["repeated_request"]["packet_index"], g3b[100]["packet_gap"]), (200, 100))
        self.assertEqual(g3b[100]["completion_observed_later_for_same_key"], "YES")
        self.assertEqual(g3b[100]["later_completion"]["associated_with_request_packet"], 200)
        self.assertIn("not necessarily", g3b[100]["later_completion"]["note"])
        self.assertEqual(g3b[160]["completion_observed_later_for_same_key"], "NO")
        self.assertIsNone(g3b[160]["later_completion"])

    def test_wording_avoids_fault_retry_and_timeout_claims(self):
        text = json.dumps(g3.detect(REQUESTS)).lower()
        for banned in ("fault", "timeout", "retry error", "anomaly", "root cause"):
            self.assertNotIn(banned, text)
        self.assertIn("same association key observed again before an associated completion was observed", text)

    def test_ids_follow_capture_order_and_output_refuses_reuse(self):
        candidates = g3.detect(REQUESTS)
        self.assertEqual([c["candidate_id"] for c in candidates], ["C001", "C002", "C003"])
        self.assertEqual([c["anchor_packet"] for c in candidates], [100, 160, 203])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "associations.json"
            source.write_text(json.dumps(REQUESTS), encoding="utf-8")
            result = g3.build(source, None)
            self.assertEqual(result["ground_truth"], "UNKNOWN")
            self.assertEqual(result["ranking"], "NONE")
            g3.write(result, root / "out")
            self.assertTrue((root / "out" / "candidates.tsv").is_file())
            with self.assertRaisesRegex(g3.G3Error, "existing output directory"):
                g3.write(result, root / "out")

    def test_broken_reissue_chain_is_rejected(self):
        broken = [request(100, 1, g3.REISSUED, reissued_at=999)]
        with self.assertRaisesRegex(g3.G3Error, "missing"):
            g3.detect(broken)


if __name__ == "__main__":
    unittest.main()
