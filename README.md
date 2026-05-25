# PKA — Personal Knowledge Agency

A local AI team you run through Claude Code. Instead of one assistant doing everything, PKA gives you a small team of named, specialized AI personas — each with a distinct identity, skill set, and work style — coordinated by an orchestrator called **Leroy**.

You talk to Leroy. Leroy delegates. Work lands in your inbox.

---

## What It Is

PKA is a folder on your machine. It contains:

- **Three SQLite databases** with three responsibilities: `pka.db` (operations — briefs, deliverables, feedback, patterns, protocols, memory, model routing, economics) and `projects.db` (engagement-scoped assets, content, project-tier memory) live in the repo; `personal.db` (journal, tasks, notes, posture, observations) lives outside the repo at a configurable location (default `~/PKA-Data/`) and is never committed
- A **browser-based viewer** to read and search the DB without any server
- A **workflow diagram** that visualizes your team, system architecture, pending proposals, and changelog
- A set of **persona files** defining who's on your team and how they operate
- A **CLAUDE.md** that tells Claude Code who Leroy is and how the system works
- A **patterns layer** of validated operational templates the team can reach for
- A **memory layer** that carries durable context from one session to the next (user facts, project state, feedback patterns, operational discipline). Each persona reads its relevant slice at session start; a monthly reflection pass keeps it consolidated. Markdown mirrors live in `memory/`; the DB is authoritative.
- A **migration framework** (`migrations/`) so the schema can evolve without breaking existing installs
- A **Learning Layer** that turns every delivery into an HBS-style teaching artifact
- A **`/close-session` slash command** that makes session close a one-step routine
- A **productization discipline** in `CLAUDE.md` Strategic Direction that binds every future tool/persona/pattern build to value-asymmetry, rule-of-three, and demotion-criterion checks — so the team ships discipline alongside capability
- A **protocols layer** (`protocols/`) for standing dispatch-layer disciplines that fire automatically when triggers land — distinct from patterns (which fire at decision time)
- An **owner-observability discipline** (`personal.db.owner_posture` / `owner_observations` / `orchestrator_observations` / `team_observations`) that captures the four observer/subject pairings the team needs to learn the principal it serves
- A **hooks layer** (`hooks/pka_guard.py`) for cross-session safety — blocks brief-ref collisions, surfaces foreign sessions, protects team_comms files. Local-only, runs as user, no network.
- A **tools catalog** (`TOOLS.md`) documenting every productized tool with its demotion criterion
- **Per-brief token economics** (`pka.db.economics` + `model_pricing`) that capture tokens, tool uses, duration, and cost per deliverable

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

The setup script asks for your name and the location for your personal-tier database (default `~/PKA-Data/`), then creates three databases: `pka.db` (Operations — 16 tables including memory, economics, model_pricing, patterns, protocols, schema_migrations), `projects.db` (Projects — 5 tables for engagement-scoped assets, content, and project-tier memory), and `personal.db` (Owner — 8 tables for journal, tasks, notes, posture, and observations). FTS5 full-text search indexes and sync triggers ship across all three tiers. The script seeds the founding team (Sam and PAX), default settings, Anthropic model providers + pricing, and six validated patterns. Six baseline migrations are recorded as pre-applied across the three tiers; future migrations land via `python3 migrations/migrate.py up --dir <tier>`.

To override the personal-tier location: `python3 setup.py --personal-data-dir ~/Documents/MyName-Data`. The chosen path is recorded in `pka.db.settings.personal_db_path` so every helper finds it without re-configuration.

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

### 6. (Optional) Activate cross-session safety hooks

The repo ships with `hooks/pka_guard.py`, a Claude Code hook that surfaces foreign sessions on open, blocks brief-ref numbering collisions, and protects team_comms files from accidental destructive operations. The hook is a no-op until registered in `~/.claude/settings.json`. To activate, add this block to your settings (merge with your existing hooks if any):

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "python3 <ABSOLUTE_PATH_TO_REPO>/hooks/pka_guard.py SessionStart"}]}],
    "PreToolUse":   [{"hooks": [{"type": "command", "command": "python3 <ABSOLUTE_PATH_TO_REPO>/hooks/pka_guard.py PreToolUse"}]}],
    "Stop":         [{"hooks": [{"type": "command", "command": "python3 <ABSOLUTE_PATH_TO_REPO>/hooks/pka_guard.py Stop"}]}],
    "SubagentStop": [{"hooks": [{"type": "command", "command": "python3 <ABSOLUTE_PATH_TO_REPO>/hooks/pka_guard.py SubagentStop"}]}]
  }
}
```

Replace `<ABSOLUTE_PATH_TO_REPO>` with the absolute path to your PKA install. The hook is local-only — no network, runs as your user, ~40ms median PreToolUse latency. See `TOOLS.md` for the full hook discipline.

---

## Folder Structure

```
my-pka/
├── CLAUDE.md                    ← Leroy's operating rules (loaded by Claude Code automatically)
├── DB_SCHEMA.md                 ← Human-readable schema reference (now three-tier)
├── TOOLS.md                     ← Catalog of productized tools + demotion criteria
├── setup.py                     ← Creates pka.db + projects.db + personal.db (install questionnaire)
├── check_names.py               ← Scans for snake_case violations (instrumented; --evaluate-demotion-criterion mode)
├── archive.py                   ← Moves completed content to archive/ (three-tier aware)
├── memory_io.py                 ← Write contract for pka.db memory + cross-tier promotion helper
├── projects_memory_io.py        ← Write contract for projects.db memory
├── economics_io.py              ← Per-brief token economics capture
├── CHANGELOG.md                 ← Running record of what the system can do
├── VERSION                      ← Current version number
├── pka.db                       ← Operations tier (created by setup.py)
├── projects.db                  ← Projects tier (created by setup.py)
│                                  personal.db lives at ~/PKA-Data/personal.db (outside repo)
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
├── patterns/                    ← Validated operational templates (6 ship at install)
├── protocols/                   ← Standing dispatch-layer disciplines (owner_observability ships at install)
├── hooks/
│   └── pka_guard.py             ← Cross-session safety hook (register in ~/.claude/settings.json)
├── tools/
│   └── status_now.py            ← Read-only pka.db status snapshot (run in a tmux pane)
├── memory/                      ← Markdown mirrors of the memory table (DB is authoritative)
├── tests/                       ← Test suite (promote-from-observation coverage)
├── migrations/                  ← Three-tier migration framework — runner + numbered SQL files
│   ├── personal/                ← Personal-tier migrations
│   └── projects/                ← Projects-tier migrations
├── archive/
│   ├── team_comms/              ← Completed briefs (git-tracked)
│   └── owners_inbox/            ← Archived deliverables (git-tracked)
└── owners_inbox/
    ├── pka-viewer/
    │   └── index.html           ← DB viewer (sql.js, no server)
    └── pka-workflow/
        └── index.html           ← Workflow + system diagrams (now includes projects.db ER + personal.db observability tables)
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

- **`TRAINING.md`** — the full story: why this system was built this way, the design decisions behind it, and how to adapt it for different use cases.
- **`TOOLS.md`** — catalog of productized tools with demotion criteria and discipline notes.
- **`CLAUDE.md`** — Leroy's full operating rules, including the Strategic Direction and Productization Discipline sections that govern future tool/persona/pattern decisions.
- **`patterns/README.md`** — pattern catalog with family taxonomy.
- **`protocols/README.md`** — protocols catalog and the protocols-vs-patterns distinction.
- **`DB_SCHEMA.md`** — full schema reference across all three tiers with ATTACH DATABASE worked examples.
