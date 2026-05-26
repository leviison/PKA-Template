# Patterns — Family Tree and Catalog

**Curation layer for `patterns/`.** Maps the catalog by shared discipline so that someone reaching for a pattern can find the right shape; names the meta-instincts that recur across patterns; carries the loose threads that aren't yet pattern entries.

*This is not a pattern. Patterns answer "what to do next." This README answers "how do these patterns relate?"*

---

## Catalog status

| Status | Count | Refs |
|---|---|---|
| `validated` | 6 | PATTERN-001, 002, 003, 004, 005, 006 |
| `proposed` | 3 | PATTERN-007, 011, 013 |
| `deprecated` | 0 | — |

Status ladder: `proposed` (one instance observed, awaiting approval) → `validated` (approved with at least one demonstrated instance) → `deprecated` (superseded or no longer applicable). Leroy proposes; the owner approves.

---

## Family tree

The catalog organises around a small number of recurring **meta-instincts**. Each instinct is a discipline that shows up in multiple operational shapes; each pattern is one operational instantiation of an instinct. The instincts themselves are not patterns — they are too general to be brief-writeable. They live here.

### Family 1 — *Characterize before you commit*

The team's pre-decision rigor. Before designing a contract, propagating a change, or building a tool, characterise the territory empirically. Operational shapes differ depending on whether the territory is an external system or an internal artifact.

- **[[empirical-probe-before-design]]** (PATTERN-006, validated) — Probes an *external system* (library callback, API behavior, runtime hook) when documentation is incomplete. Output: written characterization consumed by a downstream design step.
- **[[audit-then-execute-structural]]** (PATTERN-005, validated) — Audits *internal structural artifacts* (templates, schemas, repo surfaces) before a propagation pass. Output: a diff-audit deliverable with `propagate` / `skip` / `adapt` recommendations.

Diagnostic before reaching for this family: *what failure mode are you protecting against?* If silent integration failure → probe. If silent propagation failure → audit. If silent investment-in-the-wrong-thing → inventory (which is itself a probe of the catalog).

### Family 2 — *Coordinate multiple agents on related work*

Shapes for handing work across team members when the work cannot be done by one agent alone. The shapes differ on whether coordination is sequential or parallel.

- **[[sequential-overnight-build]]** (PATTERN-001, validated) — Upstream agent ships a complete-deliverable contract; downstream agent reads it and builds against the live upstream. Time-pressured "while-I-sleep" framing.
- **[[multi-lens-parallel-critique]]** (PATTERN-004, validated) — Multiple independent reviewers run in parallel against a single artifact, lenses constrained to stay non-overlapping. Calibration tool, not routine QA.

Diagnostic: *do the agents need each other's outputs to do their work?* If yes → sequential. If they critique the same artifact from independent angles → parallel.

### Family 3 — *Evolve the system in response to surfaced gaps*

Shapes for when the team notices it doesn't have what it needs and grows.

- **[[persona-gap-triggered-hire]]** (PATTERN-003, validated) — A brief surfaces a capability the team doesn't have; the surface itself triggers a hire conversation with Sam. Distinct from speculative hiring (where a role is added before a brief surfaces the gap).

### Family 4 — *Architecture patterns for specific surfaces*

Not all patterns generalise across the team's work. Some are domain-specific architecture patterns that earn pattern status because they recur within a domain.

- **[[single-consumer-event-stream]]** (PATTERN-002, validated) — Single-consumer + local-buffer pattern for event-stream architectures. Specific to streaming protocol design; not a cross-team discipline.

These are catalogued for completeness but are referenced from their domain rather than from the cross-team meta-instincts.

### Family 5 — *Discipline-application discipline* (meta-disciplines on the disciplines themselves)

When the team reaches for a pattern, protocol, or discipline, the act of reaching is itself subject to discipline. Family 5 patterns codify the meta-disciplines: *did the discipline honestly answer? did it apply at the right scope?* These patterns operate one level above the disciplines they govern — they fire when a discipline is named, not when a brief is shaped.

- **[[probe-validity-discipline]]** (PATTERN-011, proposed) — When a probe returns a clean verdict, the discipline that fires *on the probe*: audit the probe against four question-frames, layer it with structurally different probes, treat confirmation-affirming results with extra suspicion. Promotion gated on first template-instance firing.
- **[[scope-validity-discipline]]** (PATTERN-013, proposed) — When a discipline is applied, the discipline that fires *on the scope of the application*: name the discipline's proper scope, name the actual application scope, and close the gap if they differ. Sibling pattern to PATTERN-011. Promotion gated on first template-instance firing.

Diagnostic before reaching for this family: *is a discipline being named in this work?* If yes — probe-validity, audit-validity, verification-validity, preserve-prod, any other named discipline — the family-5 patterns ask the second-order question on top.

---

## Proposed patterns

Patterns shipped at `proposed` status pending first validated-instance evidence in template-instance use. A template-instance owner who runs an engagement against one of these patterns and finds it usable should record the instance in the pattern's *Validated instance(s)* section and promote to `validated`.

- **[[domain-engagement-template]]** (PATTERN-007, proposed) — Owner-commissioned, domain-bounded, position-taking engagement workflow. Asset intake → parallel extraction → framing memo → optional pre-meeting prep → speaker mapping → position-taking deliverable → re-underwriting contract. The pattern names the workflow shape; the domain methodology (investment thesis, security audit, consulting recommendation, hire eval, etc.) fills the position-taking slot. Promotion to `validated` requires a first template-instance run.
- **[[probe-validity-discipline]]** (PATTERN-011, proposed) — Discipline applied *on the probe* when a probe returns a clean verdict the prober wants to trust. Five-step shape (probe → four-frame audit → layer-the-probe → divergence-means-bad-probe → only-then-act). Sibling to PATTERN-013. Promotion to `validated` requires a first template-instance firing.
- **[[scope-validity-discipline]]** (PATTERN-013, proposed) — Discipline applied *on the scope* when a discipline is named in a brief or deliverable. Five-step shape (name discipline → name proper scope → name application scope → close the gap → capture scope in the artifact). Sibling to PATTERN-011. Promotion to `validated` requires a first template-instance firing.

---

## Meta-instincts surfaced but not yet pattern slots

Carrying place for disciplines that show up across briefs but haven't earned their own pattern entry (yet). When one of these accumulates a second or third instance, propose it.

- **Ownership-of-the-inherited-fix** — Team members own the cleanup of bugs they inherit, even when the bug pre-dates their work.
- **Locked-decisions-in-execution-briefs** — When a brief carries decisions already made by the commissioner, execution drift drops. Sub-pattern under audit-then-execute, worth watching for generalisation.
- **Mini-commits-during-long-tail** — Periodic mini-commits during post-close productive iteration prevent housekeeping pile-up. Operational, not pattern-shaped.

*Owners of forked-from-template instances: add your own meta-instincts here as recurring disciplines surface. The list is not bounded by what shipped at template time.*

---

## How to read a pattern entry

Every pattern file in `patterns/` follows the same shape:

1. **Status / author / approval** — at the top
2. **When to use** — preconditions
3. **When NOT to use** — disqualifiers
4. **Shape** — the operational steps
5. **What protects against failure** — the constraints that make the pattern work
6. **What the pattern does NOT protect against** — explicit limit, so the pattern doesn't get oversold (added 2026-05-16; carry into all future pattern entries)
7. **Validated instance(s)** — concrete brief refs + outcomes
8. **Adjacent patterns** — cousin patterns and family-resemblance links
9. **Governance** — propose/approve audit trail

A `[[link-name]]` references another file by slug (case study, pattern, memory). Link liberally; an unmatched link marks a future entry worth writing.

---

## Governance

This README is the curation layer for `patterns/`. Leroy maintains it. Add an entry to the family tree when a new pattern is proposed; promote a meta-instinct from the "not yet a pattern slot" section to a family when it earns its own pattern entry; demote (or move to deprecated section) when a pattern is retired.

The owner reviews the README at session-open when the catalog grows; small-edit drift between reviews is fine. Substantive reorganisation (new families, family-merge, family-split) needs the owner's explicit nod, same as a pattern proposal.

---

*Curation layer, drafted 2026-05-18. Propagated to template at v1.2.0.*
