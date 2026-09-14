#!/usr/bin/env python3
"""Secret-safe ISO-week duplicate suppression for the Brief-Me package curator."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

SKILLS = ("brief-me", "build-me", "ship-me", "maintain-me")
PACKAGE_FILES = (Path("SKILL.md"), Path("references") / "decision-and-continuation-protocol.md")
CURATOR_ID = "brief-me-package-weekly"
DEFAULT_LEASE_SECONDS = 3600


def package_hash(source_root: Path) -> str:
    digest = hashlib.sha256()
    for skill in SKILLS:
        for relative in PACKAGE_FILES:
            path = source_root / skill / relative
            digest.update(f"{skill}/{relative.as_posix()}".encode())
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


def _timestamp(value: datetime | None = None) -> datetime:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)


def _state_matches(state: dict[str, Any], period: str, sig: str) -> bool:
    return (
        state.get("curator_id") == CURATOR_ID
        and state.get("period") == period
        and state.get("signature") == sig
    )


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(state, output, sort_keys=True, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _state_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    with lock_path.open("a+") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _result(
    *,
    period: str,
    sig: str,
    decision: str,
    duplicate: bool,
    status: str,
    timestamp: str | None = None,
    claim_id: str | None = None,
    guarantees: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "curator_id": CURATOR_ID,
        "period": period,
        "signature": sig,
        "decision": decision,
        "duplicate": duplicate,
        "status": status,
        "timestamp": timestamp,
        "claim_id": claim_id,
        "side_effects": [],
        "guarantees": guarantees or [],
    }


def check(
    evidence: dict[str, Any],
    source_root: Path,
    state_path: Path,
    period: str,
    *,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    """Atomically claim a review, or report an active/completed claim.

    A claim is not completion. Call :func:`complete` only after the bounded
    review and any approved proposal/source action has finished. An abandoned
    claim becomes eligible again after its lease expires.
    """
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    sig = signature(evidence, source_root)
    current = _timestamp(now)
    with _state_lock(state_path):
        previous = _read_state(state_path)
        if previous.get("curator_id") == CURATOR_ID and previous.get("period") == period and previous.get("status") == "in_progress":
            try:
                expires = datetime.fromisoformat(str(previous["lease_expires_at"]))
            except (KeyError, TypeError, ValueError):
                expires = current
            if expires > current:
                return _result(
                    period=period,
                    sig=sig,
                    decision="review_in_progress",
                    duplicate=False,
                    status="in_progress",
                    timestamp=previous.get("timestamp"),
                )
        if _state_matches(previous, period, sig):
            if previous.get("status") == "complete":
                return _result(
                    period=period,
                    sig=sig,
                    decision="no_change",
                    duplicate=True,
                    status="complete",
                    timestamp=previous.get("timestamp"),
                    claim_id=previous.get("claim_id"),
                    guarantees=[
                        "no proposal",
                        "no source edit",
                        "no cron change",
                        "no live-project action",
                        "no duplicate delivery",
                    ],
                )

        expires = current + timedelta(seconds=lease_seconds)
        claim_id = uuid.uuid4().hex
        state = {
            "curator_id": CURATOR_ID,
            "period": period,
            "signature": sig,
            "status": "in_progress",
            "decision": "review_required",
            "timestamp": current.isoformat(),
            "lease_expires_at": expires.isoformat(),
            "claim_id": claim_id,
        }
        _write_state(state_path, state)
        return _result(
            period=period,
            sig=sig,
            decision="review_required",
            duplicate=False,
            status="in_progress",
            timestamp=state["timestamp"],
            claim_id=claim_id,
        )


def complete(
    evidence: dict[str, Any],
    source_root: Path,
    state_path: Path,
    period: str,
    *,
    decision: str,
    claim_id: str,
    proposal_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record successful completion of the current claim idempotently."""
    sig = signature(evidence, source_root)
    recorded = _timestamp(now)
    with _state_lock(state_path):
        previous = _read_state(state_path)
        if not _state_matches(previous, period, sig):
            raise ValueError("no matching curator claim")
        if previous.get("claim_id") != claim_id:
            raise ValueError("curator claim is owned by another claimant")
        if previous.get("status") == "complete":
            return _result(
                period=period,
                sig=sig,
                decision="already_complete",
                duplicate=True,
                status="complete",
                timestamp=previous.get("timestamp"),
                claim_id=claim_id,
            )
        if previous.get("status") != "in_progress":
            raise ValueError("curator claim is not in progress")
        try:
            expires = datetime.fromisoformat(str(previous["lease_expires_at"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("curator claim has no valid lease") from exc
        if expires <= recorded:
            raise ValueError("curator claim has expired")
        state = {
            "curator_id": CURATOR_ID,
            "period": period,
            "signature": sig,
            "status": "complete",
            "decision": decision,
            "timestamp": recorded.isoformat(),
            "claim_id": claim_id,
        }
        if proposal_id:
            state["proposal_id"] = proposal_id
        _write_state(state_path, state)
        return _result(
            period=period,
            sig=sig,
            decision="completed",
            duplicate=False,
            status="complete",
            timestamp=state["timestamp"],
            claim_id=claim_id,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--source-root", default=str(Path.home() / "brief-me" / "skills" / "productivity"), type=Path)
    ap.add_argument("--state-path", default=str(Path.home() / ".hermes" / "state" / "brief_me_package_curator_state.json"), type=Path)
    ap.add_argument("--period", default=date.today().strftime("%G-W%V"))
    ap.add_argument("--complete", action="store_true", help="Complete the current claim instead of claiming a review")
    ap.add_argument("--decision", default="review_required", help="Bounded review decision to persist with --complete")
    ap.add_argument("--claim-id", help="Claim identity returned by the initial check")
    ap.add_argument("--proposal-id", help="Secret-safe proposal identity to persist with --complete")
    ap.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    args = ap.parse_args()
    evidence = json.loads(args.evidence.read_text())
    if args.complete:
        if not args.claim_id:
            ap.error("--claim-id is required with --complete")
        result = complete(
            evidence,
            args.source_root,
            args.state_path,
            args.period,
            decision=args.decision,
            claim_id=args.claim_id,
            proposal_id=args.proposal_id,
        )
    else:
        result = check(evidence, args.source_root, args.state_path, args.period, lease_seconds=args.lease_seconds)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
