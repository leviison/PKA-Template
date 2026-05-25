# TRAINING.md — How PKA Was Built and Why

*A narrative of the design decisions behind the Personal Knowledge Agency system. Read this if you want to understand why things work the way they do — and how to adapt the system for your own use.*

---

## The Core Idea

Most people use Claude as a single assistant. You ask it something, it answers, you move on. That works fine for one-off tasks. But it has a real problem: **the assistant has no persistent identity, no memory of who it's supposed to be, and no consistent work style across sessions.**

PKA takes a different approach. Instead of one assistant, you have a **small team of named, specialized personas** — each defined in a profile file, each with a distinct voice and responsibility. An orchestrator called **Leroy** coordinates the team and is the only face you ever see.

The result feels less like using a tool and more like working with people.

---

## Why an Orchestrator?

The most important design decision in PKA is that **Leroy never does the work.**

This is counterintuitive. Why add a layer that doesn't produce output?

Three reasons:

1. **Routing clarity.** When you bring something to Leroy, you don't have to decide who should handle it. That's Leroy's job. You describe what you need; Leroy matches it to the right team member. Over time, this routing becomes fast and natural.

2. **Persona integrity.** When PAX speaks, they sound like PAX — methodical, dense, research-focused. When Sam speaks, they're warm and HR-brained. If the same entity did everything, the personas would blur. The orchestrator enforces the boundary.

3. **Scalability.** The team grows. Leroy's interface doesn't change. You always talk to the same person. The complexity of who handles what stays invisible.

The non-negotiable rule is in `CLAUDE.md`: *"You never do the work."* Leroy never writes a report, never produces a deliverable, never answers a research question. If a task comes in that no one can handle, Leroy escalates to Sam to hire someone.

---

## The Brief/Compaction Pattern

Early versions of AI-assisted workflows have a token problem: every session re-reads the entire conversation history to establish context. As work accumulates, this gets expensive and slow.

PKA solves this with the **brief-as-file pattern.**

When Leroy routes a task, they write a brief file to `team_comms/brief_[ref].md`. The team member reads that file — not the conversation. The brief is self-contained: context, requirements, and any relevant background. No need to scan the entire conversation history.

When the task is complete:
- The brief file is **moved** to `archive/team_comms/` via `archive.py` (tracked in git)
- The `briefs` record in the DB is updated to `status=complete`
- The deliverable is logged in the `deliverables` table
- The content is preserved forever in the DB

This is **compaction.** The working file moves to archive. The knowledge stays. The next session starts clean.

The implication: `team_comms/` should always be nearly empty. If it has old briefs in it, something didn't complete properly.

*Note: older documentation described deleting the brief file. The current system moves it to `archive/team_comms/` instead — recoverable in git history, without cluttering the working tree.*

---

## The Database as Connective Tissue

`pka.db` is a SQLite file. It is not a backup — it is the system's memory.

Every meaningful thing that happens gets written to one of three databases:

**`pka.db` — Operations tier.** Briefs, deliverables, feedback, journal, knowledge, backlog, patterns, protocols, case studies, model routing, per-brief token economics, durable memory. The team's substrate. Committed to the repo so the operating discipline accumulates in git history.

**`projects.db` — Projects tier.** Files dropped in for processing (assets table), content extracted from those files (content table), and engagement-scoped memory (`projects.db.memory` — facts that belong to one engagement, like deployment topology or environment quirks, that would not generalize across owners or projects). Committed to the repo. Lives alongside `pka.db` at the repo root.

**`personal.db` — Owner tier.** Journal, tasks, notes, posture, and observations — the owner's personal layer. Lives **outside** the git working tree at `~/PKA-Data/personal.db` by default (the location is configurable at install via `setup.py --personal-data-dir`). Never committed. The boundary is architectural — the file isn't in the repo at all — not just disciplinary.

The split is load-bearing for the production direction. When PKA-Template ships to another owner, the operations tier carries the discipline the team accumulated; the projects tier is empty (the new owner's engagements aren't ours); the personal tier is per-owner because the file itself is per-owner. Three databases, three responsibilities, three lifecycles.

**FTS5 full-text search** is enabled on all major text tables. This means you can search across everything — journal entries, knowledge base, briefs, extracted content — without any external search infrastructure.

The DB also powers the live workflow diagram. When you hire a new team member, they're added to `team_members`. The diagram reads that table and rebuilds the team layer automatically on refresh.

One design choice worth noting: in a live PKA instance, `pka.db` is committed to the private repo (for backup purposes). In this template repo, it is gitignored — it's generated by `setup.py` and contains no data worth committing.

---

## The Memory Layer

`pka.db` also includes a `memory` table — PKA's durable cross-session memory. Rows hold user facts, project state, feedback patterns, pedagogy, preferences, and operational discipline. The DB is authoritative; `memory/<slug>.md` is a markdown mirror written by `memory_io.py` so the same facts are git-readable and human-editable.

Each persona shim (`.claude/agents/<slug>.md`) declares a `load_profile` (`narrow` / `type-filtered` / `full`) and a `default_load_types` list. On every invocation, the shim runs a parameterised SQL query against `memory` and treats the returned rows as priors — the same weight as `CLAUDE.md` and the persona file. Leroy uses the full load profile at session open (CLAUDE.md Session Open step 6) so the orchestrator carries the team's accumulated context into every conversation.

A fresh install ships with an empty `memory` table — the structure is there, but no rows. Rows accumulate two ways:

1. **Ad-hoc writes through `memory_io.write_memory_row(...)`** — Leroy writes a row when the owner says something durable ("from now on, always …"), or when a feedback pattern hardens into a rule.
2. **Reflection pass** — the Learning Designer runs a monthly pass against the table (calendar-anchored, with a volume-override when ≥40 new feedback rows have accumulated). The pass proposes ADD / UPDATE / SUPERSEDE / INVALIDATE / NOOP operations against existing memory; the owner approves item-by-item; Leroy applies via `memory_io`. The procedure is documented in `owners_inbox/reflection_pass_procedure.md`. The reflection pass does NOT write to the Intent layer (CLAUDE.md, personas, patterns) — Intent-layer items surface as separate deliverables.

Schema changes (now and in the future) land via the migration framework in `migrations/`. Migration 001 (the `memory` table itself) ships pre-applied; numbered SQL files in `migrations/NNN_<slug>.sql` are how new owners evolve the schema as their use case develops.

### Cross-engagement vs. engagement-specific memory

The memory layer has two homes from v1.2.0 onward. `pka.db.memory` holds *cross-engagement discipline* — user facts, feedback patterns, operational discipline, pedagogy that applies regardless of which engagement the team is working on. `projects.db.memory` holds *engagement-specific facts* — deployment topology, environment quirks, host facts, project-scoped operational discipline that belongs to one engagement and would not generalize.

The Session Open Protocol now runs a two-read shape: a full load of operations-tier memory, plus a small universal-load of projects-tier memory (cross-engagement topology / environment / host_fact rows that apply regardless of which engagement the session touches). When a brief touches a specific engagement, Leroy follows up with a per-project lazy load.

Why the split: when PKA-Template ships to another owner, the operations tier carries the discipline the team accumulated; the projects tier ships empty (the new owner's engagements aren't ours). Without the split, a new owner would inherit the previous owner's deployment topology and environment quirks. With the split, the substrate ships empty and the new owner's projects fill it as they accumulate.

---

## The Feedback Loop

Every delivery triggers a feedback request. Leroy asks: *"Quick rating for [Name] on this one? 1–5, and any notes."*

This isn't just a nice-to-have. It's the mechanism by which your AI team improves.

The feedback is stored in the `feedback` table with the team member's name, the brief reference, the rating, notes, and which feedback model was active. Over time, patterns emerge.

The **persona review trigger** (`Sam, review [Name]`) is how those patterns get applied. Sam reads the full feedback history for a team member, identifies what they consistently do well and where they fall short, and updates the persona file. No changes without evidence.

Three feedback models are available:

| Model | Use when |
|---|---|
| `ritual` | You want consistent feedback discipline — every delivery, no exceptions |
| `on_demand` | You only want to log feedback when it feels significant |
| `self_reflect` | You want the team member to self-assess before delivery — experimental, useful for stretching quality |

Change the active model by updating the `settings` table.

---

## Hiring: Grounded in Real Expertise

PKA uses a two-step hiring process designed to prevent AI personas from being vague or generic.

Step 1: PAX researches what a real human expert in the target role actually knows, does, and cares about. The research report has a fixed format: core skills, depth markers, tools, work style traits, red flags, and persona hooks.

Step 2: Sam takes that research and builds a complete AI persona — name, identity, backstory, expertise profile. Sam presents a hire proposal to the owner for approval. **No one goes active without owner sign-off.**

This is important. An AI persona that's built on real research about the field is noticeably better than one that's just described as "an expert." PAX's job is to ground the persona in what senior practitioners in that field actually look like.

When a new hire is approved, Sam also creates a dispatch shim at `.claude/agents/<slug>.md`. The shim is what makes the persona a native Claude Code subagent — without it, the persona can't be dispatched as a subagent. **A hire isn't fully operational until both `team/<NAME>.md` and `.claude/agents/<slug>.md` exist.**

---

## The Patterns Layer

One thing that becomes clear after a team runs for a while: the same shapes of work recur. A multi-lens parallel review. A sequential overnight build. A structured research sprint followed by synthesis.

Re-deriving the right shape each time is waste. The **patterns layer** captures proven shapes as reusable templates.

Each pattern file in `patterns/` documents:
- **When to use / when NOT to use** — preconditions and disqualifiers
- **Shape** — the steps the work flows through
- **What protects against failure** — the constraints that make it work
- **Validated instances** — concrete brief refs + outcomes

Six patterns ship at install (PATTERN-001 through PATTERN-006, all `validated`). One more ships at `proposed` status — PATTERN-007 (domain-engagement-template) — earning `validated` after a first template-instance domain runs through it. See `patterns/README.md` for the family taxonomy and the discipline for proposing new patterns.

A standing protocol layer (`protocols/`) complements patterns. Where patterns codify *what discipline to apply at decision time* (Leroy reads a pattern when commissioning a brief; the engineer reads it when designing a contract), protocols codify *what discipline runs automatically when a trigger fires*. One protocol ships at install: `owner_observability.md`, the four-axis capture-and-review discipline that gives the system a memory for who the owner is. See `protocols/README.md` for the protocols-vs-patterns distinction.

Patterns go through a status ladder: `proposed` → `validated` → `deprecated`. Leroy proposes; the owner approves. The Session Open Protocol surfaces any patterns that reached `validated` status since last session — so you don't miss something the team learned while you were away.

The distinction from case studies matters: case studies teach executives *principles* from specific situations (commissioner-mode learning). Patterns are operational templates *for the team itself* — Leroy reaches for a pattern the way a senior engineer reaches for a known architecture.

---

## The Learning Layer

PKA embeds learning into the operating model, not as an add-on.

After every non-trivial delivery, the Learning Designer runs an After Action Review with the delivering team member. Four questions:
1. What was supposed to happen?
2. What actually happened?
3. What accounts for the difference?
4. What generalises?

From that AAR, the Learning Designer authors a ~800-word HBS-style case writeup. The case is authored by the Learning Designer, not the delivering team member — this protects honesty and separates execution from reflection.

Writeups live in `case_studies/`, indexed in `pka.db`. They're the raw material for an executive learning program: putting a client in the role of commissioner (not builder) and letting them discover a principle through a case, the way MBA students do.

**Cost ceiling principle:** the AAR and writeup must not block the next assignment. If the writeup would create a bottleneck, capture the AAR in writing and defer the writeup to a batch. Embedded learning is non-negotiable; its timing is flexible.

---

## Model Routing

Not every task deserves the most capable model. Routing the wrong model to a task — either too powerful (expensive, slow) or too weak (falls short) — is a quality failure.

PKA uses a tiered routing model within Anthropic:
- **Opus 4.7** — synthesis under ambiguity, architectural decisions, pedagogical writing
- **Sonnet 4.6** — implementation with a clear spec, code review, research synthesis
- **Haiku 4.5** — mechanical operations: DB inserts, archive moves, status queries

Leroy owns routing. Each persona has a `default_tier:` in its profile file — a starting point, not a fixed assignment. Leroy escalates or drops tier based on the character of the work. Per-brief overrides via a `Model:` line in the brief are first-class. The owner can override with one sentence in chat.

The DB includes `model_providers` and `task_type_models` tables for multi-provider routing. This is architecturally ready but intentionally disabled at install time (`multi_model_enabled = false`). When you're ready to wire a second provider (Perplexity, Ollama, etc.), flip the flag and add a provider row — the routing logic already knows what to do.

**Optionality without commitment** is the principle. The schema supports the full architecture; what's active today is the minimum viable slice.

---

## The Shim Layer

When Claude Code dispatches a subagent, it looks for a file in `.claude/agents/<slug>.md`. That file — the **shim** — is the dispatch contract: it tells the subagent to read the persona file, pick up the brief, write to `owners_inbox/`, and insert a deliverables row.

The shim is infrastructure, not identity. The persona's identity lives in `team/<NAME>.md`. The shim just wires the persona into the Claude Code host.

Why keep them separate? Because the persona contract should be host-agnostic. A persona defined in `team/SAM.md` describes what Sam does, how Sam thinks, and what Sam's standards are — independent of whether Sam is dispatched via `.claude/agents/`, an API call, or some future host. The shim is an adapter, not the persona itself.

In practice: Sam authors both `team/<NAME>.md` and `.claude/agents/<slug>.md` when a hire is approved. No one on the team writes directly to the Intent Layer — proposed changes come as documents to `owners_inbox/` for the owner to apply.

---

## CHANGELOG-Before-Commit

One lesson that emerged in practice: if you write the CHANGELOG entry *after* the commit, the entry lands in the *next* commit — not the one it describes. This creates a perpetual one-commit lag where the commit log doesn't match the CHANGELOG.

The fix is simple: write the CHANGELOG entry **before** running `git add`. The `/close-session` command and Session Close Protocol in CLAUDE.md both enforce this ordering. It seems minor until you're debugging history and the CHANGELOG says one thing and the commit says another.

---

## The Viewer and Diagrams

`pka-viewer/index.html` is a single HTML file that uses **sql.js** (SQLite compiled to WebAssembly) to read `pka.db` directly in the browser. No server, no backend, no installation. You open the file, select the DB, and browse.

`pka-workflow/index.html` uses **Mermaid.js** to render diagrams. It has four tabs:

- **Workflow** — dynamic team layer (reads `team_members` from the DB)
- **Engineering** — four static structural diagrams (2A folder structure, 2B brief lifecycle, 2C DB schema, 2D asset data flow)
- **Data** — browse and edit DB records directly in the browser
- **System** — pending proposals, recent changelog entries, capability status

Static diagrams need manual updates when the architecture changes. The `CLAUDE.md` rule is that Leroy owns monitoring — when a folder, table, or flow changes, Leroy flags it and routes a brief to whoever owns the interface role.

One lesson learned building the workflow viewer: **Mermaid.js does not render elements in hidden tabs.** If you're using CSS tabs with `display:none`, diagrams in inactive tabs will fail silently. The fix is `visibility:hidden; position:absolute` — the element exists in the DOM but isn't shown.

---

## What to Adapt

PKA was built for one owner's personal use. Here's what you'll likely want to change:

**The team.** Sam and PAX are founding members that belong in every PKA — they're the hiring and research engine. Your third hire should be whoever fills your most common skill gap. A developer? A writer? A data analyst? Let Sam and PAX run the process. Don't shortcut it.

**The journal and knowledge tables.** These are blank slates. Use them how they fit your workflow. Journal is personal; knowledge is reference material that the team can draw on.

**The feedback model.** Start with `ritual`. If it feels like overhead, switch to `on_demand`. Self-reflect is experimental and best used for high-stakes deliverables.

**The DB schema.** The schema is intentionally minimal. When you have a use case that doesn't fit — projects, contacts, tasks with deadlines — add a table. Document it in `DB_SCHEMA.md`. The FTS pattern applies to any new text-heavy table.

**Team member profiles.** After a few months of feedback, run Sam's review process on your team. You'll find that persona files written with real feedback data are noticeably sharper than the originals.

---

## Design Principles (Short Version)

1. **The orchestrator never works.** Leroy routes, never produces.
2. **Briefs are files, not conversation.** Keeps context lean, enables compaction.
3. **The DB is the memory.** Not conversations, not files — the DB.
4. **Personas are grounded in research.** Not vibes — PAX does the work first.
5. **Feedback is ritual.** Improvement requires evidence.
6. **The viewer lives in the browser.** No servers, no infrastructure.
7. **Naming conventions matter.** `snake_case` everywhere, or tooling breaks.
8. **Patterns beat re-deriving.** When a shape of work proves itself, codify it.
9. **Every delivery teaches.** The Learning Layer is non-optional and non-deferred.
10. **Optionality without commitment.** The schema supports the full architecture; activate only what you need today.
11. **Three-tier architecture from v1.2.0 onward.** Operations / Projects / Owner. Three databases, three responsibilities, three lifecycles. The system that builds is separated from the things that get built.
12. **Discipline ships alongside capability.** Every productized tool, persona, pattern, and protocol from v1.2.0 onward carries a demotion criterion. Discipline is what makes the operating model the product.
13. **Owner privacy is architectural, not disciplinary.** `personal.db` lives outside the repo. The file isn't there to leak.

---

## What's New in v1.2.0

A few v1.2.0 additions warrant their own design-decision notes for owners reading TRAINING.md to understand the system before adapting it.

### Three-tier architecture

Single-tier `pka.db` was the v1.0.0 / v1.1.0 shape. v1.2.0 splits to three tiers (Operations / Projects / Owner) because the production direction requires it: when PKA-Template ships to another owner, you can't ship the previous owner's engagements in the substrate. The split puts the operating discipline in `pka.db` (template-portable), the engagement-specific content in `projects.db` (empty at install), and the owner's personal layer in `personal.db` (outside the repo entirely).

The split is architectural, not disciplinary. The previous discipline ("don't put engagement-specific facts in cross-engagement memory") relied on the team's vigilance. The split removes the failure mode by making the home of each kind of fact different at the schema level.

### Productization discipline

A new `### Productization discipline` subsection in `CLAUDE.md` Strategic Direction binds every future build-vs-defer decision to four checks. The discipline emerged from a real failure mode: tools and personas got built because they *could* be built, not because they earned a build commitment. The four checks force the question:

- **Value-asymmetry** — does this artifact let value happen without the original author or persona in the room, *at the magnitude the persona-in-the-room produces?* The magnitude qualifier is load-bearing — a tool that produces a degraded version of persona-in-the-room value does not pass.
- **Rule-of-three** — three call sites or three implementations of one design shape. The first earns a single tool; the second earns a shared base. The discipline names which reading applies at build time. A template-baseline lens lets substrate ship before rule-of-three accrues (the substrate must exist before any inheriting instance can even run the discipline).
- **Demotion criterion** — at build approval, name the condition under which the tool would retire honestly. Event-based criteria are preferred; time-based and usage-based criteria are accepted only when the instrumentation exists to detect the firing.
- **Vocabulary review** — name the alternative framings the tool's API would suppress. Either accommodate them or record the vocabulary-lock as a flagged note in the demotion criterion.

The discipline also covers tool evolution (additive vs. substantive — substantive evolution is a fresh productization decision), periodic re-evaluation ("would we build this today?" fires at quarterly checkpoint), and the design-shape known-weakness clause (mechanical commonality across implementations may mask semantic divergence — promote to shared base only after a second tier empirically adopts the shape).

Why this matters for adapters: if you ship a custom tool or persona post-v1.2.0, the discipline applies. The seven tools and two personas the template ships with were built before the discipline was codified; some carry retroactive demotion criteria, others will be retrofitted as they evolve. New tools you author go through the full discipline at build time.

### Protocols layer

Some disciplines fire automatically — they're not "what to do when situation X arises" (that's a pattern) but "what runs when trigger X lands" (that's a protocol). The first protocol shipping at install is `owner_observability` — the four-axis capture-and-review discipline. Future protocols you adopt (or template-instance owners adopt later) go through the same Intent-layer flow: Leroy proposes; you approve; the protocol moves through `proposed` → `active` → `retired`. Every protocol carries a demotion criterion at adoption so it can retire honestly.

### Owner observability

`personal.db` gains four observation tables that capture the four observer/subject pairings the team needs to learn the principal it serves:

- **`owner_posture`** — your framing-and-posture about PKA over time
- **`orchestrator_observations`** — Leroy's reading of your decision style, framing tendencies, trust patterns (pending-review on write; you ratify before they go active)
- **`owner_observations`** — your observations about Leroy or any team member (active on write — your authority is the gate)
- **`team_observations`** — team members' observations about each other and Leroy (pending-review on write; you ratify)

The asymmetric trust shape — owner-authored rows go active; orchestrator/team-authored rows wait for your ratification — is load-bearing. It makes the relationship transparent and correctable rather than surveillance-shaped. The discipline is owner-private by file boundary: `personal.db` lives outside the repo at the configurable install location and is never committed.

### Hooks layer

`hooks/pka_guard.py` is the first hook in PKA. It's a no-op until you register it in `~/.claude/settings.json` (the README shows the snippet). When registered, it surfaces foreign Claude Code sessions on open (so concurrent sessions on the same repo are visible), blocks brief-ref numbering collisions with next-free suggestion, and blocks accidental destructive operations against team_comms brief files the current session hasn't claimed. The hook is local-only — no network, runs as your user, ~40ms median latency on PreToolUse.

The hook's demotion criterion is event-based: it retires when a native cross-session-coordination subsystem replaces it. Until then, it's the durable safety net for sessions running in parallel.

### Per-brief token economics

A new `economics` table captures tokens used, tool uses, duration, cache hit rate, and total cost in USD per deliverable. The `model_pricing` table ships pre-seeded with current Anthropic price rows and preserves pricing snapshots at the time of each economics row — historical rows stay interpretable even after future pricing changes. The economics layer is the substrate for cost-awareness over time. It does not block deliveries; if pricing data isn't available at deliverable close, the row inserts NULL costs and a follow-up pass can backfill.

### Tools catalog

`TOOLS.md` documents every productized tool with its demotion criterion (mirrored from the tool's top-of-file docstring). Seven tools ship in v1.2.0; new tools you productize join the catalog per the discipline in `CLAUDE.md`. The catalog's "How to add a new tool" section walks through the productization-discipline procedure.

---

## The System Grows

PKA is not a finished product. It is a starting point.

Your first hire will tell you something about your workflow that you didn't know before. Your fifth journal entry will start to reveal patterns. The feedback loop will surface things about how your AI team performs that you didn't expect.

The system is designed to grow with use. The DB schema is extensible. The team is expandable. The viewer and diagrams update without code changes.

Start simple. Let the work reveal what's missing. Hire when you need to, not before.
