# Decision and Continuation Protocol

Use this shared protocol to avoid two failure modes: converging on a familiar design before comparing credible alternatives, and treating a first safe proof as the end of a useful project.

## Boundary

The protocol is **advisory only**. It creates a recommendation and a record; it never performs a check, creates a slice, activates a cron, changes a live system, or grants approval. Execution remains governed by the written stage scope, allowed actions, approval gates, and the normal Build-Me / Ship-Me rules.

Run it only after read-only inspection leaves at least two **feasible** paths. A path is feasible only when it meets hard constraints and has a specific, safe discriminating proof. Use it when the paths differ materially in safety, cost, reversibility, ownership, or expected rework. Do not use it for a lookup, a known-root-cause fix, a hard safety rule, routine healthy polling, or an already-approved single path.

## Bounded decision expansion

Use at most three isolated lenses and at most two options per lens:

1. **Safe and operable** — blast radius, rollback, observability, privacy, credential/data boundary.
2. **Smallest evidence-producing proof** — which proof most directly removes the load-bearing uncertainty?
3. **Durable ownership** — maintenance burden, host/agent ownership, portability, lifecycle, and cost.

Converge into this record:

| Path / hypothesis | Why it fits | Key risk | Safe discriminating proof |
|---|---|---|---|

Then record:

```markdown
**Recommendation:** <path; advisory only>
**Deferred viable alternative:** <path>
**Revisit trigger:** <observable evidence or threshold>
**Execution boundary:** <already-approved slice / return to Brief-Me / Ship-Me / explicit approval>
```

A check or next-capability slice may run only if it was already inside the current written scope, listed as an allowed action, and not approval-gated. Otherwise write a proposal or return to Brief-Me.

## Mandatory post-proof record

After **every** verified proof, including a terminal one, write a concise ledger and project-Doc event with all fields below:

```markdown
**proof_id:** <stable slice/proof ID>
**choice:** close / continue / expand / revisit
**evidence_refs:** <real command, execution ID, test, or observation>
**next_verification:** <next check; for close/revisit use an explicit terminal value>
**rollback_boundary:** <what can be reverted; or "no further change made">
**approval_boundary:** <none / exact action needing approval>
**ledger_event:** <task ledger check/event reference>
**project_log_event:** <Doc event/digest/reference>
**deferred_alternative:** <credible alternative or none>
**revisit_trigger:** <observable threshold/date/failure pattern>
```

`continue` means another already-approved slice is needed; begin the next planned slice without asking Patrick to repeat “continue.” `expand` means the proof met its promotion criteria and one additional, bounded capability is proposed; it does **not** authorize execution unless already included in the approved scope. `close` means the full stated completion criteria are met. `revisit` means the evidence invalidated the current path or a scope/approval boundary blocks progress.

## User-visible progress

At task start, each planned phase transition, each meaningful verified proof, and each blocker, send a concise chat update. During active work otherwise opaque for more than 10 minutes, update at least every 10 minutes or at the next material event. State the phase, what is complete, what is in progress, the next milestone, and the latest evidence. Use narrow mobile-friendly formatting: short headings and bullets, not tables or wide code blocks. The project Doc and ledger are supporting records, not substitutes for this status.

## Stage use

- **Brief-Me:** compare credible lanes before choosing v1; define proof milestone, promotion criteria, next capability, approval boundary, and rollback.
- **Build-Me:** use hypothesis expansion only after ambiguous/repeated failure; execute one already-approved discriminating check or slice; always write the post-proof record.
- **Ship-Me:** use a three-lens Release Challenge for consequential releases before the existing approval, rollback, and risk-calibrated MoA gates. It cannot authorize shipping.
- **Maintain-Me:** use unknown-incident hypotheses only after a bounded safe recovery fails. Use improvement reviews only when a health contract explicitly names cadence, owner, alert route, stable project ID, period-key dedupe, disable path, and no-side-effect boundary.
- **Grill-Me:** ask the one question that most reduces the remaining decision branches; keep the one-question-at-a-time interaction.

## Recurring package improvement owner

The weekly Brief-Me package curator is the one package-level recurring review owner. It may use secret-safe, bounded usage evidence to propose or apply small generic package improvements under its existing public-release policy. It must not create recursive crons, touch live projects, replace evaluator verdicts, or mutate package targets directly outside the committed-release deployment path.

Agent self-evolution workflows may submit local, redacted evidence or proposals. They must not directly edit the generic package source or fleet-installed Brief-Me package copies.

## Idempotency

A recurring review uses stable curator identity + ISO week + SHA-256 of a canonical bounded evidence summary and current source package hash. The first invocation atomically claims the review and returns `review_required` plus a unique claim ID. While that claim is unexpired, another invocation returns `review_in_progress` and must not start a second review. After the bounded review and any approved follow-up complete, the claimant records completion; an unchanged completed signature then returns `no_change`: no duplicate proposal, source edit, cron update, live-project action, or repeat delivery. An interrupted claim expires after its lease and can be reclaimed. Persist only the secret-safe signature, period, decision/proposal identity when present, claim status, claim ID, lease expiry, and timestamps under the local Hermes state directory; use an atomic lock and replacement write.

When MoA is required, keep the complete evidence bundle and both parallel reviewer reports separate and append-only, then pass them to a separate aggregator that arbitrates conflicts, compares and critiques reasoning, checks for blind spots, preserves disagreement, and issues the final verdict. The curator and implementing stage cannot bypass or self-approve the verdict. Routine low-risk proofs use their normal verification without MoA.
