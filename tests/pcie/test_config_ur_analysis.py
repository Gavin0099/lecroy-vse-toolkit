import copy
import json
from pathlib import Path
import unittest

from tools.pcie_config_ur_analysis import analyze


_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pcie-config-ur-1329.json"


def _event(packet, kind, tag, **fields):
    result = {
        "packet_index": packet, "kind": kind, "tag": tag, "requester_id": 0,
        "direction": "Upstream" if kind in ("Cpl", "CplD") else "Downstream",
        "time_ns": packet * 10, "time_display": f"{packet * 10} ns",
        "device_id": 0x100, "register": None, "address": None, "length_dw": None,
        "first_be": None, "last_be": None, "value": None, "payload_bytes": None,
        "byte_count": None, "lower_address": None, "status": None,
        **fields,
    }
    result["evidence"] = [{
        "kind": "RAW_FRAME_VERIFIED", "file": "checked/native.txt",
        "sha256": "a" * 64, "line": packet + 1,
        "fields": [key for key, value in result.items() if value is not None],
    }]
    return result


def _config(packet, tag, offset, **fields):
    return _event(packet, "CfgWr0", tag, register=offset,
                  **({"length_dw": 1, "first_be": 0x3, "last_be": 0,
                      "value": 0x42, "payload_bytes": 4} | fields))


def _read(packet, tag, offset, value, **fields):
    request = _event(packet, "CfgRd0", tag, register=offset,
                     **({"length_dw": 1, "first_be": 0xF, "last_be": 0} | fields))
    response = _event(packet + 1, "CplD", tag, status="SC", value=value, length_dw=1,
                      payload_bytes=4, byte_count=4, lower_address=0,
                      device_id=request["device_id"], requester_id=request["requester_id"])
    return request, response


def _memory(packet, tag, **fields):
    return _event(packet, "MRd32", tag, device_id=None,
                  **({"address": 0x1120, "length_dw": 4, "first_be": 0xF, "last_be": 0xF} | fields))


def _cpl(packet, tag, **fields):
    return _event(packet, "Cpl", tag, **({"status": "SC", "payload_bytes": 0, "length_dw": 0} | fields))


def _fragment(packet, tag, count, address, **fields):
    return _event(packet, "CplD", tag, status="SC", byte_count=count, lower_address=address,
                  **({"length_dw": 2, "payload_bytes": 8} | fields))


def _observations(*events, cuts=(), **coverage):
    return {
        "schema": "pcie.config-ur-observations/v1",
        "analysis_id": "1" * 32,
        "source_trace_sha256": "2" * 64,
        "display_trace_sha256": "3" * 64,
        "packet_namespace": "converted_trace_packet_zero_based",
        "native_packet_count": 1000,
        "coverage": {
            "stream_complete": True, "link_boundaries_complete": True,
            "full_trace_coverage": "UNKNOWN", "unsupported_frame_rows": 0, "omitted_rows": 0,
            **coverage,
        },
        "events": list(events), "link_downs": list(cuts),
    }


class ConfigUrTests(unittest.TestCase):
    def test_1329_frozen_packets_registers_readbacks_and_bursts(self):
        fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        observations, expected = fixture["observations"], fixture["expected"]
        result = analyze(observations)
        self.assertEqual(result["schema"], "pcie.config-ur-evidence/v1")
        for field in ("analysis_id", "source_trace_sha256", "display_trace_sha256",
                      "packet_namespace", "native_packet_count", "coverage"):
            self.assertEqual(result[field], observations[field])
        writes = []
        write_statuses = []
        memory = []
        header_values = {2160355: 0x42, 2160418: 0x40}
        for row in result["rows"]:
            request = row["request"]
            if request["kind"] == "CfgWr0":
                completion = row["completion"]
                readback = row["readback"]
                self.assertEqual(row["write_effect"], "NOT_ESTABLISHED")
                write_statuses.append(row["completion_status"])
                if row["register"]["identity"] != "UNKNOWN":
                    self.assertEqual(row["register"]["scope"], "same_interval" if completion else "later_interval")
                if readback:
                    self.assertEqual(readback["scope"], "same_interval" if completion else "later_interval")
                if request["packet_index"] in header_values:
                    self.assertEqual(row["register"]["write_fields"], [
                        {"name": "Capability ID", "value": header_values[request["packet_index"]]},
                        {"name": "Next Capability Pointer", "value": 0},
                    ])
                elif row["register"]["scope"] != "same_interval":
                    self.assertNotIn("write_fields", row["register"])
                writes.append([
                    request["packet_index"], request["register"], request["value"],
                    request["first_be"], request["last_be"],
                    completion["packet_index"] if completion else None, row["register"]["identity"],
                    readback["completion"]["packet_index"] if readback else None,
                ])
            if row["completion_status"] == "UR":
                self.assertEqual(row["bar"], "BAR_UNKNOWN")
                self.assertIsNone(row["write_effect"])
                memory.append([request["packet_index"], row["completion"]["packet_index"]])
        self.assertEqual(writes, expected["writes"])
        self.assertEqual(write_statuses, expected["write_statuses"])
        self.assertEqual(memory, expected["ur_pairs"])
        self.assertEqual(result["unmatched_completions"], [])
        counts, bursts = {}, {}
        lengths = {"0x6C1FC014": 4, "0x6C1FC01C": 4, "0x6C1FC028": 8}
        for group in result["ur_groups"]:
            address = f"0x{group['address']:08X}"
            counts[address] = group["count"]
            bursts[address] = [burst["count"] for burst in group["bursts"]]
            self.assertEqual(group["byte_length"], lengths[address])
            self.assertEqual(group["row_ids"], [row_id for burst in group["bursts"] for row_id in burst["row_ids"]])
            self.assertTrue(all(burst["start_ns"] <= burst["end_ns"] for burst in group["bursts"]))
        self.assertEqual(counts, expected["ur_counts"])
        self.assertEqual(bursts, expected["ur_bursts"])

    def test_tag_collision_cannot_overwrite_memory_with_config_or_clear_pending(self):
        result = analyze(_observations(
            _memory(1, 1), _config(2, 1, 0x80), _cpl(3, 1, status="UR"),
            _config(4, 1, 0x80), _cpl(5, 1), _config(7, 1, 0x80), _cpl(8, 1), cuts=[6],
        ))
        self.assertEqual([row["completion_status"] for row in result["rows"]], ["AMBIGUOUS", "AMBIGUOUS", "SC"])
        self.assertEqual([reply["packet_index"] for reply in result["unmatched_completions"]], [3])
        self.assertEqual(result["rows"][-1]["completion"]["packet_index"], 8)

    def test_completer_requester_direction_and_anchored_link_down(self):
        result = analyze(_observations(
            _config(1, 0, 0x80),
            _cpl(2, 0, status="UR", device_id=0x101),
            _cpl(3, 0, status="CA", requester_id=1),
            _cpl(4, 0, status="UR", direction="Downstream"),
            _cpl(6, 0, status="CA"), _config(7, 0, 0x80), _cpl(8, 0, status="CA"),
            cuts=[5],
        ))
        before, after = result["rows"]
        self.assertEqual(before["completion_status"], "NO_COMPLETION_OBSERVED_BEFORE_LINK_DOWN")
        self.assertEqual(after["completion_status"], "CA")
        self.assertEqual(after["completion"]["packet_index"], 8)
        self.assertEqual([event["packet_index"] for event in result["unmatched_completions"]], [2, 3, 4, 6])

    def test_memory_error_has_no_success_payload_requirement(self):
        result = analyze(_observations(
            _memory(1, 1), _cpl(2, 1, status="UR", byte_count=1, lower_address=0x7F),
            _memory(3, 1), _cpl(4, 1, status="CA"),
            _memory(5, 1), _cpl(6, 1, status="CRS"),
        ))
        self.assertEqual([(row["id"], row["completion_status"]) for row in result["rows"]], [("p1", "UR"), ("p3", "CA")])
        self.assertEqual([event["packet_index"] for event in result["unmatched_completions"]], [6])
        self.assertEqual(result["ur_groups"][0]["row_ids"], ["p1"])

    def test_only_verified_success_fragments_retire_memory_tag(self):
        for second, status in (
            (_fragment(3, 4, 8, 0), "SC"),
            (_fragment(3, 4, 16, 0x78), "AMBIGUOUS"),
            (_fragment(3, 4, 8, 0x04), "AMBIGUOUS"),
            (_fragment(3, 4, 8, 0, length_dw=3), "AMBIGUOUS"),
            (_fragment(3, 4, 8, 0, device_id=0x101), "AMBIGUOUS"),
            (None, "AMBIGUOUS"),
        ):
            with self.subTest(fragment=second):
                events = [_memory(1, 4, address=0x1178), _fragment(2, 4, 16, 0x78)]
                if second:
                    events.append(second)
                result = analyze(_observations(*events, _config(4, 4, 0x80), _cpl(5, 4)))
                self.assertEqual(result["rows"][0]["completion_status"], status)

    def test_successful_split_cannot_retire_tag_with_impossible_boundary(self):
        result = analyze(_observations(
            _memory(1, 4), _fragment(2, 4, 16, 0x20), _fragment(3, 4, 8, 0x28),
            _config(4, 4, 0x80), _cpl(5, 4),
        ))
        self.assertEqual(result["rows"][0]["completion_status"], "AMBIGUOUS")

    def test_partial_memory_enables_preserve_ur_range_but_do_not_verify_success_split(self):
        result = analyze(_observations(
            _memory(1, 0, length_dw=1, first_be=0x6, last_be=0), _cpl(2, 0, status="UR"),
            _memory(3, 0, length_dw=1, first_be=0x5, last_be=0), _cpl(4, 0, status="UR"),
            _memory(5, 0, first_be=0xE), _fragment(6, 0, 15, 0x21, payload_bytes=7),
            _config(7, 0, 0x80), _cpl(8, 0),
        ))
        self.assertEqual([row["completion_status"] for row in result["rows"]], ["UR", "UR", "AMBIGUOUS"])
        self.assertEqual([(group["address"], group["byte_length"], group["count"])
                          for group in result["ur_groups"]], [(0x1121, 2, 1)])

    def test_incomplete_stream_boundaries_or_unknown_tag_cannot_prove_absence_or_pair(self):
        request = _config(1, 1, 0x80)
        error = _cpl(2, 1, status="UR")
        cases = (
            _observations(request, error, stream_complete=False),
            _observations(request, error, link_boundaries_complete=False),
            _observations(request, error, omitted_rows=2),
            _observations(request, _event(2, "OtherNonPosted", None), _cpl(3, 1, status="UR")),
        )
        for observation in cases:
            with self.subTest(coverage=observation["coverage"]):
                result = analyze(observation)
                self.assertEqual(result["rows"][0]["completion_status"], "DATA_GAP")
                self.assertIsNone(result["rows"][0]["completion"])
                self.assertEqual(len(result["unmatched_completions"]), 1)

    def test_metadata_does_not_establish_a_write_value_or_completion_status(self):
        request = _config(1, 0, 0x80)
        completion = _cpl(2, 0)
        request["evidence"][0]["kind"] = completion["evidence"][0]["kind"] = "METADATA_ONLY"
        result = analyze(_observations(request, completion))
        row = result["rows"][0]
        self.assertIsNone(row["request"]["value"])
        self.assertIsNone(row["request"]["register"])
        self.assertIsNone(row["request"]["time_ns"])
        self.assertEqual(row["completion_status"], "DATA_GAP")
        self.assertIsNone(result["unmatched_completions"][0]["status"])
        self.assertEqual(request["value"], 0x42)

    def test_link_control_requires_capability_pointer_and_observed_capability_id(self):
        for pointer, header, device, expected in (
            (0x80, 0x0002E010, 0x100, "PCI_EXP_LINK_CONTROL"),
            (0x80, 0x0092E010, 0x100, "UNKNOWN"),
            (0x81, 0x0002E010, 0x100, "UNKNOWN"),
            (0x80, 0x0002E001, 0x100, "UNKNOWN"),
            (0x80, 0x0002E010, 0x101, "UNKNOWN"),
        ):
            result = analyze(_observations(
                *_read(1, 0, 0x34, pointer), *_read(3, 0, 0x80, header, device_id=device),
                _config(5, 0, 0x90), _cpl(6, 0), _config(8, 0, 0x90), _cpl(9, 0), cuts=[7],
            ))
            earlier, later = result["rows"][-2:]
            self.assertEqual(earlier["register"]["identity"], expected)
            self.assertEqual(earlier["write_effect"], "NOT_ESTABLISHED")
            self.assertEqual(later["register"]["identity"], "UNKNOWN")
            if expected == "PCI_EXP_LINK_CONTROL":
                self.assertEqual(earlier["register"]["evidence_packets"], [1, 2, 3, 4])
                self.assertEqual(earlier["register"]["write_fields"], [
                    {"name": "ASPM Control", "value": 2},
                    {"name": "Common Clock Configuration", "value": 1},
                ])
            else:
                self.assertNotIn("write_fields", earlier["register"])

    def test_written_fields_require_all_bytes_and_verified_payload(self):
        result = analyze(_observations(
            *_read(1, 0, 0x100, 0x0001001E),
            _config(3, 0, 0x100, first_be=0x5, value=0xFFFFFFFF), _cpl(4, 0),
            _config(5, 0, 0x100, first_be=0xF, payload_bytes=None), _cpl(6, 0),
        ))
        partial, unverified = result["rows"][-2:]
        self.assertEqual(partial["register"]["identity"], "L1SS_EXT_CAP_HEADER")
        self.assertEqual(partial["register"]["write_fields"], [{"name": "Capability Version", "value": 15}])
        self.assertNotIn("write_fields", unverified["register"])

    def test_later_bdf_reuse_cannot_classify_an_earlier_write_field(self):
        result = analyze(_observations(
            _config(1, 0, 0x90), _cpl(2, 0),
            *_read(4, 0, 0x34, 0x80), *_read(6, 0, 0x80, 0x0002E010), cuts=[3],
        ))
        earlier = result["rows"][0]["register"]
        self.assertEqual(earlier, dict(identity="PCI_EXP_LINK_CONTROL", scope="later_interval",
                                       evidence_packets=[4, 5, 6, 7]))

    def test_readback_requires_success_and_covered_byte_enables(self):
        result = analyze(_observations(
            _config(1, 0, 0x80), *_read(2, 1, 0x80, 0x1), _cpl(4, 0),
            *_read(5, 1, 0x80, 0x2, first_be=0x1),
            *_read(7, 1, 0x80, 0x3, device_id=0x101), *_read(9, 1, 0x80, 0x4),
        ))
        readback = result["rows"][0]["readback"]
        self.assertEqual(readback["request"]["packet_index"], 9)
        self.assertEqual(readback["completion"]["value"], 0x4)
        self.assertEqual(readback["scope"], "same_interval")

    def test_unknown_time_and_link_down_split_repeated_ur_bursts(self):
        result = analyze(_observations(
            _memory(1, 1), _cpl(2, 1, status="UR"),
            _memory(3, 1, time_ns=None), _cpl(4, 1, status="UR"),
            _memory(5, 1), _cpl(6, 1, status="UR"),
            _memory(8, 1), _cpl(9, 1, status="UR"), cuts=[7],
        ))
        self.assertEqual([(part["start_ns"], part["row_ids"]) for part in result["ur_groups"][0]["bursts"]],
                         [(10, ["p1"]), (None, ["p3"]), (50, ["p5"]), (80, ["p8"])])

    def test_malformed_bindings_and_packet_order_rejected(self):
        seed = _observations(_config(1, 0, 0x80), _cpl(3, 0), cuts=[2])
        for label, mutate in (
            ("schema", lambda o: o.update(schema="wrong")),
            ("source_trace_sha256", lambda o: o.update(source_trace_sha256="f" * 63)),
            ("packet_namespace", lambda o: o.update(packet_namespace="source")),
            ("ordered event packets", lambda o: o["events"].reverse()),
            ("link_downs overlap", lambda o: o["link_downs"].append(3)),
            ("packet_index", lambda o: o["events"][0].update(packet_index=1000)),
            ("reference file", lambda o: o["events"][0]["evidence"][0].update(file="../trace.txt")),
            ("requester_id", lambda o: o["events"][0].update(requester_id=True)),
        ):
            with self.subTest(label=label):
                broken = copy.deepcopy(seed)
                mutate(broken)
                with self.assertRaisesRegex(ValueError, label):
                    analyze(broken)


if __name__ == "__main__":
    unittest.main()
