# PKA Protocols — Catalog and Curation

**Curation layer for `protocols/`.** Maps the catalog of standing operational protocols by purpose and trigger so that a team member or future agent reaching for "is there already a procedure for this?" can find the right one — or confirm that there isn't, which is itself useful information.

*This is not a protocol. Protocols answer "what procedure runs when X fires."  This README answers "which protocols exist, what do they cover, and what is deliberately not covered yet?"*

---

## What lives here

`protocols/` holds **standing operational protocols** — procedural disciplines that fire automatically (or near-automatically) on a defined trigger, distinct from patterns, briefs, or persona instructions in the following ways:

- **Patterns** ([[../patterns/README]]) answer *what to do next* when a class of situation arises. They are diagnostic-and-prescriptive instructions a team member reads at brief-write-time or decision-time.
- **Briefs** (`team_comms/`, archived in `archive/team_comms/`) are one-off task contracts dispatched to a specific persona for a specific deliverable.
- **Persona instructions** (`team/*.md`) anchor identity, voice, default tier, operating contract — what a persona *is* and how it *operates*.
- **Protocols** (`protocols/*.md`) are *standing dispatch-layer disciplines* — when situation X fires, the protocol Y runs, automatically. Closer to a cron job than to a checklist; closer to organizational policy than to a tutorial.

A protocol is the durable home for a discipline that has graduated from "orchestrator judges per case" to "this fires reliably on the trigger." Pre-promotion, the discipline lives in orchestrator's head or in CLAUDE.md as a rule. Post-promotion, it lives here as an explicit document.

---

## Catalog status

| Status | Count | Refs |
|---|---|---|
| `active` | 1 | [[owner_observability]] |
| `proposed` | 0 | — |
| `retired` | 0 | — |

Status ladder for protocols:

- `proposed` — drafted, awaiting owner approval, not yet operational
- `active` — owner-approved and operationally in force; fires on its trigger
- `retired` — superseded, demoted, or empirically failed to earn its keep

Orchestrator proposes protocols (cross-cutting view across team work); owner approves. Demotion criteria are protocol-specific (each protocol names its own demotion trigger).

---

## Catalog

### [[owner_observability]] — *Owner Observability (Four-Axis Capture and Review)*

**Status:** active (template-baseline at v1.0).
**Trigger:** Posture-shaped moments (→ `owner_posture`); orchestrator-about-owner observation-shaped moments (→ `orchestrator_observations`); owner-about-orchestrator/team observation-shaped moments (→ `owner_observations`); team-member-about-anyone observation-shaped moments (→ `team_observations`, primary expected subject: orchestrator).
**Discipline:** Four tables in `personal.db` covering the chief-of-staff-style multi-party observability model. Two tables use the pending-review gate (`orchestrator_observations` and `team_observations`); two use owner-authority gate (`owner_posture` and `owner_observations`).
**Protects against:** Silent fade of strategic framing; implicit-only orchestrator knowledge of the owner; loss of session-spanning context; unobserved orchestrator behavior.
**Demotion criterion:** Two reflection-pass evaluation window with five operational thresholds (row velocity, pending→active ratio, active row reference rate, promotion-to-memory rate, subjective owner read). Per-axis demotion permitted — `team_observations` specifically subject to retirement first if no substantive team-side observations materialize.

---

## Meta-observations on protocols vs other layers

Three observations worth carrying forward as the catalog grows:

1. **A protocol that fires only on judgment trigger is not yet a protocol.** It is a meta-instinct. Protocols earn their slot here when the trigger is mechanical or near-mechanical (a specific class of deliverable lands; a specific date passes; a specific volume threshold trips). If "fires when orchestrator decides" is the trigger, the discipline belongs in a pattern entry or persona instruction, not here.

2. **Protocols are the dispatch-layer equivalent of patterns.** Where patterns codify *what discipline to apply at decision time*, protocols codify *what discipline runs automatically when a trigger lands*. The two layers complement each other: a pattern named at brief-write-time may invoke a standing protocol; a protocol may produce deliverables that trigger pattern application downstream.

3. **Protocols should have a demotion criterion at adoption.** Unlike patterns (which can stay validated indefinitely as long as the conditions hold), protocols incur ongoing operational cost — every firing burns tokens and team-member time. If a protocol's value-per-firing trends to zero, it should retire honestly. Each protocol's *Demotion criterion* section is mandatory.

---

## How to read a protocol entry

Every protocol file in `protocols/` follows the same shape:

1. **Status / adopted date / origin** — at the top
2. **Purpose** — why this protocol exists
3. **Trigger** — exactly what fires it (mechanical or near-mechanical)
4. **Sequence** — the procedural steps that run when the trigger fires
5. **Standing brief template** (if applicable) — boilerplate for the auto-routed brief, populated per firing by orchestrator
6. **Cost model** — per-firing cost, expected frequency, total operational burden
7. **What this protocol protects against** — explicit
8. **What this protocol does NOT protect against** — explicit limit, so the protocol isn't oversold (carry into all future protocol entries; convention borrowed from `patterns/README.md`'s "What the pattern does NOT protect against")
9. **Demotion criterion** — when the protocol retires
10. **Promotion to pattern status** (if applicable) — whether the protocol's discipline may earn pattern status later
11. **Governance** — propose/approve audit trail

A `[[link-name]]` references another file by slug (protocol, pattern, persona). Link liberally.

---

## Adjacent layers

- **`patterns/`** ([[../patterns/README]]) — patterns are what to do; protocols are what fires automatically. Some protocols implement a specific pattern's discipline as a standing fixture.
- **`team/`** — persona instructions anchor identity. Some protocols depend on specific personas; if a protocol's discipline is persona-coupled, that protocol does NOT propagate when those personas are absent (template-instance owners may hire new personas and re-derive protocols later).
- **`case_studies/`** — protocols may produce case-study material when they fire and the firing surfaces an interesting result.
- **`CLAUDE.md`** — top-level Intent layer. CLAUDE.md may reference protocols (e.g., the Feedback System section names the standing feedback discipline). Substantive protocols should be cross-referenced from CLAUDE.md when adopted, via an owner-approved deliverable.

---

## Governance

This README is the curation layer for `protocols/`. Orchestrator maintains it. Add an entry to the catalog when a new protocol is adopted; move an entry to "retired" when a protocol fails its demotion criterion. Substantive reorganisation (new families, family-merge, family-split) needs the owner's explicit nod, same as a protocol proposal.

Owner reviews the README at session-open when the catalog grows; small-edit drift between reviews is fine. The README follows the *curation-layer-README* convention demonstrated by [[../patterns/README]] and the case-studies curation README.

---

*Curation layer at template inception. Catalog at one entry; will grow as the instance accumulates discipline.*
