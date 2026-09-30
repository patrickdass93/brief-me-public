# Kanban Board Workflow

Use Hermes Kanban as the concise operational status and handoff layer. Prefer a private project Doc and durable ledger for the full narrative; if either is unavailable, keep a local `PROJECT_LOG.md` beside the work artifacts and record the access gap without inventing a Doc or ledger ID. The card should point to the records that actually exist. Chat progress remains necessary and should stay phone-readable.

## Start and scope

1. Check which board and Kanban tools are available in the current profile/platform. Read the board before writing; reuse a matching non-archived task rather than creating a duplicate. Never switch boards or edit unrelated cards silently.
2. If no matching task exists, create one concise card with an idempotency key. Include the goal, bounded scope, acceptance checks, approval gates, current phase/next step, links or IDs for any project Doc/ledger that actually exists, and local log/artifact paths where a Doc or ledger is unavailable. Do not invent IDs or put credentials, tokens, or private diagnostics in card text.
3. Keep a task in `triage` only when intake/decomposition is intended and the configured dispatcher behavior is understood. Hermes Kanban can auto-decompose triage tasks; do not use `triage` as a harmless parking state. For manual orchestration where dispatch is intentionally withheld, create with `--initial-status blocked` and immediately record why; do not assume an unassigned task is non-dispatchable. The CLI may create it as `ready`, so treat a `ready` task as potentially dispatchable until verified.
4. Create separate cards only for meaningful, independently actionable deliverables or phases. Do not create a card for every small step.

## Status and dependency rules

- `triage` — intake that still needs specification or deliberate decomposition; may trigger configured automation.
- `todo` — intentionally not ready for dispatch, for example because a prerequisite is still open; do not assume a new unassigned card will land here.
- `ready` — eligible for dispatch. A CLI create may start `ready` even with no assignee. Treat it as potentially dispatchable until verified. Use only after the worker path and dispatch scope are verified and authorized.
- `running` — a worker is actively executing the task.
- `blocked` — exact human input, approval, capability, or prerequisite is required. Add a comment naming the blocked action and what would unblock it. Do not use `blocked` for work merely awaiting review.
- `review` — implementation is complete and awaiting review; it is not a blocker.
- `done` — mark only after the acceptance checks pass and the result is verified.

A parent-to-child link is a real dependency: the dispatcher holds the child until the parent is complete. Do not use links merely to group project cards, and do not link a support task to the blocked task it is meant to unblock. Use the same board/project and explicit card references for grouping instead.

## During execution and handoff

Update the card at meaningful phase changes, verified milestones, approval pauses, and blockers. Keep comments factual: what changed, verification evidence, current status, next action, and any exact approval needed. Update the card and chat; neither replaces the other.

A Kanban status is not user authorization. `ready`, `review`, or `done` never grants permission to publish, contact real recipients, launch a live campaign, make a destructive change, or cross another approval boundary. Obtain the required explicit approval for the exact action separately.

Do not trigger decomposition or dispatch merely to make the board look active. For manual work, create the card in a non-dispatchable state (`--initial-status blocked`) and comment that dispatch is intentionally withheld; only make it dispatchable after the worker profile, task scope, and dispatch path have been checked and authorized. If Kanban tools are unavailable in the current platform, use the CLI only when it is available in the authorized local environment; otherwise state the access gap, do not claim a board update, and continue only the already-authorized work that does not depend on the board.

When handing work to another phase or agent, pass the Kanban task ID alongside the stable task ID, project Doc ID, and ledger ID. Continue concise mobile-readable progress updates in chat.

## Hermes references

See the [Hermes Kanban guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban) for current status, dispatcher, and dependency behavior. Tool availability is profile/platform-specific; a toolset change takes effect in a new session.
