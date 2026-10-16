"""Distribution invariants independent of the controller's candidate logic."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portable_builder', ROOT / 'tools/build-usb-control-tool.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PortableTests(unittest.TestCase):
    def test_untrusted_runtime_is_rejected_before_unpack_or_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'runtime.zip'
            archive.write_bytes(b'not the official Python archive')
            with self.assertRaisesRegex(ValueError, 'official release'):
                builder.runtime_files(archive)
            self.assertEqual(list(Path(directory).iterdir()), [archive])

    def test_distribution_allowlist_excludes_private_traces_and_evidence(self):
        self.assertEqual(len(builder.FILES), len(set(builder.FILES)))
        for name in builder.FILES:
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn('..', Path(name).parts)
            self.assertNotIn(Path(name).suffix.lower(), ('.usb', '.tmp', '.pex'))
            self.assertNotIn('artifacts', Path(name).parts)
            self.assertTrue((ROOT / name).is_file(), name)


if __name__ == '__main__':
    unittest.main()
