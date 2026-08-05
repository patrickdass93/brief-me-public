#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("curator_review_dedupe", ROOT / "scripts" / "curator_review_dedupe.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CuratorDedupeTests(unittest.TestCase):
    def test_same_period_and_evidence_is_silent_no_change(self):
        evidence = {"improvement_decision_input": {"evidence_tag_totals": {"verification_gap": 1}, "collection_errors": [], "package_integrity_ok": True}, "package_integrity": {"by_agent": {"local": {"brief-me": True}}}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            for skill in mod.SKILLS:
                path = root / skill / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(skill)
            state = Path(tmp) / "state.json"
            first = mod.check(evidence, root, state, "2026-W32")
            second = mod.check(evidence, root, state, "2026-W32")
        self.assertEqual(first["decision"], "review_required")
        self.assertEqual(second["decision"], "no_change")
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["side_effects"], [])
        self.assertIn("no duplicate delivery", second["guarantees"])


if __name__ == "__main__":
    unittest.main()
