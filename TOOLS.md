# Tools — Catalog

Productized tools in PKA. Each entry includes the demotion criterion per
the `CLAUDE.md` productization-discipline subsection. Demotion criteria
are durable across sessions; they are updated only via Leroy-drafted,
Levi-approved deliverable.

This file is the cross-cutting view. The same criterion text also lives
in each tool's top-of-file docstring (`## Demotion criterion` section)
for proximity-of-reading; the two surfaces must stay identical. If they
drift, the docstring and this catalog are both wrong until a new
Leroy-drafted, Levi-approved deliverable reconciles them.

Paths below are written relative to `<PKA_ROOT>` — the directory in
which this PKA instance is installed. Each tool resolves its own
location via `Path(__file__).resolve().parent[.parent]` so the tools
themselves are portable; only this catalog needs to know the install
root.

---

## `archive.py`

**Purpose.** Moves completed ephemeral content (briefs, deliverables,
assets, patterns) from active folders to `archive/` and updates the
corresponding `pka.db` status atomically. Replaces hard-delete
compaction with move-to-archive so DB and disk stay in sync and content
remains recoverable from git history.

**File.** `<PKA_ROOT>/archive.py`

**Demotion criterion.** Split criterion.

Write-path: retire `archive.py`'s move-and-update operation when
either:

- (a) PKA's compaction discipline changes — e.g., briefs become
  immutable-from-creation with no archive step, or the brief lifecycle
  eliminates the open->complete->archive transition entirely, OR
- (b) A more general DB-row-and-file-coordination tool subsumes the
  function (the dual-mirror generalization is the most likely candidate
  — see BACKLOG-040 / dual_mirror_io.py from PAX BRIEF-142 §2.1 §5/test
  case 7, which would handle DB+file coordination across patterns,
  case_studies, memory, *and* the archive operation).

Read-path: permanent infrastructure as long as the `archive/` directory
exists and DB rows reference archived state. The read-path retires only
if PKA stops indexing archived rows or deletes the `archive/` tree —
neither has a current candidate.

**Last evaluated.** 2026-05-20

---

## `check_names.py`

**Purpose.** Scans the PKA directory tree for files and folders with
spaces in their names, surfacing violations before they enter
discipline drift. Run at session-open per the Session Open Protocol.

**File.** `<PKA_ROOT>/check_names.py`

**Demotion criterion.** Single criterion (no historical-data
interpretability — `check_names.py` is a validator that produces no
historical data; the output is the validation result, not a dataset).

Retire `check_names.py` when either:

- (a) The naming convention is enforced by a different mechanism —
  pre-commit hook in `.git/hooks/`, IDE integration, CI step, OR
- (b) A 90-day window passes with zero violations detected while the
  team continues to create new files at a normal rate (signal that the
  discipline is internalized and the check is no longer earning its
  keep — magnitude-of-value falls below the standing-tool threshold).

**Last evaluated.** 2026-05-20

---

## `memory_io.py`

**Purpose.** Owns the contract from `memory` row to `memory/<slug>.md`
markdown file. All durable writes to the memory table go through this
module, which manages the supersession chain, the dual-mirror
discipline, and (as of BRIEF-146) cross-tier promotion from observation
tables in `personal.db`.

**File.** `<PKA_ROOT>/memory_io.py`

**Demotion criterion.** Split criterion.

Write-path: retire the write-path when either:

- (a) The memory substrate changes substantively — `memory` schema is
  replaced by a different durable-knowledge model (e.g., external
  vector store, different table shape, multi-provider memory
  federation), OR
- (b) The dual-mirror discipline graduates to `dual_mirror_io.py` (PAX
  BRIEF-142 §2.1 §5/test case 7) — at that point `memory_io.py`'s
  mirror-writing becomes a thin wrapper around the shared base, and the
  write-path is *refactored*, not retired. (The refactor is itself an
  identity-changing tool evolution per the CLAUDE.md productization
  discipline — *"A tool's identity-changing evolution... is a fresh
  productization decision subject to the threshold."* When
  dual_mirror_io.py is commissioned, it triggers a re-check of
  `memory_io.py`'s value-asymmetry case against the smaller residual
  surface.)

Read-path: permanent infrastructure as long as the `memory` table
exists. The read helpers (`load_memory_rows()`, `get_memory_row()`,
FTS5 query wrappers) are how all other code reads memory durably. They
retire only if the `memory` table is removed entirely — no current
candidate.

Note: the cross-tier `promote_from_observation()` helper added in
BRIEF-146 inherits the same write-path criterion (it's part of
`memory_io.py` and shares its lifecycle).

**Last evaluated.** 2026-05-20

---

## `projects_memory_io.py`

**Purpose.** Sibling to `memory_io.py`. Owns the contract from
`projects.db.memory` rows to their markdown mirror at
`memory/projects/<project_slug>/<slug>.md`. All durable writes to
project-tier memory should go through `write_project_memory_row()`.

Shares private internals (`_atomic_write`, `_render_markdown`,
`_row_to_dict`) with `memory_io` via direct import — NOT a shared base.
Per BRIEF-215 §8.2 and the CLAUDE.md design-shape rule-of-three
discipline, the empirical-adoption test for a `dual_mirror_io.py`
shared base has not yet fired — promotion is gated on a third tier
actually adopting the proposed shared base in production.

**File.** `<PKA_ROOT>/projects_memory_io.py`

**Demotion criterion.** Split criterion (mirrors `memory_io.py`).

Write-path: retire when either:

- (a) The projects-tier memory substrate is replaced by a different
  durable-knowledge model, OR
- (b) The dual-mirror discipline graduates to `dual_mirror_io.py` — at
  that point this file's mirror-writing is REFACTORED to wrap the
  shared base, not retired.

Read-path: permanent infrastructure as long as `projects.memory`
exists.

**Last evaluated.** 2026-05-25 (introduced)

---

## `economics_io.py`

**Purpose.** Captures token economics per deliverable — input/output
tokens, cache hit rate, cost, provider attribution. Built in BRIEF-127
on single-instance value-asymmetry evidence (instrumentation wouldn't
have landed otherwise) — which retroactively motivated the
instrumentation-exception class named in CLAUDE.md's productization
discipline (per PAX BRIEF-142 §5.1).

**File.** `<PKA_ROOT>/economics_io.py`

**Demotion criterion.** Split criterion. `economics_io.py` lives in the
named exception class (instrumentation) per CLAUDE.md's productization
discipline. Its supporting checks (rule-of-three, stable-interface)
are recorded as deferred-evidence-pending; the retroactive
supporting-check evaluation fires after enough deliverables have been
instrumented to assess whether the value-asymmetry case holds at
present-day workflow. The demotion criterion below is independent of
that evaluation — a tool can be in deferred-evidence-pending status
and still have a defined demotion criterion.

Write-path: retire the write-path when any of:

- (a) Token economics capture moves to a harness-level post-completion
  hook architecture — the seam moves out of the persona-side helper
  into the harness, and `economics_io.py` becomes redundant for new
  captures, OR
- (b) The economics-data shape changes substantively — multi-provider
  routing activates (`multi_model_enabled=true`) and the `economics`
  table requires a different write contract that this helper's
  signature can't accommodate cleanly, OR
- (c) The deferred-evidence-pending supporting checks fail their
  post-deployment evaluation — i.e., the retroactive rule-of-three /
  stable-interface review concludes that economics_io.py shouldn't
  have been built and the instrumentation should have been done
  differently. (This is the discipline's self-corrective path; if it
  fires, it's an instructive case rather than a routine retirement.)

Read-path: permanent infrastructure. Historical token-economics data
is interpretable forever — cost trends, model-migration cost analysis,
owner-vs-team economics ratios, productization cost-vs-benefit
projections all depend on it. The `economics` table's read-path
retires only if PKA's economics-instrumentation discipline is
abandoned entirely, which would itself be a separate Intent-layer
decision.

**Last evaluated.** 2026-05-20

---

## `tools/status_now.py`

**Purpose.** Read-only snapshot of `pka.db` rendered for a ~40-column
tmux pane. Intended to be polled with `watch` so the owner can keep a
corner of the screen showing what's running across sessions and what
just landed — the cheap-first stand-in for a future native sessions
table + Live viewer tab.

**File.** `<PKA_ROOT>/tools/status_now.py`

**Demotion criterion.** Event-based. Retire `status_now.py` when
**either**:

- (a) PKA grows a native `sessions` table plus a Live viewer tab that
  registers active subagents at dispatch and reads them back — i.e.,
  the production-direction-aligned C2 build that this script is the
  cheap-first stand-in for. At that point the watcher's information
  shape is subsumed by a richer surface and the script retires cleanly
  with a single `rm`.
- (b) The brief lifecycle changes such that the columns this script
  reads (`briefs.status`, `briefs.completed_at`, `deliverables.brief_id`,
  `backlog.status`) no longer carry the semantics this snapshot depends
  on — e.g., briefs become immutable-from-creation with no
  open/complete transition, or deliverables move to a separate tier.

If neither condition fires but the owner simply stops opening the pane
for two weeks of active sessions, that's the silent-erosion signal —
flag at the next session open and reconfirm the script earns its keep,
per the periodic-revisit clause in CLAUDE.md productization discipline.

The write/read split does not apply here: this tool has no write path
and produces no historical data that would need to remain interpretable
after the read path retires. Single retirement event, clean delete.

**Last evaluated.** 2026-05-25 (introduced from PKA v1.9.0)

---

## `hooks/pka_guard.py`

**Purpose.** Claude Code hook handler registered against `SessionStart`,
`PreToolUse`, `Stop`, and `SubagentStop` in `~/.claude/settings.json`.
Prevents cross-session pain events: surprise foreign-session
commissioning, brief_ref collision on write, accidental `mv`/`rm`
clobbering a peer session's brief file. Local-only, no network egress,
no daemon, no auth surface; runs as the user with read-only DB access.

**File.** `<PKA_ROOT>/hooks/pka_guard.py`

**Installation.** The hook is a no-op until registered. See
`owners_inbox/pka_guard_rowan.md` for the `~/.claude/settings.json` edit
the owner applies. Template installs should follow the same hook-block
paste step at first-run time; documented in this template's
`README.md`.

**Demotion criterion.** Event-based. Retire `hooks/pka_guard.py` when
**either**:

- (a) PKA grows a native `sessions` table plus a dispatch-time session
  registration mechanism — the C2-tier build that Mara's BRIEF-194
  named as the rule-of-three-pending C2 substrate. At that point a
  single shared substrate replaces the filesystem-based session
  registration, and the brief-collision check should live in the
  dispatch layer (Leroy's brief writer) rather than in a hook
  intercepting the file-write. The hook retires; `pka.db`'s
  `briefs.brief_ref` UNIQUE constraint plus dispatch-time allocation
  carries the load.
- (b) Claude Code ships native cross-session locking or a brief/task
  ownership primitive that subsumes the protections this hook
  provides — i.e., the harness solves the problem we built this for.

Silent-erosion check: if neither event fires but the three pain classes
this hook prevents stop occurring even when it's disabled for a
session, that's the signal to retire it. Per the periodic-revisit
clause, the "would we build this today?" question fires at the next
Session Open quarterly checkpoint.

Write/read split does not apply: this tool produces no historical data.
Single retirement event, clean `rm hooks/pka_guard.py` plus a
`~/.claude/settings.json` edit removing the hook block.

**Last evaluated.** 2026-05-25 (introduced from PKA v1.8.x)

---

## How to add a new tool

The productization discipline applies prospectively to every new tool.
When commissioning a new productized tool:

1. **At build-brief time** — the brief commissioning the new tool names
   the proposed demotion criterion as part of the brief body. Levi
   reviews and approves the criterion at the same moment he approves
   the build.
2. **At first-deployment time** — the tool's docstring includes the
   `## Demotion criterion` section from inception (use the format above
   — criterion text + `Source:` line referencing the approving
   deliverable).
3. **At catalog time** — `TOOLS.md` gains an entry in the same commit
   that lands the new tool. Entry includes purpose, file path,
   demotion criterion (identical text to the docstring), and the
   last-evaluated date (approval date).
4. **At periodic re-check time** — the *"would we build this today?"*
   question (CLAUDE.md productization discipline, last paragraph)
   fires at Session Open quarterly checkpoint or reflection-pass when
   stable. Existing tool entries' demotion criteria are re-validated
   against current state.

Adding a tool without a demotion criterion is a discipline violation —
the build is held until the criterion is named.

---

*Catalog maintained per CLAUDE.md > Strategic Direction > Productization
discipline. Retroactive criteria for the four original tools landed via
`owners_inbox/tool_demotion_criteria_proposal.md` (Levi-approved
2026-05-20) and BRIEF-148. New entries for `projects_memory_io.py`,
`tools/status_now.py`, and `hooks/pka_guard.py` added at template
snapshot 2026-05-25 (BRIEF-226).*
