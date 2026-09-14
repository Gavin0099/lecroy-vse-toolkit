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
from test_g3f_findings import build_inputs, pkt


def findings_doc():
    return {"findings": g3f.build(*build_inputs())}


def report():
    return g7.render(findings_doc(), "sample.pex", None, 30, "A" * 64)


class G7MarkdownTests(unittest.TestCase):
    def test_report_answers_the_five_questions_in_chinese_with_english_identities(self):
        md = report()
        self.assertIn("# PCIe Trace 候選檢查位置報告（sample.pex）", md)
        self.assertIn("整理出 1 組候選檢查位置", md)
        self.assertIn(g7.NAVIGATION_NOTE, md)
        self.assertIn("## Finding F001", md)
        for title in g7.SECTION_TITLES:
            self.assertIn(title, md)
        self.assertIn(f"`Packet {pkt(2)}`，依固定規則選出的主要定位點（這一組最早出現的 request）", md)
        self.assertIn(f"`Packet {pkt(24)}` 的 `MRd(32)` request（`Tag 3`）收到 `Packet {pkt(25)}` 的 Completion，status 是 `UR`。", md)
        self.assertIn(f"- `Packet {pkt(26)}`，`ERR_COR`", md)
        self.assertIn("#### Segment A（4.848 sec）", md)
        self.assertIn("`UR`，Unsupported Request", md)
        self.assertIn("不代表這幾段屬於同一個故障事件", md)
        self.assertIn("`ERR_COR` 和 `UR` 目前只確認位置接近，沒有證明因果", md)
        self.assertIn("已在 LeCroy Split Transaction 畫面核對一致（`Split Tra 29`）", md)
        self.assertIn("`findings.json` 的 `F001`，group `G001`，candidates `C001`、`C002`。", md)
        self.assertNotIn("建議先看", md)

    def test_contract_passes_for_rendered_report(self):
        self.assertEqual(g7.contract_check(report(), findings_doc()), [])

    def test_contract_rejects_missing_sections_notes_overclaims_and_dashes(self):
        doc = findings_doc()
        md = report()
        self.assertTrue(any("lacks section" in e for e in g7.contract_check(md.replace("### 目前還不能確定", "### 其他"), doc)))
        self.assertTrue(any("UNKNOWN" in e for e in g7.contract_check(md.replace("`UNKNOWN`", "未知"), doc)))
        self.assertTrue(any("navigation-anchor note" in e for e in g7.contract_check(md.replace(g7.NAVIGATION_NOTE, ""), doc)))
        self.assertTrue(any("forbidden" in e for e in g7.contract_check(md + "\nUR 導致 ERR_COR。\n", doc)))
        self.assertTrue(any("forbidden" in e for e in g7.contract_check(md + "\n建議先看\n", doc)))
        self.assertTrue(any("dash" in e for e in g7.contract_check(md + "\nSegment A — 4.848 sec\n", doc)))
        self.assertTrue(any("omits anchor" in e for e in g7.contract_check(md.replace(f"`Packet {pkt(25)}`", "packet"), doc)))

    def test_order_must_follow_findings_json(self):
        doc = findings_doc()
        second = dict(doc["findings"][0], finding_id="F002", group_id="G002")
        doc2 = {"findings": [doc["findings"][0], second]}
        md = g7.render(doc2, "sample.pex", None, None, "A" * 64)
        self.assertEqual(g7.contract_check(md, doc2), [])
        swapped = md.replace("## Finding F001", "## Finding FTMP").replace("## Finding F002", "## Finding F001").replace("## Finding FTMP", "## Finding F002")
        self.assertTrue(any("differ from findings.json order" in e for e in g7.contract_check(swapped, doc2)))

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "findings.json"
            source.write_text(json.dumps(findings_doc()), encoding="utf-8")
            target = root / "report.md"
            self.assertEqual(g7.main(["--findings", str(source), "--trace-file-name", "sample.pex", "--output", str(target)]), 0)
            self.assertEqual(g7.main(["--findings", str(source), "--trace-file-name", "sample.pex", "--output", str(target)]), 2)


if __name__ == "__main__":
    unittest.main()
