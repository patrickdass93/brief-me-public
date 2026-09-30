---
name: brief-me
description: Use when starting a workflow, automation, app/tool setup, integration, or agent project; grill the idea into a compact build brief, then hand off to build-me for low-risk first slices.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [briefing, grill-me, planning, n8n, automation, agent-loop]
    related_skills: [grill-me, build-me, ship-me, maintain-me, automation-platform-operations, writing-plans]
---

# Brief Me

## Overview

Use this skill to turn a vague idea into a compact, buildable brief. It combines the `grill-me` questioning style with an agentic operations loop for n8n workflows, app/tool setup, homelab projects, integrations, and agent workflows.

`brief-me` is the first skill in a package:

1. **brief-me** — ask the right questions and produce the build brief.
2. **build-me** — execute the smallest safe slice, verify, and iterate.
3. **ship-me** — release/activate/expose with final gates and rollback.
4. **maintain-me** — monitor after shipping and auto-fix simple failures when safe.

Core principle:

```text
Grill the idea → write the brief → build the smallest safe slice → verify → ship → maintain
```

## When to Use

Use this skill when an authorized user:

- starts a new project, automation, workflow, integration, or self-hosted app setup;
- says "brief me", "grill me", "turn this into a plan", or asks to build something agentically;
- wants an n8n workflow or no-code/low-code automation;
- wants a new tool/app installed on a host;
- wants multiple agents to understand and execute the same task;
- needs side-effect, approval, idempotency, or rollback boundaries before implementation.

Use this skill to define the full in-scope completion contract. The same agent continues through the planned `build-me`, `ship-me`, and (when specified) `maintain-me` phases; do not stop after producing the brief or first proof.

## Questioning Style

Follow `grill-me` behavior:

1. **Always inspect first**: Run `skill_view`, `read_file`, `session_search` to answer what you can **before** asking the user anything.
2. Ask one important question at a time. Never ask something you already found in documentation, config, memory or session history.
3. For every question, provide your recommended answer.
4. Stop asking once the first safe build slice is clear.
5. Produce a brief, not a meandering conversation transcript.
6. Do not delegate work to another agent without authorization. Same-agent continuation through the package phases is expected.

Example:

```text
Question 1 — What should trigger this workflow?
Recommended answer: Start with a Manual Trigger first, then add the real trigger after output is verified.
```

## Automatic Continuation and Approval Boundaries

The brief defines the intended end state, planned phases, acceptance checks, actions allowed without another prompt, and exact approval boundaries. Once the first safe slice is clear, continue through all planned, already-authorized low-risk phases without asking Patrick to repeat “continue.” A passing proof is a checkpoint, not completion. Pause only for the exact approval gate, a material decision outside the brief, a missing prerequisite, or a genuine blocker; continue independent approved work where possible.

Low-risk includes:

- read-only inspection;
- creating draft files/configs with placeholders;
- creating inactive n8n workflows;
- testing with fake/sample data;
- local health checks;
- safe test sends only to explicitly approved destinations.

Do **not** continue automatically into a step that would:

- activate a workflow with real side effects;
- send messages to real recipients outside an approved test destination;
- post publicly;
- delete or overwrite workflows, credentials, files, containers, or database rows;
- change DNS, Cloudflare routes, tunnels, or public exposure;
- run production database migrations/backfills;
- restart critical services;
- print, move, or store secrets.

Those require the applicable `ship-me` gate or explicit approval for the exact action. A Kanban status or MoA verdict never substitutes for that approval.

## Mobile-Readable Progress and Kanban

In chat, use short headings and vertical lists—no tables or wide code blocks. Include the essential plan without requiring Patrick to open the project Doc:

**Goal:** <one sentence>
**Plan:** <numbered phases>
**I’ll continue through:** <already-authorized low-risk work>
**I’ll pause for:** <exact approval gates or decisions>

Report at task start, each phase transition, each meaningful verified milestone, and any blocker. During active work otherwise opaque for more than 10 minutes, update at least every 10 minutes or at the next material event. Use **Phase X of Y**, **Done**, **Now**, **Next**, and **Need from Patrick**; do not invent completion estimates.

For multi-phase work, inspect the selected Kanban board before writing and reuse a matching active card. If none exists, create one concise, idempotent card with scope, acceptance checks, approval gates, current phase, next step, and only real Doc/ledger IDs or local artifact paths. Keep manual work non-dispatchable until dispatch is verified and authorized; do not assume an unassigned or `ready` task is safe from dispatch, and avoid `triage` when auto-decomposition is not intended. Update the card at meaningful milestones and blockers. Board status is a handoff/status layer, not permission. See `references/kanban-board-workflow.md` for the full procedure.


## Canonical Narrative Project Log

Create or reuse **one private, full-detail Google Doc per task at the start of work**. It is not a model-audit dump: it is the human-readable, append-only story of the work. Include ordinary operational detail; exclude only credentials, tokens, passwords, and private keys.

Record a short event when it materially changes the story:

- the user or agent makes a decision, including why;
- inspection establishes an important fact or constraint;
- a meaningful build/ship action is attempted;
- verification passes or fails;
- work is blocked, needs approval, or hands off to the next stage.

Do not log routine internal reads or duplicate noise. Each entry must state **what happened, who acted/decided, why it mattered, useful evidence or outcome, and the exact next step**. Use the event writer; it creates the Doc on the first event and returns its ID/URL:

```bash
python "${BRIEF_ME_PACKAGE_ROOT:-$HOME/brief-me}/scripts/project_log.py" \
  --task-id <stable-task-id> \
  --task-title "<task title>" \
  --stage brief-me \
  --event-type project-started \
  --actor user \
  --status in-progress \
  --summary "<what the user asked for>" \
  --decision "<decision, if one was made>" \
  --rationale "<why this is the right first direction>" \
  --next-step "<first safe action>" \
  --safe-to-log
```

Reuse its `--doc-id` for every later entry and retain it in the ledger/task handoff. Never include secrets, raw private diagnostics, or credential values. For an existing task Doc, use `--doc-id` to begin readable timeline entries without creating a duplicate document.

## Risk-Calibrated MoA Review Gate

Do not run MoA after every routine phase. At a material/high-impact transition (or when Patrick requests review), record the stage contract, complete evidence, side effects, unresolved risks, and rollback boundary in the private task record. Run the two configured reviewer evaluations in parallel, then pass the full evidence bundle and both reports to a separate aggregator. Use the agent’s private configuration to select available providers/models; shared instructions must define reviewer roles, not hard-code model names.

The aggregator compares and critiques the reviewers’ reasoning, arbitrates conflicts, checks for blind spots, preserves material disagreement, and issues the final structured verdict. `PASS` clears only that review gate; `NEEDS_REVISION` returns to the smallest failing slice; `NEEDS_APPROVAL` pauses for Patrick; `EVALUATOR_ERROR` means the review is incomplete and blocks only the gated consequential action. Continue unrelated, already-authorized low-risk work. A MoA verdict never grants Patrick’s approval for an external or destructive action.

The current `scripts/moe_stage_gate.py` runner has fixed evaluator IDs and no separate aggregation pass. Do not use its result as a MoA pass. It must be refactored and tested before it can satisfy this MoA policy; do not describe a documentation-only update as enabling the runtime. Keep both reviewer reports and the aggregator verdict visible in the private task record, without collapsing them into a score. Never commit Drive IDs, task documents, actual credentials, or secrets.


## Durable Task Ledger Guardrail

For any Hermes agent task with 3+ steps, repo/file edits, cron/job changes, background processes, deployment, remote-host work, or an explicit “build/fix/verify” request, open a durable ledger entry before starting implementation:

```bash
~/.hermes/scripts/agent_task_ledger.py start \
  --title "<task title>" \
  --origin "<chat/session/source>" \
  --safe-auto-resume \
  --allowed-resume-actions "read_only_verify,retry_timeout,repo_validation,cron_validation,final_report,recover_from_transcript" \
  --check "slice1:<acceptance check>:<verification command/output>"
```

The brief must include acceptance checks that can be copied into the ledger. Do not claim the task is complete until the final blocker passes:

```bash
~/.hermes/scripts/agent_task_ledger.py check-final --task-id <task_id>
```

If a task is ambiguous, approval-gated, destructive, secret-bearing, public-facing, or involves real recipients, either omit `--safe-auto-resume` or include blocked actions so the watchdog alerts instead of resuming.

## The Brief-Me Loop

### 1. Capture Intent

Restate the idea in one sentence:

```text
You want <system> to do <action> when <trigger> happens, producing <output>, while avoiding <forbidden side effect>.
```

### 2. Classify the Domain

Pick the execution lane:

- **n8n workflow:** later load `automation-platform-operations` and `build-me`.
- **Self-hosted app/tool:** later load `linux-remote-system-operations` and `build-me`.
- **Agent workflow:** later load `subagent-driven-development` or agent-specific skills.
- **Recurring report/admin automation:** later load relevant productivity/database/email skills.
- **Code feature:** later load `writing-plans` and `test-driven-development`.

### 2.5 Decision Expansion Gate — Conditional

Before choosing a lane or first proof, load `references/decision-and-continuation-protocol.md` when read-only inspection leaves two or more feasible paths whose safety, cost, reversibility, ownership, or rework differ materially. This creates an advisory recommendation only; it cannot execute a check, create a slice, or grant approval.

Record the chosen path, a deferred viable alternative, a revisit trigger, and the execution boundary. If the next proof is not already in the written allowed scope, return to Brief-Me or obtain the required approval.

### 3. Define the First Useful Version and Expansion Ladder

Make version one smaller than the dream, but do not treat it as the finish line. For the brief, define:

- proof milestone and observable promotion criteria;
- the one next capability worth considering after proof;
- approval and rollback boundary for that capability;
- the evidence that would select `close`, `continue`, `expand`, or `revisit`.

Then make version one smaller than the dream:

- Manual trigger before real trigger.
- Draft output before live send.
- Local-only app before public URL.
- Sample payload before production data.
- One destination before many.
- One record before a backfill.

### 4. Define Verification

Every build slice needs observable proof:

- n8n execution output;
- execution ID;
- received test message;
- database row exists and no duplicate was created;
- `curl` health check;
- container/service logs;
- screenshot or UI state;
- dry-run output.

### 5. Define Approval Gates

Explicitly list what requires approval. At minimum:

- activation;
- public exposure;
- real recipients;
- production data mutation;
- deletion;
- DNS/tunnel changes;
- secret handling.

### 6. Produce the Brief

Use this format:

```markdown
# Brief: <name>

**Intent:** <one sentence>
**Domain:** <n8n/app setup/agent workflow/etc>
**First useful version:** <smallest testable outcome>
**Proof milestone / promotion criteria:** <evidence needed before considering one next capability>
**Post-proof choice:** `close` / `continue` / `expand` / `revisit` — record per `references/decision-and-continuation-protocol.md`

**Current-state inspection needed:**
- <read-only checks>

**Trigger/input:** <manual/webhook/schedule/email/etc>
**Output/side effects:** <message/database write/app action/etc>

**Allowed low-risk next actions:**
- <things build-me can do automatically>

**Approval-gated actions:**
- <things requiring user approval>

**Build slices:**
1. <slice> — verify by <check>
2. <slice> — verify by <check>
3. <slice> — verify by <check>

**Success criteria:**
- <observable success>

**Failure behavior:**
- <fail-closed behavior>

**Idempotency / duplicate policy:**
- <event ID, hash, row key, stop behavior>

**Credentials/secrets:**
- <credential names or approved stores only; no values>

**Rollback:**
- <disable workflow/revert compose/remove tunnel/etc>

**Next skill:** `build-me` / `ship-me` / `maintain-me`
```

## n8n Brief Template

```markdown
# Brief: <Workflow Name>

**Purpose:** <one sentence>
**Build status:** Inactive until tested.
**Trigger:** Manual first, then <real trigger>.
**Input sample:** <sample payload or how to obtain it>
**Actions:** <Postgres insert, Telegram message, API call, etc>
**Idempotency key:** <message ID/event ID/hash/etc>

**Build slices:**
1. Manual Trigger + sample payload — verify execution output.
2. Transform/validate — verify expected fields.
3. Dry-run action path — verify would-send/would-write output.
4. Safe test send or test write — verify exact destination/output.
5. Activation — use `ship-me` once tests pass.

**Failure behavior:** Invalid/missing input stops quietly or logs; no spam.
**Rollback:** Disable workflow; restore JSON backup if modifying an existing workflow.
```

## App/Tool Setup Brief Template

```markdown
# Brief: <Tool/App Name>

**Purpose:** <why this tool is being set up>
**Host:** <local host / VPS / workstation / server etc>
**Access policy:** Local-only first; public/tunnel exposure only after `ship-me` gates.

**Pre-flight inspection:**
- OS/reachability
- Docker/Compose or runtime availability
- disk/memory
- existing ports/services
- existing tunnels/DNS/routes
- secret storage route

**Build slices:**
1. Minimal config with placeholders — verify files contain no secret values.
2. Start locally — verify service/container is running.
3. Health check — verify local endpoint returns success.
4. Persistence check — restart and verify data survives.
5. External access — use `ship-me` after approval or low-risk internal criteria.

**Rollback:** Stop service, restore prior config, remove route/tunnel if created.
```

## Common Pitfalls

1. **Asking for everything before building.** Ask only until the first safe slice is clear.
2. **Building without a brief.** Multi-system work needs a shared artifact.
3. **Skipping current-state inspection.** Inspect safely rather than guessing.
4. **No idempotency.** Recurring automations need duplicate protection.
5. **No failure behavior.** Define what happens when inputs or APIs fail.
6. **Activating too early.** Use `ship-me` for release/activation gates.
7. **Secret leakage.** Document credential names/locations only, never values.
8. **Overbuilding v1.** Prove the path first, then expand.

## Verification Checklist

- [ ] Intent is one sentence.
- [ ] Domain is classified.
- [ ] First useful version is smaller than the full idea.
- [ ] Current-state inspection is listed and performed where safe.
- [ ] Trigger/input and output/side effects are explicit.
- [ ] Allowed low-risk next actions are explicit.
- [ ] Approval-gated actions are explicit.
- [ ] Build slices have verification methods.
- [ ] Idempotency/duplicate behavior is defined when relevant.
- [ ] Failure behavior is fail-closed where possible.
- [ ] Secrets are assigned to approved stores only.
- [ ] Rollback path is documented.
- [ ] Next skill is named.

## One-Line Reminder

```text
Ask until the first safe slice is clear, brief it, then let build-me verify it in the real world.
```
