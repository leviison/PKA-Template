# Protocol — Owner Observability (Four-Axis Capture and Review)

**Status:** active
**Version:** v1.0 (template inception)
**Proposed:** at install
**Approved by:** owner (at install acceptance)
**Activated:** at install
**Origin:** Inherited from the validated-instance discipline shaped through iterative refinement on the originating PKA instance; canonical post-rename state baked into the template baseline.

---

## Purpose

PKA accumulates four kinds of observation surface that today fade between sessions when not captured durably:

- **The owner's framing-and-posture about PKA** — how the owner is thinking about the system over time
- **The orchestrator's observations about the owner** — how the orchestrator (Leroy) reads the owner's decision style, framing tendencies, trust patterns
- **The owner's observations about the orchestrator (and any team member)** — how the owner reads the orchestrator's brief-shaping, framing choices, output density; or how the owner reads any team member's pattern of work
- **Team members' observations about each other and about the orchestrator** — the learning-designer's reflection-pass observations about the orchestrator's interpretation step; the researcher's review observations about citation patterns; the HR director's persona-review observations that touch handoff hygiene

This protocol defines the standing discipline by which all four observation surfaces get captured durably while preserving the owner's review-and-correction authority.

Four tables in `personal.db`:

- **`owner_posture`** — *owner-about-PKA*. Strategic framing, re-engagement state, pattern recognition.
- **`orchestrator_observations`** — *orchestrator-about-owner*. Decision style, framing tendencies, re-engagement patterns, trust patterns, risk posture.
- **`owner_observations`** — *owner-about-orchestrator/team-members*. Active on write — owner's authority is the gate. Highest-fidelity observation source.
- **`team_observations`** — *team-members-about-anyone-primarily-orchestrator*. Open `subject` (option 3 from the originating design conversation); primary-use-case anchored to team→orchestrator. Lands at `pending-review`; owner's gate.

The asymmetry of write-authority is the load-bearing constraint:
- For posture: owner writes directly OR orchestrator captures from chat with owner's ratification
- For `orchestrator_observations` and `team_observations`: writer is not the principal; rows land at `pending-review` status. Owner reads and either ratifies (→ active), corrects (→ active with `levi_response`), or rejects (→ archived). **No such observation goes active without the owner having seen it.**
- For `owner_observations`: owner is the writer; rows land at `active` (no review gate needed — owner's authority is the gate).

This is the trust shape the discipline was shaped to honor: power-asymmetric capture paired with structural checks — the principal accepts the capability when the gate that makes it safe is named alongside it.

> **Column-naming note for v1.0.** The `levi_response` column on `orchestrator_observations` and `team_observations` preserves the historical PKA column name for continuity. Under the canonical naming convention it reads as "owner-response." A cosmetic rename (`levi_response` → `owner_response`) is a separate brief; no functional impact.

## Architectural framing — novel territory

The team-observes-orchestrator axis is poorly documented in public agent-system practice (LangGraph, AutoGen, CrewAI all default to *operator observes supervisor*, not *workers observe supervisor*). The closest real-world analog is a chief-of-staff-to-CEO role observed by multiple parties (CEO directly, peer executives, governance, self). PKA adopts this analog and treats team-observes-orchestrator as a first-class capture, with explicit demotion criteria if the discipline doesn't earn its keep.

The four-axis architecture is scaffolded minimally and extended as discipline matures. If `team_observations` doesn't materialize substantive observation over the demotion-evaluation horizon, retire honestly. The minimal case (posture + owner observations + orchestrator observations) remains valuable on its own.

## Trust shapes and pairings — the underlying primitives

The four tables are not four canonical *axes*; they are **two trust shapes applied to four observer/subject pairings**.

| Trust shape | Default status on write | Used when the writer is... | Tables today |
|---|---|---|---|
| **Active-on-write** | `active` | The principal (owner) — their authority is itself the review gate | `owner_posture`, `owner_observations` |
| **Pending-review** | `pending-review` | Not the principal — owner's explicit review is the gate before the row goes active | `orchestrator_observations`, `team_observations` |

The four current tables cover the four observer/subject pairings the discipline has needed to date:

| Pairing | Trust shape | Table |
|---|---|---|
| owner → PKA (owner about system) | active-on-write | `owner_posture` |
| owner → {orchestrator, team member, system} | active-on-write | `owner_observations` |
| orchestrator → {owner, team member} | pending-review | `orchestrator_observations` (with `subject` column) |
| {team member} → {orchestrator, peer} | pending-review | `team_observations` |

**Why the framing matters.** Future extensions of the observability surface are read most cleanly as either (a) a new pairing inside an existing trust shape (same table, possibly an enum widening — e.g., adding the `subject` column to `orchestrator_observations` so the orchestrator can observe team members), or (b) a new trust shape (a genuinely new write-gate semantics — none anticipated today, but the framing lets one land cleanly if needed). Counting "axes" obscures this; counting trust-shapes × pairings makes the next move obvious.

A practical consequence: when a new observer/subject pairing is needed, the first question is *which trust shape* — that determines the default status and the review-gate discipline. *Which table* follows naturally from the trust shape plus whether an existing table can hold the new pairing.

## Triggers (per axis)

### Posture-shaped moments (→ `owner_posture`)

- The owner articulates a strategic question about PKA itself ("how are our memory layers performing?")
- The owner re-engages with prior work and names what he wants to advance ("I want to look at the recommendations from the morning brief")
- The owner makes a meta-observation about how PKA's structure is generalizing ("should we follow the same methodology that we are using with patterns?")
- The owner explicitly says something worth capturing ("save that for next time")
- More posture-types may emerge; the schema's `posture_type` column is open string for that reason.

### Orchestrator-about-owner observation-shaped moments (→ `orchestrator_observations`)

- A recurring pattern in the owner's interaction style is visible across multiple instances ("trusts recommendations but recombines elements before committing")
- An emerging framing-tendency that shapes the owner's decisions ("notices meta-architectural patterns before being prompted")
- A risk-posture or trust-pattern that informs how PKA should serve the owner ("prefers earned validation over granted validation")
- A self-correction the owner makes that exposes their methodology ("explicitly names when his framing is incomplete")

### Owner-about-orchestrator/team observation-shaped moments (→ `owner_observations`)

- Owner notices a pattern in how the orchestrator operates ("orchestrator hesitates too much before proposing" / "orchestrator over-elaborates on briefs by ~20%")
- Owner notices a pattern in how a team member operates that is worth carrying forward beyond a single feedback rating
- Owner notices a system-level pattern about PKA as a whole that isn't quite *posture* (which is more strategic/framing) but is *observation* (concrete, evidenced)
- Owner-initiated capture is by chat statement: "note this: orchestrator tends to X." Orchestrator writes the row at `status='active'`.

### Team-member-about-anyone observation-shaped moments (→ `team_observations`)

- The learning-designer, during a reflection pass or AAR, notices a pattern about the orchestrator's brief-shaping, persona-pairing decisions, or orchestration discipline that warrants structured capture beyond the deliverable's prose
- The researcher, during a substantive review, notices a pattern about the orchestrator's citation hygiene in briefs or about a persona's output-density tendency that warrants structured capture
- The HR director, during a persona review, notices a pattern about handoff hygiene, brief-quality, or orchestrator-side scope-setting that touches the orchestrator
- More generally: any team member, during their normal review/reflection work, may surface a pattern observation about the orchestrator or another team member that is worth carrying forward

The expected primary subject of `team_observations` is `orchestrator` (typically the lowercase first-name slug of the orchestrator persona). Other subjects are allowed (per option 3 from the originating design conversation) but rare — peer-level team-on-team observation will frequently overlap with existing feedback/persona-review structures and shouldn't duplicate them. The protocol's primary use case is closing the *who watches the orchestrator?* gap.

### Capture mechanism for team_observations — in-deliverable extension, not new triggered work

Team members do not get new dedicated observation-capture briefs. The capture discipline is an **extension of their existing review/reflection work**: when the learning-designer writes a reflection-pass deliverable, the researcher writes a substantive review, or the HR director writes a persona review, the deliverable may include a *Structured observations* section that lists rows the team member intends to write to `team_observations`. The orchestrator executes the row writes after the deliverable lands; the owner sees the pending observations at next session-open or via dedicated review.

This means:
- **No new persona triggers.** The work is additive to existing review/reflection deliverables.
- **No new commissioning surface.** The orchestrator doesn't write new briefs for observation capture.
- **The deliverable references the observation rows via `source_deliverable_id`** so the audit trail is intact.

If a team member captures observations in deliverable prose but doesn't structure them, the orchestrator may surface candidates back to the team member for ratification before writing rows. The discipline is opt-in for the reviewer; ratification by the owner closes the gate either way.

### Hesitation-as-signal across all axes

Hesitation-as-signal applies here the same way it does in the cross-cutting hesitation discipline: if the orchestrator or a team member notices a posture or observation candidate, *the noticing is the trigger* — capture the candidate, even if it might be wrong. The review gate catches what shouldn't have been captured.

## Sequences (per axis)

### For owner-posture

1. **Owner says something posture-shaped in chat.**
2. **Orchestrator decides whether to capture in-band or out-of-band.**
   - *In-band*: orchestrator says "Worth capturing as posture — yes?" Owner says yes/no/refine.
   - *Out-of-band*: orchestrator writes the posture row with `captured_by='orchestrator'` and surfaces in next session-open or status update.
   - Owner-direct: owner says "save this as posture" → orchestrator writes with `captured_by='owner'` (effectively owner-authored via orchestrator as scribe).
3. **Posture row lands in `owner_posture`** with `status='active'` (no pending-review gate — the in-band ratification or out-of-band surfacing serves the review function).
4. **Owner can supersede/archive/promote-to-memory** any posture row at any time via direct chat instruction to orchestrator.

### For orchestrator-about-owner observations

1. **Orchestrator notices an observation candidate** in working context.
2. **Orchestrator writes the observation** with `status='pending-review'` and anchored `evidence` from chat history / deliverables / specific session refs.
3. **At next session-open OR opportune moment, orchestrator surfaces pending observations to owner.** Every pending-review observation surfaced within 2 sessions of capture.
4. **Owner reviews each observation** with one of the four actions: ratify / correct / reject / defer (see *Operational details* section).
5. **Active observations inform orchestrator's working context** — orchestrator reads active observations at session-open and lets them shape interpretation.

### For owner-about-orchestrator/team observations

1. **Owner makes an observation in chat** ("note this: orchestrator tends to X" / "I noticed the researcher delivers heaviest under time pressure").
2. **Orchestrator writes the row to `owner_observations`** with `status='active'`, `subject=<who>`, body=owner's words (quoted directly when possible), evidence anchored to the chat moment.
3. **Owner-initiated supersede/archive at any time** via chat instruction.
4. **Active rows inform orchestrator's working context AND the subject team member when relevant** — if the owner observes that the HR director tends to draft persona files too tersely, that observation should be surfaced into the HR director's brief context when the next review is commissioned.

### For team-member-about-anyone observations

1. **Team member writes a reflection / review / persona-review deliverable** as part of their normal work.
2. **Deliverable optionally includes a *Structured observations* section** listing rows the reviewer intends to commit to `team_observations`. Each candidate: subject, observation_type, body, evidence anchored to specific deliverable / brief / session refs.
3. **Orchestrator executes the row writes** with `status='pending-review'`, `source_deliverable_id` linking back to the deliverable.
4. **Owner reviews at next session-open** or via dedicated review window.
5. **Owner's response** with ratify / correct / reject / defer (same actions as `orchestrator_observations` review).
6. **Active rows inform orchestrator's working context AND the subject team member's brief context** (when the subject is a team member, their next brief carries forward the observations they should be aware of).

### Hybrid path — orchestrator surfacing candidates back to team members

If a team member's deliverable contains observation-shaped prose but the team member didn't structure it explicitly, orchestrator may surface candidates back: *"I noticed this passage in your deliverable reads as a structured observation candidate — would you like to commit it to team_observations?"* The team member ratifies or refines; orchestrator writes the row at `pending-review`. This is opt-in for the reviewer and doesn't impose discipline they didn't author.

## Read discipline

### Session-open

At session open, orchestrator queries all four tables:

```sql
-- Active posture (owner about PKA), recent first
SELECT body, posture_type, captured_at FROM owner_posture
  WHERE status = 'active' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
  ORDER BY captured_at DESC LIMIT 10;

-- Active orchestrator-about-owner observations
SELECT body, observation_type, levi_response FROM orchestrator_observations
  WHERE status = 'active' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
  ORDER BY captured_at DESC LIMIT 10;

-- Active owner-about-orchestrator/team observations
SELECT body, observation_type, subject FROM owner_observations
  WHERE status = 'active' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
  ORDER BY captured_at DESC LIMIT 10;

-- Active team observations (typically about orchestrator)
SELECT body, observation_type, observer, subject FROM team_observations
  WHERE status = 'active' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
  ORDER BY captured_at DESC LIMIT 10;

-- Pending observations across both review-gated tables
SELECT 'orchestrator_observations' AS source, id, body, observation_type FROM orchestrator_observations
  WHERE status = 'pending-review'
UNION ALL
SELECT 'team_observations' AS source, id, body, observation_type FROM team_observations
  WHERE status = 'pending-review'
ORDER BY 1, captured_at;
```

Pending observations across both `orchestrator_observations` and `team_observations` are surfaced to owner if not yet reviewed in 2+ sessions.

### On-demand

Owner can query any table directly via the viewer or via SQL. FTS5 indices support free-text search on body (and evidence where present).

## Lifecycle

| Status | Meaning | Transitions |
|---|---|---|
| `active` (posture) / `pending-review` (observations) | Default at write time | → superseded, archived, promoted-to-memory, or corrected/active (for obs) |
| `superseded` | New posture/observation supersedes this one; old row preserved for audit | Terminal |
| `corrected` (observations only) | Owner refined the observation; the corrected version is in `levi_response` | Used for soft-edit cases; the underlying row stays |
| `promoted-to-memory` | The posture/observation became a durable fact; a corresponding `memory` row is created and this row points to it | Terminal |
| `archived` | No longer relevant; not deleted (audit trail preserved) | Terminal |

Promotion to memory is a real path: posture or observations that prove durable across multiple sessions are candidates for becoming `memory` rows in the operations-tier memory table. This is the upward graduation — owner-tier observability into team-tier durable knowledge. Orchestrator proposes promotion; owner approves at reflection-pass time.

## What this protocol protects against

- **Silent fade of strategic framing.** Owner observations about PKA's direction fade in chat history; this protocol captures them durably.
- **Implicit-only orchestrator knowledge about the owner.** Orchestrator accumulates implicit reads of the owner's interaction patterns; without this protocol, those reads stay in working context and don't compound.
- **Asymmetric trust around observation.** Without the `pending-review` gate, the orchestrator writing about the owner could feel surveillance-shaped. The review-before-active discipline makes the relationship transparent and correctable.
- **Loss of session-spanning context.** Re-engagement state ("I want to look at the recommendations from the morning brief") informs how next-session work should run; capturing it prevents the next session starting cold.

## What this protocol does NOT protect against

- **Owner-explicit private content.** The owner may say things in chat that he doesn't want captured. This protocol doesn't have a "do not capture this" signal channel; the owner can always say "don't capture that" and the orchestrator honors it, but the protocol assumes good-faith capture-then-review rather than capture-then-private.
- **Misobservation that the owner doesn't catch.** If the orchestrator writes an observation the owner doesn't read carefully and rubber-stamps as active, the observation goes active despite being wrong. Mitigation is the review discipline itself — the protocol assumes the owner actually reads pending observations. If pending-review accumulates unread, the protocol's value drops.
- **Over-capture / noise.** If the orchestrator captures every chat-line as a posture candidate, the table becomes noisy. The protocol depends on the orchestrator's judgment about *what's worth capturing* — the same wisdom-vs-recklessness balance the cross-cutting hesitation discipline names.
- **Privacy across multi-owner instances.** When PKA-OS templates to other owners, the `owner_posture` / `orchestrator_observations` table-naming convention is per-instance; the substrate inside the personal.db file is per-owner because the file itself is per-owner.

## Demotion criterion

The protocol's value is operational, not theoretical — if the discipline doesn't earn its keep, retire honestly. The evaluation horizon is **two completed reflection passes**, not a calendar window. Reflection passes are the moments when the system actually evaluates whether observability captures are surfacing value; a calendar window may miss two passes or contain three, and the signal lives in the pass cycle either way.

### Evaluation triggers — fire on whichever lands first

- **Two reflection passes have run** since the protocol entered `active`, and either pass surfaced no observation that earned promotion to memory, OR
- **Owner explicitly flags** the discipline as uncomfortable-in-practice or low-value (subjective check; the principal's read is always sufficient grounds)

### Operational thresholds at evaluation time

When the trigger fires, examine the four tables against these thresholds. Any one failing threshold is a signal; multiple failing thresholds is a clear demotion case.

| Threshold | Healthy | Failing |
|---|---|---|
| **Row velocity** (capture rate per session) | 1–5 per session, sustained | 0 sustained, OR >10 sustained (under-capture / over-capture) |
| **Pending → active ratio** | ≥70% of pending observations ratified (not rejected) | <50% — orchestrator's read of capture-worthiness is mis-calibrated |
| **Active row reference rate** | Active observations referenced in chat or surfaced in session-open at least monthly | Active rows accumulate without being read — table is write-only |
| **Promotion-to-memory rate** | At least one promotion candidate per two reflection passes for the older active rows | Zero promotions across multiple passes — the path is aspirational, not real |
| **Subjective owner read** | Discipline feels useful to the principal | Discipline feels surveillance-shaped, slush-pile-shaped, or noise-producing |

The subjective owner read is sufficient by itself for demotion — owner's authority overrides quantitative thresholds. The quantitative thresholds exist so the evaluation has a defensible answer-shape and so demotion-vs-keep doesn't require re-litigating what counts as substantive value every time.

### Demotion lifecycle (inheriting the patterns/protocols deprecation shape)

If demotion is the call, the protocol does **not** drop tables or delete rows. Instead, inheriting the `patterns/` and `protocols/` deprecation shape:

1. **Status transition.** Protocol status moves to `deprecated`. Table-level: no schema change yet — the tables remain queryable.
2. **Halt new writes.** Orchestrator stops capture per the protocol's trigger rules. Existing active rows continue to inform working context as long as they remain accurate; they do not need to be archived just because new captures have stopped.
3. **Preserve audit history.** All existing rows (active, pending-review, superseded, archived, promoted-to-memory) stay in place. The audit trail is the record of what the discipline produced during its run.
4. **Follow-up brief.** If/when the discipline is re-attempted with a different shape (e.g., per-axis demotion where `team_observations` retires but `orchestrator_observations` continues), a follow-up brief authors the next-version protocol. The deprecated v1.x protocol moves to `archive/protocols/` with the deprecation reasoning preserved.

This shape matches how `patterns/` handles deprecation — the validated work the pattern produced doesn't disappear because the pattern itself stops being a default. The same shape protects observation rows.

### Per-axis demotion is permitted

The four-table architecture is loosely coupled enough that one table can demote while others continue. Examples:

- `team_observations` demotes (the team-observes-orchestrator discipline doesn't earn its keep) while `owner_posture` + `owner_observations` + `orchestrator_observations` continue active.
- `orchestrator_observations` demotes (over-capture or rubber-stamping) while posture and owner-authored observations continue.
- `owner_posture` would be the last to demote — it has the strongest standalone value and the lowest discipline cost.

Per-axis demotion goes through the same lifecycle (status='deprecated' on the table's protocol section; halt writes; preserve rows; follow-up brief if re-attempted).

Retirement, partial or full, is itself a data point — it tells PKA something about which owner-tier observability shapes do and don't work for this specific owner. The data point survives in the deprecated protocol's archived form.

## Promotion to pattern status

If the protocol fires regularly and produces value for an extended operational window (60+ days), it may earn pattern candidacy. Possible pattern name: **Owner Observability — Paired Asymmetric Capture with Review-Before-Active.** The pattern's generalization beyond this specific owner / orchestrator pairing would be the test: does the discipline work for any owner + their PKA-OS instance, or is it tuned to a specific owner's trust posture?

Not yet. Protocol first; pattern emerges if the discipline generalizes.

## Operational details

### Q1 — Promotion mechanism for pending-review → active

The review interaction lives in chat. Sequence:

- **Orchestrator surfaces pending observations to owner** at one of: (a) next session-open, (b) opportune moment in the working session (a natural pause), or (c) explicit owner request ("show me pending observations"). Surfacing format: each observation's `id`, `observation_type`, `body`, and key `evidence` displayed; orchestrator waits for owner's call per item.
- **Owner responds per observation** with one of four shapes:
  - *"ratify N"* (or "yes" / "looks right") → `status='active'`, no `levi_response`
  - *"correct N: <text>"* → `status='active'`, `levi_response=<text>` (the refinement)
  - *"reject N"* (with optional reason) → `status='archived'`, optional `levi_response=<reason>`
  - *"defer N"* → row stays at `pending-review`; owner wants more time. Re-surfaces next session.
- **Orchestrator applies the status update** via SQL. The transition is auditable via the `updated_at` touch trigger.

Batch operations supported: *"ratify all except 3"* or *"ratify all"* are valid for low-stakes batches.

### Q2 — `levi_response` semantics across statuses

| Action | Status transition | `levi_response` populated? |
|---|---|---|
| Ratify without comment | `pending-review` → `active` | NULL |
| Ratify with note | `pending-review` → `active` | the note |
| Correct/refine | `pending-review` → `active` | the corrected version |
| Reject without reason | `pending-review` → `archived` | NULL |
| Reject with reason | `pending-review` → `archived` | the reason |
| Defer | `pending-review` → `pending-review` | NULL (no transition) |
| Owner-initiated supersede of active observation | `active` → `superseded` | optional explanation |

`levi_response` is always *owner's voice*; never orchestrator's framing of owner's response. Quoted directly when possible.

### Q3 — `superseded_by` back-reference on posture

`superseded_by` is present on `owner_posture`, `owner_observations`, `orchestrator_observations`, and `team_observations`. When a posture or observation is superseded by a newer entry, the old row's `superseded_by` field points to the newer row's `id`. This enables the bi-temporal "what was the state on date X" query, consistent with the memory table's discipline.

### Q4 — `promoted-to-memory` link

When a posture or observation graduates to a memory row (during a reflection pass per the learning-designer's discipline, or by explicit owner instruction), the row transitions to `status='promoted-to-memory'` and the column `promoted_to_memory_id` carries the FK reference to the `memory` table row in `pka.db`. **The FK cannot be enforced across DBs** in SQLite — the application-layer discipline is that promotion is always paired with the memory row creation, and the integrity is maintained at the promotion-step itself, not via DB constraint.

### Q5 — `private` column for team-member readability

**Not needed.** `personal.db` is owner-only by location, not by row. The file lives outside the git working tree (configurable at install via `setup.py --personal-data-dir`; default `~/PKA-Data/personal.db`) and team-member personas have no access by default. The architectural posture is *privacy by file boundary*, not *privacy by row attribute*. If the orchestrator ever needs to surface a specific observation or posture to another persona (e.g., briefing the HR director on a persona-review-relevant observation), that surfacing is done explicitly through brief content — the persona reads what the orchestrator includes in their brief, not the underlying personal.db row. The brief content can quote or paraphrase; the row stays put.

If this becomes wrong in practice (e.g., the install discovers regular surfacing is needed and copying-into-briefs is friction), revisit and add per-row visibility. For now: privacy by location.

### Q6 — Observation capture-rate ceilings

No hard cap. Two soft disciplines:

1. **Surfacing-within-2-sessions** is the main pressure relief. Pending observations don't accumulate unread; if they're piling, the surfacing discipline fires.
2. **Pending-count soft threshold of ~10.** If `SELECT COUNT(*) FROM orchestrator_observations WHERE status='pending-review'` exceeds 10, orchestrator is over-capturing. The protocol's wisdom (hesitation-as-signal applies BUT discernment also applies) suggests pulling back on capture and being more selective. The threshold is informational, not enforced — but a session-open query can surface it for visibility.

Typical capture rate per session: 1-5 observations is healthy. 0 in a session is fine if there's nothing observation-worthy. 10+ in a session is over-eager and the threshold check fires.

## Known seams

Two structural seams the protocol must operationally address. (A third historical seam — closed by an originating-instance migration — has been folded into the canonical baseline and does not require a forward-going note here.)

### Seam A — `team_observations.observer` soft-validation convention

The `observer` column is open `TEXT NOT NULL` (no closed CHECK enum). The convention is: the value must be a lowercase first-name slug sourced from `lower(pka.db.team_members.name)`. Cross-DB FK enforcement is not possible in SQLite — `team_members` lives in `pka.db`, `team_observations` lives in `personal.db` — so soft-validation moves to application-layer code (any helper that inserts `team_observations` rows checks the observer value against the live `team_members` roster).

**Operational consequence:** the hiring runbook does NOT require a CHECK-widen migration on every new hire. New team members can write to `team_observations` as soon as their `team_members` row is inserted; no schema change required.

### Seam B — promoted_to_memory writeback path

The columns `promoted_to_memory_id` and the `'promoted-to-memory'` status are in the schema. The writeback path is owned by the learning-designer persona at reflection-pass apply-time. The promotion path:

1. During a reflection pass, the learning-designer identifies posture / observation rows that have proven durable across multiple sessions and warrant graduation to operations-tier memory.
2. The learning-designer proposes promotion candidates in the reflection-pass deliverable: for each candidate, the source row id, the proposed memory row body, the proposed memory `type` / `scope`, and the reasoning.
3. **Owner approves item-by-item** (same item-by-item review pattern as the existing reflection-pass approved-by-owner flow).
4. **The learning-designer (or orchestrator on the learning-designer's behalf) executes the writeback** via the `memory_io.promote_from_observation()` helper. The helper implements memory-first / link-second failure ordering inside a single ATTACHed transaction, with experimental verification that SQLite gives atomic rollback across two ATTACHed DBs for the common failure modes (constraint violations, lock contention, exceptions inside the transaction).

The writeback is paired with the proposal-and-approval flow that already exists for reflection passes. No new dedicated mechanism needed; the reflection-pass procedure document gains a brief addendum naming this as a category.

**Atomicity caveat — WAL journal mode.** The cross-DB atomic-commit guarantee holds **only under `journal_mode=delete`** (the default for both `pka.db` and `personal.db`). If either DB is ever flipped to WAL journal mode, the atomicity guarantee degrades and the "memory exists, link missing" failure window expands from microseconds to the full duration of the link step. The reconciliation query below becomes load-bearing under WAL; under the current delete-mode it is a residual safety net for OS/process-crash windows only. Before any future migration changes either DB's journal_mode, this protocol must be revisited.

**Reconciliation query.** Detects orphaned-promotion rows — memory rows whose `source_ref` points at a personal-tier observation, but where the observation row is not linked back. Run from a `pka.db` connection with `personal.db` ATTACHed:

```sql
WITH promoted AS (
    SELECT id AS memory_id, slug AS memory_slug, source_ref
    FROM main.memory
    WHERE source_ref LIKE 'owner_posture:%'
       OR source_ref LIKE 'orchestrator_observations:%'
       OR source_ref LIKE 'owner_observations:%'
       OR source_ref LIKE 'team_observations:%'
)
SELECT
    p.memory_id,
    p.memory_slug,
    substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) AS expected_source_table,
    CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER) AS expected_source_id,
    COALESCE(lp.status, lo.status, li.status, te.status) AS actual_source_status,
    COALESCE(lp.promoted_to_memory_id, lo.promoted_to_memory_id,
             li.promoted_to_memory_id, te.promoted_to_memory_id) AS actual_promoted_to_memory_id
FROM promoted p
LEFT JOIN personal.owner_posture lp
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'owner_posture'
   AND lp.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.orchestrator_observations lo
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'orchestrator_observations'
   AND lo.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.owner_observations li
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'owner_observations'
   AND li.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.team_observations te
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'team_observations'
   AND te.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
WHERE
    COALESCE(lp.promoted_to_memory_id, lo.promoted_to_memory_id,
             li.promoted_to_memory_id, te.promoted_to_memory_id) IS NULL
    OR COALESCE(lp.promoted_to_memory_id, lo.promoted_to_memory_id,
                li.promoted_to_memory_id, te.promoted_to_memory_id) != p.memory_id
    OR COALESCE(lp.status, lo.status, li.status, te.status) != 'promoted-to-memory';
```

The query is also available as `memory_io.RECONCILE_ORPHAN_PROMOTIONS_SQL` and as a one-call helper `memory_io.reconcile_orphan_promotions(conn)`. The learning-designer runs the reconciliation query at the end of each reflection-pass apply step; any returned rows are fixed by setting `promoted_to_memory_id` + `status='promoted-to-memory'` on the source row.

---

## Governance

Protocol proposed at template-baseline as inherited canonical discipline from the originating PKA instance. The four observation tables (`owner_posture`, `owner_observations`, `orchestrator_observations`, `team_observations`) ship at the post-rename canonical names from day one; the protocol document ships at v1.0 (template inception), with the discipline shaped through iterative refinement on the originating instance compressed into the operational form above.

**v1.0 (template inception):** Discipline captured as currently shaped — two trust shapes × four observer/subject pairings; demotion criterion operationalized as 2-reflection-pass window with five named operational thresholds; per-axis demotion permitted; deprecation lifecycle inheriting patterns/protocols shape; `team_observations.observer` open-string with soft-validation; `promote_from_observation()` writeback helper owned by the learning-designer at reflection-pass apply-time; reconciliation query as residual safety net.

**Promotion to `active`:** Owner reviews this protocol at install and either approves as-drafted or refines. Once approved, orchestrator begins operational capture per the trigger rules above.

**Demotion path:** Per the demotion criterion section above. Retirement is honest if the discipline doesn't hold in practice.

---

*Protocol #1 in the `protocols/` catalog. See [[README]] for the curation layer.*
