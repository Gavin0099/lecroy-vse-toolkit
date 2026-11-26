import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))
from protocol_event_stream import normalize


class EventStreamTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.acquisition = self.root / "sample"
        self.output = self.root / "out"
        self.acquisition.mkdir()

    def sample(self, lines, counts, *, footer=True, script_result=2):
        families = ("TLP", "ACK", "NAK", "DLLP", "LINK", "LTSSM", "ORDERED_SET", "EIE")
        records = ["PETracer banner", "PCIE_EVENT_BEGIN|1|100|200|1|2|63", *lines]
        records += [f"PCIE_EVENT_COUNT|{family}|{counts.get(family, 0)}" for family in families]
        if footer:
            records += ["PCIE_EVENT_END"]
        log = ("\n".join(records) + "\n").encode()
        (self.acquisition / "protocol-events.txt").write_bytes(log)
        binding = {"source": {"sha256": "a" * 64}, "display": {"sha256": "a" * 64}}
        data = {
            "schema": "pcie.protocol-events-acquisition/v1",
            "status": "VSE_DONE",
            "script_result": script_result,
            "inputs_unchanged": True,
            "before": binding,
            "after": binding,
            "owned_analyzer_pids_remaining": [],
            "window": [100, 200],
            "native_packet_count": 201,
            "packet_namespace": "source_packet",
            "filter_status": "UNKNOWN",
            "report": {"sha256": hashlib.sha256(log).hexdigest()},
        }
        (self.acquisition / "acquisition.json").write_text(json.dumps(data), encoding="utf-8")

    def read_events(self):
        return [json.loads(row) for row in (self.output / "events.jsonl").read_text().splitlines()]

    def test_retains_more_than_sixteen_ack_and_nak_rows_including_final_packet(self):
        lines = []
        for i in range(17):
            lines.append(f"PCIE_EVENT|ACK|{100 + i * 2}|2|Downstream|0|{i}|0|0,{i},0,0,NA,NA,NA,NA,NA")
            lines.append(f"PCIE_EVENT|NAK|{101 + i * 2}|1|Upstream|0|{i}|0|1,{i},0,0,NA,NA,NA,NA,NA")
        lines.append("PCIE_EVENT|ACK|200|2|Downstream|0|40|0|0,17,0,0,NA,NA,NA,NA,NA")
        self.sample(lines, {"ACK": 18, "NAK": 17})
        result = normalize(self.acquisition, self.output)
        self.assertEqual((result["counts"]["ACK"], result["counts"]["NAK"]), (18, 17))
        events = self.read_events()
        self.assertEqual((events[-2]["packet_index"], events[-1]["packet_index"]), (133, 200))
        self.assertEqual((events[-2]["direction"], events[-1]["direction"]), ("Upstream", "Downstream"))

    def test_keeps_wrapped_psn_and_exposes_unknown_state_and_coverage(self):
        self.sample([
            "PCIE_EVENT|TLP|100|1|Upstream|0|10|0|4095,4,0,1,0,0,1,NA",
            "PCIE_EVENT|LTSSM|101|1|Upstream|0|11|0|packet,5,13,1,0",
            "PCIE_EVENT|LINK|105|2|Downstream|0|20|0|1,down",
            "PCIE_EVENT|TLP|110|1|Upstream|0|30|0|0,4,0,1,0,0,1,NA",
            "PCIE_EVENT|TLP|111|2|Downstream|0|31|0|0,4,0,1,0,0,1,NA",
        ], {"TLP": 3, "LTSSM": 1, "LINK": 1})
        result = normalize(self.acquisition, self.output)
        self.assertEqual(result["initial_data_link_state"], "UNKNOWN")
        self.assertEqual(result["capture_continuity"], "UNKNOWN")
        tlps = [event for event in self.read_events() if event["kind"] == "TLP"]
        self.assertEqual([(event["direction"], event["fields"]["psn"]) for event in tlps],
                         [("Upstream", 4095), ("Upstream", 0), ("Downstream", 0)])

    def test_crc_bad_good_and_missing_flags_are_distinct(self):
        self.sample([
            "PCIE_EVENT|TLP|100|1|Upstream|0|10|0|11,4,0,1,0,0,1,NA",
            "PCIE_EVENT|NAK|101|2|Downstream|0|11|0|1,11,1,0,NA,NA,NA,NA,NA",
            "PCIE_EVENT|ACK|102|2|Downstream|0|12|0|0,11,NA,0,NA,NA,NA,NA,NA",
        ], {"TLP": 1, "NAK": 1, "ACK": 1})
        result = normalize(self.acquisition, self.output)
        self.assertEqual(result["crc_validation_counts"],
                         {"invalid": 1, "unknown": 1, "valid_analyzer_reported": 1})
        self.assertEqual([event["fields"]["crc_validation"] for event in self.read_events()],
                         ["valid_analyzer_reported", "invalid", "unknown"])

    def test_dropped_rows_never_publish_a_manifest(self):
        self.sample([], {"ACK": 17})
        with self.assertRaisesRegex(ValueError, "counts do not match"):
            normalize(self.acquisition, self.output)
        self.assertFalse((self.output / "manifest.json").exists())

    def test_missing_footer_is_rejected(self):
        self.sample([], {}, footer=False)
        with self.assertRaisesRegex(ValueError, "footer missing"):
            normalize(self.acquisition, self.output)

    def test_modified_report_and_wrong_native_status_are_rejected(self):
        self.sample([], {})
        with (self.acquisition / "protocol-events.txt").open("ab") as report:
            report.write(b"changed after acquisition\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            normalize(self.acquisition, self.output)
        self.sample([], {}, script_result=0)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            normalize(self.acquisition, self.root / "failed")

    def test_window_order_and_duplicate_rows_are_rejected(self):
        valid = "PCIE_EVENT|ACK|130|2|Downstream|0|10|0|0,11,0,0,NA,NA,NA,NA,NA"
        invalid = [
            (valid.replace("|130|", "|99|"), "outside the window"),
            (valid.replace("|130|", "|201|"), "outside the window"),
            (valid.replace("|130|", "|129|"), "out of order"),
            (valid, "duplicate event"),
        ]
        for i, (line, reason) in enumerate(invalid):
            with self.subTest(reason=reason):
                self.sample([valid, line], {"ACK": 2})
                with self.assertRaisesRegex(ValueError, reason):
                    normalize(self.acquisition, self.root / str(i))
