import hashlib
import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))

import b1c_training_timeline as b1c

ZERO_PKT = {k: 0 for k in b1c.PKT_COUNTS}
ZERO_ERR = {k: 0 for k in b1c.ERR_SUBFLAGS}


def seg(n, first, last, first_time, last_time, events, err_any=0, **counts):
    return {"kind": "segment", "packet_index": first, "time_display": first_time, "seg": n, "first_index": first,
            "first_time": first_time, "last_index": last, "last_time": last_time, "events": events,
            **ZERO_PKT, **ZERO_ERR, "err_any": err_any, **counts}


def ltssm(index, time, channel, state_name, valid=1):
    return {"kind": "ltssm", "packet_index": index, "time_display": time, "channel": channel, "event": 5, "state": 0,
            "substate": 0, "subsubstate": 0, "valid": valid, "event_name": "ORDERED_SET", "state_name": state_name}


def linkcond(index, time, channel, name):
    return {"kind": "link_condition", "packet_index": index, "time_display": time, "channel": channel, "type": 1, "type_name": name}


def timeline():
    return [
        seg(1, 100, 105, "9.512 sec", "9.512 sec", 6, tlp=1, dllp_nak=1),
        linkcond(100, "9.512 sec", "Upstream", "LINK_DOWN"),
        ltssm(100, "9.512 sec", "Upstream", "DETECT", valid=0),
        {"kind": "nak", "packet_index": 101, "time_display": "9.512 sec", "channel": "Downstream", "seq": 1682},
        {"kind": "tlp", "packet_index": 102, "time_display": "9.512 sec", "channel": "Downstream", "tlp_type": 9},
        seg(2, 106, 200, "9.512 sec", "9.538 sec", 95, os_ts1=90, os_eieos=5),
        ltssm(106, "9.512 sec", "Downstream", "RECOVERY.RECOVERY_RCVRLOCK"),
        seg(3, 201, 201, "9.538 sec", "9.538 sec", 1),
        linkcond(201, "9.538 sec", "Downstream", "LINK_DOWN"),
        ltssm(201, "9.538 sec", "Downstream", "RECOVERY.RECOVERY_RCVRSPD"),
        seg(4, 202, 202, "9.538 sec", "9.538 sec", 1),
        linkcond(202, "9.538 sec", "Downstream", "LINK_UP"),
        seg(5, 203, 203, "9.541 sec", "9.541 sec", 1),
        linkcond(203, "9.541 sec", "Downstream", "LINK_DOWN"),
        seg(6, 204, 400, "9.575 sec", "9.600 sec", 197, err_any=197, os_ts1=197),
        ltssm(204, "9.575 sec", "Downstream", "POLLING", valid=0),
        seg(7, 401, 450, "10.912 sec", "10.912 sec", 50, os_ts1=30, os_ts2=20),
        linkcond(401, "10.912 sec", "Upstream", "LINK_UP"),
        seg(8, 451, 460, "10.912 sec", "10.912 sec", 10, os_ts1=10),
        ltssm(451, "10.912 sec", "Downstream", "CONFIG.CFG_LINKWIDTH_STRT"),
        seg(9, 461, 470, "10.912 sec", "10.912 sec", 10, os_ts2=10),
        ltssm(461, "10.912 sec", "Upstream", "CONFIG.CFG_COMPLETE"),
        seg(10, 471, 480, "10.912 sec", "10.912 sec", 10, dllp_fc=10),
        ltssm(471, "10.912 sec", "Downstream", "L0"),
        {"kind": "speed_width", "packet_index": 475, "time_display": "10.912 sec", "channel": "Downstream", "event": 2, "speed": 0, "width": 1},
    ]


class B1cTests(unittest.TestCase):
    def test_phases_merge_same_state_and_link_conditions_and_show_gap(self):
        phases = b1c.build(timeline(), Decimal("0.1"))
        self.assertEqual([p["kind"] for p in phases],
                         ["DETECT", "RECOVERY", "LINK_CONDITION", "POLLING", "NO_OBSERVED_EVENTS", "LINK_CONDITION", "CONFIG", "L0"])
        recovery = phases[1]
        self.assertEqual([s["substate"] for s in recovery["steps"] if s["kind"] == "ltssm"], ["RCVRLOCK", "RCVRSPD"])
        self.assertEqual(recovery["events"], 96)
        self.assertEqual(len(phases[2]["steps"]), 2)
        self.assertEqual(phases[4]["duration_seconds"], "1.312")
        self.assertEqual((phases[4]["after_index"], phases[4]["before_index"]), (400, 401))
        self.assertEqual(phases[3]["error_subtype"], "UNKNOWN")
        self.assertEqual(phases[6]["channels"], ["Downstream", "Upstream"])

    def test_markdown_keeps_unknowns_and_passes_contract(self):
        phases = b1c.build(timeline(), Decimal("0.1"))
        md = b1c.render_markdown(phases, {"timeline_sha256": "A" * 64, "window": {"start": 100, "end": 480}, "gap_seconds": "0.1"})
        self.assertEqual(b1c.contract_check(md, phases), [])
        self.assertIn("error subtype：`UNKNOWN`", md)
        self.assertIn("沒有觀察到事件（1.312 sec）", md)
        for unknown in b1c.UNKNOWNS:
            self.assertIn(unknown, md)

    def test_contract_rejects_judgement_wording_and_hidden_unknown(self):
        phases = b1c.build(timeline(), Decimal("0.1"))
        md = b1c.render_markdown(phases, {"timeline_sha256": "A" * 64, "window": {"start": 100, "end": 480}, "gap_seconds": "0.1"})
        self.assertTrue(any("judgement" in e for e in b1c.contract_check(md + "\n這段 link training 異常。\n", phases)))
        self.assertTrue(any("judgement" in e for e in b1c.contract_check(md + "\nMUX switch\n", phases)))
        self.assertTrue(any("UNKNOWN" in e for e in b1c.contract_check(md.replace("error subtype：`UNKNOWN`", "error subtype：TS parity"), phases)))

    def test_rejects_record_outside_its_segment(self):
        broken = timeline()
        broken.insert(1, {"kind": "nak", "packet_index": 999, "time_display": "9.6 sec", "channel": "Downstream", "seq": 1})
        with self.assertRaisesRegex(b1c.B1cError, "outside segment"):
            b1c.build(broken, Decimal("0.1"))

    def test_cli_requires_matching_pass_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = json.dumps(timeline()).encode("utf-8")
            (root / "timeline.json").write_bytes(raw)
            good = {"status": "PASS_WINDOW_EXPORT", "timeline_json_sha256": hashlib.sha256(raw).hexdigest().upper(),
                    "named_with_constants": True, "window": {"start": 100, "end": 480}}
            (root / "summary.json").write_text(json.dumps({**good, "timeline_json_sha256": "B" * 64}), encoding="utf-8")
            args = ["--timeline", str(root / "timeline.json"), "--summary", str(root / "summary.json"), "--output-dir", str(root / "out")]
            self.assertEqual(b1c.main(args), 2)
            (root / "summary.json").write_text(json.dumps(good), encoding="utf-8")
            self.assertEqual(b1c.main(args), 0)
            self.assertTrue((root / "out" / "training.md").is_file() and (root / "out" / "training.json").is_file())
            self.assertEqual(b1c.main(args), 2)


def r1_timeline():
    rows = timeline()
    for row in rows:
        if row["kind"] == "segment" and row["seg"] == 7:
            row["err_any"] = 20
    return rows


X2 = {
    "header": {"start": 100, "end": 480, "r1_end": 203, "r2_end": 400, "cap": 10},
    "scopes": {"R1": {"has_errors": 0}, "R2": {"has_errors": 197}, "R3": {"has_errors": 20}},
    "cells": {"R1C1": {"events": 1, "ts1": 0, "has_errors": 0}, "R1C2": {"events": 102, "ts1": 90, "has_errors": 0}, "R1C3": {"events": 0, "ts1": 0, "has_errors": 0},
              "R2C1": {"events": 0, "ts1": 0, "has_errors": 0}, "R2C2": {"events": 197, "ts1": 197, "has_errors": 197}, "R2C3": {"events": 0, "ts1": 0, "has_errors": 0},
              "R3C1": {"events": 40, "ts1": 20, "has_errors": 0}, "R3C2": {"events": 40, "ts1": 30, "has_errors": 20}, "R3C3": {"events": 0, "ts1": 0, "has_errors": 0}},
    "channel_names": {"C2": "Downstream"},
}
GUI = {"link_events": [{"packet_index": 100, "gui_text": "Link Down", "vse_constant": "LINK_DOWN"}],
       "ts1_error_samples": [{"packet_index": 410, "direction_arrow": "R→", "speed": "2.5", "width": "x1", "gui_error_labels": ["TSRsrvErr"]}]}


def r1_meta():
    return {"timeline_sha256": "A" * 64, "window": {"start": 100, "end": 480}, "gap_seconds": "0.1", "r1": True, "x2_sha256": "B" * 64,
            "gui_sha256": "C" * 64, "link_events": GUI["link_events"], "ranges": b1c.channel_ranges(X2), "cells": X2["cells"],
            "channel_labels": {cid: b1c.channel_label(X2, cid) for cid in (1, 2, 3)}}


class B1cR1Tests(unittest.TestCase):
    def test_channel_cells_must_match_scope_before_attribution(self):
        for count in (196, 198, -197):
            bad = copy.deepcopy(X2)
            bad['cells']['R2C2']['has_errors'] = count
            with self.subTest(count=count), self.assertRaises(b1c.B1cError):
                b1c.build(r1_timeline(), Decimal('0.1'), bad, GUI)

    def test_straddled_phase_still_validates_channel_totals(self):
        bad = copy.deepcopy(X2)
        bad['header']['r1_end'] = 300
        for name in ('R1C2', 'R2C2'):
            broken = copy.deepcopy(bad)
            broken['cells'][name]['has_errors'] = -1
            with self.subTest(name=name), self.assertRaises(b1c.B1cError):
                b1c.build(r1_timeline(), Decimal('0.1'), broken, GUI)

    def test_gui_link_claim_requires_matching_timeline_packet_and_text(self):
        for update in ({'vse_constant': 'LINK_UP', 'gui_text': 'Link Up'},
                       {'packet_index': 999}, {'gui_text': 'Link Up'}):
            bad = copy.deepcopy(GUI)
            bad['link_events'][0].update(update)
            with self.subTest(update=update), self.assertRaises(b1c.B1cError):
                b1c.build(r1_timeline(), Decimal('0.1'), X2, bad)

    def test_carried_state_channel_and_sample_after_gap(self):
        phases = b1c.build(r1_timeline(), Decimal("0.1"), X2, GUI)
        after_gap = phases[5]
        self.assertEqual(after_gap["kind"], "LINK_CONDITION")
        self.assertEqual(after_gap["channels"], ["Upstream"])
        self.assertEqual(after_gap["ltssm_at_start"]["Downstream"]["state"], "POLLING")
        self.assertEqual(after_gap["ltssm_at_start"]["Upstream"]["state"], "DETECT")
        self.assertEqual(after_gap["has_errors_channel"]["channel"], "Downstream")
        self.assertEqual(after_gap["error_subtype"], "UNKNOWN")
        self.assertEqual([s["packet_index"] for s in after_gap["gui_samples"]], [410])
        self.assertIn("link condition ×1（起點 Upstream；HasErrors 在 Downstream，Downstream 仍為 Polling）", b1c.flow_line(phases, True))

    def test_r1_markdown_passes_contract_and_marks_samples(self):
        phases = b1c.build(r1_timeline(), Decimal("0.1"), X2, GUI)
        md = b1c.render_markdown(phases, r1_meta())
        self.assertEqual(b1c.contract_check(md, phases, True), [])
        self.assertIn("僅代表此 sample", md)
        self.assertIn("依據 B1c-x2 R3", md)
        self.assertIn("Link Event「Link Down」", md)
        for unknown in b1c.UNKNOWNS_R1:
            self.assertIn(unknown, md)

    def test_r1_contract_rejects_unmarked_label_and_missing_basis(self):
        phases = b1c.build(r1_timeline(), Decimal("0.1"), X2, GUI)
        md = b1c.render_markdown(phases, r1_meta())
        self.assertTrue(any("sample-only" in e for e in b1c.contract_check(md + "\n空白後的 TS1 都是 `TSRsrvErr`。\n", phases, True)))
        stripped = md.replace("依據 B1c-x2 R3", "範圍 R3")
        self.assertTrue(any("without its basis" in e for e in b1c.contract_check(stripped, phases, True)))

    def test_range_sum_mismatch_and_orphan_sample_are_rejected(self):
        bad = {**X2, "scopes": {**X2["scopes"], "R3": {"has_errors": 21}}}
        with self.assertRaisesRegex(b1c.B1cError, "range total 21"):
            b1c.build(r1_timeline(), Decimal("0.1"), bad, GUI)
        orphan = {"ts1_error_samples": [{**GUI["ts1_error_samples"][0], "packet_index": 999}]}
        with self.assertRaisesRegex(b1c.B1cError, "exactly one phase"):
            b1c.build(r1_timeline(), Decimal("0.1"), X2, orphan)


if __name__ == "__main__":
    unittest.main()
