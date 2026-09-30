# brief-me skill package

A Hermes skill package for turning vague project ideas into verified agentic execution loops — especially for n8n workflows, no-code/low-code automations, self-hosted app/tool setup, homelab operations, and multi-agent work.

## Skills

- `brief-me` — grill the idea into a compact build brief, with approval gates and first safe slice.
- `build-me` — execute the smallest safe slice using inspect → build → run → observe → fix loops.
- `ship-me` — release/activate/expose with final verification, rollback, and side-effect gates.
- `maintain-me` — create quiet monitoring/watchdogs, auto-fix simple failures when safe, and run evidence-gated improvement reviews when the health contract allows them.

The package shares [`references/decision-and-continuation-protocol.md`](references/decision-and-continuation-protocol.md): a bounded, advisory comparison process that prevents premature convergence and requires every verified proof to record whether to close, continue, expand, or revisit. It never replaces approvals, rollback, ledgers, or risk-calibrated MoA review when required.

## Operating model

```text
brief-me → build-me → ship-me → maintain-me
```

The package translates the coding-agent loop into operational work:

```text
Vague idea → grilled questions → decision comparison → safe proof → verified run → evidence-gated continuation → safe ship → quiet maintenance + improvement review
```

## Install into Hermes

Clone this repo, then copy or symlink the skill directories into your Hermes skills folder:

```bash
mkdir -p ~/.hermes/skills/productivity
cp -R skills/productivity/brief-me ~/.hermes/skills/productivity/
cp -R skills/productivity/build-me ~/.hermes/skills/productivity/
cp -R skills/productivity/ship-me ~/.hermes/skills/productivity/
cp -R skills/productivity/maintain-me ~/.hermes/skills/productivity/
```

Start a new Hermes session after installing so the skill loader can see them.

## Use

Start with:

```text
Use brief-me. I want to build <workflow/app/tool/integration>.
```

The agent should ask one question at a time, recommend a default answer, produce a build brief, then continue through every planned, already-authorized low-risk phase without requiring Patrick to prompt it at each handoff.

## Completion and mobile-first progress

A brief is a checkpoint, not completion. It lists the planned in-scope phases and observable acceptance checks. Continue through those phases without asking Patrick to repeat “continue.” Pause only for the exact approval gate, a material decision outside the brief, a missing prerequisite, or a genuine blocker. Include `maintain-me` only when the brief calls for ongoing monitoring.

Send progress in chat at task start, each phase transition, each verified milestone, and any blocker. During active work that would otherwise be opaque for more than 10 minutes, update at least every 10 minutes or at the next meaningful event. Keep messages readable on a phone: short headings and bullets, no tables or wide code blocks. Use:

**Phase 2 of 4 — Build**
- **Done:** <verified slice>
- **Now:** <current work>
- **Next:** <next milestone>
- **Need from Patrick:** <none or exact decision>

The project Doc and ledger support the update; they do not replace it.

## Safety defaults

Low-risk actions can proceed automatically:

- read-only inspection;
- draft files/configs with placeholders;
- inactive n8n workflows;
- sample/fake data tests;
- local health checks;
- safe test sends to explicitly approved destinations.

Approval is required for public exposure, real recipients outside approved destinations, destructive changes, broad production data mutation, secrets movement/storage, DNS/tunnel changes, or critical restarts.

Use Hermes Kanban as the concise operational status and handoff layer for multi-phase work; keep the full narrative in a private project Doc and durable ledger when available, otherwise use a local `PROJECT_LOG.md` and report the access gap. Continue mobile-readable chat updates. New manual cards must be created non-dispatchable until dispatch is verified and authorized; board status never grants user approval. See [`references/kanban-board-workflow.md`](references/kanban-board-workflow.md) for task reuse, status, dependency, and dispatch safeguards.

## Risk-calibrated MoA reviews

Use model-agnostic Mixture-of-Agents (MoA) evaluation only at material or high-impact boundaries, or when Patrick requests it—not after every routine phase. Run both configured reviewer evaluations in parallel against the stage record. Then pass the full evidence bundle and both reports to a separate aggregator. The aggregator arbitrates conflicts, compares and critiques the reviewers’ reasoning, checks for blind spots, preserves unresolved disagreement, and issues the final structured verdict. Select available providers/models from each agent’s private local configuration; shared instructions must define reviewer roles, not require a vendor or model. Prefer distinct models when available and record when reviewers use the same model.

The aggregator’s `PASS` clears only that specific review gate. `NEEDS_REVISION` returns to the smallest failing slice; `NEEDS_APPROVAL` pauses for Patrick; `EVALUATOR_ERROR` means the review was incomplete and blocks only the gated consequential action. Continue unrelated, already-approved low-risk work. MoA review never substitutes for Patrick’s explicit approval.

Each workflow task has one private Google Doc as its canonical **full-detail, secret-safe project story**. It is created at the first material event—not only at a final stage gate—and it records the chronological decisions made by the authorized user and the agent, key inspection facts, attempted actions, verification results, blockers, approvals, and handoffs. Every entry answers: **what happened, who decided or acted, why it mattered, useful evidence/outcome, and what happens next.** Include ordinary operational detail; exclude only credentials, tokens, passwords, and private keys.

Use `scripts/project_log.py` to create/reuse and append idempotent human-readable events. New records use `safe_to_log: true`; previously saved `redactions_applied: true` project-log and stage-gate records remain readable and valid for backward compatibility. Configure its Drive folder and Google backend outside the repository in `~/.hermes/brief_me_stage_reviews.private.json`; start from `brief_me_stage_reviews.private.json.example`. The planned MoA stage-gate runtime appends its readable outcome to the same timeline and preserves the full evidence bundle, independent reviewer reports, aggregator verdict, and canonical machine record. The public package also retains model-specific prompt files, fixed evaluator configuration keys and sample model IDs, plus older plan/test fixtures for compatibility. These artifacts are legacy, not the approved model-agnostic reviewer selection or gate path; do not treat their output as a MoA pass. Refactor them to use each agent’s private available-model configuration before activating the MoA policy:

**Runtime implementation requirement:** the current stage-gate runner has fixed evaluator IDs and no separate aggregation pass. Do not use its result as a MoA pass. Refactor its evaluator configuration, prompts, runner, and tests before treating this MoA policy as active. The runtime must select both reviewers and aggregator from each agent’s private available-model configuration, run reviewer calls in parallel, and send their full evidence bundle to the separate aggregator. Do not publish fixed model names or imply that a documentation-only change enables MoA.

```text
schemas/stage-gate-record.v1.json
schemas/project-log-entry.v1.json
contracts/stage-contracts.v1.json
prompts/
scripts/project_log.py
scripts/moe_stage_gate.py
scripts/google_doc_stage_record.py
tests/
```

The gate runtime requires Python 3, [`jsonschema`](requirements.txt), and configured `hermes` CLI providers. For task Docs, select the authenticated backend in the private config: `gog`, `gws`, or `hermes-api`. `hermes-api` uses that target Hermes profile's own Google Workspace OAuth helper and never copies credentials between agents. Install the public Python dependency with `python -m pip install -r requirements.txt` before using the gate CLI on a new host.

The current `scripts/moe_stage_gate.py` runner validates records locally and runs its two fixed evaluator calls in parallel; it is a legacy path, not the planned model-agnostic MoA flow. Do not use its result as a MoA pass. Report `EVALUATOR_ERROR` for the formal gate until the model-agnostic pipeline, separate aggregator, and report capture are implemented. The `--help` output documents legacy CLI syntax only. The runtime is invoked from the package checkout by default (`$HOME/brief-me`); set `BRIEF_ME_PACKAGE_ROOT` when the checkout is elsewhere. Never commit Drive IDs, task documents, raw evaluator prompts, or actual credentials.

## Versioned public release and opt-in source pull

Generic runtime source can be released through a public Git tag only after the public-release preflight passes. The public repository contains code and a hash manifest only—never target routes, private configs, runtime state, task artifacts, credentials, or agent data.

A target may **opt in** to fetch a pinned tag into a versioned local source checkout. This command does not install a runtime, create a database, or activate anything:

```bash
python3 scripts/pull_package_release.py \
  --repo-url https://github.com/OWNER/REPOSITORY.git \
  --ref vX.Y.Z \
  --expected-commit <immutable-commit-sha> \
  --checkout ~/.hermes/packages/brief-me/vX.Y.Z \
  --json
```

Before public push/tag creation, run the fail-closed scan using a local external deny-term file:

```bash
python3 scripts/public_release_preflight.py \
  --repo-root . \
  --deny-terms-file ~/.hermes/brief_me_public_scan_terms.txt
```

The pull command verifies the tag commit and `release-manifest.json` before retaining the source checkout. A separate, explicitly approved installer command is still required to put any runtime into a profile root.

## Runtime bundle and read-only fleet audit

The same repository can stage the runtime alongside the four-skill package, while keeping target routes in a private config outside the repository. This is **not** an activation command:

```bash
python3 scripts/deploy_package_install.py \
  --config ~/.hermes/brief_me_package_targets.json \
  --dry-run --json
```

A later non-dry-run installation backs up the target’s existing skill directories and `runtime/task-runtime/` directory before staging:

```text
<profile-root>/runtime/task-runtime/task_runtime.py
```

### Per-target transactional boundary

An installer invocation is **transactional only within one target profile**: it stages the package, takes that target’s backups, applies the four skills and runtime, and attempts compensation from those backups if its apply fails. The structured result distinguishes a successful apply from a rollback attempt, a confirmed rollback, and an unknown/unconfirmed rollback state. Treat missing, malformed, or transport-interrupted rollback evidence as a failed, manually inspectable target state—not as restored.

A multi-target command is an ordered collection of independent target transactions. It provides **no batch/global atomicity**: a failure on one target does not undo a previously successful target, and independent later target attempts are not automatically cancelled. Review each target’s result and exact backup/manifest paths before any follow-up; use `--agent` to constrain an invocation to one approved target. A target installation remains inactive; source pull, installation, and activation are separate gated actions.

Before any install, use the read-only auditor. It reads only versions, hashes, file-presence flags, and path accessibility; it never opens private configuration contents or writes to a target:

```bash
python3 scripts/audit_runtime_readiness.py \
  --config ~/.hermes/brief_me_package_targets.json
```

The auditor distinguishes `ready_for_inactive_install`, `drift`, and `blocked`. A package-skill hash match is not a claim that a live runtime, target-owned integrations, model providers, or scheduled activation are ready.

## Local inactive Task Runtime proof

`scripts/task_runtime.py` is a standard-library-only, local proof of the durable execution contract. It does **not** invoke Hermes tools, models, networks, crons, messaging, or remote agents. It stores synthetic task state and append-only transition events in SQLite, prevents duplicate triggers using `(agent_id, idempotency_key)`, supports approval waits, records parent-child task lineage, and can import a legacy JSON ledger without changing the source file.

Run the zero-side-effect demonstration:

```bash
python3 scripts/task_runtime.py dry-run --agent local-test
```

Expected output is JSON with duplicate suppression, a blocked consequential action before approval, an allowed action after approval, a completed synthetic task, and `"external_side_effects": []`.

Import a legacy JSON ledger into a caller-selected local SQLite database without changing the source ledger:

```bash
python3 scripts/task_runtime.py import-ledger --db /tmp/task-runtime.sqlite3 \
  --ledger /path/to/legacy-ledger.json --agent local-test
```

The command emits a JSON `imported`/`skipped` summary on success. Invalid JSON, invalid UTF-8, and an invalid `tasks` shape fail closed: the CLI emits `error: <stable message>` to standard error, returns exit code `2`, and emits no traceback or partial JSON. The Python API raises `TaskRuntimeError` with the same stable messages; a missing parent fails before a child task or event is created.

SQLite connections use a 50 ms busy timeout. A recognized `database is locked` or `database is busy` error is retried at 25 ms, 50 ms, and 100 ms only; after those three retries the API/CLI reports `database busy after 3 retries`. Other database errors are not retried. This bounded local policy never dispatches an external action.

Run its deterministic tests:

```bash
python3 tests/test_task_runtime.py
```

This is a build-stage proof only. Remote installation, active watchdog/cron enablement, real ledger migration, and external effects remain `ship-me` approval-gated.

## Public-release privacy gate

This repository is designed to be publicly shareable. Never commit local fleet target files, session evidence, credentials, personal/work details, hostnames, IP addresses, or direct identifiers.

Before every GitHub upload, run the fail-closed scanner against the tracked tree and staged diff. Supply any organization-specific prohibited terms from a local file that is **not** committed:

```bash
scripts/privacy_scan.py --staged --deny-terms-file ~/.hermes/brief_me_public_scan_terms.txt
```

Before changing repository visibility or rewriting history, also scan reachable history and commit identities:

```bash
scripts/privacy_scan.py --history --deny-terms-file ~/.hermes/brief_me_public_scan_terms.txt
```

The weekly self-improvement cron must run the same staged-release scan before it commits or pushes. The ignored private target configuration and deny-terms file stay outside this repository.

## License

MIT

## Optional self-improvement cron

You can run a weekly Hermes cron to review usage of this package across one or more configured agents, then improve the skills and push updates back to this repo.

The primary support scripts are:

```bash
scripts/brief_me_usage_collect.py --repo-root /path/to/brief-me-public
scripts/curator_review_dedupe.py
```

The weekly curator uses `curator_review_dedupe.py` with a stable ISO-week and bounded evidence signature. The first invocation atomically claims the review and returns a claim ID; after the bounded review completes, record it with `--complete --claim-id <claim-id>`. An unchanged completed signature is `no_change`; a live claim is `review_in_progress`, and an interrupted claim can be reclaimed after its lease expires. The state file contains only the secret-safe signature, period, decision/proposal identity when present, claim status, and timestamps.

It collects compact, redacted skill-usage evidence, evidence-tag counts, package-integrity hashes, and bounded-improvement decision metadata. The collector compares against its own checkout when run from a checkout; a deployed copy defaults to the conventional public-checkout location. Pass `--repo-root` whenever the checkout is elsewhere so a legacy/private checkout cannot create false drift. The cron prompt should abstract any work/personal details into reusable skill improvements and avoid committing sensitive content.

Treat the GitHub `main` branch as the **release record**. On every review, verify the local checkout and `origin/main` agree. If an installed package copy differs from the checkout, inspect that drift before overwriting it: publish a validated, generic improvement to GitHub first, then deploy the resulting commit to configured targets. Never create empty commits; a genuine no-change run should still report that GitHub is current.

Additional helpers:

- `scripts/verify_package_install.py` — verifies installed package hashes against the repo manifest. Public-safe by default; pass a private target config outside the repo for multi-agent fleets.
- `scripts/deploy_package_install.py` — creates per-target backups and deploys the four package skills from the local checkout to trusted configured targets; use it only after the source commit is pushed.
- `scripts/create_improvement_proposal.py` — writes proposal-mode output under `proposals/` when evidence is ambiguous or policy-changing.
- `scripts/append_review_log.py` — appends a local machine-readable JSONL review record, normally under `~/.hermes/state/brief_me_package_reviews.jsonl`.

Recommended policy: **bounded auto-improvement**.

- Auto-fix package drift when configured targets are missing package files or hashes do not match the repo manifest.
- Auto-commit only small, validated skill-text changes when there is concrete reusable evidence: repeated corrections, clear misuse, missing approval/verification gates, drift, or broken instructions.
- Create a proposal instead of editing when evidence is ambiguous, one-off, structural, or would change delivery/model/tool/secret-handling policy.
- Default to `no_change` when the week has usage but no concrete reusable improvement.

See `examples/self-improvement-cron.md` for the recommended cron prompt structure.
