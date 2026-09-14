import json
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = TEST_DIR.parents[1] / "scripts" / "pcie"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(TEST_DIR))

import g3f_findings as g3f
import g7_render_markdown as g7
import g8_render_html as g8
from test_g3f_findings import build_inputs, pkt


def findings_doc():
    return {"findings": g3f.build(*build_inputs())}


def page(trace="sample.pex"):
    return g8.render(findings_doc(), trace, None, 30, "A" * 64)


class G8HtmlTests(unittest.TestCase):
    def test_layered_card_with_warning_panel_and_scan_badges(self):
        doc = page()
        self.assertIn('class="warn"', doc)
        self.assertIn("<code>UNKNOWN</code>", doc)
        self.assertIn(g7.NAVIGATION_NOTE, doc)
        self.assertIn('<span class="badge b-ur">UR</span>', doc)
        self.assertIn('<span class="badge b-msg">ERR_COR</span>', doc)
        self.assertIn("同 key 再次出現", doc)
        card = doc.split('<section class="card" ')[1]
        first, _, details = card.partition("<details>")
        self.assertIn(f"<code>Packet {pkt(2)}</code>", first)
        self.assertIn("主要定位點", first)
        self.assertNotIn("目前還不能確定", first)
        self.assertIn("展開完整證據", details)
        self.assertIn("目前還不能確定", details)
        self.assertIn(f"<code>Packet {pkt(25)}</code>", details)
        self.assertIn("不代表這幾段屬於同一個故障事件", details)

    def test_markdown_and_html_share_wording(self):
        doc = page()
        parts = g7.finding_parts(findings_doc()["findings"][0])
        for sentence in parts["observations"] + parts["unknown"]:
            self.assertIn(g8.inline(sentence), doc)

    def test_contract_passes_and_rejects_scripts_external_and_missing_evidence(self):
        fd = findings_doc()
        doc = page()
        self.assertEqual(g8.contract_check(doc, fd), [])
        self.assertTrue(any("script" in e for e in g8.contract_check(doc.replace("</main>", "<script>x()</script></main>"), fd)))
        self.assertTrue(any("external" in e for e in g8.contract_check(doc.replace("</main>", '<img src="https://x/y.png"></main>'), fd)))
        self.assertTrue(any("expandable" in e for e in g8.contract_check(doc.replace("<details>", "<div>"), fd)))
        self.assertTrue(any("forbidden" in e for e in g8.contract_check(doc.replace("</main>", "<p>root cause</p></main>"), fd)))

    def test_trace_name_is_escaped(self):
        doc = page('<img src=x onerror=alert(1)>.pex')
        self.assertNotIn("<img src=x", doc)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;.pex", doc)

    def test_conversion_provenance_panel_precedes_cards(self):
        prov = {"original_sha256": "F" * 64, "conversion": "PETracer 12.36 (Build 19) → 13.26 (Build 43) format update", "analysis_target": "converted disposable copy"}
        fd = findings_doc()
        doc = g8.render(fd, "sample.pex", "C" * 64, 30, "A" * 64, prov)
        head = doc.split('<section class="card" ')[0]
        self.assertIn(g8.PROVENANCE_LABEL, head)
        self.assertIn(g7.PACKET_INDEX_NOTE, head)
        self.assertIn("F" * 64, head)
        self.assertEqual(g8.contract_check(doc, fd, prov), [])
        self.assertTrue(g8.contract_check(doc.replace(g7.PACKET_INDEX_NOTE, ""), fd, prov))
        self.assertTrue(g8.contract_check(page(), fd, prov))

    def test_cli_writes_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "findings.json"
            source.write_text(json.dumps(findings_doc()), encoding="utf-8")
            target = root / "report.html"
            args = ["--findings", str(source), "--trace-file-name", "sample.pex", "--output", str(target)]
            self.assertEqual(g8.main(args), 0)
            self.assertEqual(g8.main(args), 2)


if __name__ == "__main__":
    unittest.main()
