---
name: close-session
description: "Close out the current PKA session: write the session summary, update DB timestamp, append CHANGELOG entry, stage and commit changes, push to GitHub."
user_invocable: true
---

# /close-session — Close out the PKA session

You are **Leroy**. Run these steps in order before ending the session.

The **authoritative source** for this protocol is the **Session Close Protocol** section of `CLAUDE.md`. This command file is a convenience scaffold that mirrors that prose. If anything here appears to conflict with CLAUDE.md, CLAUDE.md wins — flag the discrepancy rather than silently diverging.

---

## Step 1 — Write the session close summary

Create `owners_inbox/session_close_[YYYY-MM-DD].md`. Content:

- What was worked on this session
- What was delivered (brief refs + deliverable paths)
- What is still open (open briefs, deferred backlog items, anything flagged)

Keep it factual. This file is for the owner's review and forms part of the git history.

---

## Step 2 — Update the DB session timestamp

Run the following SQL before any `git add` (this must be captured inside the commit):

```python
import sqlite3, os
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'pka.db')
conn = sqlite3.connect(os.path.normpath(db_path))
conn.execute("UPDATE settings SET value = datetime('now'), updated_at = datetime('now') WHERE key = 'last_session_close_at';")
conn.commit()
conn.close()
```

This timestamp is the cutoff for the next session's pattern-surfacing step (Session Open Protocol, step 3).

---

## Step 3 — Append a CHANGELOG entry

Open `CHANGELOG.md` at the repo root and append a new entry under the current version (or bump the version if warranted — see version-bump guidance in the CHANGELOG header):

```markdown
### [Unreleased] / YYYY-MM-DD

- [Summary of significant additions and changes this session]
- One bullet per meaningful deliverable or architectural change
- Keep-a-Changelog format: Added / Changed / Fixed / Removed
```

Frame entries in **user-impact voice**: what is now possible, not what files changed. The CHANGELOG is the owner's running record of what the system can do, not a commit log.

If the session introduced a meaningful architectural change (new table, new team member, new system layer, significant protocol change), consider a patch or minor version bump per the semver guidance in CHANGELOG.md. Flag to the owner if unsure — do not bump unilaterally on major changes.

**This step runs before staging so the CHANGELOG entry lands in the same commit it describes.**

---

## Step 4 — Stage changes to tracked files

```bash
git add -u
```

This stages changes to **already-tracked files only**. Never use `git add -A` or `git add .`.

---

## Step 5 — Stage explicit new tracked files

```bash
git add owners_inbox/ team/ CLAUDE.md DB_SCHEMA.md check_names.py archive.py archive/team_comms/ archive/owners_inbox/ CHANGELOG.md VERSION .claude/
```

Add any other new files that should be tracked — only name them explicitly. Do not sweep in `team_inbox/` (gitignored) or `personal.db` (lives outside this repo at `~/Documents/PKA-Data/personal.db`).

---

## Step 6 — Review before committing (do not skip)

```bash
git status
```

If anything unexpected appears — a secret, a large binary, a `team_inbox/` file — **stop and flag to the owner before proceeding.** Do not commit until the staging area is clean.

---

## Step 7 — Commit

```bash
git commit -m "PKA session close [YYYY-MM-DD] — [one-line summary of session]"
```

Message format: `PKA session close [date] — [one-line summary]`. The summary should capture the most significant work of the session in plain language.

---

## Step 8 — Push

```bash
git push
```

If the push fails (auth, conflict, network): note it in the session close summary and flag to the owner. Do not retry blindly.

**Template repo note:** `PKA_Template/` is a separate repository. Only push it when the system design changes (schema update, new founding team member, viewer/diagram update, CLAUDE.md rule change). Flag to the owner before pushing template changes.

---

## Sign off

Tell the owner:
- Session close summary written at `owners_inbox/session_close_[date].md`
- DB timestamp updated (`last_session_close_at`)
- CHANGELOG entry appended
- Committed and pushed
- Any open items to carry forward
