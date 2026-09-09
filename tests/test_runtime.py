import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rms", ROOT / "skills/routed-modular-skill/scripts/rms.py")
rms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rms)


class RuntimeTests(unittest.TestCase):
    def test_length(self):
        output = rms.dispatch("run", "text-length", {"text": "你好 RMS"})
        self.assertEqual(output["result"], {"length": 6})
        self.assertEqual(output["trace"][-1]["event"], "execution:completed")

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

    def test_schema_rejects_extra_property(self):
        with self.assertRaisesRegex(ValueError, "unexpected extra"):
            rms.dispatch("run", "text-length", {"text": "ok", "extra": True})

    def test_route_selects_clear_winner(self):
        decision = rms.dispatch("route", payload=[
            {"id": "text-length", "score": 0.92},
            {"id": "text-uppercase", "score": 0.20},
        ])
        self.assertEqual(decision["status"], "selected")
        self.assertEqual(decision["module_id"], "text-length")

    def test_route_requires_clarification_when_ambiguous(self):
        decision = rms.dispatch("route", payload=[
            {"id": "text-length", "score": 0.86},
            {"id": "text-uppercase", "score": 0.82},
        ])
        self.assertEqual(decision["status"], "needs_clarification")
        self.assertEqual(decision["reason"], "ambiguous_margin")

    def test_optional_state_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            output = rms.dispatch("run", "text-uppercase", {"text": "hi"}, directory)
            state = Path(output["state_path"])
            self.assertTrue(state.is_file())
            self.assertIn('"status": "ok"', state.read_text(encoding="utf-8"))

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
        self.assertFalse(any("text-uppercase/GUIDE.md" in path for path in reads))


if __name__ == "__main__":
    unittest.main()
