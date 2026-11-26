import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "pcie"))
from com_protocol_events import render_probe, verify_conversion


class AcquisitionInputTests(unittest.TestCase):
    def test_window_replaces_exact_constants(self):
        script = "const FIRST_PACKET = 0;\nconst LAST_PACKET = 100;\n"
        self.assertEqual(render_probe(script, 4095, 4100),
                         "const FIRST_PACKET = 4095;\nconst LAST_PACKET = 4100;\n")

    def test_reversed_window_or_missing_declaration_is_rejected(self):
        script = "const FIRST_PACKET = 0;\nconst LAST_PACKET = 100;\n"
        with self.assertRaisesRegex(ValueError, "invalid inclusive"):
            render_probe(script, 4100, 4095)
        with self.assertRaisesRegex(ValueError, "LAST_PACKET"):
            render_probe("const FIRST_PACKET = 0;\n", 0, 0)

    def test_distinct_display_requires_matching_sealed_conversion(self):
        source = {"sha256": "a" * 64, "bytes": 12}
        display = {"sha256": "b" * 64, "bytes": 13}
        self.assertIsNone(verify_conversion(source, source, None))
        with self.assertRaisesRegex(ValueError, "required"):
            verify_conversion(source, display, None)
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            body = {
                "binding": {"schema": "pcie.converted-copy/v1", "source_sha256": "a" * 64},
                "status": "SEALED_CONVERSION",
                "display_sha256": "b" * 64,
                "cleanup_confirmed": True,
                "bytes": 13,
            }
            raw = json.dumps(body).encode()
            manifest.write_bytes(raw)
            self.assertEqual(verify_conversion(source, display, manifest), hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError, "does not bind"):
                verify_conversion({"sha256": "c" * 64}, display, manifest)
