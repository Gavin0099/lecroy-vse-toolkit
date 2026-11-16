from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import usb_report_appendix as a
import s01_contract as s
OUT = HERE / "usb-composed-report"
C5 = ROOT / "c5-output-20260911-v3/suspicious-regions.json"
PLAN = ROOT / "artifacts/evidence/serial-slices-20261013/u02-prepared/plan.json"
RUN = ROOT / "artifacts/evidence/serial-slices-20261013/u02-run-a"
model = a.load_model(C5, PLAN, RUN); saved = s.read_json(OUT / "report.json")
assert saved["historical_c5"] == s.read_json(C5)
assert saved["native_command_observations"] == model["native_command_observations"]
base = (OUT / "historical-c5.html").read_text(encoding="utf-8-sig")
section = a.render_block(model["native_command_observations"], OUT)
actual = (OUT / "report.html").read_text(encoding="utf-8")
assert actual == a.compose(base, model["native_command_observations"], OUT)
assert actual.replace(section, "") == base
assert saved["historical_render_sha256"] == a.digest(OUT / "historical-c5.html")
for record in list(model["native_command_observations"]["sources"].values()) + list(model["historical_timelines"].values()):
    assert a.digest(record["path"]) == record["sha256"]

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links = []; self.ids = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "href": self.links.append(value)
            if key == "id": self.ids.append(value)

parser = Links(); parser.feed(actual)
assert "script" not in parser.tags and len(parser.ids) == len(set(parser.ids))
links = Links(); links.feed(section); resolved = 0
for url in links.links:
    path, pointer = url.split("#"); source = OUT / unquote(path)
    assert source.exists()
    data = s.read_json(source)
    if unquote(pointer).startswith("/records/"):
        i = int(unquote(pointer).split("/")[-1]); assert data["records"][i] == model["native_command_observations"]["observation"]["records"][i]; resolved += 1
assert resolved == 128
review = {"slice": "I02", "review": "APPROVE_TYPED_U02_SOURCE_BLOCK", "source_trace_sha256": model["native_command_observations"]["trace_sha256"],
          "report_directory": str(OUT), "report_sha256": {name: a.digest(OUT / name) for name in ["report.json", "report.html", "historical-c5.html"]},
          "historical_c5_json_unchanged": True, "historical_html_preserved_except_added_section": True, "resolved_packet_source_links": resolved,
          "limits": ["128 sampled LINK_CMD rows; no CRC/compliance/Enumeration/root-cause verdict", "retention/filters/epoch/capture mode unknown",
                     "historical C5 candidate ranking and integrity retain original scope; not new field qualification",
                     "both input directories must remain available for evidence links"],
          "next_allowed": "review next candidate input/source prerequisites; no routine owner reapproval required"}
(HERE / "i02-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review": review["review"], "packet_links": resolved, "historical_c5_unchanged": True}))
