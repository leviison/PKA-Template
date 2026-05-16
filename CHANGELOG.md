# Changelog

All notable changes to PKA are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/).

## Version bump guidance

- **Patch (x.x.N):** Bug fixes, minor protocol clarifications, small additive files (commands, tooling).
- **Minor (x.N.0):** New team member, new system layer or table, significant new capability (e.g., patterns layer, model routing, Learning Layer).
- **Major (N.0.0):** Fundamental rearchitecture — e.g., replacing the brief/DB model, restructuring the team model entirely, migrating to a new platform.

Append a new entry at the **top** of the releases section each session close. Use the format below.

---

## Releases

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
