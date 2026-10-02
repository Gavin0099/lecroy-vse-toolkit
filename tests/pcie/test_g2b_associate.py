import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))

import g2b_associate as g2b


def row(n, index, type_hex, tag, requester=0, completer=None, status=None, channel="Downstream"):
    return {
        "row": n, "packet_index": index, "time_display": "5.000 sec", "channel": channel, "tlp_type_hex": type_hex,
        "tag": tag, "requester_id": requester, "completer_id": completer, "compl_status": status,
    }


def run(rows):
    roles = [g2b.classify(r) for r in rows]
    requests, orphans = g2b.associate(rows, roles)
    return roles, requests, orphans


class ClassificationTests(unittest.TestCase):
    def test_roles_follow_vendor_constants_and_field_shape(self):
        roles = [g2b.classify(r) for r in (
            row(1, 10, "0x9", 3),
            row(2, 11, "0x3", 0),
            row(3, 12, "0xE", 0),
            row(4, 13, "0x11", 3, completer=0x100, status=1, channel="Upstream"),
            row(5, 14, "0x12", 3, completer=0x100, status=0, channel="Upstream"),
            row(6, 15, "0x1B", 0),
            row(7, 16, "0x11", 3),
        )]
        self.assertEqual([r["role"] for r in roles], [
            g2b.NON_POSTED_REQUEST, g2b.POSTED, g2b.POSTED, g2b.COMPLETION_CANDIDATE, g2b.COMPLETION_CANDIDATE, g2b.UNKNOWN, g2b.UNKNOWN,
        ])
        self.assertEqual(roles[0]["type_evidence"], "GUI_CONFIRMED+VENDOR_CONSTANT")
        self.assertEqual(roles[3]["type_evidence"], "VENDOR_CONSTANT")
        self.assertEqual(roles[5]["type_evidence"], "UNMAPPED")
        self.assertIn("completion type without", roles[6]["notes"][0])


class AssociationTests(unittest.TestCase):
    def test_split_completions_accumulate_on_one_request(self):
        _, requests, orphans = run([
            row(1, 10, "0x1", 5),
            row(2, 20, "0x12", 5, completer=0x100, status=0, channel="Upstream"),
            row(3, 30, "0x12", 5, completer=0x100, status=0, channel="Upstream"),
        ])
        self.assertEqual(requests[0]["outcome"], g2b.COMPLETIONS_OBSERVED)
        self.assertEqual([c["packet_index"] for c in requests[0]["completions"]], [20, 30])
        self.assertEqual(requests[0]["completions"][0]["direction_relation"], "opposite")
        self.assertEqual(orphans, [])

    def test_no_completion_is_not_called_timeout(self):
        _, requests, _ = run([row(1, 10, "0x9", 2)])
        self.assertEqual(requests[0]["outcome"], "NONE_OBSERVED_IN_CAPTURE")
        self.assertNotIn("TIMEOUT", requests[0]["outcome"])

    def test_reissued_key_before_completion_is_not_guessed(self):
        _, requests, _ = run([
            row(1, 10, "0x9", 4),
            row(2, 20, "0x9", 4),
            row(3, 30, "0x11", 4, completer=0x100, status=1, channel="Upstream"),
        ])
        self.assertEqual(requests[0]["outcome"], g2b.REISSUED)
        self.assertEqual(requests[0]["reissued_at_packet"], 20)
        self.assertEqual(requests[1]["outcome"], g2b.COMPLETIONS_OBSERVED)
        self.assertEqual(requests[1]["completions"][0]["compl_status_name"], "UR")

    def test_key_uses_requester_and_tag_only_and_completion_must_follow(self):
        _, requests, orphans = run([
            row(1, 10, "0x11", 6, completer=0x100, status=0, channel="Upstream"),
            row(2, 20, "0x9", 6, requester=0x0000),
            row(3, 30, "0x11", 6, requester=0x0100, completer=0x100, status=0, channel="Upstream"),
            row(4, 40, "0x11", 6, requester=0x0000, completer=0x200, status=4, channel="Upstream"),
        ])
        self.assertEqual([o["packet_index"] for o in orphans], [10, 30])
        self.assertEqual(orphans[0]["association"], g2b.ORPHAN)
        self.assertEqual([c["packet_index"] for c in requests[0]["completions"]], [40])
        self.assertEqual(requests[0]["completions"][0]["compl_status_name"], "CA")

    def test_rejects_out_of_order_rows_and_existing_output(self):
        rows = [row(1, 20, "0x9", 1), row(2, 10, "0x9", 1)]
        with self.assertRaisesRegex(g2b.G2bError, "capture order"):
            run(rows)
        roles, requests, orphans = run([row(1, 10, "0x9", 1)])
        summary = g2b.summarize([row(1, 10, "0x9", 1)], roles, requests, orphans)
        self.assertIn("completion timeout: no completion observed before capture end is not a protocol timeout", summary["not_established"])
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "out"
            g2b.write_outputs(target, roles, requests, orphans, summary)
            self.assertTrue((target / "associations.tsv").is_file())
            with self.assertRaisesRegex(g2b.G2bError, "existing output directory"):
                g2b.write_outputs(target, roles, requests, orphans, summary)


if __name__ == "__main__":
    unittest.main()
