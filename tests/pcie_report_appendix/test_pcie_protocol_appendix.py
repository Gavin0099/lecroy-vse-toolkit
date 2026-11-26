import copy
import hashlib
from html.parser import HTMLParser
import json
import ntpath
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import pcie_protocol_appendix as a
import s01_contract as s

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "artifacts/evidence/p03-serial-20261013"
TIMELINE = ROOT / "artifacts/evidence/pcie-unified-timeline-20261002/run1/timeline.json"
BLOBS = Path(__file__).with_name("frozen-renderer-blobs.txt")


def checkout_renderer(directory):
    # Use a separate index and worktree. Borrow HEAD's objects read-only even
    # for a depth-one source checkout, without cloning the trace history.
    head = a.git(ROOT, "rev-parse", "HEAD").decode().strip()
    objects = a.git(ROOT, "rev-parse", "--path-format=absolute", "--git-path", "objects")
    a.git(directory.parent, "init", "--quiet", str(directory))
    (directory / ".git/objects/info/alternates").write_bytes(objects)
    a.git(directory, "sparse-checkout", "set", "scripts/pcie")
    a.git(directory, "checkout", "--quiet", "--detach", head)

    # The test pin is available even in a shallow clone. The independent I01
    # blob inventory below binds the actual loaded code to the historical pin.
    # Other PCIe tests may already have imported modules from the main checkout.
    with patch.object(a, "FROZEN_HEAD", head), patch.dict(sys.modules), patch.object(sys, "path", sys.path.copy()):
        for name in list(sys.modules):
            if name.startswith(("b1", "b2", "b3", "g2")):
                del sys.modules[name]
        return a.frozen_renderer(directory)


def write_authority_register(directory):
    sources = []
    for source_id in ("LC-01", "LC-07", "LC-15"):
        document = directory / (source_id + ".txt")
        content = (source_id + " appendix test document\n").encode()
        document.write_bytes(content)
        sources.append({"id": source_id, "version": "fixture", "sections": ["fixture"],
                        "local_path": str(document), "sha256": hashlib.sha256(content).hexdigest()})
    register = directory / "docs/pcie-usb-source-register-20261013.json"
    register.parent.mkdir()
    register.write_text(json.dumps({"sources": sources}), encoding="utf-8")
    return register


class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.ids = []; self.links = []; self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        for key, value in attrs:
            if key == "id": self.ids.append(value)
            if key == "href": self.links.append(value)


class AppendixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        fixture = Path(temp.name)
        cls.frozen = fixture / "renderer"
        cls.report, cls.dependencies = checkout_renderer(cls.frozen)
        cls.base = cls.report.build_model(cls.report.adapter.verified_timeline(TIMELINE, ROOT), ROOT)
        probes = {}; sources = {}
        for profile in ["dllp", "tlp"]:
            probes[profile], sources[profile] = a.load_probe(EVIDENCE / "prepared/plan.json", EVIDENCE / (profile + "-a"), profile)
        cls.appendix = a.build_appendix(probes, cls.base["capture_sha256"], sources)
        cls.register = write_authority_register(fixture)
        # bind_authorities locates the register relative to its own module.
        with patch.object(a, "__file__", str(fixture / "tools/pcie_protocol_appendix.py")):
            a.bind_authorities(cls.appendix)

    def test_base_bytes_and_w1_states_unchanged(self):
        md = self.report.render_markdown(self.base, "."); webpage = self.report.render_html(self.base, ".")
        new_md, new_html = a.compose(md, webpage, self.appendix, ROOT)
        self.assertTrue(new_md.startswith(md))
        _, section = a.render_block(self.appendix, ROOT)
        self.assertEqual(new_html.replace(section, ""), webpage)
        self.assertTrue(self.base["intents"])
        self.assertTrue(all(i["observation"]["effective_state"] == "UNKNOWN" and i["observation"]["expected_state"] == "UNKNOWN" and i["observation"]["policy_result"] == "NOT_EVALUATED" for i in self.base["intents"]))

    def test_raw_unknown_na_and_missing_evidence_equal_in_both_formats(self):
        md, webpage = a.render_block(self.appendix, ROOT)
        for text in ["AckNak_SeqNum=1682", "HdrFC=80", "未知（API 空值）", "不適用", "未知（抽樣沒有記錄）", "連續的雙向 capture、mode 與 epoch"]:
            self.assertIn(text, md); self.assertIn(text, webpage)
        self.assertEqual(self.appendix["qualification"], "NOT_EVALUATED")
        self.assertNotIn("extensions", self.appendix); self.assertNotIn("verdict", self.appendix)
        self.assertEqual(self.appendix["coverage"]["epoch"], "unknown")

    def test_every_row_source_pointer_resolves_and_equal(self):
        self.assertEqual({key: len(probe["rows"]) for key, probe in self.appendix["profiles"].items()},
                         {"dllp": 73, "tlp": 51})
        for profile, probe in self.appendix["profiles"].items():
            source = self.appendix["sources"][profile]["observations"]
            data = s.read_json(Path(source["path"]))
            for i, row in enumerate(probe["rows"]):
                self.assertEqual(self.report.contract.pointer_value(data, "/rows/" + str(i)), row)

    def test_html_unique_ids_offline_and_escaped(self):
        md, webpage = a.render_block(self.appendix, ROOT); parser = Tags(); parser.feed(webpage)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertNotIn("script", parser.tags)
        for url in parser.links:
            resolved = urlsplit(urljoin(ROOT.as_uri() + "/", url))
            self.assertEqual(resolved.scheme, "file")
            self.assertFalse(resolved.netloc)
            self.assertTrue(Path(url2pathname(resolved.path)).is_file(), url)
        model = copy.deepcopy(self.appendix); model["missing_evidence"] = ["<script>alert(1)</script>"]
        _, escaped = a.render_block(model, ROOT)
        self.assertNotIn("<script>", escaped); self.assertIn("&lt;script&gt;", escaped)

    def test_capture_mismatch_rejected(self):
        with self.assertRaises(s.ContractError): a.build_appendix(self.appendix["profiles"], "f" * 64, self.appendix["sources"])

    def test_cross_drive_links_are_offline_file_uris(self):
        source = EVIDENCE / "dllp-a/observations.json"
        # Windows drive comparison is lexical; the other drive need not exist.
        other_drive = "Y:/" if source.drive.upper() == "Z:" else "Z:/"
        with patch.object(a.os.path, "relpath", ntpath.relpath):
            target = a.link({"path": str(source)}, "/rows/0", other_drive)
        self.assertEqual(target, source.as_uri() + "#%2Frows%2F0")

    def test_opaque_or_raw_tampering_rejected_before_render(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for rel in ["before.json", "after.json", "observations.json", "native/com-run.json", "native/report-lines.json"]:
                destination = target / rel; destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(EVIDENCE / "dllp-a" / rel, destination)
            original = s.read_json(target / "observations.json")
            for mutation in ["opaque", "value", "unknown_to_pass"]:
                data = copy.deepcopy(original)
                if mutation == "opaque": data["extensions"] = {"verdict": "PASS"}
                elif mutation == "value": data["rows"][0]["fields"]["HdrFC"]["value"] = 81
                else: data["coverage"]["epoch"] = "PASS"
                (target / "observations.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(s.ContractError, "observation differs from native source replay"):
                    a.load_probe(EVIDENCE / "prepared/plan.json", target, "dllp")

            write_authority_register(target)
            (target / "LC-07.txt").write_bytes(b"changed revision")
            with patch.object(a, "__file__", str(target / "tools/pcie_protocol_appendix.py")):
                with self.assertRaisesRegex(s.ContractError, "document/source revision drift"):
                    a.bind_authorities(copy.deepcopy(self.appendix))

    def test_dependencies_match_pinned_commit_and_new_output_only(self):
        review = s.read_json(EVIDENCE / "i01-review.json")
        self.assertEqual(a.FROZEN_HEAD, review["frozen_commit"])
        self.assertEqual(set(self.dependencies), set(review["frozen_dependencies"]))
        entries = (line.split() for line in BLOBS.read_text().splitlines() if not line.startswith("#"))
        expected = {path: blob for blob, path in entries}
        actual = {}
        for path, disk_sha in self.dependencies.items():
            self.assertEqual(disk_sha, a.digest(self.frozen / path))
            blob = a.git(self.frozen, "hash-object", "--path=" + path, str(self.frozen / path)).decode().strip()
            actual[path] = blob
        self.assertEqual(actual, expected)
        self.assertFalse(a.git(self.frozen, "status", "--porcelain").strip())
        with patch.object(a, "FROZEN_HEAD", "0" * 40):
            with self.assertRaisesRegex(s.ContractError, "verified clean frozen checkout"):
                a.frozen_renderer(self.frozen)
        head = a.git(self.frozen, "rev-parse", "HEAD").decode().strip()
        with tempfile.NamedTemporaryFile(dir=self.frozen), patch.object(a, "FROZEN_HEAD", head):
            with self.assertRaisesRegex(s.ContractError, "verified clean frozen checkout"):
                a.frozen_renderer(self.frozen)
        authorities = s.read_json(self.register)["sources"]
        self.assertEqual([(row["source_id"], row["sha256"]) for row in self.appendix["authorities"]],
                         [(row["id"], row["sha256"]) for row in authorities])
        output = self.frozen / "not-created-output"
        with self.assertRaisesRegex(s.ContractError, "fresh output outside frozen checkout required"):
            a.generate(self.frozen, TIMELINE, EVIDENCE / "prepared/plan.json",
                       EVIDENCE / "dllp-a", EVIDENCE / "tlp-a", output)
        self.assertFalse(output.exists())


if __name__ == "__main__": unittest.main()
