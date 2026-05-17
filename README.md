# PKA — Personal Knowledge Agency

A local AI team you run through Claude Code. Instead of one assistant doing everything, PKA gives you a small team of named, specialized AI personas — each with a distinct identity, skill set, and work style — coordinated by an orchestrator called **Leroy**.

You talk to Leroy. Leroy delegates. Work lands in your inbox.

---

## What It Is

PKA is a folder on your machine. It contains:

- A **SQLite database** (`pka.db`) that stores everything: briefs, deliverables, journal entries, knowledge base items, assets, feedback, backlog, case studies, and patterns
- A **browser-based viewer** to read and search the DB without any server
- A **workflow diagram** that visualizes your team, system architecture, pending proposals, and changelog
- A set of **persona files** defining who's on your team and how they operate
- A **CLAUDE.md** that tells Claude Code who Leroy is and how the system works
- A **patterns layer** of validated operational templates the team can reach for
- A **memory layer** that carries durable context from one session to the next (user facts, project state, feedback patterns, operational discipline). Each persona reads its relevant slice at session start; a monthly reflection pass keeps it consolidated. Markdown mirrors live in `memory/`; the DB is authoritative.
- A **migration framework** (`migrations/`) so the schema can evolve without breaking existing installs
- A **Learning Layer** that turns every delivery into an HBS-style teaching artifact
- A **`/close-session` slash command** that makes session close a one-step routine

The system grows with you. You start with two team members. You hire more when you need them.

---

## Quickstart

### 1. Clone or download this template

```bash
git clone <this-repo> my-pka
cd my-pka
```

### 2. Create the database

```bash
python3 setup.py
```

The setup script asks for your name, then creates `pka.db` with the full schema: 15 tables (including the `memory` layer and the `schema_migrations` ledger), FTS5 full-text search indexes, and sync triggers. It seeds the founding team (Sam and PAX), default settings, and Anthropic model providers. Migration 001 (`memory` table + FTS + triggers) ships pre-applied; future migrations land via `python3 migrations/migrate.py up`.

### 3. Open the viewer

Open `owners_inbox/pka-viewer/index.html` in Chrome or Edge.

Click **Open pka.db** and select your `pka.db` file. You'll see tabs for Journal, Knowledge, Briefs, Backlog, Assets, and Feedback — all searchable.

### 4. Open the workflow diagram

Open `owners_inbox/pka-workflow/index.html` in Chrome or Edge.

Click **Connect pka.db** to load the live team layer. The Workflow tab shows your full team; the Engineering tab shows the system scaffolding (folder structure, brief lifecycle, DB schema, asset data flow); the System tab shows pending proposals, recent changelog entries, and capability status.

### 5. Start a Claude Code session

```bash
claude
```

Introduce yourself to Leroy. Tell them your name. Give them a task.

---

## Folder Structure

```
my-pka/
├── CLAUDE.md                    ← Leroy's operating rules (loaded by Claude Code automatically)
├── DB_SCHEMA.md                 ← Human-readable schema reference
├── setup.py                     ← Creates pka.db on first run (includes install questionnaire)
├── check_names.py               ← Scans for snake_case violations
├── archive.py                   ← Moves completed content to archive/ and updates pka.db
├── CHANGELOG.md                 ← Running record of what the system can do
├── VERSION                      ← Current version number
├── pka.db                       ← SQLite database (created by setup.py)
├── team/
│   ├── SAM.md                   ← HR Director
│   └── PAX.md                   ← Senior Researcher
├── .claude/
│   ├── agents/                  ← Subagent dispatch shims (one per team member)
│   └── commands/
│       └── close-session.md     ← Slash command: /close-session
├── team_comms/                  ← Internal: task briefs (not for the owner)
├── team_inbox/                  ← Drop files here for the team to process
├── case_studies/                ← Learning Layer case writeups
├── patterns/                    ← Validated operational templates
├── memory/                      ← Markdown mirrors of the memory table (DB is authoritative)
├── memory_io.py                 ← Write contract for the memory layer (UPSERT + markdown mirror)
├── migrations/                  ← Migration framework — runner + numbered SQL files
├── archive/
│   ├── team_comms/              ← Completed briefs (git-tracked)
│   └── owners_inbox/            ← Archived deliverables (git-tracked)
└── owners_inbox/
    ├── pka-viewer/
    │   └── index.html           ← DB viewer (sql.js, no server)
    └── pka-workflow/
        └── index.html           ← Workflow + system diagrams
```

---

## How Work Flows

1. You drop a task on Leroy in the Claude Code chat
2. Leroy writes a brief file to `team_comms/` and logs it to the DB
3. Leroy announces the handoff — *"Routing to PAX. Here's why."*
4. The team member reads the brief (not the conversation — keeps context lean) and does the work
5. Deliverable lands in `owners_inbox/` and is logged to the DB
6. Leroy notifies you and asks for a 1–5 rating
7. Feedback is stored — used later by Sam to evolve the persona
8. The Learning Designer runs an After Action Review and writes a case study

---

## Your Founding Team

| Name | Role | What they do |
|---|---|---|
| **Sam** | HR Director | Runs hiring, manages persona reviews, translates PAX research into AI hires |
| **PAX** | Senior Researcher | Deep domain research, asset review, structured reports |

**To hire someone new:** tell Leroy what you need. Leroy briefs Sam. Sam+PAX research the role, build a persona, and present it for your approval before anyone goes active.

---

## Session Open and Close

**Session open** (automatic): Leroy runs `check_names.py`, surfaces open backlog items, and alerts you to any validated patterns added since last session.

**Session close** (one command): type `/close-session` in the chat. Leroy writes a summary, updates the DB timestamp, appends a CHANGELOG entry, stages and commits all changes, and pushes to GitHub.

---

## Talking to Leroy

Some things you can say:

- *"PAX, research [topic] and give me a summary"* → Leroy routes to PAX
- *"Add a journal entry about [thing]"* → Leroy routes to a team member or handles via DB
- *"Sam, review PAX"* → Sam reads PAX's feedback history and updates the persona
- *"Who's on the team?"* → Leroy answers directly
- *"I need someone who can [skill]"* → Leroy escalates to Sam for a hire

---

## Tools Required

- **Claude Code** (claude.ai/claude-code)
- **Python 3** (for setup.py, archive.py, and DB writes)
- **Chrome or Edge** (for the file viewer — requires File System Access API)
- SQLite is bundled via sql.js (WebAssembly) — no install needed

---

## For More Context

Read `TRAINING.md` for the full story: why this system was built this way, the design decisions behind it, and how to adapt it for different use cases.
