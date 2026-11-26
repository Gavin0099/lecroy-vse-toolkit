import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcie_protocol_appendix as a
import s01_contract as s
OUT = Path(r"C:\Users\reiko\.codex\visualizations\2026\10\13\01a13339-798e-7020-8e39-ec838f3ed292\pcie-observations")
FROZEN = Path(r"C:\Users\reiko\.codex\worktrees\pcie-slice-delivery\lecroy-vse-toolkit")
TIMELINE = FROZEN / "artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json"
report, dependencies = a.frozen_renderer(FROZEN)
base = report.build_model(report.adapter.verified_timeline(TIMELINE, FROZEN), FROZEN)
model = s.read_json(OUT / "report.json")
assert model["base_report"] == base
prefix = Path(os.path.relpath(FROZEN, OUT)).as_posix()
base_md = report.render_markdown(base, prefix); base_html = report.render_html(base, prefix)
probes = {}; sources = {}
for profile in ["dllp", "tlp"]:
    probes[profile], sources[profile] = a.load_probe(HERE / "prepared/plan.json", HERE / (profile + "-a"), profile)
appendix = a.build_appendix(probes, base["capture_sha256"], sources); a.bind_authorities(appendix)
assert model["protocol_appendix"] == appendix
expected_md, expected_html = a.compose(base_md, base_html, appendix, OUT)
assert (OUT / "report.md").read_text(encoding="utf-8") == expected_md
assert (OUT / "report.html").read_text(encoding="utf-8") == expected_html
assert model["provenance"]["dependencies"] == dependencies
assert all(i["observation"]["effective_state"] == "UNKNOWN" and i["observation"]["expected_state"] == "UNKNOWN" and i["observation"]["policy_result"] == "NOT_EVALUATED" for i in base["intents"])
assert "extensions" not in appendix and "details" not in appendix and "verdict" not in appendix

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links = []; self.ids = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "href": self.links.append(value)
            if key == "id": self.ids.append(value)

links = Links(); links.feed(expected_html)
assert len(links.ids) == len(set(links.ids)) and "script" not in links.tags
resolved = 0
for url in links.links:
    if url.startswith("#"): continue
    parsed = urlsplit(url)
    assert parsed.scheme in {"", "file"}
    path = Path(unquote(parsed.path).lstrip("/")) if parsed.scheme == "file" else OUT / unquote(parsed.path)
    assert path.exists(), path
    if parsed.fragment.startswith("%2F"):
        report.contract.pointer_value(s.read_json(path), unquote(parsed.fragment)); resolved += 1
review = {"slice": "I01", "review": "APPROVE_TYPED_P03_SOURCE_BLOCK", "report_directory": str(OUT),
          "report_sha256": {name: a.digest(OUT / name) for name in ["report.json", "report.md", "report.html"]},
          "frozen_commit": a.FROZEN_HEAD, "frozen_dependencies": dependencies, "base_model_unchanged": True,
          "base_markdown_prefix_preserved": True, "base_html_preserved_except_added_section": True,
          "resolved_json_pointer_links": resolved, "sampled_rows": 124, "capture_sha256": appendix["capture_sha256"],
          "limits": ["P03 bounded observation only; not whole protocol qualification", "separate source block; no new W1 verdict",
                     "links require both original checkouts/evidence locations; not a portable standalone package",
                     "file links across C/E drives; existing W5 links require output on frozen checkout drive"],
          "next_allowed": "I02 USB command observation source block, independently typed and validated"}
(HERE / "i01-review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"review": review["review"], "resolved_links": resolved, "base_model_unchanged": True}))
