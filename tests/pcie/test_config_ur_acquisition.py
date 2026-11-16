from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import pcie_config_ur_acquisition as acquisition
import pcie_config_ur_analysis as association


def metadata(packet, type_code, *, tag=8, direction='Downstream', completion_status=None, row=1):
    return dict(packet_index=packet, tlp_type_hex=hex(type_code), time_display='93.664 sec',
                channel=direction, requester_id=0, tag=tag, compl_status=completion_status,
                completer_id=256 if completion_status is not None else None, row=row)


class ConfigUrAcquisitionTests(unittest.TestCase):
    def test_raw_config_read_and_completion_are_usable_by_association(self):
        rows = [dict(metadata(2309447, 9, tag=6), time_display='94.700 sec'),
                dict(metadata(2309449, 18, tag=6, direction='Upstream', completion_status=0, row=2),
                     time_display='94.700 sec')]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            events = acquisition.make_events(rows, output)
            path = output / 'b2a-register-fields.txt'
            path.write_text('\n'.join((
                acquisition.b2a.HEADER,
                'B2A_ROW|2309447|94.700 sec|Downstream|0x9|0x0|0x6|0x100|0x80|NA|NA|0xF|0x0|0x0|NA|NA|NA|NA|NA|FB0037040000010000060F0100008005',
                'B2A_ROW|2309449|94.700 sec|Upstream|0x12|0x0|0x6|NA|NA|0x0|0x2E010|NA|NA|0x4|10E00200|0x100|0x0|0x4|0x0|FB00354A000001010000040000060010E00200',
                'B2A_END|tlps=2|rows=2|reason=trace_end', acquisition.g1a.DONE_MARKER,
            )), encoding='utf-8')
            self.assertEqual(acquisition.add_raw(path, rows, events, 2), (0, 0))
            observations = dict(schema=acquisition.SCHEMA, analysis_id='a'*32, source_trace_sha256='b'*64,
                                display_trace_sha256='c'*64, packet_namespace='native_trace_packet_zero_based',
                                native_packet_count=2310000, events=list(events.values()), link_downs=[],
                                coverage=dict(stream_complete=True, link_boundaries_complete=True,
                                              full_trace_coverage='UNKNOWN', unsupported_frame_rows=0, omitted_rows=0))
            result = association.analyze(observations)
        self.assertEqual(result['rows'][0]['completion_status'], 'SC')
        completion = result['rows'][0]['completion']
        self.assertEqual((completion['length_dw'], completion['value']), (1, 0x0002E010))
        self.assertIn('length_dw', completion['evidence'][-1]['fields'])

    def raw_report(self, output, prefix):
        # Packet 2151492's header and independently observed payload 00 00 0F 00.
        path = output / 'b2a-register-fields.txt'
        path.write_text('\n'.join((acquisition.b2a.HEADER,
            'B2A_ROW|2151492|93.664 sec|Downstream|0xA|0x0|0x8|0x100|0x78|NA|0xF0000|0xC|0x0|0x4|00000F00|NA|NA|NA|NA|' + prefix,
            'B2A_END|tlps=1|rows=1|reason=trace_end', acquisition.g1a.DONE_MARKER)), encoding='utf-8')
        return path

    def test_full_dword_must_match_wire_payload(self):
        frame_header = 'FB0013440000010000080C01000078'
        rows = [metadata(2151492, 10)]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            events = acquisition.make_events(rows, output)
            path = self.raw_report(output, frame_header + '00000F00')
            self.assertEqual(acquisition.add_raw(path, rows, events, 1), (0, 0))
            event = events[2151492]
            self.assertEqual((event['register'], event['first_be'], event['last_be'], event['value']),
                             (0x78, 0xC, 0, 0x000F0000))
            strong = event['evidence'][-1]
            self.assertEqual((strong['line'], strong['sha256']), (2, acquisition.nav.digest(path)))
            self.assertIn('value', strong['fields'])
            path = self.raw_report(output, frame_header + '00000E00')
            with self.assertRaisesRegex(ValueError, 'Frame/payload mismatch'):
                acquisition.add_raw(path, rows, events, 1)

    def test_legacy_or_unsupported_framing_does_not_promote_value(self):
        rows = [metadata(2151492, 10)]
        frame_header = 'FB0013440000010000080C01000078'
        for prefix, tally, register in ((frame_header + '00', (0, 1), 0x78),
                                         ('AA' + frame_header[2:] + '00000F00', (1, 0), None)):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                events = acquisition.make_events(rows, output)
                self.assertEqual(acquisition.add_raw(self.raw_report(output, prefix), rows, events, 1), tally)
                event = events[2151492]
                self.assertEqual(event['register'], register)
                self.assertIsNone(event['value'])
                self.assertFalse(any('value' in ref['fields'] for ref in event['evidence']))

    def test_detail_plan_checks_opposite_direction_and_observed_link_cut(self):
        rows = [metadata(12, 1), metadata(20, 1), metadata(23, 1, direction='Upstream'),
                metadata(25, 2), metadata(28, 17, direction='Upstream', completion_status=1)]
        with tempfile.TemporaryDirectory() as temporary:
            events = acquisition.make_events(rows, Path(temporary))
            plan, omitted = acquisition.detail_plan(events, [17], 30)
        self.assertEqual(events[25]['kind'], 'OtherNonPosted')
        self.assertEqual([a['packet_index'] for w in plan for a in w['anchors']], [20, 28])
        self.assertEqual([(w['first'], w['last']) for w in plan], [(19, 29)])
        self.assertEqual(omitted, 0)

    def test_mrd_payload_requires_matching_identity_and_native_format(self):
        event = acquisition.metadata_event(metadata(2161214, 1, tag=11))
        row = dict(direction='Downstream', timestamp_seconds='0093.672515042000',
                   native_text='Downstream TLP(24) Mem MRd(32)(000:00000) Length(2) '
                               'RequesterID(000:00:0) Tag(11) Address(6C1FC028) '
                               '1st BE(1111) Last BE(1111)')
        self.assertEqual(acquisition.text_enrichment(row, event, 1),
                         dict(address=0x6C1FC028, length_dw=2, first_be=15, last_be=15, time_ns=93672515042))
        self.assertEqual(acquisition.text_enrichment(row, event, 4), {})
        self.assertEqual(acquisition.text_enrichment(dict(row, direction='Upstream'), event, 1), {})
        self.assertNotIn('time_ns', acquisition.text_enrichment(dict(row, timestamp_seconds='93.672515042001'), event, 1))

    def test_pre_cancel_does_not_launch_background_or_touch_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = Path(temporary)
            root, output = case / 'analysis', case / 'config-ur-attempt'
            root.mkdir()
            output.mkdir()
            working = root / 'display-working.pex'
            working.touch()
            cancelled = threading.Event()
            cancelled.set()
            with patch.object(acquisition.subprocess, 'Popen') as launch:
                with self.assertRaises(InterruptedError):
                    acquisition.run(working, root, output, {}, cancelled)
            launch.assert_not_called()
            self.assertEqual(list(output.iterdir()), [])

    def test_zero_tlp_worker_checks_binding_and_completes_without_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            analysis_id = uuid.uuid4().hex
            case = Path(temporary) / analysis_id
            root, output = case / 'analysis', case / 'config-ur-attempt'
            root.mkdir(parents=True)
            output.mkdir()
            working = root / 'display-working.pex'
            working.write_bytes(b'sealed display copy')
            working.chmod(0o444)
            self.addCleanup(lambda: working.chmod(0o666) if working.exists() else None)
            identity = acquisition.nav.identity(working)
            digest = identity['sha256']
            binding = dict(analysis_id=analysis_id, source_trace_sha256=digest, display_trace_sha256=digest,
                           packet_namespace='native_trace_packet_zero_based', native_packet_count=3)
            count_path = root / 'count.txt'
            count_path.write_text('\n'.join((acquisition.g1a.HEADER,
                'PCIE_G1A_SUMMARY|tlp_count=0|first_index=0|first_time=|last_index=0',
                acquisition.g1a.DONE_MARKER)), encoding='utf-8')
            acquisition.probe.write(root / 'worker.json', dict(status='NO_TLP_OBSERVED', cleanup_status='confirmed',
                before={'source_trace': identity}, working_after=identity, working_unchanged=True, native_packet_count=3,
                tlp_count=0, probes=[dict(name='count', finished={'result': 2}, log_sha256=acquisition.nav.digest(count_path))]))
            request = output / 'acquisition-request.json'
            acquisition.probe.write(request, dict(binding=binding, working=str(working), analysis_root=str(root)))
            with patch.object(acquisition, 'acquire_native') as native:
                self.assertEqual(acquisition.worker(request), 0)
            native.assert_not_called()
            observations = acquisition.probe.read_json(output / 'observations.json')
            self.assertEqual(observations['events'], [])
            self.assertTrue(observations['coverage']['stream_complete'])
            self.assertEqual(observations['coverage']['full_trace_coverage'], 'UNKNOWN')
            self.assertFalse(observations['coverage']['link_boundaries_complete'])
            working.chmod(0o666)


if __name__ == '__main__':
    unittest.main()
