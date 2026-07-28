#!/usr/bin/env python3
"""Append a human-readable, full-detail, secret-safe event to a task Doc.

The task Doc is an append-only narrative: each event states what happened, who
made a decision, why it mattered, the observed evidence, and the next step.
Machine markers make retries idempotent without making the human view depend on
raw JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from google_doc_stage_record import (
    GoogleDocsError,
    append_task_document,
    create_task_document,
    document_url,
    read_task_document,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "project-log-entry.v1.json"
TEMPLATE_PATH = ROOT / "templates" / "task-review-template.md"
MARKER_PATTERN = re.compile(
    r"@@BRIEF_ME_PROJECT_LOG_V1@@\s*\n(?P<record>.*?)\n@@END_BRIEF_ME_PROJECT_LOG_V1@@",
    re.DOTALL,
)
EVENT_TYPES = (
    "project-started", "decision", "inspection", "action", "verification",
    "blocker", "approval", "handoff", "summary",
)
ACTORS = ("user", "agent", "system")
STATUSES = ("planned", "in-progress", "passed", "failed", "blocked", "waiting-on-user", "complete")
STAGES = ("brief-me", "build-me", "ship-me", "maintain-me", "project")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_entry(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(load_json(SCHEMA_PATH))
    for error in sorted(validator.iter_errors(entry), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "entry"
        errors.append(f"schema:{location}: {error.message}")
    if entry.get("event_type") == "decision" and not entry.get("decision"):
        errors.append("decision events require decision")
    if entry.get("event_type") == "blocker" and not entry.get("next_step"):
        errors.append("blocker events require next_step")
    return errors


def entry_digest(entry: dict[str, Any]) -> str:
    """Fingerprint the semantic event, excluding clock and document metadata."""
    stable = {key: value for key, value in entry.items() if key not in {"recorded_at", "entry_digest", "document"}}
    body = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def parsed_entries(document_text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for match in MARKER_PATTERN.finditer(document_text):
        try:
            candidate = json.loads(match.group("record"))
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            entries.append(candidate)
    return entries


def document_has_entry_digest(document_text: str, digest: str) -> bool:
    return any(item.get("entry_digest") == digest for item in parsed_entries(document_text))


def _label(value: str) -> str:
    return value.replace("-", " ").title()


def render_entry(entry: dict[str, Any]) -> str:
    lines = [
        "",
        f"### {entry['recorded_at']} — {_label(entry['event_type'])}",
        f"**Stage:** `{entry.get('stage', 'project')}`  ",
        f"**Recorded by:** `{entry['actor']}`  ",
        f"**Status:** `{entry['status']}`",
        "",
        "**What happened:** " + entry["summary"],
    ]
    if entry.get("decision"):
        lines.extend(["", "**Decision:** " + entry["decision"]])
    if entry.get("rationale"):
        lines.extend(["", "**Why this was chosen:** " + entry["rationale"]])
    if entry.get("outcome"):
        lines.extend(["", "**Result:** " + entry["outcome"]])
    if entry.get("evidence"):
        lines.extend(["", "**Evidence:**"])
        lines.extend(f"- {evidence}" for evidence in entry["evidence"])
    if entry.get("next_step"):
        lines.extend(["", "**Next:** " + entry["next_step"]])
    lines.extend([
        "",
        "@@BRIEF_ME_PROJECT_LOG_V1@@",
        json.dumps(entry, ensure_ascii=False, sort_keys=True, indent=2),
        "@@END_BRIEF_ME_PROJECT_LOG_V1@@",
    ])
    return "\n".join(lines)


def apply_google_cli_config(config: dict[str, Any]) -> str:
    backend = str(config.get("google_cli", "auto")).lower()
    if backend not in {"auto", "gog", "gws", "hermes-api"}:
        raise ValueError("google_cli must be one of auto, gog, gws, or hermes-api")
    if backend == "auto":
        os.environ.pop("BRIEF_ME_GOOGLE_CLI", None)
    else:
        os.environ["BRIEF_ME_GOOGLE_CLI"] = backend
    return backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-title", help="Required when creating a task document")
    parser.add_argument("--doc-id", help="Existing task Doc to append")
    parser.add_argument("--folder-id", help="Folder for a new task document")
    parser.add_argument("--stage", choices=STAGES, default="project")
    parser.add_argument("--event-type", choices=EVENT_TYPES, required=True)
    parser.add_argument("--actor", choices=ACTORS, required=True)
    parser.add_argument("--status", choices=STATUSES, required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--decision")
    parser.add_argument("--rationale")
    parser.add_argument("--outcome")
    parser.add_argument("--evidence", action="append", default=[], help="Useful proof or reference; repeatable")
    parser.add_argument("--next-step")
    parser.add_argument("--recorded-at", help="UTC ISO-8601 timestamp; defaults to now")
    parser.add_argument("--config", type=Path, default=Path.home() / ".hermes" / "brief_me_stage_reviews.private.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print; do not call Google Docs")
    parser.add_argument("--safe-to-log", action="store_true", help="Confirm this entry has no credentials, tokens, passwords, or private keys")
    parser.add_argument("--redacted", dest="safe_to_log", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        entry: dict[str, Any] = {
            "schema_version": "project-log/v1",
            "task_id": args.task_id,
            "stage": args.stage,
            "event_type": args.event_type,
            "actor": args.actor,
            "status": args.status,
            "summary": args.summary,
            "safe_to_log": args.safe_to_log,
        }
        for key in ("decision", "rationale", "outcome", "next_step"):
            value = getattr(args, key)
            if value:
                entry[key] = value
        if args.evidence:
            entry["evidence"] = args.evidence
        entry["recorded_at"] = args.recorded_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        entry["entry_digest"] = entry_digest(entry)
        errors = validate_entry(entry)
        if errors:
            print(json.dumps({"decision": "NEEDS_REVISION", "validation_errors": errors}, indent=2))
            return 2

        config = load_json(args.config) if args.config.exists() else {}
        apply_google_cli_config(config)
        if args.dry_run:
            print(json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True))
            return 0

        doc_id = args.doc_id
        if not doc_id:
            folder_id = args.folder_id or config.get("drive_folder_id")
            if not folder_id:
                raise ValueError("a --doc-id, --folder-id, or configured drive_folder_id is required")
            if not args.task_title:
                raise ValueError("--task-title is required when creating a task document")
            created = create_task_document(
                str(folder_id), args.task_title, TEMPLATE_PATH,
                {"task_id": args.task_id, "task_title": args.task_title},
            )
            doc_id = created["document_id"]
        existing_document = read_task_document(doc_id)
        if not document_has_entry_digest(existing_document, entry["entry_digest"]):
            append_task_document(doc_id, render_entry(entry))
            existing_document = read_task_document(doc_id)
        if not document_has_entry_digest(existing_document, entry["entry_digest"]):
            raise GoogleDocsError("Google Doc read-back did not contain this narrative log entry")
        entry["document"] = {"id": doc_id, "url": document_url(doc_id)}
        print(json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, GoogleDocsError) as exc:
        print(json.dumps({"decision": "ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
