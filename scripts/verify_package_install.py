#!/usr/bin/env python3
"""Verify the brief-me skill package and Task Runtime against a source manifest.

This helper reads target files only. Private target routing belongs in a JSON file
outside the repository.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SKILLS = ["brief-me", "build-me", "ship-me", "maintain-me"]
REFERENCE_RELATIVE = Path("references") / "decision-and-continuation-protocol.md"
RUNTIME_RELATIVE = Path("runtime") / "task-runtime" / "task_runtime.py"

REMOTE_CHECK = r'''
import argparse, hashlib, json
from pathlib import Path
SKILLS = ["brief-me", "build-me", "ship-me", "maintain-me"]
REFERENCE_RELATIVE = Path('references') / 'decision-and-continuation-protocol.md'
def sha(path):
    try: return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception: return None
ap = argparse.ArgumentParser()
ap.add_argument('--agent', required=True)
ap.add_argument('--profile-root', default='~/.hermes')
ap.add_argument('--expected-json', required=True)
a = ap.parse_args(); expected = json.loads(a.expected_json); root = Path(a.profile_root).expanduser()
skills = {}
all_skills_ok = True
for name in SKILLS:
    p = root / 'skills' / 'productivity' / name / 'SKILL.md'; digest = sha(p)
    reference = root / 'skills' / 'productivity' / name / REFERENCE_RELATIVE; reference_digest = sha(reference)
    expected_skill = expected['skills'].get(name, {}); expected_skill = {'skill': expected_skill} if isinstance(expected_skill, str) else expected_skill
    skill_ok = p.is_file() and digest == expected_skill.get('skill')
    reference_ok = reference.is_file() and reference_digest == expected_skill.get('reference')
    ok = skill_ok and reference_ok
    skills[name] = {'exists': p.is_file(), 'bytes': p.stat().st_size if p.is_file() else 0, 'sha256': digest, 'expected_sha256': expected_skill.get('skill'), 'reference_exists': reference.is_file(), 'reference_bytes': reference.stat().st_size if reference.is_file() else 0, 'reference_sha256': reference_digest, 'expected_reference_sha256': expected_skill.get('reference'), 'ok': ok}
    all_skills_ok = all_skills_ok and ok
p = root / 'runtime' / 'task-runtime' / 'task_runtime.py'; digest = sha(p)
runtime = {'exists': p.is_file(), 'bytes': p.stat().st_size if p.is_file() else 0, 'sha256': digest, 'expected_sha256': expected['runtime'], 'ok': p.is_file() and digest == expected['runtime']}
print(json.dumps({'agent': a.agent, 'profile_root': str(root), 'skills': skills, 'runtime': runtime, 'all_skills_ok': all_skills_ok, 'all_ok': all_skills_ok and runtime['ok']}))
'''


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def repo_manifest(repo_root: Path) -> dict[str, Any]:
    base = repo_root / "skills" / "productivity"
    return {"skills": {name: {"skill": sha256(base / name / "SKILL.md"), "reference": sha256(base / name / REFERENCE_RELATIVE)} for name in SKILLS}, "runtime": sha256(repo_root / "scripts" / "task_runtime.py")}


def check_local(agent: str, profile_root: str, expected: dict[str, Any]) -> dict[str, Any]:
    root = Path(profile_root).expanduser()
    base = root / "skills" / "productivity"
    skills: dict[str, Any] = {}
    all_skills_ok = True
    for name in SKILLS:
        path = base / name / "SKILL.md"
        digest = sha256(path)
        reference = base / name / REFERENCE_RELATIVE
        reference_digest = sha256(reference)
        expected_skill = expected["skills"].get(name, {}); expected_skill = {"skill": expected_skill} if isinstance(expected_skill, str) else expected_skill
        skill_ok = path.is_file() and digest == expected_skill.get("skill")
        reference_ok = reference.is_file() and reference_digest == expected_skill.get("reference")
        ok = skill_ok and reference_ok
        skills[name] = {"exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0, "sha256": digest, "expected_sha256": expected_skill.get("skill"), "reference_exists": reference.is_file(), "reference_bytes": reference.stat().st_size if reference.is_file() else 0, "reference_sha256": reference_digest, "expected_reference_sha256": expected_skill.get("reference"), "ok": ok}
        all_skills_ok = all_skills_ok and ok
    runtime_path = root / RUNTIME_RELATIVE
    runtime_digest = sha256(runtime_path)
    runtime = {"exists": runtime_path.is_file(), "bytes": runtime_path.stat().st_size if runtime_path.is_file() else 0, "sha256": runtime_digest, "expected_sha256": expected["runtime"], "ok": runtime_path.is_file() and runtime_digest == expected["runtime"]}
    return {"agent": agent, "profile_root": str(root), "skills": skills, "runtime": runtime, "all_skills_ok": all_skills_ok, "all_ok": all_skills_ok and runtime["ok"]}


def check_ssh(target: dict[str, Any], expected: dict[str, Any], timeout: int) -> dict[str, Any]:
    agent, ssh_target = str(target["agent"]), str(target["ssh_target"])
    profile_root, mode = str(target.get("profile_root") or "~/.hermes"), str(target.get("mode") or "posix")
    encoded = base64.b64encode(REMOTE_CHECK.encode()).decode()
    py = f"import base64; exec(base64.b64decode({encoded!r}))"
    parts = ["python3", "-c", py, "--agent", agent, "--profile-root", profile_root, "--expected-json", json.dumps(expected, separators=(",", ":"))]
    posix = shlex.join(parts)
    command = "wsl.exe sh -lc " + shlex.quote(posix) if mode == "wsl" else posix
    ssh_args = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10"]
    if target.get("ssh_port"):
        ssh_args.extend(["-p", str(target["ssh_port"])])
    process = subprocess.run(ssh_args + [ssh_target, command], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if process.returncode:
        return {"agent": agent, "all_ok": False, "error": (process.stderr or process.stdout)[-1200:] or f"ssh exit {process.returncode}"}
    try:
        return json.loads(process.stdout)
    except Exception as exc:
        return {"agent": agent, "all_ok": False, "error": f"json parse failed: {type(exc).__name__}: {exc}"}


def load_targets(args: argparse.Namespace) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    if args.config:
        data = json.loads(Path(args.config).expanduser().read_text())
        targets.extend(data.get("targets", data if isinstance(data, list) else []))
    for item in args.target_json or []:
        targets.append(json.loads(item))
    return targets or [{"agent": args.local_agent_name, "type": "local", "profile_root": args.local_profile_root}]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(Path.home() / "brief-me"))
    parser.add_argument("--config")
    parser.add_argument("--target-json", action="append")
    parser.add_argument("--local-agent-name", default="local")
    parser.add_argument("--local-profile-root", default="~/.hermes")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-fail", action="store_true")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    repo = Path(args.repo_root).expanduser(); expected = repo_manifest(repo)
    if not expected["runtime"] or any(not item for item in expected["skills"].values()):
        print(json.dumps({"all_ok": False, "error": "missing repo package sources"}), file=sys.stderr); return 2
    checked = [check_local(str(t.get("agent", "local")), str(t.get("profile_root", "~/.hermes")), expected) if t.get("type", "local") == "local" else check_ssh(t, expected, args.timeout) for t in load_targets(args)]
    result = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "repo_root": str(repo), "expected": expected, "targets": checked, "all_ok": all(bool(t.get("all_ok")) for t in checked)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (result["all_ok"] or args.no_fail) else 2


if __name__ == "__main__":
    raise SystemExit(main())
