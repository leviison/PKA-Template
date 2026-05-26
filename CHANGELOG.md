# Changelog

All notable changes to PKA are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## Version bump guidance

- **Patch (x.x.N):** Bug fixes, minor protocol clarifications, small additive files (commands, tooling).
- **Minor (x.N.0):** New team member, new system layer or table, significant new capability (e.g., patterns layer, model routing, Learning Layer).
- **Major (N.0.0):** Fundamental rearchitecture — e.g., replacing the brief/DB model, restructuring the team model entirely, migrating to a new platform.

**Demotion-criterion changes (per the CLAUDE.md productization-discipline subsection):** adding a new productized tool with a demotion criterion is a minor bump (new system capability lands). Modifying an existing tool's demotion criterion is a patch bump (clarification of an existing capability).

Append a new entry at the **top** of the releases section each session close. Use the format below.

---

## Releases

## [1.2.1] — 2026-05-25

### Added

**Two new patterns ship at `proposed` status — a discipline-application family.** PATTERN-011 (probe-validity-discipline) codifies the discipline that fires *on the probe* when a probe returns a clean verdict the prober wants to trust: a four-frame audit (environment match, path traversal, success-condition match, state-not-under-the-probe), structurally different layering, and the principle that probe-result-affirming-my-hypothesis warrants *extra* suspicion. PATTERN-013 (scope-validity-discipline) codifies the discipline that fires *on the scope of a discipline's application*: name the discipline being applied, name its proper scope, name the actual application scope, close the gap if they differ. The two patterns are siblings — PATTERN-011 protects against bad-probe-of-correct-scope; PATTERN-013 protects against good-probe-of-wrong-scope. Together they constitute a new pattern family (Family 5 — *Discipline-application discipline*) that operates one level above the disciplines they govern. Both ship at `proposed` because their PKA-source empirical base (single-engagement clustering) does not transfer to template-instance use; each template-instance install starts the empirical base from zero and promotes to `validated` on first local firing.

### Changed

**`CLAUDE.md` Productization Discipline gains a reverse-direction clause on the template-baseline / rule-of-three relationship.** The existing template-baseline vs rule-of-three paragraph already named that template-baseline wins on the substrate-must-exist case; the new sentence completes the relationship by naming the converse case explicitly: when rule-of-three says "defer" but template-baseline says "ship" on validated-and-day-1-universal substrate, template-baseline wins because the discipline being closed there is speculation about the *current* operator, which the day-1 universality test resolves on its own terms. The clarification removes a class of ambiguity where the previous wording could be read as "template-baseline only beats rule-of-three when the substrate can't run without it."

**`patterns/README.md` curation layer adds Family 5 (*Discipline-application discipline*)** with PATTERN-011 and PATTERN-013 as the founding members, and adds both to the *Proposed patterns* section. The catalog status table updates from 6 validated / 1 proposed to 6 validated / 3 proposed.

**`setup.py` `pattern_seeds` block seeds PATTERN-011 and PATTERN-013 at `proposed` status.** Re-running `setup.py` on an existing v1.2.0 install adds the two new rows via `INSERT OR IGNORE`; no migration script required. Fresh installs get all 9 patterns from the start.

## [1.2.0] — 2026-05-25

### Added

**PKA installs now ship with a three-tier database architecture.** What used to be a single `pka.db` is now three databases with three responsibilities: `pka.db` (Operations — briefs, deliverables, patterns, protocols, memory, feedback, model routing, economics) lives at the repo root and is committed; `projects.db` (Projects — engagement-scoped assets, content, project-tier memory) lives at the repo root and is committed; `personal.db` (Owner — journal, tasks, notes, posture, observations) lives at a configurable location outside the repo (default `~/PKA-Data/personal.db`) and is never committed. The split protects template instances from cross-engagement leakage and protects owner-private data from accidental commits. `setup.py --personal-data-dir <path>` lets each owner choose where their personal tier lives; the chosen path is recorded in `pka.db.settings.personal_db_path` so every helper finds it without re-configuration.

**A productization discipline now governs every new tool the team ships.** A `### Productization discipline` subsection in `CLAUDE.md` Strategic Direction binds every future build-vs-defer decision to four checks: value-asymmetry as primary threshold (does this artifact let value happen without the original author or persona in the room, at the magnitude the persona-in-the-room produces?); rule-of-three and stable-interface as supporting checks (with a template-baseline lens that lets substrate ship before rule-of-three accrues); a demotion criterion at build approval (the condition under which the tool would retire honestly); vocabulary review (name the alternative framings the tool's API would suppress). The discipline also covers tool evolution (additive vs. substantive), periodic re-evaluation ("would we build this today?"), and the design-shape known-weakness clause (mechanical commonality may mask semantic divergence — promote to shared base only after a second tier empirically adopts the shape). The discipline applies to every productized tool the template owner ships from v1.2.0 onward.

**The team can now capture per-brief token economics automatically.** A new `economics` table in `pka.db` records `tokens_used` / `tool_uses` / `duration_ms` / `cache_hit_rate` / `total_cost_usd` per deliverable, plus an aggregate per-brief view. A `model_pricing` table ships pre-seeded with the three current Anthropic price rows (Sonnet 4.6, Opus 4.7, Haiku 4.5); the helper `economics_io.py` computes cost from pricing-snapshot lookup at deliverable-close time. The pricing snapshot is preserved at write — historical economics rows stay interpretable even after future pricing changes. Each deliverable row also carries `tokens_used` / `tool_uses` / `duration_ms` columns directly for at-a-glance visibility without joining.

**Cross-session safety now has a hooks-based safety net.** `hooks/pka_guard.py` is a Claude Code hook registered against `SessionStart` + `PreToolUse` + `Stop` + `SubagentStop`. It surfaces foreign sessions on open (so concurrent Claude Code sessions on the same repo are visible), blocks `brief_ref` numbering collisions with next-free suggestion, and blocks accidental `mv`/`rm`/`Write` against team_comms brief files the current session hasn't claimed. The hook is local-only — no network, no daemon, runs as user, read-only against `pka.db`, ~40ms median PreToolUse latency. It is a no-op until registered in `~/.claude/settings.json` (README explains the install snippet).

**A standing protocol layer codifies disciplines that fire automatically when triggers land.** `protocols/` is a new top-level directory holding protocols that complement patterns: where patterns codify *what discipline to apply at decision time*, protocols codify *what runs automatically when a trigger fires*. The catalog at `protocols/README.md` enumerates active protocols (currently one — owner observability) and explains the distinction. New protocols go through the same Intent-layer flow: Leroy proposes; the owner approves; the protocol moves through `proposed` → `active` → `retired`. Every protocol declares a demotion criterion at adoption so the discipline can retire honestly when it stops earning its keep.

**An owner-observability discipline gives the system a memory for who the owner is.** Four new tables in `personal.db` — `owner_posture`, `owner_observations`, `orchestrator_observations`, `team_observations` — capture the four observer/subject pairings the team needs to learn the principal it serves: the owner's framing about PKA, the orchestrator's reading of the owner's decision style, the owner's observations about the orchestrator or any team member, and team members' observations about each other and the orchestrator (the chief-of-staff axis that public agent-system practice doesn't have). Two trust shapes govern writes: owner-authored rows land at `active`; orchestrator- or team-authored rows land at `pending-review` and wait for the owner's explicit ratification. The discipline is owner-private by file boundary — `personal.db` lives outside the git working tree at the configurable install location. Discipline document at `protocols/owner_observability.md`.

**Six validated patterns ship as starting catalog.** `patterns/` now contains PATTERN-001 (sequential-overnight-build), PATTERN-002 (single-consumer-event-stream), PATTERN-003 (persona-gap-triggered-hire), PATTERN-004 (multi-lens-parallel-critique), PATTERN-005 (audit-then-execute-structural), and PATTERN-006 (empirical-probe-before-design). Each documents when to use, when NOT to use, the shape, what protects against failure, and validated-instance evidence. The `patterns/README.md` curation layer organizes the catalog by family and explains how to read the catalog, propose additions, and govern promotion through `proposed` → `validated` → `deprecated`. PATTERN-007 (domain-engagement-template) also ships, at `proposed` status — a domain-agnostic engagement workflow that earns `validated` after a first template-instance domain runs through it.

**Briefs and deliverables can now carry source-material pointers and project tags.** Two new columns: `briefs.source_material` (free-form text — file path, URL, video title + date, short description of what triggered the brief) and `briefs.project_slug` (the engagement slug when the brief touches a specific project). The `source_material` column also lands on `deliverables` and default-copies from the parent brief at write time, so a deliverable is independently queryable months later without re-reading the brief. Together these columns make every brief and deliverable answer "what triggered this?" and "which engagement does this belong to?" without external context.

**Projects-tier memory carries engagement-scoped facts without polluting operations.** `projects.db.memory` (and its FTS5 mirror) is the engagement-scoped sibling of the operations-tier `memory` table: facts that belong to one engagement (deployment topology, environment quirks, host facts, project-scoped operational discipline) live there, anchored to a `projects.db.projects` row via FK. The Session Open Protocol now runs a two-read shape: full load of operations-tier memory (cross-engagement discipline), then a small universal-load of projects-tier memory (engagement-spanning topology / environment / host_fact rows that apply regardless of which engagement the session touches). When a brief touches a specific engagement, Leroy follows up with a per-project lazy load. The split protects operations-tier from being pre-loaded with another owner's engagements when the template ships.

**A `leroy_rates_levi_audits` feedback model is available at install** (default at v1.2.0). The orchestrator auto-rates routine deliveries with substantive notes; the owner audits a sample at configurable cadence (default 7 days, `settings.audit_cadence_days`); owner-rated rows always supersede orchestrator-rated rows for the same `(brief_ref, team_member)` pair. Per-brief escalation preserved — Leroy or the persona may flag judgment-laden briefs for owner-direct rating regardless of the default model. Owners who prefer continuous ritual can switch with one UPDATE: `UPDATE settings SET value='ritual' WHERE key='feedback_model'`.

**A tools catalog at `TOOLS.md` documents every productized tool with its demotion criterion.** Seven tools ship in this version: `archive.py` (three-tier-aware compaction), `check_names.py` (snake_case validation with instrumented JSONL logging + `--evaluate-demotion-criterion` mode), `memory_io.py` (write contract for operations-tier memory + cross-tier promotion helper), `projects_memory_io.py` (write contract for projects-tier memory), `economics_io.py` (per-brief token economics capture), `tools/status_now.py` (read-only tmux-pane status snapshot), and `hooks/pka_guard.py` (cross-session safety hook). Each tool carries its demotion criterion in its top-of-file docstring; the catalog mirrors the criteria for proximity-of-reading. New tools join `TOOLS.md` per the discipline named in `CLAUDE.md`.

### Changed

**`setup.py` is now a three-tier installer.** Same single-command experience (`python3 setup.py`) creates all three databases, seeds the founding two-person team (Sam + PAX), seeds Anthropic model providers + pricing, records the personal-tier location in `settings`, and applies six baseline migrations across the three tiers. The `--personal-data-dir <path>` flag lets owners pick where their personal tier lives. Idempotent — re-running `setup.py` on an existing install confirms per-DB overwrite independently, so an owner can rebuild `pka.db` without touching `personal.db`.

**The DB schema documentation (`DB_SCHEMA.md`) now reflects three tiers** — a top-of-document tier table identifies which database holds which substrate, with ATTACH DATABASE worked examples for cross-tier reads and writes. The historical single-tier framing is gone; the three-tier discipline is the install reality from v1.2.0 onward.

**The Session Open Protocol now runs a two-read memory load** — operations-tier (cross-engagement discipline; full load) followed by projects-tier universal-small-load (cross-engagement topology / environment / host_fact rows). When a brief touches a specific engagement, Leroy follows up with a per-project lazy load. On a fresh install both reads return zero rows.

**The Hiring Process now requires every new shim to declare `load_profile` and `default_load_types`** in YAML frontmatter — the convention that lets each persona load its relevant slice of memory at invocation time without burning tokens on irrelevant rows.

**Diagram 2C (pka.db schema) loses `assets` and `content` (moved to projects.db) and gains `source_material` / `project_slug` / `rater` / `memory.scope` enum annotation / `economics` / `model_pricing`.** New diagram 2C-b (personal.db) gains the four observability tables. New diagram 2C-c documents projects.db. Diagram 2A (folder structure) gains `patterns/`, `protocols/`, and `projects.db` nodes; the `personal.db` label now enumerates all seven tables and notes the configurable install location.

**`memory.scope` enum is canonical owner-neutral from day one.** The scope enum reads `'global' | 'owner_only' | 'team_member:<slug>'` — no historical `'levi_only'` value exists in the template baseline. Personal-tier observability tables use canonical `owner_*` / `orchestrator_*` naming from v1.2.0 install.

### Notes for v1.2.0+ owners

A few items shipped in v1.2.0 are subject to demotion criteria; if the discipline they enforce stops earning its keep in your install, retire honestly per the named conditions. The notable ones:

- **`owner_observability` protocol** — demotion fires after two reflection passes if observation captures aren't surfacing value (five operational thresholds documented in the protocol).
- **`hooks/pka_guard.py`** — demotion fires when a native cross-session-coordination subsystem replaces the hook.
- **`leroy_rates_levi_audits` feedback model** — if the failure modes named in the founding proposal (silent orchestrator bias, low-signal ratings, persona gaming, audit fatigue) emerge in your install, revert to `ritual` with one UPDATE.

The discipline is to retire on the named condition, not to maintain the tool past its value. Each tool and protocol carries its own demotion criterion in the artifact itself.

---

## [1.1.0] — 2026-05-16

### Added

**PKA installs ship with a durable memory layer.** A `memory` table in `pka.db` (with markdown mirrors in `memory/`) carries user facts, project state, feedback patterns, pedagogy, preferences, and operational discipline from one session to the next. The DB is authoritative; the markdown mirror keeps the same facts git-readable and human-editable. Each persona's dispatch shim (`.claude/agents/<slug>.md`) declares a `load_profile` and reads its relevant slice of memory on every invocation — treating the rows as priors alongside `CLAUDE.md` and the persona file.

**A monthly reflection pass keeps memory consolidated.** The Learning Designer runs a calendar-anchored monthly pass (with a volume override when ≥40 new feedback rows or a major architectural event have accumulated) that proposes ADD / UPDATE / SUPERSEDE / INVALIDATE / NOOP operations against the `memory` table. The owner approves item-by-item in chat; Leroy applies via `memory_io`. The procedure is documented in `owners_inbox/reflection_pass_procedure.md`. The pass does not write to the Intent layer — Intent-layer items surface as separate deliverables.

**A migration framework supports future schema evolution.** New owners can grow `pka.db`'s schema via numbered SQL files in `migrations/`, applied with `python3 migrations/migrate.py up`. Each migration carries an UP block and a DOWN block separated by a `-- +migrate Down` marker. The runner records applied migrations in the `schema_migrations` table. Migration 001 (the `memory` table itself) ships pre-applied via `setup.py` so the install experience stays single-script.

**Leroy now loads memory context at session open.** A new step in the Session Open Protocol queries the `memory` table for all active rows and carries the result into the conversation as durable working context. On a fresh install the table is empty; rows accumulate through ad-hoc `memory_io.write_memory_row()` writes and through reflection-pass promotions.

**Leroy surfaces when a reflection pass is due.** A new Session Open step checks whether the calendar floor has been crossed or the volume threshold has been hit since `last_reflection_pass_at`. If either fires, Leroy asks whether to run the pass this session or defer.

### Changed

**`setup.py` creates two new tables (`memory`, `schema_migrations`)** and seeds `last_reflection_pass_at` with an epoch sentinel so the first session correctly observes "no pass has ever run." Idempotent — re-running `setup.py` on an existing install does not duplicate seed rows.

**`CLAUDE.md` Session Open Protocol now has 6 steps** (was 4): naming check, backlog surfacing, pattern surfacing, reflection-pass-due check, the no-block rule, and memory-context load.

**The Learning Layer section in `CLAUDE.md` now includes the Reflection Pass subsection** describing the monthly cadence, volume override, governance flow, and the no-Intent-layer-writes rule.

**Diagram 2C now reflects the `memory` + `memory_fts` blocks** in the entity-relationship view.

---

## [1.0.0] — template-initial

### Added

**You start with a two-person team.** Sam (HR Director) and PAX (Senior Researcher) are live from day one. Sam runs hiring and persona reviews; PAX handles deep research and asset processing. To grow the team, tell Leroy what you need — Sam and PAX will research the role and present a hire proposal for your approval before anyone goes active.

**Every task is tracked in a structured database.** `pka.db` comes with 13 tables out of the box: briefs, deliverables, feedback, journal, knowledge, backlog, case studies, patterns, model providers, and more. FTS5 full-text search is enabled on all major text tables. Run `python3 setup.py` once to create it.

**A browser-based viewer lets you read and search your DB without any server.** Open `owners_inbox/pka-viewer/index.html` in Chrome. Click a DB file to load it — no server, no install. Browse journal, knowledge, briefs, assets, backlog, and feedback with search.

**A workflow diagram shows your team and how work flows.** Open `owners_inbox/pka-workflow/index.html`. Connect your `pka.db` to see the live team layer rebuild from the `team_members` table. The Engineering tab has four structural diagrams: folder layout, brief lifecycle, DB schema, and asset data flow. The System tab shows pending proposals, recent changelog entries, and current capability status.

**The session open and close are structured routines.** Every session starts with naming-violation checks, open backlog surfacing, and net-new pattern alerts. Every session ends with a summary file, a DB timestamp update, a CHANGELOG entry, and a git push — so the next session starts with full context.

**A patterns layer lets the team re-use proven shapes of work.** The `patterns/` folder and `patterns` DB table track validated operational templates. When a way of working proves itself in practice, it gets codified here rather than re-derived each session. The Session Open Protocol surfaces any new validated patterns automatically.

**A Learning Layer turns every delivery into a teaching artifact.** After every non-trivial delivery, the Learning Designer runs an After Action Review and produces an HBS-style case writeup (~800 words). Writeups live in `case_studies/` and are indexed in `pka.db`. This is the raw material for an executive learning program or personal teaching corpus.

**Model routing is built in from the start.** The DB includes `model_providers` and `task_type_models` tables. Leroy routes work to Opus 4.7 / Sonnet 4.6 / Haiku 4.5 based on the character of the task — synthesis vs. implementation vs. mechanical ops. Per-brief overrides are first-class. Multi-provider routing (Perplexity, Ollama, etc.) is architecturally ready; it activates with a single settings flip when you're ready to wire a second provider.

**A `/close-session` slash command makes session close a one-step routine.** `.claude/commands/close-session.md` is a scaffold that mirrors the Session Close Protocol in CLAUDE.md. It runs eight steps in order: summary, DB timestamp, CHANGELOG entry, staged adds, git status review, commit, and push.

**The install questionnaire sets your name so Leroy addresses you correctly.** Run `python3 setup.py` and answer one question. Leroy addresses you by name from the first session.

**Personal data stays private by design.** `personal.db` lives outside the repo at `~/Documents/PKA-Data/personal.db`, never committed, never mixed with operational data. The boundary is architectural, not disciplinary.
