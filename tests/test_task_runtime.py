#!/usr/bin/env python3
"""Deterministic tests for the local inactive Task Runtime proof."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "task_runtime.py"
spec = importlib.util.spec_from_file_location("task_runtime", MODULE_PATH)
assert spec and spec.loader
runtime_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime_module
spec.loader.exec_module(runtime_module)

TaskRuntime = runtime_module.TaskRuntime
TaskRuntimeError = runtime_module.TaskRuntimeError


def wait_for_lock_holder_ready(holder: subprocess.Popen[str], timeout: float = 2.0) -> None:
    """Wait a bounded interval for a lock-holder subprocess readiness signal."""
    assert holder.stdout is not None
    assert holder.stderr is not None
    ready, _, _ = select.select([holder.stdout], [], [], timeout)
    if not ready:
        raise AssertionError(f"lock holder readiness timed out after {timeout:.1f}s")
    signal = holder.stdout.readline().strip()
    if signal == "locked":
        return
    stderr = holder.stderr.read().strip() if holder.poll() is not None else "<holder still running>"
    raise AssertionError(f"lock holder readiness failed: signal={signal!r}; stderr={stderr!r}")


class TaskRuntimeTests(unittest.TestCase):
    def make_runtime(self) -> tuple[tempfile.TemporaryDirectory[str], TaskRuntime]:
        tmp = tempfile.TemporaryDirectory()
        return tmp, TaskRuntime(Path(tmp.name) / "runtime.sqlite3")

    def test_first_trigger_creates_durable_task_and_event(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        result = runtime.create_or_get_task(
            agent_id="local-test",
            idempotency_key="telegram:message:100",
            title="Synthetic local proof",
        )
        self.assertTrue(result["created"])
        task = result["task"]
        self.assertEqual(task["state"], "received")
        self.assertEqual(task["agent_id"], "local-test")
        events = runtime.list_events(task["task_id"])
        self.assertEqual([event["event_type"] for event in events], ["task.created"])

    def test_task_and_events_survive_runtime_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "runtime.sqlite3"
            first = TaskRuntime(db)
            task = first.create_or_get_task("local-test", "reopen-key", "Persistence proof")["task"]
            first.transition(task["task_id"], "briefing", "persist this transition")
            first.close()
            reopened = TaskRuntime(db)
            self.addCleanup(reopened.close)
            self.assertEqual(reopened.get_task(task["task_id"])["state"], "briefing")
            self.assertEqual([event["event_type"] for event in reopened.list_events(task["task_id"])], ["task.created", "task.transitioned"])

    def test_duplicate_trigger_returns_existing_task_without_duplicate_event(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        first = runtime.create_or_get_task("local-test", "duplicate-key", "First")
        second = runtime.create_or_get_task("local-test", "duplicate-key", "Ignored duplicate")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["task"]["task_id"], second["task"]["task_id"])
        self.assertEqual(len(runtime.list_events(first["task"]["task_id"])), 1)

    def test_valid_transitions_append_events_and_invalid_transition_fails_closed(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        task = runtime.create_or_get_task("local-test", "state-key", "State proof")["task"]
        runtime.transition(task["task_id"], "briefing", "brief created")
        runtime.transition(task["task_id"], "ready_to_build", "approved brief")
        runtime.transition(task["task_id"], "building", "local code starts")
        self.assertEqual(runtime.get_task(task["task_id"])["state"], "building")
        self.assertEqual(len(runtime.list_events(task["task_id"])), 4)
        with self.assertRaises(TaskRuntimeError):
            runtime.transition(task["task_id"], "completed", "cannot skip verification")
        self.assertEqual(runtime.get_task(task["task_id"])["state"], "building")

    def test_invalid_approval_wait_fails_without_mutating_task_metadata(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        task = runtime.create_or_get_task("local-test", "invalid-wait", "Invalid wait proof")["task"]
        with self.assertRaises(TaskRuntimeError):
            runtime.await_approval(task["task_id"], "must not be recorded")
        unchanged = runtime.get_task(task["task_id"])
        self.assertEqual(unchanged["state"], "received")
        self.assertEqual(unchanged["metadata"], {})
        self.assertEqual([event["event_type"] for event in runtime.list_events(task["task_id"])], ["task.created"])

    def test_approval_wait_blocks_consequential_action_until_approval(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        task = runtime.create_or_get_task("local-test", "approval-key", "Approval proof")["task"]
        runtime.transition(task["task_id"], "briefing", "brief")
        runtime.transition(task["task_id"], "ready_to_build", "ready")
        runtime.transition(task["task_id"], "building", "build")
        runtime.transition(task["task_id"], "verifying", "verified")
        premature = runtime.attempt_action(task["task_id"], "send_message", consequential=True)
        self.assertEqual(premature, {"status": "blocked", "reason": "state_not_authorized", "action": "send_message"})
        runtime.await_approval(task["task_id"], "real recipient send")
        blocked = runtime.attempt_action(task["task_id"], "send_message", consequential=True)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["reason"], "awaiting_approval")
        runtime.approve(task["task_id"], "test-approver")
        allowed = runtime.attempt_action(task["task_id"], "send_message", consequential=True)
        self.assertEqual(allowed["status"], "allowed")
        self.assertEqual(runtime.get_task(task["task_id"])["state"], "shipping")

    def test_child_task_retains_parent_lineage(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        parent = runtime.create_or_get_task("local-test", "parent", "Parent")["task"]
        child = runtime.create_child_task(parent["task_id"], "local-test", "child", "Child")
        self.assertEqual(child["parent_task_id"], parent["task_id"])
        self.assertEqual(runtime.get_task(child["task_id"])["parent_task_id"], parent["task_id"])

    def test_json_ledger_import_is_read_only_and_creates_inspectable_legacy_task(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        source = Path(tmp.name) / "legacy-ledger.json"
        source.write_text(json.dumps({"version": 1, "tasks": {
            "legacy-001": {"task_id": "legacy-001", "title": "Legacy task", "status": "completed", "origin": "test"}
        }}))
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        summary = runtime.import_json_ledger(source, agent_id="local-test")
        after = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual(summary, {"imported": 1, "skipped": 0})
        imported = runtime.get_task("legacy-001")
        self.assertEqual(imported["state"], "completed")
        self.assertEqual(imported["metadata"]["legacy_import"], True)

    def test_import_ledger_cli_returns_parseable_idempotent_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "runtime.sqlite3"
            ledger = root / "legacy-ledger.json"
            ledger.write_text(json.dumps({"version": 1, "tasks": {
                "legacy-cli-001": {
                    "task_id": "legacy-cli-001",
                    "title": "CLI import proof",
                    "status": "completed",
                }
            }}), encoding="utf-8")
            command = [
                sys.executable, str(MODULE_PATH), "import-ledger",
                "--db", str(db), "--ledger", str(ledger), "--agent", "local-test",
            ]
            first = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            second = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout), {"imported": 1, "skipped": 0})
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout), {"imported": 0, "skipped": 1})

    def test_import_ledger_cli_reports_stable_errors_without_tracebacks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "runtime.sqlite3"
            malformed = root / "malformed-ledger.json"
            malformed.write_text("{not valid json", encoding="utf-8")
            invalid_shape = root / "invalid-shape-ledger.json"
            invalid_shape.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            for ledger, expected_error in (
                (malformed, "invalid legacy ledger"),
                (invalid_shape, "legacy ledger tasks must be an object"),
            ):
                completed = subprocess.run(
                    [
                        sys.executable, str(MODULE_PATH), "import-ledger",
                        "--db", str(db), "--ledger", str(ledger), "--agent", "local-test",
                    ],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertEqual(completed.stderr, f"error: {expected_error}\n")
                self.assertNotIn("Traceback", completed.stderr)

    def test_import_ledger_cli_normalizes_invalid_utf8_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "runtime.sqlite3"
            ledger = root / "invalid-utf8-ledger.json"
            ledger.write_bytes(b"\xff\xfe")
            completed = subprocess.run(
                [
                    sys.executable, str(MODULE_PATH), "import-ledger",
                    "--db", str(db), "--ledger", str(ledger), "--agent", "local-test",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "error: invalid legacy ledger\n")
        self.assertNotIn("Traceback", completed.stderr)

    def test_malformed_json_ledger_fails_closed_with_stable_error_and_no_mutation(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        source = Path(tmp.name) / "malformed-ledger.json"
        source.write_text("{not valid json", encoding="utf-8")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(TaskRuntimeError, r"^invalid legacy ledger$"):
            runtime.import_json_ledger(source, agent_id="local-test")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)

    def test_invalid_ledger_shape_fails_closed_with_stable_error_and_no_mutation(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        source = Path(tmp.name) / "invalid-shape-ledger.json"
        source.write_text(json.dumps({"version": 1, "tasks": []}), encoding="utf-8")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(TaskRuntimeError, r"^legacy ledger tasks must be an object$"):
            runtime.import_json_ledger(source, agent_id="local-test")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)

    def test_nonexistent_parent_fails_closed_without_creating_child_or_event(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        with self.assertRaisesRegex(TaskRuntimeError, r"^unknown task: missing-parent$"):
            runtime.create_child_task("missing-parent", "local-test", "orphan-child", "Orphan child")
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
        self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)

    def test_lock_holder_readiness_failure_is_bounded_and_diagnostic(self) -> None:
        holder = subprocess.Popen(
            [sys.executable, "-c", "import sys; print('startup failure', file=sys.stderr)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            started = time.monotonic()
            with self.assertRaisesRegex(AssertionError, r"lock holder readiness failed.*startup failure"):
                wait_for_lock_holder_ready(holder, timeout=0.2)
            self.assertLess(time.monotonic() - started, 1.0)
        finally:
            holder.wait(timeout=5)
            if holder.stdout is not None:
                holder.stdout.close()
            if holder.stderr is not None:
                holder.stderr.close()

    def test_process_held_sqlite_lock_retries_with_bounded_stable_busy_error(self) -> None:
        """A separate process holds a write lock; the runtime must fail predictably."""
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "runtime.sqlite3"
            runtime = TaskRuntime(db)
            self.addCleanup(runtime.close)
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sqlite3, sys; "
                        "connection = sqlite3.connect(sys.argv[1]); "
                        "connection.execute('BEGIN IMMEDIATE'); "
                        "print('locked', flush=True); "
                        "sys.stdin.readline(); "
                        "connection.rollback(); connection.close()"
                    ),
                    str(db),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                assert holder.stdout is not None
                assert holder.stderr is not None
                wait_for_lock_holder_ready(holder)
                started = time.monotonic()
                with self.assertRaisesRegex(TaskRuntimeError, r"^database busy after 3 retries$"):
                    runtime.create_or_get_task("local-test", "busy-key", "Busy policy proof")
                self.assertLess(time.monotonic() - started, 1.0)
                self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
                self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)
            finally:
                if holder.stdin is not None:
                    holder.stdin.close()
                holder.wait(timeout=5)
                if holder.stdout is not None:
                    holder.stdout.close()
                if holder.stderr is not None:
                    holder.stderr.close()
            created = runtime.create_or_get_task("local-test", "busy-key", "Busy policy proof")
            self.assertTrue(created["created"])
            self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)
            self.assertEqual(runtime.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)

    def test_transition_retries_with_bounded_stable_busy_error(self) -> None:
        """A held write lock must not expose a raw SQLite error from transition."""
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "runtime.sqlite3"
            runtime = TaskRuntime(db)
            self.addCleanup(runtime.close)
            task = runtime.create_or_get_task("local-test", "transition-busy-key", "Transition busy policy proof")["task"]
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sqlite3, sys; "
                        "connection = sqlite3.connect(sys.argv[1]); "
                        "connection.execute('BEGIN IMMEDIATE'); "
                        "print('locked', flush=True); "
                        "sys.stdin.readline(); "
                        "connection.rollback(); connection.close()"
                    ),
                    str(db),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                wait_for_lock_holder_ready(holder)
                started = time.monotonic()
                with self.assertRaisesRegex(TaskRuntimeError, r"^database busy after 3 retries$"):
                    runtime.transition(task["task_id"], "briefing", "must fail closed while locked")
                self.assertLess(time.monotonic() - started, 1.0)
                self.assertEqual(runtime.get_task(task["task_id"])["state"], "received")
                self.assertEqual(len(runtime.list_events(task["task_id"])), 1)
            finally:
                if holder.stdin is not None:
                    holder.stdin.close()
                holder.wait(timeout=5)
                if holder.stdout is not None:
                    holder.stdout.close()
                if holder.stderr is not None:
                    holder.stderr.close()
            self.assertEqual(runtime.transition(task["task_id"], "briefing", "lock released")["state"], "briefing")

    def test_dry_run_has_no_external_side_effects_and_proves_core_lifecycle(self) -> None:
        tmp, runtime = self.make_runtime()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(runtime.close)
        evidence = runtime.run_dry_run("local-test")
        self.assertEqual(evidence["external_side_effects"], [])
        self.assertTrue(evidence["duplicate_suppressed"])
        self.assertEqual(evidence["blocked_action"]["status"], "blocked")
        self.assertEqual(evidence["allowed_action"]["status"], "allowed")
        self.assertEqual(evidence["final_state"], "completed")

    def test_dry_run_cli_returns_parseable_evidence(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), "dry-run", "--agent", "local-test"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        evidence = json.loads(completed.stdout)
        self.assertEqual(evidence["external_side_effects"], [])
        self.assertTrue(evidence["duplicate_suppressed"])
        self.assertEqual(evidence["final_state"], "completed")


if __name__ == "__main__":
    unittest.main()
