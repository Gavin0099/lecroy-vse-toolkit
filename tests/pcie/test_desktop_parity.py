"""Boundary regressions; observable state/files, not duplicated detector logic."""
from pathlib import Path
import json
import sys
import tempfile
import threading
from contextlib import nullcontext
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import usb_control_app as host
import pcie_pipeline as pipeline
from test_workspace import fixture
import pcie_workspace as view


class DesktopTests(unittest.TestCase):
    def setUp(self):
        # These tests substitute native acquisition. Real mutex/session isolation
        # is exercised separately by the Windows worker qualification.
        guard=patch.object(host,'native_exclusive',nullcontext);guard.start();self.addCleanup(guard.stop)
    def test_cancel_after_model_build_does_not_publish_case(self):
        import pcie_ui_pages
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'late.pex';source.write_bytes(b'independent test capture identity')
            tool=host.Tool(root/'tool')
            def run(src,out,aid,progress,**kwargs):
                fixture(out)
                return dict(model=view.compose(out,aid),working=out/'display-working.pex',elapsed_seconds=1)
            real_write=pcie_ui_pages.write
            def cancel_after_pages(*args,**kwargs):
                value=real_write(*args,**kwargs)
                self.assertTrue(tool.native_command({'action':'cancel'}))
                return value
            with patch.object(pipeline,'run',side_effect=run),patch.object(pcie_ui_pages,'write',side_effect=cancel_after_pages):
                tool.import_trace(source);tool.thread.join(10)
            self.assertFalse(tool.state['busy']);self.assertEqual(tool.state['phase'],'cancelled')
            self.assertIsNone(tool.case);self.assertIsNone(tool.public()['case_id'])
    def test_pcie_import_persists_same_model_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'中文 大寫.PEX';source.write_bytes(b'independent test capture identity')
            tool=host.Tool(root/'tool')
            def run(src,out,aid,progress,**kwargs):
                fixture(out);m=view.compose(out,aid)
                # Source bytes are identical and model identity is source-bound;
                # this fixture substitutes only native acquisition.
                return dict(model=m,working=out/'display-working.pex',elapsed_seconds=1)
            with patch.object(pipeline,'run',side_effect=run):
                self.assertTrue(tool.import_trace(source,'drag_drop'));tool.thread.join(10)
            self.assertFalse(tool.state['busy']);self.assertEqual(tool.state['phase'],'report')
            model=json.loads((tool.case['folder']/'inspection.json').read_text(encoding='utf-8'))
            self.assertEqual(model,tool.case['model']);self.assertEqual(model['candidates'][0]['locator']['packet_index'],100)
            self.assertEqual((tool.case['folder']/'report.md').read_text(encoding='utf-8'),view.markdown(model))
            self.assertEqual((tool.case['folder']/'report.html').read_text(encoding='utf-8'),view.render(model))
            tool.integrity()

    def test_busy_rejects_second_import_and_stale_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'x.pex';source.write_bytes(b'x');tool=host.Tool(root/'tool')
            entered=threading.Event();release=threading.Event()
            def slow(*args,**kw):entered.set();release.wait(5);raise RuntimeError('fixture failed acquisition')
            with patch.object(pipeline,'run',side_effect=slow):
                self.assertTrue(tool.import_trace(source));self.assertTrue(entered.wait(3))
                self.assertFalse(tool.import_trace(source));self.assertFalse(tool.navigate('old',1))
                release.set();tool.thread.join(5)
            self.assertIsNone(tool.public()['case_id']);self.assertEqual(tool.state['phase'],'error')
            self.assertFalse(list(tool.root.rglob('inspection.json')))

    def test_failed_new_import_does_not_republish_previous_case(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'bad.pex';source.write_bytes(b'x');tool=host.Tool(root/'tool')
            tool.case=dict(id='old',name='old',model=dict(scope='old',analyses=[]))
            with patch.object(tool,'close_navigation'),patch.object(pipeline,'run',side_effect=ValueError('bad source')):
                tool.import_trace(source);tool.thread.join(5)
            self.assertIsNone(tool.case);self.assertIsNone(tool.public()['case_id'])
            with self.assertRaises(ValueError):tool.navigate('old',1)

    def test_cancel_is_cooperative_and_never_publishes_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'cancel.pex';source.write_bytes(b'x');tool=host.Tool(root/'tool')
            started=threading.Event()
            def run(*args,cancel,**kwargs):
                started.set();cancel.wait(5);raise pipeline.Cancelled('safe boundary')
            with patch.object(pipeline,'run',side_effect=run):
                tool.import_trace(source);self.assertTrue(started.wait(3));self.assertTrue(tool.native_command(dict(action='cancel')))
                tool.thread.join(5)
            self.assertEqual(tool.state['phase'],'cancelled');self.assertIsNone(tool.case)

    def test_timeout_keeps_native_unknown_and_disables_new_work(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'timeout.pex';source.write_bytes(b'x');tool=host.Tool(root/'tool')
            with patch.object(pipeline,'run',side_effect=TimeoutError('native UNKNOWN')):
                tool.import_trace(source);tool.thread.join(5)
            self.assertEqual(tool.state['phase'],'unresponsive');self.assertIsNone(tool.case)
            self.assertFalse(tool.import_trace(source));self.assertFalse(list(tool.root.rglob('inspection.json')))

    def test_partial_and_cleanup_unknown_keep_candidates_empty(self):
        for error,phase in ((pipeline.Partial('missing DONE'),'partial'),(pipeline.CleanupUnknown('native state unknown'),'cleanup_unknown')):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as d:
                root=Path(d);source=root/'incomplete.pex';source.write_bytes(b'x');tool=host.Tool(root/'tool')
                with patch.object(pipeline,'run',side_effect=error):
                    tool.import_trace(source);tool.thread.join(5)
                self.assertEqual(tool.state['phase'],phase);self.assertIsNone(tool.public()['case_id'])
                self.assertFalse(list(tool.root.rglob('inspection.json')))


if __name__=='__main__':unittest.main()
