#!/usr/bin/env python3
"""Secret-safe ISO-week duplicate suppression for the Brief-Me package curator."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

SKILLS = ("brief-me", "build-me", "ship-me", "maintain-me")
CURATOR_ID = "brief-me-package-weekly"


def package_hash(source_root: Path) -> str:
    digest = hashlib.sha256()
    for skill in SKILLS:
        path = source_root / skill / "SKILL.md"
        digest.update(skill.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.exists() else b"MISSING")
        digest.update(b"\0")
    return digest.hexdigest()


def bounded_summary(raw: dict[str, Any]) -> dict[str, Any]:
    decision = raw.get("improvement_decision_input", {})
    integrity = raw.get("package_integrity", {})
    return {
        "evidence_tag_totals": decision.get("evidence_tag_totals", {}),
        "collection_errors": decision.get("collection_errors", []),
        "package_integrity_ok": decision.get("package_integrity_ok"),
        "integrity": integrity.get("by_agent", {}),
    }


def signature(raw: dict[str, Any], source_root: Path) -> str:
    payload = {"evidence": bounded_summary(raw), "package_hash": package_hash(source_root)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check(evidence: dict[str, Any], source_root: Path, state_path: Path, period: str) -> dict[str, Any]:
    sig = signature(evidence, source_root)
    previous: dict[str, Any] = {}
    if state_path.exists():
        previous = json.loads(state_path.read_text())
    duplicate = previous.get("curator_id") == CURATOR_ID and previous.get("period") == period and previous.get("signature") == sig
    result = {
        "curator_id": CURATOR_ID,
        "period": period,
        "signature": sig,
        "decision": "no_change" if duplicate else "review_required",
        "duplicate": duplicate,
        "side_effects": [],
        "guarantees": ["no proposal", "no source edit", "no cron change", "no live-project action", "no duplicate delivery"] if duplicate else [],
    }
    if not duplicate:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({**result, "proposal_id": None}, sort_keys=True, indent=2) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--source-root", default=str(Path.home() / "brief-me" / "skills" / "productivity"), type=Path)
    ap.add_argument("--state-path", default=str(Path.home() / ".hermes" / "state" / "brief_me_package_curator_state.json"), type=Path)
    ap.add_argument("--period", default=date.today().strftime("%G-W%V"))
    args = ap.parse_args()
    print(json.dumps(check(json.loads(args.evidence.read_text()), args.source_root, args.state_path, args.period), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
