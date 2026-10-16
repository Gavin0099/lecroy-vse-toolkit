"""Behavior invariants from the owner contract and explicit USB request fixtures."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import usb_control_triage as triage

# Handwritten USB request and descriptor bytes, independent of production code.
DEVICE = "120100020000004034127856000101020301"


def wire(index=0, sec=1, ns=0, addr=5, completed=1, halted=0, error=0,
         direction=1, reqtype=0, recipient=0, request=6, value=256,
         request_index=0, length=18, payload=None):
    if payload is None:
        payload = "8006000100001200" + DEVICE
    values = [index, sec, ns, 0, 1000, 1, 0, addr, 0, completed, halted, error,
              direction, reqtype, recipient, request, value, request_index,
              length, len(bytes.fromhex(payload))]
    return "UCT|" + "|".join(map(str, values)) + "|" + payload[:128]


def raw(lines):
    return {"trace_sha256": "a" * 64, "script_sha256": "b" * 64,
            "run_result": 2, "finished_result": 2, "error": "",
            "integrity": dict(source_unchanged=True, working_copy_unchanged=True,
                              working_copy_readonly=True, script_unchanged=True),
            "summary": [len(lines), len(lines), len(lines), 0, 3], "reports": lines}


def analyze(lines):
    return triage.discover(triage.normalize(raw(lines)))


class GuidanceTests(unittest.TestCase):
    def test_native_setup_is_verified_and_excluded_from_data_length(self):
        e = triage.normalize(raw([wire()]))["events"][0]
        self.assertTrue(e["setup_bytes_match"])
        self.assertEqual(e["data_length"], 18)
        self.assertEqual(e["data_prefix_hex"], DEVICE)
        self.assertIsNone(e["packet_refs"])

    def test_prefix_truncation_keeps_actual_length_and_does_not_fill_bytes(self):
        line=wire(length=100,payload="8006000100006400"+"AA"*100)
        e=triage.normalize(raw([line]))["events"][0]
        self.assertEqual(e["data_length"],100)
        self.assertEqual(len(bytes.fromhex(e["data_prefix_hex"])),56)

    def test_class_and_vendor_transfers_remain_outside_chapter9_ranking(self):
        self.assertEqual(analyze([wire(reqtype=1,completed=0)])["candidates"],[])

    def test_unknown_native_payload_representation_stays_unknown(self):
        e = triage.normalize(raw([wire(payload="01020304")]))["events"][0]
        self.assertFalse(e["setup_bytes_match"])
        self.assertIsNone(e["data_length"])
        m = analyze([wire(completed=0, payload="01020304")])
        self.assertIn("確認有無 DATA", m["candidates"][0]["next_step"])

    def test_healthy_and_empty_do_not_make_up_a_first_candidate_or_pass(self):
        for lines in ([], [wire()]):
            m = analyze(lines)
            self.assertEqual(m["candidates"], [])
            self.assertEqual(m["status"], "no_supported_candidate")
            self.assertEqual(m["verdict"], "NOT_EVALUATED")

    def test_legitimate_header_probe_and_short_string_are_not_faults(self):
        probe = wire(length=8, payload="80060001000008001201000200000040")
        string = wire(index=1, sec=2, value=769, length=255,
                      payload="800601030000FF0004034100")
        self.assertEqual(analyze([probe, string])["candidates"], [])

    def test_isolated_unsupported_descriptor_halt_is_not_prioritized(self):
        negative = wire(value=513, halted=1, length=9, payload="8006010200000900")
        self.assertEqual(analyze([wire(), wire(index=1,sec=2,value=513,halted=1,length=9,payload="8006010200000900")])["candidates"], [])
        self.assertEqual(analyze([negative])["candidates"], [])

    def test_incomplete_no_data_has_position_reason_and_conditional_hint(self):
        m = analyze([wire(index=10, sec=35, ns=611541400, completed=0,
                          value=512, length=9, payload="8006000200000900")])
        c = m["candidates"][0]
        self.assertEqual(c["transfer_indices"], [10])
        self.assertEqual(c["start_ns"], 35_611_541_400)
        self.assertTrue(c["facts"] and c["reasons"] and c["next_step"])
        self.assertIn("確認是否被 ACK", c["next_step"])
        self.assertIn("capture", c["next_step"])
        self.assertTrue(any("觀測尾端" in g for g in c["evidence_gaps"]))
        self.assertIsNone(c["packet_refs"])

    def test_incomplete_with_data_points_at_status_not_descriptor_edit(self):
        c = analyze([wire(completed=0)])["candidates"][0]
        self.assertIn("反向 status", c["next_step"])
        self.assertNotIn("確認是否被 ACK", c["next_step"])

    def test_prior_success_then_halt_has_concrete_reference(self):
        c = analyze([wire(index=5), wire(index=8, sec=2, halted=1,
                    payload="8006000100001200")])["candidates"][0]
        self.assertIn("response_change", c["rules"])
        self.assertEqual(c["transfer_indices"], [8])
        self.assertIn("transfer 5 與 8", c["next_step"])
        self.assertTrue(any("負向" in g for g in c["evidence_gaps"]))

    def test_completed_descriptor_inconsistency_directs_content_check(self):
        c = analyze([wire(payload="8006000100001200120200020000004034127856000101020301")])["candidates"][0]
        self.assertIn("descriptor_content", c["rules"])
        self.assertIn("不把它當成傳輸未完成", c["next_step"])

    def test_declared_total_length_respects_requested_header_length(self):
        p = "090220000101008032"
        good = wire(value=512, length=9, payload="8006000200000900"+p)
        bad = wire(value=512, length=32, payload="8006000200002000"+p)
        self.assertEqual(analyze([good])["candidates"], [])
        self.assertEqual(analyze([bad])["candidates"][0]["rules"], ["descriptor_content"])

    def test_repeated_same_request_is_one_episode_starting_at_first(self):
        lines = [wire(index=i,sec=i,completed=0,payload="8006000100001200") for i in range(1,11)]
        m = analyze(lines)
        self.assertEqual(m["episode_count"], 1)
        self.assertEqual(m["candidates"][0]["transfer_indices"], list(range(1,11)))
        self.assertIn("transfer 1", m["candidates"][0]["next_step"])

    def test_success_between_bad_requests_separates_episodes(self):
        lines = [wire(index=0,completed=0),wire(index=1,sec=2),wire(index=2,sec=3,completed=0)]
        self.assertEqual(analyze(lines)["episode_count"], 2)

    def test_address_assignment_breaks_prior_response_history(self):
        assignment = wire(index=1,sec=2,addr=0,request=5,direction=0,value=5,length=0,payload="0005050000000000")
        stopped = wire(index=2,sec=3,halted=1,payload="8006000100001200")
        self.assertEqual(analyze([wire(),assignment,stopped])["candidates"], [])

    def test_large_context_gap_does_not_assume_continuity(self):
        self.assertEqual(analyze([wire(),wire(index=1,sec=20,halted=1,payload="8006000100001200")])["candidates"], [])

    def test_rank_cap_is_three_and_different_addresses_do_not_merge(self):
        m = analyze([wire(index=i,sec=i,addr=i,completed=0) for i in range(1,6)])
        self.assertEqual(len(m["candidates"]),3)
        self.assertEqual(m["episode_count"],5)
        self.assertEqual(m["omitted_episodes"],2)

    def test_labels_markers_and_known_time_cannot_change_candidates(self):
        r = raw([wire(completed=0)])
        expected = triage.discover(triage.normalize(r))
        r.update(filename="PASS_IGNORE_THIS.usb", Marker="FAIL 35.611541400", known_failure_time=123)
        r["reports"].append("<HTML>GetConfigDesc fail at 1.000000000</HTML>")
        self.assertEqual(triage.discover(triage.normalize(r)),expected)

    def test_change_observation_changes_outcome(self):
        self.assertEqual(len(analyze([wire(completed=0)])["candidates"]),1)
        self.assertEqual(analyze([wire(completed=1)])["candidates"],[])

    def test_completed_zero_data_needs_relative_delay_and_five_references(self):
        reference=[wire(index=i,sec=1,ns=i*10000) for i in range(5)]
        # One-second duration is explicit fixture input, unrelated to real fail time.
        delayed=wire(index=5,sec=2,payload="8006000100001200").split('|')
        delayed[4]='1'
        delayed='|'.join(delayed)
        c=analyze(reference+[delayed])["candidates"][0]
        self.assertIn('no_data_delay',c['rules'])
        self.assertIn('Completed=1',c['next_step'])
        self.assertEqual(analyze(reference[:4]+[delayed])["candidates"],[])
        brief=wire(index=5,sec=2,payload="8006000100001200")
        self.assertEqual(analyze(reference+[brief])["candidates"],[])

    def test_time_translation_does_not_change_candidate_identity(self):
        first=analyze([wire(index=8,completed=0)])['candidates'][0]
        shifted=analyze([wire(index=8,sec=101,completed=0)])['candidates'][0]
        self.assertEqual(first['transfer_indices'],shifted['transfer_indices'])
        self.assertEqual(first['rules'],shifted['rules'])
        self.assertEqual(shifted['start_ns']-first['start_ns'],100_000_000_000)

    def test_header_then_empty_larger_read_uses_declared_length_not_delay(self):
        # BOS five-byte header declares total length 40. No timing baseline exists.
        first=wire(index=3,value=3840,length=5,payload='8006000F00000500050F280001')
        second=wire(index=4,sec=2,value=3840,length=40,payload='8006000F00002800')
        c=analyze([first,second])['candidates'][0]
        self.assertIn('empty_descriptor_followup',c['rules'])
        self.assertIn('transfer 3',c['next_step'])
        self.assertIn('wTotalLength',c['next_step'])
        # A genuinely unsupported index with no same-index header is not promoted.
        unsupported=wire(index=4,sec=2,value=3841,length=40,payload='8006010F00002800')
        self.assertEqual(analyze([first,unsupported])['candidates'],[])


class InputAndRenderTests(unittest.TestCase):
    def test_malformed_fields_and_duplicate_missing_records_fail_closed(self):
        for mutate in (lambda r:r.update(summary=[1,2,2,0,3]),
                       lambda r:r["reports"].append(r["reports"][0]),
                       lambda r:r["reports"].clear(),
                       lambda r:r.update(finished_result=True),
                       lambda r:r["integrity"].update(source_unchanged=False),
                       lambda r:r.update(trace_sha256="x")):
            r = raw([wire()]);mutate(r)
            with self.assertRaises(triage.InputError):triage.normalize(r)
        for line in [wire(ns=1_000_000_000),wire(payload="8006000100001200")+"00",wire()+"|extra"]:
            with self.assertRaises(triage.InputError):triage.normalize(raw([line]))

    def test_html_has_required_guidance_no_external_assets_and_escaping(self):
        m = analyze([wire(completed=0)])
        m["candidates"][0]["title"]='<img src=x onerror=alert(1)>'
        s=triage.render(m)
        for text in ["發生什麼事","為什麼先看這裡","工程師下一步","Transfer ID 不等於 Packet ID","1.000000000","data-copy="]:
            self.assertIn(text,s)
        self.assertIn("&lt;img",s)
        self.assertNotIn("<img src=x",s)
        self.assertNotIn("src=\"http",s)
        self.assertNotIn("href=\"http",s)

    def test_empty_state_is_scope_limited_not_pass(self):
        s=triage.render(analyze([]))
        self.assertIn("未找到足夠可疑",s)
        self.assertIn("並不是 USB PASS",s)

    def test_file_interface_ignores_input_basename_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            a=p/'FAIL_35.611541400.json';b=p/'PASS.json'
            a.write_text(json.dumps(raw([wire(completed=0)])),encoding='utf-8')
            b.write_bytes(a.read_bytes())
            first=triage.analyze_file(a,p/'a');second=triage.analyze_file(b,p/'b')
            self.assertEqual(first,second)
            with self.assertRaises(triage.InputError):triage.analyze_file(a,p/'a')


if __name__ == '__main__':
    unittest.main()
