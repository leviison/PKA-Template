# PKA — Personal Knowledge Agency

A local AI team you run through Claude Code. Instead of one assistant doing everything, PKA gives you a small team of named, specialized AI personas — each with a distinct identity, skill set, and work style — coordinated by an orchestrator called **Leroy**.

You talk to Leroy. Leroy delegates. Work lands in your inbox.

---

## What It Is

PKA is a folder on your machine. It contains:

- A **SQLite database** (`pka.db`) that stores everything: briefs, deliverables, journal entries, knowledge base items, assets, and feedback on your team's performance
- A **browser-based viewer** to read and search the DB without any server
- A **workflow diagram** that visualizes your team and how work flows
- A set of **persona files** defining who's on your team and how they operate
- A **CLAUDE.md** that tells Claude Code who Leroy is and how the system works

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

This creates `pka.db` with the full schema: all tables, FTS5 full-text search indexes, and sync triggers. It seeds two founding team members (Sam and PAX) and default settings.

### 3. Open the viewer

Open `owners_inbox/pka-viewer/index.html` in Chrome or Edge.

Click **Open pka.db** and select your `pka.db` file. You'll see tabs for Journal, Knowledge, Briefs, Assets, and Feedback — all searchable.

### 4. Open the workflow diagram

Open `owners_inbox/pka-workflow/index.html` in Chrome or Edge.

Click **Connect pka.db** to load the live team layer. The Workflow tab shows your full team; the Engineering tab shows the system scaffolding.

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
├── setup.py                     ← Creates pka.db on first run
├── check_names.py               ← Scans for snake_case violations
├── pka.db                       ← SQLite database (created by setup.py)
├── team/
│   ├── SAM.md                   ← HR Director
│   └── PAX.md                   ← Senior Researcher
├── team_comms/                  ← Internal: task briefs (not for the owner)
├── team_inbox/                  ← Drop files here for the team to process
└── owners_inbox/
    ├── pka-viewer/
    │   └── index.html           ← DB viewer
    └── pka-workflow/
        └── index.html           ← Workflow diagrams
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

---

## Your Founding Team

| Name | Role | What they do |
|---|---|---|
| **Sam** | HR Director | Runs hiring, manages persona reviews, translates PAX research into AI hires |
| **PAX** | Senior Researcher | Deep domain research, asset review, structured reports |

**To hire someone new:** tell Leroy what you need. Leroy briefs Sam. Sam+PAX research the role, build a persona, and present it for your approval before anyone goes active.

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
- **Python 3** (for setup.py and DB writes)
- **Chrome or Edge** (for the file viewer — requires File System Access API)
- SQLite is bundled via sql.js (WebAssembly) — no install needed

---

## For More Context

Read `TRAINING.md` for the full story: why this system was built this way, the design decisions behind it, and how to adapt it for different use cases.
