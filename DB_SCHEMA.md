# PKA Database Schema Reference

**File:** `pka.db` (SQLite 3, FTS5 enabled)
**Location:** `<PKA_ROOT>/pka.db`

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
| tokens_used | INTEGER | Total tokens consumed by the agent for this task |
| tool_uses | INTEGER | Number of tool calls made by the agent |
| duration_ms | INTEGER | Wall-clock time in milliseconds |

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
| notes | TEXT | Owner's optional comments |
| model | TEXT | Which feedback model was active (`ritual`, `on_demand`, `self_reflect`) |
| created_at | TEXT | ISO datetime |
| ai_model_provider_id | INTEGER FK | References `model_providers.id`; which provider ran this delivery. Backfilled to id=1 (Sonnet) for all pre-multi-model rows. |

---

### `settings`
System configuration as key/value pairs.

| Key | Default | Notes |
|---|---|---|
| `feedback_model` | `ritual` | Active feedback model: `ritual` / `on_demand` / `self_reflect` |
| `last_session_close_at` | *(set at session close)* | ISO datetime; written by Leroy at session close; used by Session Open Protocol step 3 to surface net-new validated patterns. |
| `multi_model_enabled` | `false` | Opt-in flag for provider routing. `false` = Anthropic tier logic only. Flip to `true` when a Phase 2 provider is activated. |
| `default_model_provider_id` | `1` | FK to `model_providers.id`; id=1 = Claude Sonnet 4.6. System fallback when no member- or task-level override exists. |
| `model_routing` | `member` | Routing mode: `member` / `task_type` / `both`. Controls whether `task_type_models` is consulted. |

---

### `team_members`
Registry of active PKA team members. Used by the live workflow diagram (dynamic layer). Each row is inserted by Sam when a new hire is approved.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT NOT NULL | Full team member name, e.g. `Sam` |
| role | TEXT NOT NULL | Role title, e.g. `HR Director` |
| short_role | TEXT | Abbreviated role for diagram display |
| profile_file | TEXT | Path to persona file, e.g. `team/SAM.md` |
| hired_date | TEXT | ISO date |
| active | INTEGER NOT NULL DEFAULT 1 | 1=active, 0=inactive |
| model_provider_id | INTEGER FK | References `model_providers.id`; NULL = use `settings.default_model_provider_id`. Set when a team member is wired to a non-Anthropic provider. |

---

### `backlog`
Canonical backlog for deferred ideas, architectural tasks, and tracked future work. Replaces the prior convention of tagging `knowledge` rows with 'backlog'.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| ref | TEXT UNIQUE | Human-readable ref, e.g. `BACKLOG-001` |
| title | TEXT | Item headline |
| body | TEXT | Full description and notes |
| priority | INTEGER | 1=high / 2=medium / 3=low |
| status | TEXT | `idea` / `active` / `complete` / `deferred` |
| tags | TEXT | Comma-separated |
| source | TEXT | Where the item originated |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime, update on edits |

**FTS5:** `backlog_fts` indexes `title + body`

**Status lifecycle:**
- `idea` — logged, not yet planned
- `active` — being worked on this session
- `complete` — done, kept for record
- `deferred` — explicitly pushed out; not surfaced at session open

---

### `case_studies`
Case writeups produced by the Learning Layer. One row per AAR + case writeup, tied back to the deliverable that triggered it. Captures both the raw AAR (four questions) and the finished case writeup (~800 words, HBS-style).

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| case_ref | TEXT UNIQUE | Human-readable ref, e.g. `CASE-001` (nullable until assigned) |
| deliverable_id | INTEGER FK | References `deliverables.id` ON DELETE RESTRICT |
| team_member | TEXT | Who delivered the original work (denormalized for stability) |
| aar_what_supposed | TEXT | AAR Q1 — what was supposed to happen |
| aar_what_actually | TEXT | AAR Q2 — what actually happened |
| aar_difference | TEXT | AAR Q3 — what accounts for the difference |
| aar_generalises | TEXT | AAR Q4 — what generalises |
| aar_date | TEXT | ISO datetime, when AAR was captured |
| case_body | TEXT | The case writeup itself (~800 words) |
| teaching_point | TEXT | The principle extracted (load-bearing for curriculum) |
| principles_tags | TEXT | CSV of PKA principles, drawn from: `orchestrator`, `handoffs`, `three_layer`, `brief_lifecycle`, `feedback_ritual` |
| author | TEXT | Defaults to the Learning Designer name (per Learning Layer rule — case authored by Designer, not delivering team member) |
| status | TEXT | CHECK constraint: `aar_pending` / `aar_captured` / `draft` / `published` / `deferred` |
| published_date | TEXT | ISO datetime, set when status → `published` |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime, auto-updated via trigger |

**Constraints (CHECK):**
- `status` must be one of the five allowed values
- If `status = 'published'`, both `case_body` and `published_date` must be NOT NULL
- If `status` is `aar_captured` / `draft` / `published` / `deferred`, all four AAR fields must be NOT NULL

**Triggers:** `updated_at` auto-refreshes on UPDATE (when not explicitly set by the app).

**FTS5:** `case_studies_fts` indexes `case_body + teaching_point + four AAR fields`. Synced via insert/update/delete triggers.

**Foreign key enforcement:** SQLite requires `PRAGMA foreign_keys = ON` per connection for the FK to be enforced — application code must set this.

**Status lifecycle:**
- `aar_pending` — case row created, AAR not yet captured
- `aar_captured` — all four AAR fields populated, writeup not yet drafted
- `draft` — case_body in flight
- `published` — case writeup finalized, published_date set
- `deferred` — AAR captured but writeup intentionally batch-held (cost-ceiling rule)

---

### `patterns`
Validated operational templates for the PKA team — when to reach for a shape of work, what the deliverable contract looks like, what disqualifies it. Part of the Intent layer (alongside `CLAUDE.md` and `team/*.md`). New patterns require owner approval before status transitions from `proposed` to `validated`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| pattern_ref | TEXT UNIQUE | Human-readable ref, e.g. `PATTERN-001` |
| slug | TEXT UNIQUE | Filename stem (no extension), e.g. `sequential-overnight-build` |
| title | TEXT | Pattern headline |
| body | TEXT | Full pattern markdown — DB is authoritative; `patterns/<slug>.md` is the git safety net |
| status | TEXT | CHECK: `proposed` / `validated` / `deprecated` |
| proposed_by | TEXT | Usually `Leroy` |
| approved_by | TEXT | Owner once validated; NULL until then |
| deprecated_reason | TEXT | Nullable; required context when status → `deprecated` |
| superseded_by | TEXT | Nullable; `PATTERN-NNN` ref if replaced by another pattern |
| validated_instances | TEXT | JSON array of brief refs, e.g. `'["BRIEF-001","BRIEF-002"]'` |
| proposed_at | TEXT | ISO datetime |
| approved_at | TEXT | ISO datetime; set when status → `validated` |
| deprecated_at | TEXT | ISO datetime; set when status → `deprecated` |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime; auto-updated via trigger |

**Constraints (CHECK):**
- `status` must be one of the three allowed values

**Triggers:** `updated_at` auto-refreshes on UPDATE (when not explicitly set by the app). FTS sync via insert/update/delete triggers.

**FTS5:** `patterns_fts` indexes `title + body`. Synced via insert/update/delete triggers.

**Status lifecycle:**
- `proposed` — one or more instances observed; awaiting owner approval
- `validated` — approved by owner with at least one confirmed instance; `approved_at` and `approved_by` are set
- `deprecated` — superseded or no longer applicable; `deprecated_at` and `deprecated_reason` are set. Row is retained; file moves to `archive/patterns/`. Reinstatement: move file back + `UPDATE patterns SET status='validated', deprecated_at=NULL, deprecated_reason=NULL WHERE pattern_ref='PATTERN-NNN'`.

**Archive:** `python3 archive.py pattern PATTERN-001` moves the file to `archive/patterns/<slug>.md` and sets `status='deprecated'`. The DB row is never deleted — full history is preserved.

**Note:** `superseded_by` is a text cross-reference (not a FK) — same convention as brief_ref cross-references elsewhere in the schema.

---

### `model_providers`
Registry of AI model providers PKA can route work to. Each row is a specific model at a specific endpoint with its own auth configuration and fallback chain.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT NOT NULL | Human-readable label, e.g. `Claude Sonnet 4.6` |
| provider | TEXT NOT NULL | Provider slug: `anthropic` / `perplexity` / `ollama` / `openai` / `google` |
| model_id | TEXT NOT NULL | Identifier sent to the API, e.g. `claude-sonnet-4-6`, `sonar-pro` |
| endpoint | TEXT | Base URL; NULL = use provider SDK default (appropriate for Anthropic) |
| api_key_env | TEXT | Env var name holding the API key; NULL for local no-auth providers (Ollama) |
| fallback_id | INTEGER FK | Self-referencing: references `model_providers.id`; NULL = surface to owner if unavailable |
| active | INTEGER NOT NULL DEFAULT 1 | 1=active, 0=disabled without deleting the row |
| notes | TEXT | Free-form: cost tier, latency notes, quirks |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | ISO datetime, auto-set |
| updated_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | ISO datetime, update on change |

**Seed rows (Anthropic-only at DDL time; non-Anthropic rows added when a Phase 2 provider is activated):**
- id=1: Claude Sonnet 4.6 (anthropic) — system default; `fallback_id=NULL`
- id=2: Claude Opus 4.7 (anthropic) — high-tier; `fallback_id=1`
- id=3: Claude Haiku 4.5 (anthropic) — low-tier; `fallback_id=1`

**FK note:** `fallback_id` is a self-referencing FK declared `DEFERRABLE INITIALLY DEFERRED` to allow seed data insertion without ordering constraints. Requires `PRAGMA foreign_keys = ON`.

**Template for future providers (copy-edit-INSERT when ready):**
```sql
-- Non-Anthropic example rows — NOT seeded; add when Phase 2 provider is activated
-- INSERT INTO model_providers (name, provider, model_id, endpoint, api_key_env, fallback_id, active, notes)
-- VALUES
--   ('Perplexity sonar-pro', 'perplexity', 'sonar-pro',
--    'https://api.perplexity.ai', 'PERPLEXITY_API_KEY', 1, 0,
--    'Live-web research. Inactive until activated. Fallback to Sonnet.'),
--   ('Ollama local', 'ollama', 'llama3',
--    'http://<LAN-IP>:11434/v1', NULL, 1, 0,
--    'Local offload. Inactive until activated. Endpoint IP TBD. Fallback to Sonnet.');
```

---

### `task_type_models`
Maps task types to preferred providers. Consulted when `settings.model_routing` is `task_type` or `both`. No rows seeded at DDL time — rows are added when task-type routing is activated.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| task_type | TEXT NOT NULL | Slug: `research`, `summarize`, `format`, `code_review`, `persona_build`, etc. |
| model_provider_id | INTEGER NOT NULL FK | References `model_providers.id` |
| description | TEXT | Why this task type routes to this provider |
| active | INTEGER NOT NULL DEFAULT 1 | 1=active, 0=disabled |
| created_at | TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP | ISO datetime, auto-set |

---

## Extending the Schema

Add new tables as new use cases emerge. Document them here. Do not modify existing table structures without considering migration.

---

---

# Personal Database — personal.db

**File:** `personal.db` (SQLite 3, FTS5 enabled)
**Location:** `~/Documents/PKA-Data/personal.db`
**Git status:** NOT tracked. Lives outside the PKA working directory. Never committed.

This database holds the owner's personal-layer data, separate from team-operational records. Team members (e.g. PAX during research) may query records where `private=0`. Records default to `private=0` (available to team). Set `private=1` for entries the owner wants kept personal-only.

---

### `owner_journal`
Personal journal entries — distinct from team-operational journal entries in `pka.db`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| date | TEXT | Entry date (date only), e.g. `2026-01-01` |
| title | TEXT | Optional title |
| body | TEXT | Entry content |
| tags | TEXT | Comma-separated |
| mood | TEXT | Optional mood tag |
| private | INTEGER | 0=team may read, 1=personal only (default: 0) |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime |

**FTS5:** `owner_journal_fts` indexes `title + body`

---

### `owner_tasks`
Personal task list — distinct from team briefs.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Task headline |
| body | TEXT | Optional detail / notes |
| status | TEXT | `open` / `in_progress` / `done` / `deferred` |
| priority | INTEGER | 1=high / 2=medium / 3=low |
| due_date | TEXT | ISO date, optional |
| tags | TEXT | Comma-separated |
| private | INTEGER | 0=team may read, 1=personal only (default: 0) |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime |

**FTS5:** `owner_tasks_fts` indexes `title + body`

---

### `owner_notes`
Personal reference notes — captures that don't belong in the team knowledge base.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Note title |
| body | TEXT | Full content |
| source | TEXT | Where it came from (optional) |
| tags | TEXT | Comma-separated |
| private | INTEGER | 0=team may read, 1=personal only (default: 0) |
| created_at | TEXT | ISO datetime |
| updated_at | TEXT | ISO datetime |

**FTS5:** `owner_notes_fts` indexes `title + body`
