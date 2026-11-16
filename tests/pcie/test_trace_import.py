from pathlib import Path
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_trace_import as importer

DONE = "------- D O N E !!! -------"
INFO = {"source_trace": {"sha256": "a" * 64}, "display_trace": {"sha256": "b" * 64}}


def logs(root, complete=False):
    # Independent fixture: two reads sharing a Tag with no intervening Cpl,
    # or one read followed by its successful Completion with Data.
    (root / "count.txt").write_text("PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none\n"
        "PCIE_G1A_SUMMARY|tlp_count=2|first_index=100|first_time=1.000 sec|last_index=110\n" + DONE)
    second_type, channel = ("0x12", "Upstream") if complete else ("0x9", "Downstream")
    (root / "rows.txt").write_text("PCIE_G1B_TLP_ROWS_V2 cap=100000000 time=vendor_display_text\n"
        "PCIE_G1B_TLP|100|1.000 sec|TLP|Downstream|0x9|1\n"
        f"PCIE_G1B_TLP|110|1.001 sec|TLP|{channel}|{second_type}|1\n"
        "PCIE_G1B_END|rows=2|reason=trace_end\n" + DONE)
    tail = "0x0100|0" if complete else "NA|NA"
    (root / "fields.txt").write_text("PCIE_G2A_TLP_FIELDS_V1 fields=tag,requester_id,completer_id,compl_status\n"
        "PCIE_G2A_TLP|100|1.000 sec|Downstream|0x9|3|0x0000|NA|NA\n"
        f"PCIE_G2A_TLP|110|1.001 sec|{channel}|{second_type}|3|0x0000|{tail}\n"
        "PCIE_G2A_END|rows=2|reason=trace_end\n" + DONE)
    (root / "messages.txt").write_text("PCIE_G3C0_MSG_FIELDS_V1 fields=requester_id,message_code,message_route\n"
        "PCIE_G3C0_END|tlps=2|messages=0|reason=trace_end\n" + DONE)


class ImportTests(unittest.TestCase):
    def test_worker_releases_event_connections_before_native_close(self):
        # Connection-point lifetime invariant from pywin32 getevents: the server
        # retains its sink until close()/Unadvise. Persisted output, not call
        # counts alone, must show safe cleanup before analysis is published.
        for cancel in (False, True):
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); logs(root)
                captured={n:(root/(n+'.txt')).read_text().splitlines() for n in importer.PROBES}
                for n in importer.PROBES:(root/(n+'.txt')).unlink()
                source=root/'input.PEX';source.write_bytes(b'independent lifecycle fixture')
                request=dict(source_trace=importer.nav.identity(source),display_trace=importer.nav.identity(source))
                importer.probe.write(root/'request.json',request)
                events={};sinks=[];state=dict(created=False,closed=False)
                class Sink:
                    connected=True
                    def close(self): self.connected=False
                class Engine:
                    def __init__(self,name):self.name=name
                    def LaunchVScript(self):
                        for line in captured[self.name]:events['lines'].append(line)
                        events['finished']=dict(result=2)
                        if cancel:(root/'cancel.json').write_text('{}')
                class Trace:
                    def GetPacketsCountEx(self):return 120
                    def GetVScriptEngine(self,path):return Engine(next(n for n,p in importer.PROBES.items() if p==Path(path).name))
                    def Close(self):
                        if any(s.connected for s in sinks):raise RuntimeError('connection still owns native server')
                        state['closed']=True
                class Analyzer:
                    def OpenFile(self,path):return Trace()
                def dispatch(_):state['created']=True;return Analyzer()
                def with_events(*args):
                    sink=Sink();sinks.append(sink);return sink
                com=types.ModuleType('pythoncom');com.CoInitialize=lambda:None;com.CoUninitialize=lambda:None;com.PumpWaitingMessages=lambda:None
                client=types.ModuleType('win32com.client');client.Dispatch=dispatch;client.WithEvents=with_events
                win32=types.ModuleType('win32com');win32.client=client
                callbacks=types.ModuleType('a1_com_g1a_probe');callbacks.EVENTS=events;callbacks.VseEvents=object
                fake_modules={'pythoncom':com,'win32com':win32,'win32com.client':client,'a1_com_g1a_probe':callbacks}
                with patch.dict(sys.modules,fake_modules), patch.object(importer.probe,'capabilities',return_value={}), patch.object(importer.probe,'processes',side_effect=lambda:[123] if state['created'] and not state['closed'] else []), patch.object(importer.time,'sleep'):
                    code=importer._worker(root/'request.json',root)
                receipt=json.loads((root/'worker.json').read_text(encoding='utf-8'))
                self.assertTrue(state['closed']);self.assertTrue(all(not s.connected for s in sinks))
                self.assertEqual(receipt['remaining_pids'],[])
                self.assertTrue(all(d['ok'] for d in receipt['event_disconnects']))
                self.assertEqual(receipt['status'],'CANCELLED' if cancel else 'ANALYSIS_COMPLETE')
                self.assertEqual(code,2 if cancel else 0)
                self.assertEqual((root/'analysis.json').exists(),not cancel)

    def test_repeated_request_reaches_existing_pipeline_with_bound_locator(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); logs(root)
            result = importer.finish_extraction(root, INFO)
            self.assertEqual(result["status"], "ANALYSIS_COMPLETE")
            self.assertGreater(result["findings_total"], 0)
            location = result["locators"][0]
            self.assertEqual(location["packet_index"], 100)
            self.assertEqual(location["source_trace_sha256"], "a" * 64)
            self.assertEqual(location["display_trace_sha256"], "b" * 64)
            self.assertEqual(location["packet_namespace"], "converted_trace_packet_zero_based")
            self.assertIsNone(location["timestamp"])
            self.assertEqual(location["time_display"], "1.000 sec")
            self.assertEqual(location["direction"], "Downstream")
            self.assertIn("not a ranking", result["ordering"])
            self.assertTrue((root / "report/report.html").is_file())

    def test_complete_pair_empty_result_is_not_product_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); logs(root, complete=True)
            result = importer.finish_extraction(root, INFO)
            self.assertEqual(result["findings_total"], 0)
            self.assertEqual(result["locators"], [])
            self.assertEqual(result["product_verdict"], "NOT_EVALUATED")
            self.assertIn("TLP", result["coverage"])

    def test_truncated_extraction_produces_no_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); logs(root)
            path = root / "fields.txt"; path.write_text(path.read_text().replace(DONE, ""))
            with self.assertRaises(ValueError): importer.finish_extraction(root, INFO)
            self.assertFalse((root / "report").exists())
            self.assertFalse((root / "analysis.json").exists())
            self.assertTrue(path.is_file())

    def test_zero_verified_tlp_has_bounded_empty_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "count.txt").write_text("PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none\n"
                "PCIE_G1A_SUMMARY|tlp_count=0|first_index=0|first_time=|last_index=0\n" + DONE)
            result = importer.finish_extraction(root, INFO)
            self.assertEqual(result["status"], "NO_TLP_OBSERVED")
            self.assertEqual(result["product_verdict"], "NOT_EVALUATED")
            self.assertFalse((root / "report").exists())

    def test_partial_count_not_treated_as_empty_trace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "count.txt").write_text("PCIE_G1A_TLP_COUNT_V1 progress_every=250000 rows=none")
            with self.assertRaises(ValueError): importer.finish_extraction(root, INFO)
            self.assertFalse((root / "analysis.json").exists())


if __name__ == "__main__": unittest.main()
