#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("curator_review_dedupe", ROOT / "scripts" / "curator_review_dedupe.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CuratorDedupeTests(unittest.TestCase):
    def make_source(self, root: Path) -> None:
        for skill in mod.SKILLS:
            path = root / skill / "references" / "decision-and-continuation-protocol.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            (root / skill / "SKILL.md").write_text(skill)
            path.write_text("shared-protocol")

    def test_claim_requires_completion_before_no_change(self):
        evidence = {
            "improvement_decision_input": {
                "evidence_tag_totals": {"verification_gap": 1},
                "collection_errors": [],
                "package_integrity_ok": True,
            },
            "package_integrity": {"by_agent": {"local": {"brief-me": True}}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            self.make_source(root)
            state = Path(tmp) / "state.json"
            now = datetime(2026, 9, 14, tzinfo=timezone.utc)
            first = mod.check(evidence, root, state, "2026-W38", now=now)
            second = mod.check(evidence, root, state, "2026-W38", now=now)
            completed = mod.complete(evidence, root, state, "2026-W38", decision="no_change", claim_id=first["claim_id"], now=now)
            third = mod.check(evidence, root, state, "2026-W38", now=now)
            saved = json.loads(state.read_text())
        self.assertEqual(first["decision"], "review_required")
        self.assertEqual(second["decision"], "review_in_progress")
        self.assertEqual(completed["decision"], "completed")
        self.assertEqual(third["decision"], "no_change")
        self.assertTrue(third["duplicate"])
        self.assertEqual(third["side_effects"], [])
        self.assertEqual(saved["status"], "complete")
        self.assertEqual(saved["decision"], "no_change")
        self.assertIsInstance(saved["timestamp"], str)
        self.assertNotIn("proposal_id", saved)

    def test_abandoned_claim_can_be_reclaimed_after_lease_expiry(self):
        evidence = {"improvement_decision_input": {}, "package_integrity": {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            self.make_source(root)
            state = Path(tmp) / "state.json"
            first_time = datetime(2026, 9, 14, tzinfo=timezone.utc)
            first = mod.check(evidence, root, state, "2026-W38", now=first_time, lease_seconds=60)
            active = mod.check(evidence, root, state, "2026-W38", now=datetime(2026, 9, 14, 0, 0, 30, tzinfo=timezone.utc), lease_seconds=60)
            reclaimed = mod.check(evidence, root, state, "2026-W38", now=datetime(2026, 9, 14, 0, 1, 1, tzinfo=timezone.utc), lease_seconds=60)
            with self.assertRaisesRegex(ValueError, "owned by another claimant"):
                mod.complete(
                    evidence,
                    root,
                    state,
                    "2026-W38",
                    decision="no_change",
                    claim_id=first["claim_id"],
                    now=datetime(2026, 9, 14, 0, 1, 2, tzinfo=timezone.utc),
                )
            completed = mod.complete(
                evidence,
                root,
                state,
                "2026-W38",
                decision="no_change",
                claim_id=reclaimed["claim_id"],
                now=datetime(2026, 9, 14, 0, 1, 30, tzinfo=timezone.utc),
            )
        self.assertEqual(first["decision"], "review_required")
        self.assertEqual(active["decision"], "review_in_progress")
        self.assertEqual(reclaimed["decision"], "review_required")
        self.assertEqual(completed["decision"], "completed")

    def test_completion_rejects_an_expired_owned_claim(self):
        evidence = {"improvement_decision_input": {}, "package_integrity": {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            self.make_source(root)
            state = Path(tmp) / "state.json"
            first = mod.check(
                evidence,
                root,
                state,
                "2026-W38",
                now=datetime(2026, 9, 14, tzinfo=timezone.utc),
                lease_seconds=60,
            )
            with self.assertRaisesRegex(ValueError, "expired"):
                mod.complete(
                    evidence,
                    root,
                    state,
                    "2026-W38",
                    decision="no_change",
                    claim_id=first["claim_id"],
                    now=datetime(2026, 9, 14, 0, 1, tzinfo=timezone.utc),
                )

    def test_changed_evidence_cannot_replace_an_active_same_period_claim(self):
        first_evidence = {"improvement_decision_input": {"evidence_tag_totals": {"verification_gap": 1}}, "package_integrity": {}}
        changed_evidence = {"improvement_decision_input": {"evidence_tag_totals": {"verification_gap": 2}}, "package_integrity": {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            self.make_source(root)
            state = Path(tmp) / "state.json"
            first = mod.check(first_evidence, root, state, "2026-W38", now=datetime(2026, 9, 14, tzinfo=timezone.utc))
            blocked = mod.check(changed_evidence, root, state, "2026-W38", now=datetime(2026, 9, 14, 0, 0, 30, tzinfo=timezone.utc))
            saved = json.loads(state.read_text())
        self.assertEqual(first["decision"], "review_required")
        self.assertEqual(blocked["decision"], "review_in_progress")
        self.assertIsNone(blocked["claim_id"])
        self.assertEqual(saved["claim_id"], first["claim_id"])
        self.assertEqual(saved["signature"], first["signature"])

    def test_package_hash_includes_shared_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills"
            self.make_source(root)
            original = mod.package_hash(root)
            (root / "build-me" / "references" / "decision-and-continuation-protocol.md").write_text("changed")
            self.assertNotEqual(original, mod.package_hash(root))


if __name__ == "__main__":
    unittest.main()
