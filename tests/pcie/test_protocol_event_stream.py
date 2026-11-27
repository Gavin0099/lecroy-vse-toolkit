import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))
from protocol_event_stream import normalize, summarize_dllp_anomalies


def dllp_event(packet_index, kind="ACK", *, direction="Upstream", **fields):
    return {"kind": kind, "packet_index": packet_index, "direction": direction, "fields": fields}


class DllpSummaryTests(unittest.TestCase):
    def test_empty_and_non_dllp_events(self):
        expected = {
            "schema": "pcie.dllp-anomaly-summary/v1",
            "diagnosis_claim": "summary_only_not_pcie_dll_001_verdict",
            "total_dllp_events": 0,
            "by_direction": {},
        }
        self.assertEqual(summarize_dllp_anomalies(iter(())), expected)
        self.assertEqual(summarize_dllp_anomalies([{"kind": "TLP"}, {"kind": "LINK"}]), expected)

    def test_wrap_and_backward_sequences_are_isolated_by_direction(self):
        events = [
            dllp_event(1, ack_nak_seq_num=4095),
            dllp_event(2, direction="Downstream", ack_nak_seq_num=100),
            dllp_event(3, ack_nak_seq_num=0),
            dllp_event(4, "NAK", direction="Downstream", ack_nak_seq_num=95),
        ]
        directions = summarize_dllp_anomalies(iter(events))["by_direction"]
        self.assertEqual(list(directions), ["Downstream", "Upstream"])
        upstream, downstream = directions["Upstream"], directions["Downstream"]
        self.assertEqual((upstream["wrap_around_count"], upstream["backward_seq_count"]), (1, 0))
        self.assertEqual((downstream["wrap_around_count"], downstream["backward_seq_count"]), (0, 1))
        self.assertEqual(downstream["backward_seq_samples"],
                         [{"packet_index": 4, "kind": "NAK", "prev_seq": 100, "curr_seq": 95}])

    def test_half_range_delta_is_backward(self):
        events = [dllp_event(1, ack_nak_seq_num=0), dllp_event(2, ack_nak_seq_num=2048)]
        upstream = summarize_dllp_anomalies(events)["by_direction"]["Upstream"]
        self.assertEqual(upstream["backward_seq_count"], 1)
        self.assertEqual(upstream["wrap_around_count"], 0)

    def test_missing_and_invalid_sequences_do_not_interrupt_repeat_tracking(self):
        events = [dllp_event(1, ack_nak_seq_num=10), dllp_event(2)]
        events.extend(
            dllp_event(index, ack_nak_seq_num=seq)
            for index, seq in enumerate((None, -1, 4096, True, "10", 10.0), start=3)
        )
        events.extend([dllp_event(9, "DLLP", ack_nak_seq_num=100),
                       dllp_event(10, "NAK", ack_nak_seq_num=10)])
        upstream = summarize_dllp_anomalies(events)["by_direction"]["Upstream"]
        self.assertEqual(upstream["missing_seq_count"], 2)
        self.assertEqual(upstream["out_of_range_seq_count"], 5)
        self.assertEqual(upstream["repeated_seq_count"], 1)
        self.assertEqual(upstream["backward_seq_count"], 0)
        self.assertEqual(upstream["wrap_around_count"], 0)

    def test_crc_counts_and_unknown_direction(self):
        events = [
            dllp_event(1, direction="", crc_validation="valid_analyzer_reported"),
            {"kind": "NAK", "packet_index": 2, "fields": {"crc_validation": "invalid"}},
            dllp_event(3, "DLLP", direction="UNKNOWN", crc_validation="unknown"),
            dllp_event(4, "DLLP", direction="UNKNOWN"),
            dllp_event(5, "DLLP", direction="UNKNOWN", crc_validation="unrecognized"),
        ]
        summary = summarize_dllp_anomalies(events)
        self.assertEqual(summary["total_dllp_events"], 5)
        self.assertEqual(list(summary["by_direction"]), ["UNKNOWN"])
        unknown = summary["by_direction"]["UNKNOWN"]
        self.assertEqual((unknown["ack_count"], unknown["nak_count"], unknown["other_dllp_count"]),
                         (1, 1, 3))
        self.assertEqual(unknown["crc_validation_counts"],
                         {"valid_analyzer_reported": 1, "invalid": 1, "unknown": 3})
        self.assertEqual(unknown["invalid_crc_packet_indices"], [2])

    def test_samples_are_capped_while_counts_remain_exact(self):
        events = (
            dllp_event(index, ack_nak_seq_num=30 - index, crc_validation="invalid")
            for index in range(25)
        )
        upstream = summarize_dllp_anomalies(events)["by_direction"]["Upstream"]
        self.assertEqual(upstream["backward_seq_count"], 24)
        self.assertEqual(upstream["crc_validation_counts"], {"invalid": 25})
        self.assertEqual([sample["packet_index"] for sample in upstream["backward_seq_samples"]],
                         list(range(1, 21)))
        self.assertEqual(upstream["invalid_crc_packet_indices"], list(range(20)))


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

    def test_summarizes_normalized_jsonl(self):
        self.sample([
            "PCIE_EVENT|TLP|100|1|Upstream|0|10|0|11,4,0,1,1,0,1,NA",
            "PCIE_EVENT|ACK|101|1|Upstream|0|11|0|0,4095,0,0,NA,NA,NA,NA,NA",
            "PCIE_EVENT|NAK|102|1|Upstream|0|12|0|1,0,1,0,NA,NA,NA,NA,NA",
            "PCIE_EVENT|DLLP|103|1|Upstream|0|13|0|2,NA,NA,0,NA,NA,NA,NA,NA",
        ], {"TLP": 1, "ACK": 1, "NAK": 1, "DLLP": 1})
        normalize(self.acquisition, self.output)
        with (self.output / "events.jsonl").open(encoding="utf-8") as stream:
            summary = summarize_dllp_anomalies(json.loads(row) for row in stream)

        self.assertEqual(summary["total_dllp_events"], 3)
        self.assertEqual(summary["by_direction"], {
            "Upstream": {
                "ack_count": 1,
                "nak_count": 1,
                "other_dllp_count": 1,
                "crc_validation_counts": {"valid_analyzer_reported": 1, "invalid": 1, "unknown": 1},
                "missing_seq_count": 0,
                "out_of_range_seq_count": 0,
                "repeated_seq_count": 0,
                "wrap_around_count": 1,
                "backward_seq_count": 0,
                "backward_seq_samples": [],
                "invalid_crc_packet_indices": [102],
            },
        })

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
