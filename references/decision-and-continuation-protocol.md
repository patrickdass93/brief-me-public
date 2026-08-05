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

`continue` means another already-approved slice is needed. `expand` means the proof met its promotion criteria and one additional, bounded capability is proposed; it does **not** authorize execution. `close` means the stated success criteria are met. `revisit` means the evidence invalidated the current path or a scope/approval boundary blocks progress.

## Stage use

- **Brief-Me:** compare credible lanes before choosing v1; define proof milestone, promotion criteria, next capability, approval boundary, and rollback.
- **Build-Me:** use hypothesis expansion only after ambiguous/repeated failure; execute one already-approved discriminating check or slice; always write the post-proof record.
- **Ship-Me:** use a three-lens Release Challenge for consequential releases before the existing approval, rollback, and independent MoE gates. It cannot authorize shipping.
- **Maintain-Me:** use unknown-incident hypotheses only after a bounded safe recovery fails. Use improvement reviews only when a health contract explicitly names cadence, owner, alert route, stable project ID, period-key dedupe, disable path, and no-side-effect boundary.
- **Grill-Me:** ask the one question that most reduces the remaining decision branches; keep the one-question-at-a-time interaction.

## Recurring package improvement owner

The weekly Brief-Me package curator is the one package-level recurring review owner. It may use secret-safe, bounded usage evidence to propose or apply small generic package improvements under its existing public-release policy. It must not create recursive crons, touch live projects, replace evaluator verdicts, or mutate package targets directly outside the committed-release deployment path.

Agent self-evolution workflows may submit local, redacted evidence or proposals. They must not directly edit the generic package source or fleet-installed Brief-Me package copies.

## Idempotency

A recurring review uses stable curator identity + ISO week + SHA-256 of a canonical bounded evidence summary and current source package hash. If the signature is unchanged for that period, it returns `no_change`: no duplicate proposal, source edit, cron update, live-project action, or repeat delivery. Persist only the secret-safe signature, period, decision/proposal identity, and timestamp under the local Hermes state directory.

Independent MoE reports remain separate, append-only mandatory stage gates. The curator and implementing stage cannot merge, replace, bypass, or self-approve their verdicts.
