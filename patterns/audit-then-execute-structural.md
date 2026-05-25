# Pattern 5 — Audit-Then-Execute on Structural Surfaces

**Status:** validated (one instance — BRIEFs 115 → 116 → 117, 2026-05-16; case study CASE-006)
**Author:** Leroy
**Approved by:** owner (2026-05-16)

---

## When to use

A structural-surface task where:

- The work touches **many small surfaces** at once — files, schema columns, persona configurations, install scripts, diagrams, documentation — and the surfaces interact. Template refreshes, migration arcs, large refactors, schema cutovers, repo-to-repo syncs all qualify.
- The **map of what needs to change is not obvious from any single file.** Different surfaces are owned by different concepts (intent vs state vs ephemeral; code vs config vs docs); no one file tells you the whole story.
- **Adjacent changes interact.** Editing one surface affects what should be edited in another. A propagation pass without a map invites re-derivation under execution pressure.
- **Reversibility is moderate or low.** Edits commit. A bad propagation that lands across ten files is more expensive to unwind than to plan against.

The audit step is the *map*; the execute step works the map. Splitting them prevents the execute step from doing two jobs at once.

## When NOT to use

- **Small focused edits.** A two-file change with no cross-surface implications does not need an audit pass — the audit overhead exceeds the protection it buys.
- **Time-critical hotfixes.** When a bug is actively breaking production, audit-then-execute is too slow. Fix-then-postmortem is the right shape; the audit becomes a follow-up if the fix surfaces unknowns.
- **Greenfield work.** Nothing structural to audit yet. Use a build pattern (e.g., [[sequential-overnight-build]] for time-pressured upstream/downstream splits) instead.
- **Single-surface refactors.** Renaming a function across one codebase with grep is direct; no audit map needed.

## Shape

1. **Audit brief (Step 1).** Commission a diff-audit of the relevant structural surfaces. The deliverable must produce: a catalog of every delta found, per-delta recommendations from a fixed vocabulary (`propagate` / `skip` / `adapt` / `no-action` or a similar small set), per-delta one-line rationale, and an ordering call if dependencies exist. **The audit may not edit any target surface** — it is a read-only pass that produces a map.

2. **Owner (or commissioner) reviews the map.** Per-row review. The commissioner has the final call on every recommendation — the auditor proposes, the commissioner disposes. Decisions that should be locked at this point: scope splits, adaptation specifics where the audit named options, version bumps, anything ambiguous in the audit.

3. **Execute brief (Step 2).** Commission the propagation pass against the audited map. Brief locks in every decision from Step 2 (so the executor doesn't re-deliberate). Brief references the audit's row IDs directly rather than restating the deltas — token-economical, audit-trail-coherent. Out-of-scope items (audit `skip` rows) are explicitly named as out-of-scope.

4. **Executor flags in-flight deviations rather than silently rerouting.** If the executor finds during execution that an audit recommendation is wrong (e.g., a `propagate` row contains a regex contradicting a Step-2 lock), the executor pauses, deviates with reasoning, and documents the deviation in the deliverable. Silent deviation breaks the trust between map and territory.

5. **Verification hits the deployed surface, not the file diff.** A successful file edit and a green structural check are not proof the surface works. For templates: instantiate a fresh install and exercise it. For schemas: run a fresh migration against a clean DB. For viewer code: render in a browser. The verification gate must match where failures actually surface.

6. **Hotfix tail is expected, not exceptional.** Structural work touches enough surfaces that the visual/manual/last-mile verification pass will surface things the structural verification missed. Build the expectation of a Step-3 hotfix into the schedule rather than treating it as a failure of Step 2.

## What protects against failure

- **The audit's fixed-vocabulary calls.** `propagate` / `skip` / `adapt` are coarse enough that the auditor can't over-think and fine enough that the commissioner can rule on each one without re-reading the underlying file.
- **Locked decisions in Step 2.** The executor receives a brief with decisions already made — what was a judgment call in Step 1 is no longer up for debate in Step 2. Reduces in-execution drift and protects scope discipline.
- **Surface-area enumeration in Step 2.** The brief lists every surface to touch and every surface explicitly *not* to touch. Two-sided enumeration catches sibling-path miss.
- **In-flight deviation flagged, not silent.** The executor's persona must support pausing-and-flagging rather than auto-routing. Personas that silently re-route are the wrong fit for Step 2.
- **Verification surface matches failure surface.** Structural balance checks miss render bugs. Migration-DDL checks miss runtime bugs. The verification step in Step 2 has to hit where failures actually live. This is the *load-bearing* protection: when verification surface drifts from failure surface, the pattern fails silently.

## What the pattern does NOT protect against

This is named explicitly because the case study (CASE-006) surfaced it as a boundary worth carrying forward:

**The audit cannot protect a verification surface it has no way to inspect.** Step 1's read-only nature means it can't run a browser, can't render a diagram, can't exercise an install. If the Step-2 verification spec gates on the wrong surface (e.g., structural Mermaid balance instead of rendered output), the pattern produces a clean audit, a clean execute, and a broken artifact. The hotfix tail (Step 6) catches it, but at the cost of a 4/5 rating where a 5/5 was achievable.

Mitigation: at Step-2 brief-writing time, the commissioner should ask "where does this class of work actually fail?" and write the verification gate against *that* surface. Visual things need visual checks. Behavioral things need behavioral checks. Don't let convenience pick the gate.

## Validated instance

**BRIEFs 115 → 116 → 117** (2026-05-16) — template refresh from v1.0.0 to v1.1.0.

- **BRIEF-115** (audit) produced 51 cataloged deltas across 14 surface groups with `propagate` / `skip` / `adapt` / `no-action` calls, propagation ordering, and side observations. Read-only — no template files touched. Rated 5/5.
- **BRIEF-116** (execute) propagated the audit's 8 propagate + 13 adapt rows in the order the audit recommended, with 5 locked decisions in the brief. Caught one in-flight deviation (a regex contradicting the Step-2 lock — rewrote the regex, flagged the deviation in the deliverable). 16 files changed. Verified via fresh `git clone` + `setup.py` + install-surface checks. Rated 4/5 — the 1-point ding came from a Mermaid syntax error in a diagram that the structural verification missed.
- **BRIEF-117** (hotfix) replaced the offending syntax in the affected node label. Executor escalated own verification beyond brief spec to headless-Chrome render check — caught the boundary the structural check could not. Rated 5/5.

**Net outcome:** template at v1.1.0 + hotfix pushed to remote; one case study (CASE-006) and one pattern proposal (this) emerged. Total time: one work session.

## Adjacent patterns

- **Empirical-probe-before-design** ([[empirical-probe-before-design]]) — **cousin pattern.** Both share the *"characterize the territory before committing"* instinct. The probe characterizes external systems (library hooks, API behaviors, version-dependent shapes); the audit characterizes internal artifacts (templates, schemas, repo structure). Probe protects against silent integration failure; audit protects against silent propagation failure.
- **Sequential-overnight-build** ([[sequential-overnight-build]]) — distinct shape. That pattern handles time-pressured upstream/downstream splits with a contract handoff; audit-then-execute handles structural-surface work where the surface is bounded but interacts. Both can coexist; rarely the same instance.
- **Locked-decisions briefs** — sub-pattern visible in Step 2. When a brief carries explicit decision-locks (vs leaving them for the executor), execution drift drops. Worth watching across other patterns for whether it generalizes.

## Governance

Pattern proposed by Leroy 2026-05-16 following case study CASE-006; promoted to `validated` same date by the owner. PATTERN-005.

The pattern's *limit* (the read-only nature of Step 1 leaving Step 2's verification spec as the load-bearing protection) is named explicitly above so future use does not oversell it.

---

*Pattern #5 of N. See `/patterns/` for the full set.*
