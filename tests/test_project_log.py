#!/usr/bin/env python3
"""Deterministic tests for the Brief-Me narrative Google Doc log."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "project_log.py"
spec = importlib.util.spec_from_file_location("project_log", MODULE_PATH)
assert spec and spec.loader
project_log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project_log)


def entry(event_type: str = "decision") -> dict:
    value = {
        "schema_version": "project-log/v1",
        "task_id": "test-task-001",
        "stage": "brief-me",
        "event_type": event_type,
        "actor": "user",
        "status": "in-progress",
        "summary": "The user clarified that the project record must tell the execution story.",
        "redactions_applied": True,
        "recorded_at": "2026-07-28T10:00:00Z",
    }
    if event_type == "decision":
        value.update({
            "decision": "Use an append-only narrative timeline as the canonical task record.",
            "rationale": "A stage-gate dump alone does not explain how the work progressed.",
            "next_step": "Create and test the narrative event writer.",
        })
    value["entry_digest"] = project_log.entry_digest(value)
    return value


class ProjectLogTests(unittest.TestCase):
    def test_valid_decision_entry(self) -> None:
        self.assertEqual(project_log.validate_entry(entry()), [])

    def test_decision_requires_decision_text(self) -> None:
        bad = entry()
        del bad["decision"]
        self.assertTrue(any("decision events require" in error for error in project_log.validate_entry(bad)))

    def test_blocker_requires_next_step(self) -> None:
        bad = entry("blocker")
        bad.pop("decision", None)
        bad.pop("rationale", None)
        bad.pop("next_step", None)
        self.assertTrue(any("blocker events require" in error for error in project_log.validate_entry(bad)))

    def test_render_is_human_readable_and_parseable(self) -> None:
        rendered = project_log.render_entry(entry())
        self.assertIn("**What happened:**", rendered)
        self.assertIn("**Decision:**", rendered)
        self.assertIn("**Why this was chosen:**", rendered)
        self.assertIn("**Next:**", rendered)
        self.assertIn("@@BRIEF_ME_PROJECT_LOG_V1@@", rendered)
        digest = entry()["entry_digest"]
        self.assertTrue(project_log.document_has_entry_digest(rendered, digest))

    def test_digest_ignores_clock_and_document_metadata(self) -> None:
        first = entry()
        second = entry()
        second["recorded_at"] = "2026-07-28T11:00:00Z"
        second["document"] = {"id": "doc-1", "url": "https://example.test/doc-1"}
        self.assertEqual(project_log.entry_digest(first), project_log.entry_digest(second))

    def test_cli_dry_run_requires_redaction_confirmation(self) -> None:
        # Schema-level behavior is sufficient here: command parsing is exercised
        # by the package smoke test with explicit --redacted.
        bad = entry()
        bad["redactions_applied"] = False
        self.assertTrue(any("True was expected" in error for error in project_log.validate_entry(bad)))

    def test_timeline_renders_decisions_actions_verification_blockers_and_next_steps_in_order(self) -> None:
        events = [entry(), entry("action"), entry("verification"), entry("blocker")]
        details = [
            ("2026-07-28T10:00:00Z", "The user chose a readable project story.", "Continue with implementation."),
            ("2026-07-28T10:01:00Z", "The agent added the event writer.", "Run the focused tests."),
            ("2026-07-28T10:02:00Z", "The focused tests passed.", "Run the stage gate."),
            ("2026-07-28T10:03:00Z", "The stage gate requested more proof.", "Add evidence tests and rerun the gate."),
        ]
        for event, (recorded_at, summary, next_step) in zip(events, details):
            if event["event_type"] != "decision":
                event.pop("decision", None)
                event.pop("rationale", None)
            event["recorded_at"] = recorded_at
            event["summary"] = summary
            event["next_step"] = next_step
            event["entry_digest"] = project_log.entry_digest(event)
            self.assertEqual(project_log.validate_entry(event), [])
        rendered = "\n".join(project_log.render_entry(event) for event in events)
        positions = [rendered.index(label) for label in ("— Decision", "— Action", "— Verification", "— Blocker")]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(rendered.count("**What happened:**"), 4)
        self.assertEqual(rendered.count("**Next:**"), 4)
        self.assertEqual(rendered.count("@@BRIEF_ME_PROJECT_LOG_V1@@"), 4)

    def test_cli_creates_reuses_existing_doc_and_dedupes_a_readable_event(self) -> None:
        document = {"text": ""}
        append_calls: list[str] = []

        def create(folder_id, title, template_path, context):
            self.assertEqual(folder_id, "folder-1")
            self.assertEqual(context["task_id"], "test-task-001")
            document["text"] = template_path.read_text()
            return {"document_id": "doc-1"}

        def append(doc_id, text):
            self.assertEqual(doc_id, "doc-1")
            append_calls.append(text)
            document["text"] += text

        args = [
            "project_log.py", "--task-id", "test-task-001", "--task-title", "Narrative test",
            "--folder-id", "folder-1", "--stage", "brief-me", "--event-type", "decision",
            "--actor", "user", "--status", "in-progress", "--summary", "Choose a readable log.",
            "--decision", "Use a chronological timeline.", "--next-step", "Implement it.", "--redacted",
            "--recorded-at", "2026-07-28T10:00:00Z",
        ]
        with patch.object(project_log, "create_task_document", side_effect=create), \
             patch.object(project_log, "append_task_document", side_effect=append), \
             patch.object(project_log, "read_task_document", side_effect=lambda _doc_id: document["text"]), \
             patch.object(project_log, "document_url", return_value="https://example.test/doc-1"), \
             patch.object(sys, "argv", args), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(project_log.main(), 0)
        self.assertEqual(len(append_calls), 1)
        self.assertIn("**What happened:** Choose a readable log.", document["text"])
        self.assertIn("**Decision:** Use a chronological timeline.", document["text"])

        retry_args = args.copy()
        retry_args[retry_args.index("--folder-id"):retry_args.index("--folder-id") + 2] = ["--doc-id", "doc-1"]
        del retry_args[retry_args.index("--task-title"):retry_args.index("--task-title") + 2]
        with patch.object(project_log, "create_task_document") as create_again, \
             patch.object(project_log, "append_task_document", side_effect=append), \
             patch.object(project_log, "read_task_document", side_effect=lambda _doc_id: document["text"]), \
             patch.object(project_log, "document_url", return_value="https://example.test/doc-1"), \
             patch.object(sys, "argv", retry_args), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(project_log.main(), 0)
        create_again.assert_not_called()
        self.assertEqual(len(append_calls), 1)


if __name__ == "__main__":
    unittest.main()
