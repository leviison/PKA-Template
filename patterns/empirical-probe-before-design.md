# Pattern 6 — Empirical Probe Before Design

**Status:** validated (one instance — BRIEF-078, 2026-05-14; case study CASE-003)
**Author:** Leroy
**Approved by:** owner (2026-05-16, pre-approved with judgment delegated to Leroy)

---

## When to use

A design task where:

- The design depends on the **behavior of an external system** — a library callback, a third-party API, a runtime hook, an OS interface, a model's output shape.
- **Documentation describes the spirit of the interface; the system describes the letter.** Field types, payload shapes, firing cadences, transient states, and edge values are not fully captured in docs — or the version installed differs from the version documented.
- The **downstream cost of a wrong contract is silent rework**, not a clean error. Mismatched payloads parse incorrectly; missed cadence assumptions produce frozen UIs; unhandled transients corrupt state.
- The dependency is one of the predictably-fuzzy classes: **callback surfaces** (where shape and timing drift), **version-dependent APIs** (where a minor bump rewrites semantics), **streaming interfaces** (where chunking and back-pressure aren't documented), **probabilistic outputs** (where edge-case shapes are not the doc's center).

When those conditions hold, the brief — not the engineer's judgment — must require a probe as the first work item.

## When NOT to use

- **Well-typed, version-stable, CI-tested contracts.** A REST API with OpenAPI spec and integration tests does not need re-probing per consumer.
- **Internal interfaces under team control.** If your team owns both sides, change the contract; don't probe it.
- **The cost of wrong is a loud error.** A contract mismatch that throws on first call self-discloses. Probing is for the silent failure mode.
- **Time-critical hotfixes.** If a system is on fire, probe and fix simultaneously; do not gate the fix on a clean characterization.

## Shape

1. **Brief commissions probe as Step 1**, design as Step 2. The probe step has its own deliverable expectation: raw samples, captured payloads, observed cadences, version identifiers, and a written characterization summary. The probe is throwaway code; the *characterization* is the durable artifact.

2. **Probe runs against realistic input**, not a toy unit test. The behavior that matters is the behavior the system exhibits at production load, with production-shaped inputs. Toy probes characterize toy behavior.

3. **Probe captures shape AND cadence AND edge values.** Not just "what does the callback emit" but "how many times, at what intervals, in what order, with what variance." Cadence is usually the most surprising dimension and the one docs cover least.

4. **Design is built against the characterization**, not the documentation. The characterization document is the design's authoritative reference; doc citations are supporting, not load-bearing.

5. **The characterization becomes part of the deliverable** so downstream consumers (the engineer building against the contract, the agent doing the integration, the reviewer auditing the design) can audit the basis on which the design was made. Surface the raw evidence, not just the conclusions.

6. **Edge cases observed in the probe are pre-named in the contract.** If the probe surfaced `total=0` boundary events or `percent > 100` overflow or version-dependent type polymorphism, the contract handles them by spec, not by accident.

## What protects against failure

- **Brief framing is load-bearing.** If the brief says "design the contract for X" without naming a probe step, even probe-by-instinct engineers will often skip it under time pressure. The brief is the only place to commit the probe to scope.
- **Probe runs in target environment, not assumed environment.** Library version, runtime version, OS, GPU model — characterize what's actually installed, not what the docs assume.
- **Characterization is captured in writing**, not just held in the engineer's head. The next engineer / next session / next agent invocation needs the artifact, not the memory.
- **Design step explicitly references the characterization**, citing specific findings. Generic appeals to "the probe found X" are not enough; the design must show its work.
- **Verification at integration time uses real upstream**, not mocks. The probe established the truth; the integration validates the design against that truth.

## What the pattern does NOT protect against

(Discipline borrowed from [[audit-then-execute-structural]] — every pattern names its limits.)

**A probe characterizes the system at one moment in time, against one set of inputs.** A library upgrade between probe and integration invalidates the characterization. A different input class triggers behavior the probe didn't sample. Probes are not protection against drift over time or coverage outside the sample.

**Mitigation:** date-stamp the characterization, version-pin the dependency it characterized, and re-probe (cheap) when the dependency moves. For input-class coverage, the probe should explicitly enumerate the input classes it sampled — gaps become known unknowns, not silent assumptions.

## Validated instance

**BRIEF-078** (SSE backend for streaming progress, 2026-05-14) → case study **CASE-003** ("When the Documentation Is Not the System").

- Brief required an empirical-characterization step before any contract design.
- Probe found: installed library version was a minor bump ahead of the brief's assumption, a kwarg was sometimes a 0-d PyTorch Tensor (needed `.item()`), firing cadence was ~40 fires in one stage (front-loaded, sub-second) vs. ~114 fires in another stage (steady 380ms cadence, the dominant real-time progress signal), `total=0` events at stage boundaries, `percent > 100` overflow at batch alignment.
- Contract was designed against the characterization. Downstream frontend (BRIEF-079) consumed it overnight; integration was clean on morning verification. Both BRIEFs rated 5/5.
- Counterfactual: a contract designed against docs alone would have specified the wrong field type, assumed the wrong event count, and made no provision for the Tensor polymorphism, the stage-boundary markers, or the overflow case. The frontend would have crashed parsing the first Tensor-shaped payload; the morning would have been spent patching, not testing.

## Adjacent patterns

- **Audit-then-execute on structural surfaces** ([[audit-then-execute-structural]]) — **cousin pattern.** Both share the *"characterize the territory before committing"* instinct. Probe characterizes external systems where the source of truth is runtime behavior; audit characterizes internal artifacts where the source of truth is the file system. Probe protects against silent integration failure; audit protects against silent propagation failure. The probes and audits sometimes feed each other — an audit may surface an external-dependency surface that warrants its own probe.
- **Sequential-overnight-build** ([[sequential-overnight-build]]) — the probe pattern is the *grounding step* for upstream contracts in that pattern. PATTERN-001 already cites empirical-probe-before-design as the upstream's empirical grounding.

## Governance

Pattern proposed by Leroy 2026-05-16 (in the same session as PATTERN-005, where the owner explicitly named the cousin relationship). The owner pre-approved promotion conditional on Leroy's agreement; Leroy judged the pattern worthy on the basis of:
- one rated-5/5 instance (BRIEF-078) with full case study (CASE-003)
- an independent feedback memory capturing the same principle
- prior citation as adjacent pattern in PATTERN-001

Promoted directly to `validated` on these grounds. If new instances surface a counter-class — a case where the probe was paid for and did not earn — the pattern's *When NOT to use* section should expand before its status downgrades.

---

*Pattern #6 of N. See `/patterns/` for the full set.*
