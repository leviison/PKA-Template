# Reflection-Pass Procedure (PKA Memory Layer)

**Author:** Learning Designer (persona named on hire)
**Status:** Procedure document — read this when running a reflection pass.

---

## TL;DR

The **reflection pass** is the operational analogue of the AAR-on-delivery practice, run at the team-rhythm scale rather than the per-deliverable scale. It reads recent operational evidence (feedback rows, deliverables, session-closes, journals once they exist) and proposes durable memory promotions that route through the owner's approval before they enter the `memory` table.

- **Cadence.** Calendar-anchored monthly (first session on/after the 1st of each month), with a **volume override** that triggers an early pass when ≥40 new feedback rows or a major architectural event have accumulated since the last pass.
- **Trigger.** Leroy-initiated brief (`BRIEF-NNN: run monthly reflection`) — surfaces at Session Open when the calendar or volume condition is met. Not automatic; the owner must be in-session to approve, so the pass never runs while they are offline.
- **Inputs.** `feedback` since last pass, `deliverables` since last pass, recent session-closes, `journal` rows (once they exist), and the current `memory` table as the consolidation substrate.
- **Decision tree.** Five operations: **ADD / UPDATE / SUPERSEDE / INVALIDATE / NOOP**. DELETE is reserved for emergencies (PII leak, fabrication) and is not a routine option — the `memory` table is built for soft-deletion via the `superseded_by` + `valid_to` bi-temporal columns.
- **Output.** Single deliverable to `owners_inbox/reflection_<date>.md`. Each proposed op cites its evidence.
- **Governance flow.** Leroy reads → in-chat surfaces to the owner → owner approves/defers/rejects per item → Leroy applies approved ops via `memory_io.write_memory_row()` / `supersede()` / `UPDATE memory SET status='invalidated'`.

---

## 1. When the pass runs

### Cadence: calendar-anchored monthly with volume override

**Floor:** monthly. Always run a pass in the first session on/after the 1st of each month if one has not run that month.

**Volume override:** run early when **either** of these conditions is met since the last pass —
- ≥40 new `feedback` rows, **or**
- A "major architectural event" — defined as: a new team member hired, a new top-level table added to `pka.db`, a new top-level folder added to PKA, a new validated `patterns/` entry, or owner-flagged ("we should reflect on this").

**Why these thresholds.** 40 feedback rows is roughly two weeks of high activity. A major architectural event is the team's own signal that durable patterns may have shifted. Both conditions are concrete and queryable.

**What this design protects against.**
- *Late capture of fast-moving learning.* High-velocity stretches that produce many feedback rows over a short window get a reflection pass while the signal is still fresh, instead of waiting weeks for the calendar to come around.
- *Empty ritual.* The calendar floor means even a quiet month produces *a* pass — but the pass-authoring template explicitly allows "no proposed operations" as a legitimate output when the evidence doesn't support promotions.

### Trigger mechanism

The reflection pass is **Leroy-initiated as a brief** — not auto-running, not session-open ritual.

Why a brief rather than auto-running:
1. The pass produces proposals that need the owner in-session for approval. Running it while the owner is offline produces a deliverable sitting in `owners_inbox/` for an unknown time, during which the memory layer drifts further. Better to run only when approval can close the loop.
2. Brief-as-trigger means the cadence decision is visible — it appears in the `briefs` table, gets a `brief_ref`, gets archived after completion. Reflection passes themselves become evidence in future reflection passes.

Session-open ritual: At Session Open, Leroy runs the reflection-pass-due query (CLAUDE.md Session Open step 4):

```sql
SELECT
  (SELECT COUNT(*) FROM feedback
   WHERE created_at > (SELECT value FROM settings WHERE key='last_reflection_pass_at'))
    AS new_feedback_rows,
  (SELECT value FROM settings WHERE key='last_reflection_pass_at') AS last_pass,
  date('now', 'start of month') AS current_month_start;
```

If `new_feedback_rows >= 40` OR `last_pass < current_month_start` (calendar floor crossed), Leroy surfaces: *"A reflection pass is due — [N] new feedback rows since [date]; we last reflected on [date]. Want to run it this session, or defer?"*

If the owner defers, no pass runs that session. Defer counter increments — if a calendar-floor pass has been deferred three sessions in a row, Leroy escalates the deferral count.

---

## 2. Input window

### What the pass reads each run

```python
import sqlite3
conn = sqlite3.connect('pka.db')
conn.row_factory = sqlite3.Row

# The cutoff for "since last pass"
last_pass = conn.execute(
    "SELECT value FROM settings WHERE key='last_reflection_pass_at'"
).fetchone()[0]
# Fallback if no prior pass: read everything in the last 30 days.
# (On first run, the cutoff is the epoch sentinel from setup.py.)

# 1. Feedback rows since last pass
feedback = conn.execute("""
    SELECT id, brief_ref, team_member, rating, notes, created_at
    FROM feedback
    WHERE created_at > ?
    ORDER BY created_at ASC
""", (last_pass,)).fetchall()

# 2. Deliverables since last pass (file paths to read selectively)
deliverables = conn.execute("""
    SELECT d.id, d.brief_id, d.file_path, d.created_by, d.created_at,
           b.brief_ref, b.title AS brief_title
    FROM deliverables d
    LEFT JOIN briefs b ON d.brief_id = b.id
    WHERE d.created_at > ?
    ORDER BY d.created_at ASC
""", (last_pass,)).fetchall()

# 3. Briefs that closed since last pass (catches scope/learning context)
briefs = conn.execute("""
    SELECT id, brief_ref, assigned_to, title, completed_at, status
    FROM briefs
    WHERE completed_at > ? OR (status='complete' AND completed_at IS NULL AND created_at > ?)
    ORDER BY completed_at ASC
""", (last_pass, last_pass)).fetchall()

# 4. Patterns that changed status since last pass
patterns = conn.execute("""
    SELECT pattern_ref, slug, title, status, approved_at, updated_at
    FROM patterns
    WHERE (approved_at > ? OR updated_at > ?)
    ORDER BY updated_at ASC
""", (last_pass, last_pass)).fetchall()

# 5. The current memory table (consolidation substrate — what we're reflecting against)
memory = conn.execute("""
    SELECT id, slug, type, scope, title, body, status, source_ref,
           approved_by, provenance, valid_from, valid_to, tags
    FROM memory
    WHERE status = 'active'
      AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
    ORDER BY type, slug
""").fetchall()

# 6. Journal rows (once journals are populated)
# 7. Session-close summaries: glob owners_inbox/session_close_*.md
#    filtered by file mtime > last_pass timestamp.
conn.close()
```

### Reading discipline

Order of attention:

1. **Feedback rows rated < 5.** Highest signal density. A 4 or 3 is the owner saying "this was good but here is what to do differently next time." That sentence is durable-memory-class evidence.
2. **Feedback rows rated 5 with substantive `notes` content.** Pattern-naming feedback signals an emergent practice that may already deserve a memory or a pattern row.
3. **Session-closes' "what worked" / "what's open" sections.** These are Leroy's already-synthesised view of the team rhythm — high signal but already filtered by another author.
4. **Deliverables.** Read titles + file paths; open only the ones that intersect with a candidate operation. Deliverables are usually evidence-of-execution, not evidence-of-pattern.
5. **Memory table.** Read all active rows. Every proposed op must be defensible against what already exists.

### Input window: what NOT to read

- **Briefs themselves.** The brief is the spec; the feedback row is the verdict. The verdict is what reflects, not the spec.
- **Case studies.** Already teaching artefacts authored by the Learning Designer — would create circular reflection.
- **Anything in `archive/`.** The window is "since last pass." Archived material is older than the window or already reflected on.
- **Personal data.** `~/Documents/PKA-Data/personal.db` is out of scope for the reflection pass — that store is owner-owned, not team-shared.

---

## 3. The decision tree — ADD / UPDATE / SUPERSEDE / INVALIDATE / NOOP

### Why five operations, not four

DELETE is **not** in the routine set. The `memory` table ships with `status='superseded'` and `valid_to` as bi-temporal columns and an XOR-style CHECK constraint that ties `status='superseded'` to a non-null `superseded_by` slug. The schema is built for soft-deletion. Using DELETE in a reflection pass would discard the audit trail the schema is explicitly designed to preserve, contradict the discipline established in `patterns/` and `case_studies/`, and make reflection passes irreversible.

DELETE remains *available* as an emergency op (PII leak, accidental write of model-fabricated content), but it does not appear in the routine reflection-pass deliverable.

**INVALIDATE replaces DELETE for "this is wrong."** A row marked `status='invalidated'` stops loading into any shim (the active-status filter excludes it) but persists for audit.

### The five operations

#### ADD — promote a new durable memory

**When to use.** Recent evidence reveals a durable principle or fact that:
1. Is not already captured by any active memory row (check by slug, type, and body grep)
2. Has appeared in ≥3 distinct evidence items (feedback rows from ≥3 different briefs, OR feedback row + session-close mention + persona-amendment-proposal), OR ≥1 direct statement from the owner that explicitly names the durability ("we should always do X going forward")
3. Generalises beyond the specific brief it was observed in

**Evidence threshold.** Be able to fill this template before drafting the ADD:

```
Evidence for this ADD:
- Source 1: <brief_ref or session-close file or deliverable path> — <one-line quote>
- Source 2: <...> — <quote>
- Source 3: <...> — <quote>
Why this generalises: <one sentence — what category of future work this applies to>
```

If you can't fill all four lines, the ADD doesn't make the deliverable.

**Row defaults.**
- `provenance = 'leroy_inferred'` (the Designer is inferring from evidence; the owner has not directly stated this as a memory)
- `approved_by` ← per the governance gates in §5
- `scope` — `'global'` if the principle applies to all team members; `'team_member:<slug>'` if it applies to one persona; `'owner_only'` if it's a fact about the owner's preferences that should not load into team-member contexts
- `type` — one of the seven enum values:
  - If the row tells the team *how to operate* → `operational`
  - If it tells the team *what the owner expects post-hoc* → `feedback`
  - If it's a *teaching principle* → `pedagogy`
  - If it's a *workflow preference* → `preference`
  - If it's a *project state fact* → `project`
  - If it's a *fact about the owner* → `user_fact`
  - If it's a *pointer to a `patterns/` entry* → `pattern_ref`
- `source_ref` — comma-separated brief refs of the evidence, prefixed by the reflection brief ref
- `tags` — kebab-case, max 4

#### UPDATE — refine an existing memory row in place

**When to use.** An existing active memory row is *correct but incomplete* — recent evidence adds nuance, scope, or a counter-condition that should be folded in. The slug stays the same; the body changes.

**Evidence threshold.** ≥1 evidence item naming the refinement plus a clear delta from the current body. The refinement must be *additive* or *clarifying* — never *contradicting*. If the new evidence contradicts the existing row, that's a SUPERSEDE, not an UPDATE.

#### SUPERSEDE — replace an old memory with a new one

**When to use.** An existing memory row has been superseded — a new pattern has overtaken it, or the owner has named a change of stance. The old row remains in the DB with `status='superseded'` and `superseded_by` pointing at the new slug; the new row is inserted afresh.

**Evidence threshold.** ≥2 distinct evidence items naming the new pattern AND a clear identification of the old row being replaced. The old and new bodies must be incompatible — if both could be true simultaneously, this is an UPDATE.

#### INVALIDATE — mark a memory as no-longer-correct, no replacement

**When to use.** Evidence shows an existing active memory row is wrong, but there is *no successor pattern* to replace it with. The row stops loading; no new row is added.

**Evidence threshold.** ≥1 evidence item explicitly contradicting the row, OR a direct owner statement that the row is wrong.

#### NOOP — explicit acknowledgement that something came up but does not need a memory change

**When to use.** A pattern was observed in the evidence window that *might* have prompted an operation but doesn't — because the existing memory already covers it, the pattern hasn't crossed the evidence threshold, or the pattern is more appropriately captured outside the memory layer (case study, pattern entry, persona amendment).

NOOP is a forcing function: if the Designer notices something and decides not to act, that decision is captured in writing — preventing silent omission.

### Decision-tree summary table

| Operation | Min evidence | What changes | Status before | Status after |
|---|---|---|---|---|
| **ADD** | ≥3 distinct items OR direct owner statement | New row inserted | (no row) | `active` |
| **UPDATE** | ≥1 item, additive only | Existing row's body refined | `active` | `active` |
| **SUPERSEDE** | ≥2 items + clear successor | Old row marked superseded, new row inserted | old `active` → `superseded` | new `active` |
| **INVALIDATE** | ≥1 contradicting item, no successor | Old row marked invalidated | `active` → `invalidated` | (loads stop) |
| **NOOP** | n/a (forcing-function entry) | Nothing | — | — |
| **DELETE** | Emergency only (PII, fabrication) | Row removed | — | (gone) |

---

## 4. Output deliverable format

### File path and naming

`owners_inbox/reflection_<YYYY-MM-DD>.md` where the date is the first calendar day of the period the pass *reflects on* (not the day the pass runs). E.g., the pass run on 2026-06-04 reflecting on May → `reflection_2026-05-01.md`.

### Document structure

```markdown
# Reflection Pass — <window: "Month YYYY" or "YYYY-MM-DD → YYYY-MM-DD">

**Author:** <Learning Designer name>
**Brief:** BRIEF-NNN
**Period reflected on:** <start_date> → <end_date>
**Inputs read:** <N feedback rows>, <M deliverables>, <K session-closes>, <J journal entries>
**Proposed operations:** <summary line — "3 ADD, 1 UPDATE, 1 NOOP" — or "0 operations; calendar-only pass, no durable signal accumulated">

## Summary

<2–4 sentences. What was the dominant pattern in this window? Is the team learning,
plateauing, or drifting? Any meta-observation about the reflection itself.>

## Proposed operations

```yaml
- op: ADD
  slug: <kebab-case>
  type: <enum>
  scope: <scope>
  provenance: leroy_inferred
  title: <human-readable>
  body: |
    <body>
  source_ref: BRIEF-NNN:reflect,<evidence brief refs>
  tags: <tag1>, <tag2>
  evidence:
    - <ref> — "<quote>"
    - <ref> — "<quote>"
    - <ref> — "<quote>"
  generalises_to: <one-line scope description>
  rationale: <one paragraph>

- op: UPDATE
  slug: <existing>
  changes:
    body: |
      <new body — full text>
  evidence:
    - <ref> — "<quote>"
  rationale: <one paragraph: what's added>

- op: SUPERSEDE
  old_slug: <existing>
  new_slug: <new>
  new_row:
    type: <enum>
    title: <human-readable>
    scope: <scope>
    source_ref: BRIEF-NNN:reflect
    tags: <tags>
    body: |
      <body>
  evidence:
    - <ref> — "<quote>"
    - <ref> — "<quote>"
  rationale: <one paragraph: why old is wrong, why new is right>

- op: INVALIDATE
  slug: <existing>
  evidence:
    - <ref> — "<quote>"
  rationale: <one paragraph: why no successor>

- op: NOOP
  context: <what was observed>
  evidence:
    - <ref> — "<quote>"
  rationale: <one paragraph: why no action>
  watch_for: <one-line trigger that would flip this to ADD next pass>
```

## Out-of-scope items surfaced

<For each item the reflection observed that requires Intent-layer action (CLAUDE.md
amendment, persona change, new pattern), name it explicitly with the routing:>

- **<observation>** — propose as separate deliverable to Sam (persona-update for <name>).
- **<observation>** — propose as separate deliverable to Leroy (pattern proposal: <slug>).
- **<observation>** — propose as separate deliverable to owner (CLAUDE.md amendment to <section>).

## Open questions for owner

<For each disagreement between evidence items, unresolved tension, or design call
the pass cannot make.>

## Approval surface

The in-chat approval format the owner uses:

> "approve 1, 3, 5; defer 2; reject 4, 6; INVALIDATE 7 with note 'Z'"

Where the numbers correspond to the proposed-operations list in order.

## Pass metadata

- Token cost (rough): <input tokens read>, <output tokens written>
- Inputs touched: <queries run, files opened>
- Next pass due: <calendar floor date>
- Watch counters: <number of "watch_for" carryovers from previous passes>
```

### What gets omitted by design

- **No SQL.** The deliverable contains YAML; Leroy translates to `memory_io` calls. This separates "what should change" (the Designer's output) from "how to apply" (Leroy's mechanical work).
- **No proposed Intent-layer changes inline.** Persona amendments, CLAUDE.md additions, and pattern proposals are flagged in the "Out-of-scope items" section but written as separate deliverables. The reflection pass must not become a back-door write path.
- **No reflection on case studies.** Case studies are the Designer's own teaching artefacts; reflecting on them would be self-referential.

---

## 5. Governance / promotion flow

1. **Pass runs.** The Designer writes the deliverable to `owners_inbox/reflection_<date>.md`, inserts a `deliverables` row, notifies Leroy in chat.

2. **Leroy reads.** Reviews the deliverable for:
   - Self-evidence (every op has cited evidence — §6 test)
   - Governance gate compliance (every op's `provenance` and `approved_by` defaults match the table below)
   - No back-door Intent-layer writes
   If any check fails, returns to the Designer with specific notes.

3. **Leroy surfaces to the owner in chat.** Format:
   > *"<Designer>'s reflection pass for <window> is in your owners_inbox. Headline: <summary>. <N> proposed ops. Want to walk through them now, or read first and come back?"*

4. **Owner approves.** In-chat, item-by-item:
   > *"approve 1, 3, 5; defer 2; reject 4; INVALIDATE 6 with note 'this was always wrong'"*

5. **Leroy applies.** For each approved op:
   - ADD → `memory_io.write_memory_row(conn, slug, type, title, body, scope, source_ref, approved_by, provenance, tags)`
   - UPDATE → `memory_io.write_memory_row(...)` with the same slug
   - SUPERSEDE → `memory_io.supersede(conn, old_slug, new_slug_kwargs)`
   - INVALIDATE → raw SQL: `UPDATE memory SET status='invalidated', updated_at=datetime('now') WHERE slug=?`
   - NOOP → no DB action
   - **Deferred / rejected** → no DB action; Leroy logs the disposition in the pass's `deliverables.notes` field.

6. **Settings update.** Leroy runs:
   ```sql
   UPDATE settings SET value=datetime('now'), updated_at=datetime('now')
     WHERE key='last_reflection_pass_at';
   ```
   This sets the cutoff for the next pass's input window.

7. **Pass archived.** The reflection deliverable lives in `owners_inbox/` until session close, then archives per the standard rule.

### Governance gates

| Op type | Scope | Approval required | `approved_by` |
|---|---|---|---|
| ADD `user_fact`, `project`, `operational` | `global` | Owner | `Owner` |
| ADD `pedagogy`, `preference` | any | Owner | `Owner` |
| ADD `feedback`, `pattern_ref` | `team_member:<slug>` | Leroy may insert (low blast radius) | `Leroy` |
| ADD anything | `owner_only` | Owner | `Owner` |
| UPDATE any | any | Same gate as a fresh ADD of that row's type+scope | preserved from original |
| SUPERSEDE any | any | Same gate as a fresh ADD of the new row | per new row |
| INVALIDATE any | any | Owner (always — invalidation has higher blast radius than addition) | `Owner` |
| NOOP | — | — | — |

**The reflection pass's default is `provenance='leroy_inferred'`.** The Designer is inferring from evidence; the transition to `human_confirmed` happens *at the owner's verbal approval of a specific row* — Leroy sets `provenance='human_confirmed'` on the row that gets inserted.

---

## 6. Token-cost ceiling

The cost grows roughly linearly with the input window. **The cap is: if the projected input exceeds 100k tokens, the pass runs in tiers.**

- **Tier 1:** read feedback rows only. Propose `feedback`-type and `operational`-type ops. Surface to owner.
- **Tier 2** (separate deliverable): read deliverables + session-closes. Propose `pedagogy` / `pattern_ref` / Intent-layer-routing ops.
- **Tier 3:** read journal entries. Propose journal-derived ops.

The cap is a future safeguard, not a current constraint for most installs.

---

## 7. First-run plan

The first reflection pass for any new PKA install is targeted for the **first session on/after the install date + ~3 weeks** — long enough that there is real evidence to reflect on, but not so far out that the practice slips.

### First-run differences from steady-state

1. **The `last_reflection_pass_at` setting is seeded with an epoch sentinel** (`1970-01-01T00:00:00`) by `setup.py`. The first pass uses that as its cutoff — meaning it reads everything since install.

2. **The memory table will be empty on the first pass** unless the owner has manually written rows via `memory_io.py`. That's fine — the first pass is mostly ADDs.

3. **The owner will be in-session.** No applying-without-approval; no asynchronous deliverable sitting. The first pass closes its loop the day it opens.

---

## Procedure tests

Three validations the Designer bakes into the procedure and Leroy enforces on read:

### Test 1 — Self-evidence check

Every proposed ADD / UPDATE / SUPERSEDE / INVALIDATE cites specific source evidence. Refs must resolve: brief refs must exist in the `briefs` table, file paths must exist under `owners_inbox/` or `archive/`, feedback row IDs must exist in `feedback.id`. No vibes-based proposals.

### Test 2 — Provenance hygiene

Every proposed ADD or UPDATE row's `provenance` field is `leroy_inferred` in the deliverable as the Designer writes it. The transition to `human_confirmed` happens at the moment the owner explicitly approves the row in chat — Leroy makes the substitution at insertion time.

### Test 3 — No back-door Intent-layer writes

The reflection deliverable may *propose* persona-file revisions, CLAUDE.md amendments, and new `patterns/` entries, but must clearly route them as separate deliverables, not as memory ops:

- Persona-file revisions (`team/<NAME>.md`) → "Out of scope for memory insertion — propose as separate deliverable for Sam"
- CLAUDE.md amendments → "Out of scope for memory insertion — propose as separate deliverable for the owner"
- New `patterns/` entries → "Out of scope for memory insertion — propose as separate deliverable for Leroy (pattern proposal)"

This is the most important test. The reflection pass's whole legitimacy depends on staying out of Intent-layer drift.

---

*End of procedure document.*
