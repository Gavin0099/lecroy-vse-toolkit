import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/pcie'))
import b2d_observed_state as b2d
import b2h2_sidecar as sc
import catc_regdef as rd

EV = ROOT / 'artifacts/evidence'
SNAP = EV / 'pcie-b2h1-cfgspace-20261005/run1/config-space.json'
BOUNDARY = EV / 'pcie-b2h1-cfgspace-20261005/run2-boundary/config-space.json'
LOG = EV / 'pcie-b2b-hang-20260930/r2-run1/accesses.json'
LINKCTL = ROOT / 'docs/pcie-register-defs/linkcontrol-aspm.regdef.json'
SHA = 'AA' * 32


def space(dwords):
    data, mask = [0] * 1024, [0] * 1024
    for off, (v, m) in dwords.items():
        data[off // 4], mask[off // 4] = v, m
    return {'GetData': [data, mask], 'entries': []}


def run(spaces, bdf=256, sha=SHA):
    return {'bdf': bdf, 'pre': [{'path': 'x.pex', 'sha256': sha}], 'packets': {str(p): s for p, s in spaces.items()},
            'identities_unchanged': True, 'process_exit_ok': True}


def mini_log(accesses=(), sha=SHA, disconnect=1000):
    return {'schema': 'pcie.b2b-config-access/v1', 'trace': {'sha256': sha},
            'anchors': {'disconnect_packet': disconnect, 'reconnect_packet': 2000}, 'accesses': list(accesses)}


def synth_regdef():
    r = json.loads(LINKCTL.read_text(encoding='utf-8'))
    r['name'] = 'synthetic'
    r['registers'] = [
        {'name': 'RegA', 'offset': '0x940', 'width_bits': 16, 'fields': [
            {'name': 'Lo', 'lsb': 0, 'width': 4, 'values': {'2': 'two', '3': 'three'}},
            {'name': 'Span', 'lsb': 4, 'width': 8, 'values': {}},
            {'name': 'Hi', 'lsb': 12, 'width': 4, 'values': {'5': 'five'}}]},
        {'name': 'RegB', 'offset': '0x942', 'width_bits': 16, 'fields': [{'name': 'Y', 'lsb': 0, 'width': 4, 'values': {'9': 'nine'}}]}]
    return rd.validate(r)


def decoded(reg, offset, value, known):
    return {(r['register'], f['field']): f for r in rd.decode_known(reg, offset, value, known) for f in r['fields']}


class NormalizeTests(unittest.TestCase):
    def test_validates_shape_and_forces_unknown_bits_to_zero(self):
        n = sc.normalize_snapshot(space({0x90: (0xDEAD0042, 0x0000FFFF)}))
        self.assertEqual(n['value'][0x90 // 4], 0x42)
        self.assertEqual(n['known_bytes'], 2)
        for bad in ({}, {'GetData': [[0] * 3, [0] * 3]}, {'GetData': [[-1] + [0] * 1023, [0] * 1024]},
                    {'GetData': [['x'] + [0] * 1023, [0] * 1024]}):
            with self.assertRaises(ValueError):
                sc.normalize_snapshot(bad)

    def test_partial_bit_masks_are_recorded_not_hidden(self):
        n = sc.normalize_snapshot(space({0x90: (3, 3)}))
        self.assertEqual(n['partial_byte_offsets'], [0x90])
        self.assertEqual(n['known_bytes'], 0)


class UnknownAndLayoutTests(unittest.TestCase):
    def test_unknown_high_byte_does_not_block_low_byte_field_nor_depend_on_filler(self):
        reg = synth_regdef()
        results = []
        for filler in (0x0000, 0xFF00, 0xA500):
            n = sc.normalize_snapshot(space({0x940: (0x0002 | filler, 0x000000FF)}))   # filler sits in unknown bits
            f = decoded(reg, 0x940, n['value'][0x940 // 4], n['known'][0x940 // 4])
            results.append({k: (v['value'], v['status']) for k, v in f.items()})
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[0][('RegA', 'Lo')], (2, 'DECODED'))
        self.assertEqual(results[0][('RegA', 'Span')], (None, 'UNKNOWN_BITS_NOT_KNOWN'))   # bits 4..11 need byte 1
        self.assertEqual(results[0][('RegA', 'Hi')], (None, 'UNKNOWN_BITS_NOT_KNOWN'))

    def test_cross_byte_field_and_two_registers_in_one_dword_do_not_pollute(self):
        reg = synth_regdef()
        # RegA = 0x5AB2: Lo=2, Span=0xAB (bits 4..11 cross a byte boundary), Hi=5; RegB = 0x0009 at 0x942
        out = {k: v['value'] for k, v in decoded(reg, 0x940, 0x0009_5AB2, 0xFFFFFFFF).items()}
        self.assertEqual(out, {('RegA', 'Lo'): 2, ('RegA', 'Span'): 0xAB, ('RegA', 'Hi'): 5, ('RegB', 'Y'): 9})
        out = {k: v['status'] for k, v in decoded(reg, 0x940, 0x0009_0000, 0xFFFF0000).items()}   # only RegB bytes known
        self.assertEqual(out[('RegB', 'Y')], 'DECODED')
        self.assertTrue(all(v == 'UNKNOWN_BITS_NOT_KNOWN' for k, v in out.items() if k[0] == 'RegA'))


@unittest.skipUnless(SNAP.exists() and LOG.exists(), 'local trace evidence unavailable')
class SavedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.run = json.loads(SNAP.read_text(encoding='utf-8'))
        self.log = json.loads(LOG.read_text(encoding='utf-8'))
        self.reg = rd.load(LINKCTL)

    def doc(self, packet, run=None, log=None, reg=None):
        return sc.build(run or self.run, log or self.log, reg or self.reg, packet, 256)

    def test_five_saved_positions_reproduce_recorded_link_control(self):
        # expected ASPM values come from the engineer-question record: writes 0x42, 0x40, 0x42 and none before 8658
        expected = {3300: None, 8650: None, 8662: 2, 9920: 0, 10360: 2}
        for packet, aspm in expected.items():
            row = self.doc(packet)['rows'][0]
            self.assertEqual(row['catc_merged']['value'], aspm, packet)
            self.assertEqual(row['last_write_intent']['value'], aspm, packet)
            self.assertIsNone(row['last_read_back']['value'])   # 0x90 was never read in this epoch
            self.assertIn(row['native_comparison'], ('MATCH', 'NOT_COMPARABLE_UNKNOWN'))

    def test_binding_and_evidence_packets(self):
        d = self.doc(10360)
        self.assertEqual(d['binding']['trace']['sha256'], self.log['trace']['sha256'])
        self.assertEqual((d['binding']['bdf'], d['binding']['epoch'], d['binding']['snapshot_position_packet']),
                         (256, 'before_disconnect', 10360))
        self.assertEqual(d['rows'][0]['last_write_intent']['evidence_request_packets'], [10354])
        self.assertIn('not the packet of the last update', d['snapshot_position_note'])

    def test_inputs_are_not_mutated(self):
        run, log = copy.deepcopy(self.run), copy.deepcopy(self.log)
        self.doc(10360)
        self.assertEqual(run, self.run)
        self.assertEqual(log, self.log)

    def test_wrong_native_value_field_position_known_mask_and_value_are_caught(self):
        run = copy.deepcopy(self.run)
        for e in run['packets']['10360']['entries']:
            for r in e.get('registers', []):
                if r.get('GetName') == 'Link Control':
                    r['fields'][0]['GetFieldValue'] = [3, 3]
        d = self.doc(10360, run=run)
        self.assertEqual(d['rows'][0]['native_comparison'], 'DIFFERS')
        self.assertEqual(len(d['differences']), 1)
        bad = copy.deepcopy(self.reg)
        bad['registers'][0]['fields'][0]['lsb'] = 4
        self.assertNotEqual(self.doc(10360, reg=bad)['rows'][0]['native_comparison'], 'MATCH')
        run = copy.deepcopy(self.run)
        run['packets']['10360']['GetData'][1][0x90 // 4] = 0
        row = self.doc(10360, run=run)['rows'][0]
        self.assertEqual((row['catc_merged']['value'], row['catc_merged']['status']), (None, 'UNKNOWN_BITS_NOT_KNOWN'))
        self.assertEqual(row['last_write_intent']['value'], 2)   # independent view unaffected
        run = copy.deepcopy(self.run)
        run['packets']['10360']['GetData'][0][0x90 // 4] = 0x43
        row = self.doc(10360, run=run)['rows'][0]
        self.assertEqual(row['catc_merged']['value'], 3)
        self.assertEqual(row['last_write_intent']['value'], 2)

    def test_out_of_scope_is_refused_not_decoded(self):
        run = copy.deepcopy(self.run)
        run['packets']['300000'] = run['packets']['10360']
        with self.assertRaisesRegex(sc.OutOfScope, 'epoch'):
            self.doc(300000, run=run)
        with self.assertRaisesRegex(sc.OutOfScope, 'device'):
            sc.build(self.run, self.log, self.reg, 10360, 257)
        bad = copy.deepcopy(self.run)
        bad['pre'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(sc.OutOfScope, 'SHA-256'):
            self.doc(10360, run=bad)
        with self.assertRaisesRegex(ValueError, 'no query'):
            self.doc(10361)

    def test_cli_exit_codes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'o'
            args = ['--snapshot', str(SNAP), '--log', str(LOG), '--regdef', str(LINKCTL), '--device-id', '256',
                    '--packet', '10360', '--output-dir', str(out)]
            self.assertEqual(sc.main(args), 0)
            self.assertTrue((out / 'sidecar.json').exists() and (out / 'sidecar.md').exists())
            self.assertEqual(sc.main(args), 2)   # existing output is never overwritten
            args[args.index('10360')] = '300000'
            args[-1] = str(Path(t) / 'o2')
            self.assertEqual(sc.main(args), 4)   # out of scope epoch, distinct exit code
            self.assertFalse((Path(t) / 'o2').exists())


@unittest.skipUnless(BOUNDARY.exists() and LOG.exists(), 'local trace evidence unavailable')
class PacketBoundaryTests(unittest.TestCase):
    """Saved ordered COM queries show when CATC includes a value; B2b has to make the same call."""

    def setUp(self):
        self.q = json.loads(BOUNDARY.read_text(encoding='utf-8'))['queries']
        self.log = json.loads(LOG.read_text(encoding='utf-8'))

    def known(self, query, offset):
        mask = query['result']['GetData'][1][offset // 4]
        return mask == 0xFFFFFFFF if offset == 0x80 else mask & 0xFFFF == 0xFFFF

    def at(self, packet):
        return next(x for x in self.q if x['packet'] == packet)

    def test_write_included_at_request_packet_read_at_completion_packet(self):
        self.assertFalse(self.known(self.at(8657), 0x90))   # write request 8658, completion 8660
        self.assertTrue(self.known(self.at(8658), 0x90))
        self.assertFalse(self.known(self.at(3245), 0x80))   # read request 3246, completion 3250
        self.assertFalse(self.known(self.at(3249), 0x80))
        self.assertTrue(self.known(self.at(3250), 0x80))

    def test_b2b_makes_the_same_inclusion_call_on_every_boundary_query(self):
        for x in self.q:
            state = b2d.build(self.log, 256, x['packet'])
            self.assertEqual(self.known(x, 0x90), '144' in state['write_intent_bytes'], x['packet'])
            self.assertEqual(self.known(x, 0x80), '128' in state['read_bytes'], x['packet'])

    def test_query_order_does_not_change_results(self):
        by_packet = {}
        for x in self.q:
            by_packet.setdefault(x['packet'], []).append(x['result']['GetData'])
        repeated = {p: v for p, v in by_packet.items() if len(v) > 1}
        self.assertEqual(sorted(repeated), [8657, 10360])   # queried twice, in different orders
        for p, v in repeated.items():
            self.assertTrue(all(g == v[0] for g in v), p)


class SyntheticEndToEndTests(unittest.TestCase):
    def test_read_and_write_views_stay_apart(self):
        reg = synth_regdef()
        common = {'device_id': 256, 'epoch': 'before_disconnect', 'register_byte_offset': 0x940, 'last_be': 0, 'requester_id': 0}
        log = mini_log([
            {**common, 'access_id': 'r', 'packet_index': 10, 'type': 'CfgRd0', 'first_be': 3, 'write_value': None,
             'read_value': 0x5AB2, 'completions': [{'packet_index': 12}], 'tag': 1},
            {**common, 'access_id': 'w', 'packet_index': 20, 'type': 'CfgWr0', 'first_be': 1, 'write_value': 0x03,
             'read_value': None, 'completions': [], 'tag': 2}])
        # CATC merged: read 0x5AB2 then a byte-0 write of 0x03 gives 0x5AB3 known in bits 0..15
        d = sc.build(run({25: space({0x940: (0x5AB3, 0xFFFF)})}), log, reg, 25, 256)
        by = {(r['register'], r['field']): r for r in d['rows']}
        self.assertEqual(by[('RegA', 'Lo')]['catc_merged']['value'], 3)
        self.assertEqual(by[('RegA', 'Lo')]['last_write_intent']['value'], 3)
        self.assertEqual(by[('RegA', 'Lo')]['last_read_back']['value'], 2)   # read-back kept apart
        self.assertEqual(by[('RegA', 'Span')]['last_write_intent']['status'], 'UNKNOWN_BITS_NOT_KNOWN')   # one byte written only
        self.assertEqual(by[('RegA', 'Span')]['catc_merged']['value'], 0xAB)
        self.assertEqual(by[('RegB', 'Y')]['catc_merged']['status'], 'UNKNOWN_BITS_NOT_KNOWN')
        self.assertTrue(all(r['native_comparison'] == 'NATIVE_NOT_AVAILABLE' for r in d['rows']))   # no entries saved


if __name__ == '__main__':
    unittest.main()
