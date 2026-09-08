import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rms", ROOT / "skills/routed-modular-skill/scripts/rms.py")
rms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rms)


class RuntimeTests(unittest.TestCase):
    def test_length(self):
        self.assertEqual(rms.dispatch("run", "text-length", {"text": "你好 RMS"})["result"], {"length": 6})

    def test_empty(self):
        self.assertEqual(rms.dispatch("run", "text-length", {"text": ""})["result"], {"length": 0})

    def test_uppercase(self):
        self.assertEqual(rms.dispatch("run", "text-uppercase", {"text": "Straße"})["result"], {"text": "STRASSE"})

    def test_unknown(self):
        with self.assertRaises(ValueError):
            rms.dispatch("load", "missing")

    def test_invalid_input(self):
        for value in ({}, {"text": 4}, []):
            with self.assertRaises(ValueError):
                rms.dispatch("run", "text-length", value)

    def test_traversal(self):
        with self.assertRaises(ValueError):
            rms.contained_file("../../README.md")

    def test_load_only_selected_guide(self):
        original = Path.read_text
        reads = []
        def tracked(path, *args, **kwargs):
            reads.append(str(path))
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", tracked):
            rms.dispatch("load", "text-length")
        self.assertEqual(len(reads), 2)
        self.assertTrue(reads[1].endswith("text-length/GUIDE.md"))


if __name__ == "__main__":
    unittest.main()
