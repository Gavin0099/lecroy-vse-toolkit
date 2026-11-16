"""Test the shared UI/export projection against independently checked 1329 rows."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcie_config_ur_report as report


def result_fixture():
    fixture = json.loads((ROOT / "tests/fixtures/pcie-config-ur-1329.json").read_text(encoding="utf-8"))
    observations, expected = fixture["observations"], fixture["expected"]
    packets = {e["packet_index"]: e for e in observations["events"]}
    result = {key: observations[key] for key in (*report.IDENTITY, "coverage")}
    result.update(schema=report.SCHEMA, rows=[], ur_groups=[], unmatched_completions=[])
    for packet, _, _, _, _, reply, identity, read_reply in expected["writes"]:
        readback = None
        if read_reply is not None:
            read_packet = {2309449: 2309447, 2309473: 2309469}[read_reply]
            readback = dict(request=packets[read_packet], completion=packets[read_reply], scope="later_interval")
        register = dict(identity=identity, scope="later_interval" if identity != "UNKNOWN" else "unknown",
                        evidence_packets=[2309436, 2309449] if identity == "PCI_EXP_CAP_HEADER" else [])
        if identity == "PCI_EXP_CAP_HEADER":
            register["write_fields"] = [{"name": "Capability ID", "value": packets[packet]["value"]},
                                        {"name": "Next Capability Pointer", "value": 0}]
        result["rows"].append(dict(id=f"p{packet}", request=packets[packet], completion=packets.get(reply),
                                  completion_status="SC" if reply else "NO_COMPLETION_OBSERVED_BEFORE_LINK_DOWN",
                                  epoch=0, register=register, readback=readback,
                                  write_effect="NOT_ESTABLISHED", bar=None))
    for packet, reply in expected["ur_pairs"]:
        result["rows"].append(dict(id=f"p{packet}", request=packets[packet], completion=packets[reply],
                                  completion_status="UR", epoch=1, register=None, readback=None,
                                  write_effect=None, bar="BAR_UNKNOWN"))
    for address, count in expected["ur_counts"].items():
        requests = [packets[packet] for packet, _ in expected["ur_pairs"]
                    if packets[packet]["address"] == int(address, 16)]
        bursts = []
        i = 0
        for size in expected["ur_bursts"][address]:
            segment = requests[i:i+size]
            bursts.append(dict(start_ns=segment[0]["time_ns"], end_ns=segment[-1]["time_ns"], count=size,
                               row_ids=[f"p{r['packet_index']}" for r in segment]))
            i += size
        result["ur_groups"].append(dict(address=int(address, 16), byte_length=requests[0]["length_dw"]*4,
                                        count=count, bursts=bursts,
                                        row_ids=[f"p{r['packet_index']}" for r in requests]))
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ConfigUrReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "config-ur-0540af894a514d8ea4f9f433d5b90382"
        self.result = result_fixture()

    def test_pages_and_exports_preserve_checked_pairs_and_boundaries(self):
        index = report.write(self.output, self.result)
        self.assertEqual(index, read_json(self.output / "index.json"))
        self.assertEqual(index["row_count"], 15)
        self.assertEqual(index["groups"]["writes"]["count"], 6)
        self.assertEqual(index["groups"]["memory"]["count"], 9)
        self.assertEqual(index["groups"]["ur_summary"]["count"], 3)
        self.assertIn("原始 frame 格式未支援 263 筆", index["coverage_text"])
        self.assertIn("完整擷取範圍未知", index["coverage_text"])
        rows = read_json(self.output / "writes-0.json")["rows"]
        self.assertEqual([r["id"] for r in rows], ["p2151476", "p2151486", "p2151492", "p2151602", "p2160355", "p2160418"])
        self.assertEqual(rows[0]["columns"][4:7], ["0xFFFFFFFF / 0xF / 0x0", "Link Down 前未見回覆", "回讀未確認"])
        self.assertEqual(rows[4]["columns"][4:7], ["0x00000042 / 0x3 / 0x0", "SC · 2160359", "0x0002E010（後續連線區間）"])
        self.assertEqual(rows[4]["locations"], {"request": 2160355, "completion": 2160359, "read_request": 2309447,
                                                "read_completion": 2309449})
        self.assertIn("觀察到的寫入欄位 Capability ID = 0x42", rows[4]["details"])
        self.assertIn("硬體寫入效果尚未建立。", rows[4]["details"])
        self.assertIn("後續連線區間，僅可供比對", "\n".join(rows[4]["details"]))
        self.assertIn("暫存器身分未知", "\n".join(rows[2]["details"]))
        memory = read_json(self.output / "memory-0.json")["rows"]
        self.assertEqual(len(memory), 9)
        self.assertEqual(memory[0]["locations"], {"request": 2161214, "completion": 2161217})
        self.assertEqual(memory[-1]["locations"], {"request": 2308135, "completion": 2308137})
        self.assertIn("BAR 未知", "\n".join(memory[0]["details"]))
        for name in ("report.html", "report.md"):
            output = (self.output / name).read_text(encoding="utf-8")
            for text in ("2151492", "2161217", "0x6C1FC01C", "4 次 UR", "BAR 未知",
                         "0x00000042 / 0x3 / 0x0", "原始 frame 核對", "原始 frame 格式未支援 263 筆",
                         "完整擷取範圍未知", "2309449", "後續連線區間", "Capability ID = 0x42"):
                self.assertIn(text, output)

    def test_bounded_second_page_and_escaped_source(self):
        self.result["rows"] = self.result["rows"][:1] * 21
        self.result["rows"][0]["request"]["evidence"][0]["file"] = "<script>test</script>"
        index = report.write(self.output, self.result)
        first, second = index["groups"]["writes"]["pages"]
        self.assertEqual(len(read_json(self.output / first)["rows"]), 20)
        self.assertEqual(len(read_json(self.output / second)["rows"]), 1)
        self.assertEqual(read_json(self.output / second)["page"], 1)
        for name in ("report.html", "report.md"):
            output = (self.output / name).read_text(encoding="utf-8")
            self.assertNotIn("<script>test</script>", output)
            self.assertIn("&lt;script&gt;test&lt;/script&gt;", output)

    def test_failed_report_does_not_publish_index_and_cannot_replace_existing(self):
        with patch.object(report, "MAX_REPORT_BYTES", 256):
            with self.assertRaises(report.large.ResourceLimit):
                report.write(self.output, self.result)
        self.assertFalse((self.output / "index.json").exists())
        ready = self.output.with_name("previous")
        report.write(ready, self.result)
        before = (ready / "index.json").read_bytes()
        with self.assertRaises(FileExistsError):
            report.write(ready, self.result)
        self.assertEqual((ready / "index.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
