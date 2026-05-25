# Pattern 1 — Sequential Overnight Build

**Status:** validated (one instance — BRIEF-078 → BRIEF-079, 2026-05-14)
**Author:** Leroy
**Approved by:** owner (2026-05-15)

---

## When to use

A multi-disciplinary task where:

- There is a clear **upstream/downstream split** — one piece defines a contract, the other consumes it. (Backend defines an API; frontend consumes it. Designer publishes specs; builder implements. Researcher delivers a brief; writer drafts.)
- **Both pieces are self-testable.** The upstream can be verified against curl/probe/empirical sampling without the downstream. The downstream can be verified against the deployed upstream (or a faithfully-recreated contract surface).
- **Time pressure** — there is a "while I sleep" framing, or a sequential-across-business-days schedule is unacceptable.
- **The downstream can read** the upstream's deliverable as input rather than needing live conversation. If the design space is uncertain enough that downstream might need to push back mid-design, this pattern is wrong.

## When NOT to use

- **Tight feedback loops needed.** Genuinely uncertain design space; iteration during work is the value. Use parallel design memos with morning reconciliation instead.
- **Truly co-dependent work.** Neither piece is testable without the other already complete. Use a single combined brief or pair the agents differently.
- **Upstream contract is uncertain.** If the upstream might invent constraints the downstream needs to challenge, no overnight build — the cross-check is doing the work.

## Shape

1. **Upstream brief** specifies a *complete-deliverable* contract requirement. The deliverable must include a fully specified contract spec — every event type, every field, every edge case, every error condition. The contract spec is the handoff artifact; it must be read-once, build-against.

2. **Upstream ships, self-tests with raw output, commits, pushes.** The deliverable lands in `owners_inbox/`. Verification is captured in the deliverable as raw output (not "passed").

3. **Downstream brief** is written *after* upstream's deliverable lands, explicitly referencing it as mandatory reading. The downstream treats the contract as fixed. The brief tells the downstream to build against the *live deployed upstream*, not a mock — upstream's self-test already proved the surface is real.

4. **Downstream ships, self-tests against the live upstream, commits, pushes.** The downstream deliverable cross-references the upstream contract and documents how each edge case was handled. Anomalies surfaced during build that affect the contract are flagged in the deliverable for Leroy to decide (do not unilaterally amend the contract).

5. **Integration test happens with the owner's eyes.** Whatever cannot be self-tested — visual rendering, UX flow, real-world end-to-end — is the owner's morning task. The team builds and self-tests overnight; final human validation is asynchronous to the build.

## What protects against failure

- **The contract spec must be complete.** Vague contracts produce downstream invention. The upstream brief must require enumeration of every edge case the downstream will hit.
- **Upstream is empirically grounded.** When the contract depends on external behavior (library hooks, third-party APIs), upstream characterizes that behavior empirically before designing (see related: [[empirical-probe-before-design]]). Designing on assumption produces a contract the downstream cannot trust.
- **Downstream reads, doesn't skim.** The downstream brief makes "read the upstream deliverable" an explicit first step, not a courtesy.
- **Both pieces share the same verification standard.** Raw output captured in deliverables. No "verified, passed" — actual numbers, samples, captured streams.
- **Subagents are sized to fit.** Each agent's work should fit one subagent invocation start-to-finish. If either upstream or downstream needs splitting, the pattern is being stretched.

## What the pattern does NOT protect against

(Discipline added 2026-05-18 per `patterns/README.md` convention — every pattern names its limits so it doesn't get oversold.)

**The pattern does not enforce contract correctness, only contract completeness.** A contract that *looks* complete but was designed against documentation rather than empirical characterization will pass the handoff cleanly, and downstream will build against it cleanly. The wrong-contract failure mode is invisible until the integration test exercises an edge case the contract didn't cover. Mitigation: pair with [[empirical-probe-before-design]] when the upstream depends on external systems — the probe step is what makes the contract empirically grounded rather than documentation-grounded.

**The owner morning-integration step is the only catch for visual/UX correctness, and the pattern explicitly delegates it to the owner.** If the owner trusts the green-check and skips real exercise, regressions ship under the same pattern execution that would otherwise have caught them. Visual/UX correctness must hit a visual/UX verification surface — structural balance checks miss render bugs.

**Downstream silently inventing semantics around contract ambiguity is invisible.** The pattern says the contract must be complete; if it isn't, downstream's invention is the failure mode. The brief writer carries the burden of demanding enumerated edge cases — "no ambiguity left" is a verification gate, not an expectation.

## Validated instance

**BRIEF-078** (backend SSE for diarize progress) handed off to **BRIEF-079** (EventSource frontend) overnight 2026-05-14 → 2026-05-15.

- The upstream deliverable's contract-spec section (endpoint shapes, four event types with field-by-field schemas, five enumerated edge cases including `percent > 100`, `total === 0`, no-reconnection-protocol) was the handoff artifact.
- The downstream agent read it, built against the live deployed backend, self-tested with a captured 60-event SSE stream from a real job, integrated cleanly.
- Caught a two-consumer race during implementation (single-consumer + local buffer pattern) — surfaced by *building*, not designing; the kind of catch the pattern is designed to allow.
- A handful of minor revisits surfaced by the owner's morning integration testing — pre-existing issues, not overnight regressions.
- Both deliveries rated 5/5.

**Net outcome:** ~6 hours of agent time across two subagents, no live coordination needed, integration validated by the owner in ~10 minutes of morning testing.

## Adjacent patterns (candidates not yet validated)

- **Contract-first handoff between agents** — the principle here generalizes to non-overnight work (any time one agent's deliverable is another's input).
- **Empirical-probe-before-design** ([[empirical-probe-before-design]]) — now its own pattern (PATTERN-006, validated 2026-05-16). The upstream's empirical grounding step.
- **Multi-lens parallel review** ([[multi-lens-parallel-critique]]) — PATTERN-004, validated.

## Governance

Patterns are part of the Intent layer (alongside `CLAUDE.md` and `team/*.md`). New pattern entries require owner approval before merge. Leroy proposes; the owner accepts.

Pattern status values: `proposed` (one instance observed, awaiting approval) → `validated` (approved with at least one instance) → `deprecated` (superseded or no longer applicable).

---

*Pattern #1 of N. See `/patterns/` for the full set.*
