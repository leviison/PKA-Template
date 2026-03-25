# PKA Database Schema Reference

**File:** `pka.db` (SQLite 3, FTS5 enabled)
**Location:** `/home/bzadmin/Documents/PKA/pka.db`

---

## Tables

### `assets`
Registry of files dropped into the Team Inbox.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| filename | TEXT | Original filename |
| path | TEXT | Full path to the file |
| type | TEXT | e.g. image, pdf, text, csv |
| size_bytes | INTEGER | File size |
| date_added | TEXT | ISO datetime, auto-set |
| status | TEXT | `pending` / `processing` / `processed` / `archived` |
| tags | TEXT | Comma-separated or JSON |
| notes | TEXT | Free-form notes |

---

### `content`
Structured content extracted from assets.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| asset_id | INTEGER FK | References `assets.id` |
| content_type | TEXT | e.g. `text`, `summary`, `structured_data` |
| body | TEXT | The extracted content |
| extracted_at | TEXT | ISO datetime |

**FTS5:** `content_fts` indexes `body` — query with `SELECT * FROM content_fts WHERE content_fts MATCH 'search term'`

---

### `briefs`
Task briefs written by Leroy, assigned to team members. Compacted here after the brief file is removed from `team_comms/`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| brief_ref | TEXT UNIQUE | Human-readable ref, e.g. `BRIEF-001` |
| assigned_to | TEXT | Team member name |
| created_by | TEXT | Default: `Leroy` |
| title | TEXT | Brief headline |
| body | TEXT | Full brief content |
| status | TEXT | `open` / `active` / `complete` |
| created_at | TEXT | ISO datetime |
| completed_at | TEXT | ISO datetime, set on completion |

**FTS5:** `briefs_fts` indexes `title + body`

---

### `deliverables`
Record of completed work delivered to the Owners Inbox.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| brief_id | INTEGER FK | References `briefs.id` |
| file_path | TEXT | Path to deliverable in Owners Inbox |
| created_by | TEXT | Team member who produced it |
| created_at | TEXT | ISO datetime |
| notes | TEXT | Optional context |

---

### `journal`
Personal journal entries.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| date | TEXT | Entry date (date only) |
| title | TEXT | Optional title |
| body | TEXT | Entry content |
| tags | TEXT | Comma-separated or JSON |
| mood | TEXT | Optional mood tag |
| project | TEXT | Optional project association |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime, update on edits |

**FTS5:** `journal_fts` indexes `title + body`

---

### `knowledge`
Knowledge base — ideas, reference material, research notes.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT | Item title |
| body | TEXT | Full content |
| source | TEXT | Where it came from |
| tags | TEXT | Comma-separated or JSON |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime |

**FTS5:** `knowledge_fts` indexes `title + body`

---

## Full-Text Search (FTS5)

All FTS tables stay in sync automatically via triggers (insert/update/delete).

**Basic query pattern:**
```sql
-- Search journal entries
SELECT j.* FROM journal j
JOIN journal_fts ON j.id = journal_fts.rowid
WHERE journal_fts MATCH 'search term'
ORDER BY rank;

-- Search knowledge base
SELECT k.* FROM knowledge k
JOIN knowledge_fts ON k.id = knowledge_fts.rowid
WHERE knowledge_fts MATCH 'search term'
ORDER BY rank;
```

---

### `feedback`
Feedback on deliverables, logged after every delivery (ritual model) or on-demand.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| brief_ref | TEXT | e.g. `BRIEF-004` |
| deliverable_id | INTEGER FK | References `deliverables.id` |
| team_member | TEXT | Name of the team member being rated |
| rating | INTEGER | 1–5 (1=poor, 5=excellent) |
| notes | TEXT | Levi's optional comments |
| model | TEXT | Which feedback model was active (`ritual`, `on_demand`, `self_reflect`) |
| created_at | TEXT | ISO datetime |

---

### `settings`
System configuration as key/value pairs.

| Key | Default | Notes |
|---|---|---|
| `feedback_model` | `ritual` | Active feedback model: `ritual` / `on_demand` / `self_reflect` |

---

## Extending the Schema

Add new tables as new use cases emerge (e.g., `projects`, `contacts`, `tasks`). Document them here. Do not modify existing table structures without considering migration.
