#!/usr/bin/env python3
"""TDD coverage for generic Task Runtime distribution and readiness auditing."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


deploy = load("deploy_package_install", "deploy_package_install.py")
verify = load("verify_package_install", "verify_package_install.py")
audit = load("audit_runtime_readiness", "audit_runtime_readiness.py")
collector = load("brief_me_usage_collect", "brief_me_usage_collect.py")


class RuntimeDistributionTests(unittest.TestCase):
    def test_archive_contains_skills_and_one_runtime_source(self) -> None:
        source = deploy.source_root(ROOT)
        bundle = deploy.archive_bytes(source, ROOT / "scripts" / "task_runtime.py")
        with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
            names = set(archive.getnames())
        for skill in deploy.SKILLS:
            self.assertIn(f"{skill}/SKILL.md", names)
            self.assertIn(f"{skill}/references/decision-and-continuation-protocol.md", names)
        self.assertIn("runtime/task_runtime.py", names)
        self.assertEqual(sum(name == "runtime/task_runtime.py" for name in names), 1)

    def test_local_dry_run_leaves_target_root_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target_root = Path(directory) / "target-hermes"
            result = deploy.deploy_local(
                {"agent": "local-test", "profile_root": str(target_root)},
                deploy.source_root(ROOT),
                ROOT / "scripts" / "task_runtime.py",
                dry_run=True,
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["dry_run"])
            self.assertFalse(target_root.exists())

    def test_local_deploy_installs_runtime_and_backs_up_existing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "target-hermes"
            old_runtime = root / "runtime" / "task-runtime"
            old_runtime.mkdir(parents=True)
            (old_runtime / "task_runtime.py").write_text("old-runtime")
            result = deploy.deploy_local(
                {"agent": "local-test", "profile_root": str(root)},
                deploy.source_root(ROOT),
                ROOT / "scripts" / "task_runtime.py",
                dry_run=False,
            )
            installed = root / "runtime" / "task-runtime" / "task_runtime.py"
            self.assertTrue(result["ok"])
            self.assertTrue(result["backup_created"])
            self.assertEqual(installed.read_bytes(), (ROOT / "scripts" / "task_runtime.py").read_bytes())
            for skill in deploy.SKILLS:
                installed_reference = root / "skills" / "productivity" / skill / "references" / "decision-and-continuation-protocol.md"
                self.assertEqual(installed_reference.read_bytes(), (ROOT / "references" / "decision-and-continuation-protocol.md").read_bytes())
            backups = list((root / "backups").glob("brief-me-runtime-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "task-runtime" / "task_runtime.py").read_text(), "old-runtime")

    def test_verification_reports_runtime_separately_from_skill_sync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "target-hermes"
            runtime = root / "runtime" / "task-runtime"
            runtime.mkdir(parents=True)
            (runtime / "task_runtime.py").write_bytes((ROOT / "scripts" / "task_runtime.py").read_bytes())
            result = verify.check_local("local-test", str(root), verify.repo_manifest(ROOT))
            self.assertIn("runtime", result)
            self.assertTrue(result["runtime"]["exists"])
            self.assertTrue(result["runtime"]["ok"])
            self.assertFalse(result["all_ok"], "skills are intentionally absent in this isolated test")

    def test_verification_requires_shared_reference_for_every_skill(self) -> None:
        expected = verify.repo_manifest(ROOT)
        self.assertIsInstance(expected["skills"]["brief-me"], dict)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "target-hermes"
            deploy.deploy_local(
                {"agent": "local-test", "profile_root": str(root)},
                deploy.source_root(ROOT),
                ROOT / "scripts" / "task_runtime.py",
                dry_run=False,
            )
            matching = verify.check_local("local-test", str(root), expected)
            self.assertTrue(matching["all_ok"])
            (root / "skills" / "productivity" / "brief-me" / "references" / "decision-and-continuation-protocol.md").unlink()
            missing_reference = verify.check_local("local-test", str(root), expected)
            self.assertFalse(missing_reference["all_ok"])
            self.assertFalse(missing_reference["skills"]["brief-me"]["ok"])

    def test_audit_marks_missing_package_or_cli_prerequisite_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".hermes"
            root.mkdir()
            report = audit.audit_local_root("local-test", root)
            self.assertEqual(report["status"], "drift")

    def test_collector_integrity_requires_shared_reference_hashes(self) -> None:
        expected = {name: {"skill_sha16": f"skill-{name}", "reference_sha16": f"reference-{name}"} for name in collector.TERMS}
        agent = {"agent": "local-test", "skills": {name: {"exists": True, "sha16": f"skill-{name}", "reference_exists": True, "reference_sha16": f"reference-{name}"} for name in collector.TERMS}}
        self.assertTrue(collector.package_integrity([agent], expected)["all_agents_match_expected"])
        agent["skills"]["brief-me"]["reference_sha16"] = "tampered"
        self.assertFalse(collector.package_integrity([agent], expected)["all_agents_match_expected"])

    def test_collector_uses_its_public_checkout_as_default_source(self) -> None:
        self.assertEqual(collector.default_repo_root(), ROOT)
        expected = collector.expected_manifest(ROOT)
        digest = hashlib.sha256((ROOT / "skills" / "productivity" / "brief-me" / "SKILL.md").read_bytes()).hexdigest()[:16]
        self.assertEqual(expected["brief-me"]["skill_sha16"], digest)

    def test_audit_local_root_reports_safe_presence_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".hermes"
            (root / "state").mkdir(parents=True)
            (root / "brief_me_stage_reviews.private.json").write_text('{"secret":"not read"}')
            report = audit.audit_local_root("local-test", root)
            self.assertEqual(report["agent"], "local-test")
            self.assertTrue(report["private_stage_config_present"])
            self.assertNotIn("secret", json.dumps(report))
            self.assertIn("runtime", report)
            self.assertIn("skills", report)


if __name__ == "__main__":
    unittest.main()
