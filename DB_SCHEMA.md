# PKA Database Schema Reference

PKA operates across a **three-tier database architecture**. Each tier lives in its own SQLite file. Cross-tier queries use `ATTACH DATABASE` (see §"ATTACH DATABASE pattern" at the bottom of this document).

| Tier | File | Location | Tracked in git |
|---|---|---|---|
| **Operations** | `pka.db` | `<PKA_ROOT>/pka.db` | yes |
| **Projects** | `projects.db` | `<PKA_ROOT>/projects.db` | yes |
| **Owner** | `personal.db` | `~/PKA-Data/personal.db` (default; configurable at setup) | no — outside the repo |

**Operations tier (pka.db)** — about how PKA-the-team operates. Briefs, deliverables, patterns, case_studies, memory, settings, model_providers, model_pricing, economics, feedback, team_members, knowledge, backlog, journal (operational/session journal), task_type_models, schema_migrations.

**Projects tier (projects.db)** — engagement-specific content AND project-scoped operational discipline. Data-room extractions, audio assets, engagement-tagged content; plus the memory analog for project-bound facts (deployment topology, environment quirks, project history). Tables: `assets`, `content`, `content_fts`, `projects`, `memory`, `memory_fts`, schema_migrations.

**Owner tier (personal.db)** — the owner's personal-layer data. Not committed.

**Foreign-key boundary.** SQLite does not enforce FOREIGN KEY constraints across attached databases. Cross-tier integrity is enforced at the application/helper layer; cross-tier reads go through `ATTACH DATABASE`. The migration that introduced this split (003) preserved the only existing FK that touched these tables — `content.asset_id -> assets.id ON DELETE CASCADE` — by keeping both tables together in projects.db, so it remains intra-DB.

**Personal-tier naming convention.** Personal-tier tables use `owner_*` prefix (`owner_journal` / `owner_tasks` / `owner_notes` / `owner_posture` / `owner_observations`) and the orchestrator's observation table is `orchestrator_observations`. This is the canonical naming from v1.2.0 onward — personas may NOT introduce role-named alternatives (e.g., a future hire-named observation table).

---

## Operations tier — `pka.db`

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
| source_material | TEXT | Optional: file path, URL, video title + date, short description. Backing for the source-pointer convention; default-copies to deliverables on insert. |
| project_slug | TEXT | Optional: cross-tier pointer to `projects.db.projects.slug`. NULL = brief is PKA-internal substrate work (no project context). Soft-validated at the application layer (SQLite cannot enforce cross-DB FKs). |

**Indexes:** `briefs_project_idx (project_slug)` — supports "all briefs that touched project X" queries.

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
| source_material | TEXT | Default-copies from `briefs.source_material` at deliverable-insert time (helper-layer convention). Per-deliverable override is supported. |

---

### `journal`
Operational journal entries — distinct from the personal journal in `personal.db.owner_journal`.

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
Feedback on deliverables, logged after every delivery (ritual model), on-demand, or via the orchestrator-rates / owner-audits model.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| brief_ref | TEXT | e.g. `BRIEF-004` |
| deliverable_id | INTEGER FK | References `deliverables.id` |
| team_member | TEXT | Name of the team member being rated |
| rating | INTEGER | 1–5 (1=poor, 5=excellent) |
| notes | TEXT | Owner's optional comments |
| model | TEXT | Which feedback model was active (`ritual`, `on_demand`, `self_reflect`, `leroy_rates_levi_audits`) |
| created_at | TEXT | ISO datetime |
| ai_model_provider_id | INTEGER FK | References `model_providers.id`; which provider ran this delivery |
| rater | TEXT | `levi` / `leroy` — who entered this rating row. Default `levi`. Owner-rated rows supersede orchestrator-rated rows for the same `(brief_ref, team_member)` pair via ordering. |

---

### `settings`
System configuration as key/value pairs.

| Key | Default | Notes |
|---|---|---|
| `feedback_model` | `leroy_rates_levi_audits` | Active feedback model: `ritual` / `on_demand` / `self_reflect` / `leroy_rates_levi_audits` |
| `audit_cadence_days` | `7` | How often owner audits orchestrator-rated rows (used by the `leroy_rates_levi_audits` model) |
| `last_session_close_at` | epoch sentinel `1970-01-01T00:00:00` | ISO datetime; written by Leroy at session close; used by Session Open Protocol to surface net-new validated patterns. |
| `last_reflection_pass_at` | epoch sentinel `1970-01-01T00:00:00` | ISO datetime; written by Leroy after a reflection pass; used by Session Open Protocol to fire the calendar-anchored reminder. |
| `multi_model_enabled` | `false` | Opt-in flag for provider routing. `false` = Anthropic tier logic only. Flip to `true` when a Phase 2 provider is activated. |
| `default_model_provider_id` | `1` | FK to `model_providers.id`; id=1 = Claude Sonnet 4.6. System fallback when no member- or task-level override exists. |
| `model_routing` | `member` | Routing mode: `member` / `task_type` / `both`. Controls whether `task_type_models` is consulted. |
| `user_name` | `''` (empty) | Owner's first name. Collected by First-Run Protocol. |
| `user_use_case` | `''` (empty) | One-sentence framing of what the owner is mainly building PKA for. Optional. |
| `personal_db_separation` | `''` (empty) | `yes` / `no`. Owner's choice on personal-tier separation. Collected by First-Run Protocol. |
| `personal_db_path` | (set at setup) | Absolute path to `personal.db`. Default `~/PKA-Data/personal.db`. Override at install with `python3 setup.py --personal-data-dir <path>`. |

---

### `team_members`
Registry of active PKA team members. Used by the live workflow diagram (dynamic layer). Each row is inserted by Sam when a new hire is approved.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT NOT NULL | Full team member name |
| role | TEXT NOT NULL | Role title |
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
| validated_instances | TEXT | JSON array of brief refs |
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
- `validated` — approved by the owner with at least one confirmed instance; `approved_at` and `approved_by` are set
- `deprecated` — superseded or no longer applicable; `deprecated_at` and `deprecated_reason` are set. Row is retained; file moves to `archive/patterns/`. Reinstatement: move file back + `UPDATE patterns SET status='validated', deprecated_at=NULL, deprecated_reason=NULL WHERE pattern_ref='PATTERN-NNN'`.

**Archive:** `python3 archive.py pattern PATTERN-001` moves the file to `archive/patterns/<slug>.md` and sets `status='deprecated'`. The DB row is never deleted — full history is preserved.

**Note:** `superseded_by` is a text cross-reference (not a FK) — same convention as brief_ref cross-references elsewhere in the schema.

---

### `memory`
PKA-native durable memory layer. The DB is authoritative; `memory/<slug>.md` is the human/git-readable mirror written by `memory_io.py`. Memory rows are how PKA carries durable context (user facts, project state, feedback patterns, pedagogy, operational discipline) from one session to the next.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| slug | TEXT UNIQUE | Kebab-case stable id; used in `[[wikilinks]]` and as the markdown filename stem |
| type | TEXT NOT NULL | CHECK: `user_fact` / `project` / `feedback` / `pedagogy` / `preference` / `pattern_ref` / `operational` |
| title | TEXT NOT NULL | One-line summary; becomes the index entry |
| body | TEXT NOT NULL | Durable content |
| scope | TEXT NOT NULL | CHECK: `global` / `owner_only` / `team_member:<slug>` |
| source_ref | TEXT | Brief ref, feedback id, deliverable id, etc. |
| status | TEXT NOT NULL | CHECK: `active` / `superseded` / `deferred` / `invalidated`; default `active` |
| superseded_by | TEXT | Slug of replacement; NULL unless status=`superseded` |
| valid_from | TEXT NOT NULL | ISO datetime; defaults to creation |
| valid_to | TEXT | ISO datetime; NULL = currently valid (bi-temporal) |
| ingested_at | TEXT NOT NULL | When PKA learned it; defaults to creation |
| approved_by | TEXT | Owner for promotions requiring Intent-layer approval |
| provenance | TEXT NOT NULL | CHECK: `human_confirmed` / `leroy_inferred` / `model_inferred` |
| tags | TEXT | CSV |
| created_at | TEXT NOT NULL | ISO datetime, auto-set |
| updated_at | TEXT NOT NULL | ISO datetime, auto-updated via trigger |

**Constraints (CHECK):**
- `type`, `scope`, `status`, `provenance` are enum-checked (see column notes).
- `status='superseded'` iff `superseded_by IS NOT NULL` (XOR invariant).
- `valid_to IS NULL OR valid_to >= valid_from`.

**Indexes:**
- `memory_scope_status_idx (scope, status)` — drives the narrow load profile.
- `memory_status_type_idx (status, type)` — drives the type-filtered load profile.
- `memory_ingested_at_idx (ingested_at DESC)` — drives the `ORDER BY ingested_at DESC LIMIT 30` recency clause.

**Triggers:** `memory_ai` / `memory_au` / `memory_ad` keep `memory_fts` in sync; `memory_touch` auto-refreshes `updated_at` on UPDATE (when not explicitly set by the app).

**FTS5:** `memory_fts` indexes `title + body`, external content (`content='memory'`).

**Markdown mirror:** Each row is mirrored to `memory/<slug>.md` by `memory_io.py`. The DB is authoritative on conflict — external edits to the markdown file are not synced back automatically.

**Status lifecycle:**
- `active` — currently valid memory
- `superseded` — replaced by a newer row (`superseded_by` set, `valid_to` set)
- `deferred` — proposed but not promoted (rare; used by the reflection pass for "owner declined to promote yet")
- `invalidated` — explicitly retracted (the row was wrong, not just stale)

**Bi-temporal query — "what did PKA believe at time T":**
```sql
SELECT * FROM memory
WHERE valid_from <= :T
  AND (valid_to IS NULL OR valid_to > :T);
```

**Note:** `superseded_by` is a text cross-reference (not a FK) — same convention as `patterns.superseded_by`.

**DB authoritative; mirror at `memory/<slug>.md`.** Operational writes go through `memory_io.write_memory_row(...)` and `memory_io.supersede(...)`. External edits to the markdown files are not auto-synced back — use `memory_io.import_markdown(<slug>)` or `python3 memory_io.py import <path>` to roundtrip a manual edit.

**Schema management:** the memory table lands via `migrations/001_memory_table.sql`, recorded as already-applied by `setup.py` in `schema_migrations`. Future schema evolution uses `python3 migrations/migrate.py up`.

---

### `memory_episodic_view`
Read-only SQL view that projects rows from `briefs` + `deliverables` + `feedback` + `journal` into the `memory` row shape, so consumers can `UNION ALL` it with `memory` without column-shape drift. Added via migration 004.

Two projections, `UNION ALL`'d:
- **Briefs projection** — one row per `(completed brief, deliverable)` pair with feedback `LEFT JOIN`ed. Briefs that completed without a deliverable produce one row with slug suffix `open`.
- **Journal projection** — one row per journal entry.

**Provenance vocabulary:** view rows emit `provenance='projected'`. This value is reserved for view projections and is **not** accepted by `memory`'s `provenance` CHECK constraint — view rows are read-only and not meant to be materialized into `memory`.

**No FTS over the view.** SQLite FTS5 cannot index views; the source tables already have FTS (`briefs_fts`, `journal_fts`).

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

### `model_pricing`
Versioned per-model price table (per-1M-token rates, per-rate-class: input / output / cache_write / cache_read). Rows are immutable snapshots; pricing changes add a new row, never UPDATE in place. Added via migration 002.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| provider | TEXT NOT NULL | e.g. `anthropic` |
| model | TEXT NOT NULL | e.g. `claude-sonnet-4-6` |
| input_price_per_1m | REAL NOT NULL | USD per 1,000,000 input tokens |
| output_price_per_1m | REAL NOT NULL | USD per 1,000,000 output tokens |
| cache_write_price_per_1m | REAL NOT NULL | USD per 1,000,000 cache-write tokens |
| cache_read_price_per_1m | REAL NOT NULL | USD per 1,000,000 cache-read tokens |
| currency | TEXT NOT NULL DEFAULT 'USD' | |
| effective_from | TEXT NOT NULL | ISO date when this pricing went live |
| last_verified_at | TEXT NOT NULL | When the rates were last reconciled against the source |
| source_url | TEXT | Usually `https://www.anthropic.com/pricing` |
| notes | TEXT | Free-form |
| created_at | TEXT NOT NULL DEFAULT (datetime('now')) | |

**UNIQUE:** `(provider, model, effective_from)` — never UPDATE in place; insert a new row on price change.

**Indexes:** `model_pricing_lookup_idx (provider, model, effective_from DESC)` — drives "current price for this model" queries.

---

### `economics`
One row per deliverable (1:1, FK on `deliverables.id`), capturing the Anthropic-specific breakdown: cache-creation tokens, cache-read tokens, input/output split, model, and the USD cost computed at write time against a specific `model_pricing.id`. Added via migration 002.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| deliverable_id | INTEGER UNIQUE FK | References `deliverables.id` ON DELETE CASCADE |
| provider | TEXT NOT NULL DEFAULT 'anthropic' | |
| model | TEXT NOT NULL | e.g. `claude-sonnet-4-6` |
| input_tokens | INTEGER NOT NULL DEFAULT 0 | |
| output_tokens | INTEGER NOT NULL DEFAULT 0 | |
| cache_creation_tokens | INTEGER NOT NULL DEFAULT 0 | |
| cache_read_tokens | INTEGER NOT NULL DEFAULT 0 | |
| estimated_cost_usd | REAL NOT NULL | Computed at write time against `model_pricing_id` |
| model_pricing_id | INTEGER NOT NULL FK | References `model_pricing.id` ON DELETE RESTRICT — locks in the pricing snapshot used |
| cache_hit_rate | REAL | Pre-computed: `cache_read_tokens / (cache_read_tokens + input_tokens)`. NULL when denominator is 0. |
| created_at | TEXT NOT NULL DEFAULT (datetime('now')) | |

**Constraints (CHECK):** non-negative token counts; non-negative cost.

**Indexes:** `economics_deliverable_idx (deliverable_id)`, `economics_model_idx (model)`, `economics_created_at_idx (created_at DESC)`.

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

### `schema_migrations`
Migration history for `pka.db`. Created by the migration runner on first invocation (and seeded eagerly by `setup.py` so the install experience is single-script). On a fresh v1.2.0 install, the following migrations are recorded as already-applied (their DDL is embedded in `setup.py`):

- `001_memory_table`
- `002_token_economics`
- `003_split_projects_db`
- `004_memory_episodic_view`
- `006_briefs_project_slug`
- `007_feedback_rater`

(There is no migration `005` in the template baseline. PKA's `005_template_readiness_pka.sql` was a rebuild migration that converted the historical `levi_only` scope enum to `owner_only` and added `source_material` columns; both are baked into the template's setup.py DDL directly, so the rebuild migration is unnecessary.)

| Column | Type | Notes |
|---|---|---|
| name | TEXT PK | Migration stem, e.g. `001_memory_table` |
| applied_at | TEXT NOT NULL DEFAULT (datetime('now')) | ISO datetime |

---

---

## Projects tier — `projects.db`

Engagement-specific content. Created by migration 003 (template baseline). Tracked in git alongside `pka.db`.

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
| tags | TEXT | Comma-separated. Engagement slugs land here (e.g. `<engagement-slug>,audited-financials`). |
| notes | TEXT | Free-form notes |

---

### `content`
Structured content extracted from assets.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| asset_id | INTEGER FK | References `assets.id` ON DELETE CASCADE (intra-DB FK, preserved through the 003 split) |
| content_type | TEXT | e.g. `text`, `summary`, `structured_data` |
| body | TEXT | The extracted content |
| extracted_at | TEXT | ISO datetime |

**FTS5:** `content_fts` indexes `body` — query with `SELECT * FROM content_fts WHERE content_fts MATCH 'search term'`.

**Triggers:** `content_ai` (after INSERT) and `content_ad` (after DELETE) sync `content_fts`. **Note:** there is no AFTER UPDATE trigger — direct UPDATEs to `content.body` will leave `content_fts` stale. The intended pattern is DELETE + INSERT for body changes.

---

### `projects`
Engagement registry. Slug-keyed; the FK target for `memory.project_slug`. Ships empty in the template — owners populate it as engagements emerge. Added via projects-tier migration 001.

| Column | Type | Notes |
|---|---|---|
| slug | TEXT PRIMARY KEY | Kebab-case canonical project id; never reused |
| name | TEXT NOT NULL | Human-readable name |
| description | TEXT | Short engagement summary |
| status | TEXT NOT NULL DEFAULT `'active'` | CHECK in (`'active'`, `'dormant'`, `'archived'`); drives the lazy loader's active-projects filter |
| primary_host | TEXT | Optional convenience pointer; not authoritative (the `topology` memory row is) |
| repo_url | TEXT | Optional canonical repo URL (e.g., GitHub/GitLab) |
| repo_path | TEXT | Optional local clone path |
| created_at | TEXT NOT NULL | ISO datetime, default `datetime('now')` |
| updated_at | TEXT NOT NULL | ISO datetime, default `datetime('now')` |

**Indexes:** `projects_status_idx` on (`status`).

Minimal-by-design. Richer engagement metadata (contacts, billing state, milestones) is a separate brief if it earns one.

---

### `memory`
Projects-tier memory analog. Holds project-scoped facts — deployment topology, environment quirks, project conventions, project history — that travel with the engagement, not with PKA-the-team. Ships empty in the template. Same bi-temporal supersession discipline as `pka.db.memory`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| slug | TEXT NOT NULL | Kebab-case stable id; UNIQUE within `(project_slug, slug)` |
| project_slug | TEXT NOT NULL | FK to `projects.slug` ON DELETE RESTRICT |
| type | TEXT NOT NULL | CHECK in (`'topology'`, `'environment'`, `'host_fact'`, `'dependency'`, `'project'`, `'operational'`, `'feedback'`, `'pattern_ref'`) |
| title | TEXT NOT NULL | One-line summary |
| body | TEXT NOT NULL | The durable content |
| scope | TEXT NOT NULL | CHECK in (`'project_global'`, `'host:<role>'`, `'team_member:<slug>'`); role-shaped, not IP-shaped |
| source_ref | TEXT | Brief ref, deliverable id, etc. |
| status | TEXT NOT NULL | CHECK in (`'active'`, `'superseded'`, `'deferred'`, `'invalidated'`) |
| superseded_by | TEXT | Slug of replacement (XOR invariant with status='superseded') |
| valid_from | TEXT NOT NULL | ISO datetime, default `datetime('now')`; bi-temporal |
| valid_to | TEXT | ISO datetime; NULL = currently valid |
| ingested_at | TEXT NOT NULL | When PKA learned it |
| approved_by | TEXT | `'Levi'` for promotions into the durable layer; owner-name in general |
| provenance | TEXT NOT NULL | CHECK in (`'human_confirmed'`, `'orchestrator_inferred'`, `'model_inferred'`) — templated naming from day 1 |
| tags | TEXT | CSV |
| created_at | TEXT NOT NULL | ISO datetime, default `datetime('now')` |
| updated_at | TEXT NOT NULL | ISO datetime, default `datetime('now')` |

**Indexes:**
- `memory_project_idx` on (`project_slug`, `status`) — drives the per-brief lazy loader
- `memory_project_type_idx` on (`project_slug`, `type`, `status`) — drives the universal-small-load type filter
- `memory_scope_idx` on (`scope`, `status`)
- `memory_type_status_idx` on (`type`, `status`)
- `memory_ingested_at_idx` on (`ingested_at` DESC)

**Five differences from `pka.db.memory` (rationale: project-bound facts travel with the engagement, not with PKA-the-team):**

1. `project_slug` column + composite UNIQUE `(project_slug, slug)` — slug is unique within a project but can repeat across projects.
2. Scope enum is `project_global` / `host:<role>` / `team_member:<slug>` — no `global`, no `owner_only` (those are pka.db scopes). `host:<role>` is role-shaped (`host:prod` survives server replacement; `host:192.168.15.21` would not).
3. Type enum dropped `user_fact` / `pedagogy` / `preference` (those are pka.db scope); kept `operational` / `project` / `feedback` / `pattern_ref`; added `topology` / `environment` / `host_fact` / `dependency` (the must-know-before-routing facts).
4. Provenance enum uses `orchestrator_inferred` not `leroy_inferred` — templated from day 1.
5. UNIQUE is `(project_slug, slug)` not just `slug` — per-project namespacing.

**Loader:** see `CLAUDE.md` Session Open Protocol (universal-small-load over `topology` / `environment` / `host_fact` types across active projects) and Persona Handoff Model `briefs.project_slug` (per-brief lazy load).

### `memory_fts`

FTS5 virtual table over `memory.title` and `memory.body`. External-content shape with `content='memory'`, `content_rowid='id'`. Sync triggers: `memory_ai` / `memory_au` / `memory_ad` / `memory_touch` — body-identical to `pka.db.memory_fts`'s set. `project_slug` is deliberately NOT in FTS — low-cardinality categorical, better served by `memory_project_idx`.

---

### `schema_migrations`
Migration history for `projects.db`. Same shape as the Operations-tier version. Independent of `pka.db.schema_migrations`. On a fresh template install, the following rows are seeded as already-applied:

- `003_split_projects_db` — the historical bootstrap convention from PKA's BRIEF-132 split
- `001_projects_memory_substrate` — the projects-tier-native first migration

---

## ATTACH DATABASE pattern (cross-tier queries)

SQLite's `ATTACH DATABASE` lets a single connection see tables from multiple DB files. Use this when a query needs to join Operations-tier and Projects-tier data — for example, "show all content rows that came out of a specific brief," or "count engagement-tagged content rows by the brief that produced them."

**Pattern:**

```python
import sqlite3

conn = sqlite3.connect('<PKA_ROOT>/pka.db')
conn.execute("ATTACH DATABASE '<PKA_ROOT>/projects.db' AS projects")

# Now `briefs`, `deliverables`, etc. are unqualified (or `main.briefs`),
# and Projects-tier tables are addressable as `projects.assets`,
# `projects.content`, `projects.content_fts`.

rows = conn.execute("""
    SELECT b.brief_ref, b.title, COUNT(c.id) AS content_count
    FROM main.briefs b
    LEFT JOIN projects.assets a
      ON a.tags LIKE '%' || lower(replace(b.brief_ref, 'BRIEF-', 'brief-')) || '%'
    LEFT JOIN projects.content c
      ON c.asset_id = a.id
    GROUP BY b.brief_ref
    ORDER BY content_count DESC
    LIMIT 5;
""").fetchall()

conn.execute("DETACH DATABASE projects")
conn.close()
```

**Worked example — join Operations briefs to Projects content by engagement tag:**

```python
import sqlite3
conn = sqlite3.connect('<PKA_ROOT>/pka.db')
conn.execute("ATTACH DATABASE '<PKA_ROOT>/projects.db' AS projects")
rows = conn.execute("""
    SELECT
      b.brief_ref AS brief,
      COUNT(c.id) AS content_rows
    FROM projects.assets a
    JOIN projects.content c ON c.asset_id = a.id
    LEFT JOIN main.briefs b
      ON b.body LIKE '%' || :engagement_slug || '%'
     AND b.status = 'complete'
    WHERE a.tags LIKE '%' || :engagement_slug || '%'
    GROUP BY b.brief_ref
    ORDER BY content_rows DESC
    LIMIT 5;
""", {'engagement_slug': 'my-engagement'}).fetchall()
for r in rows:
    print(r)
conn.execute("DETACH DATABASE projects")
conn.close()
```

**Worked example — read owner observability into a session-open context (cross-tier into personal.db):**

```python
import sqlite3
conn = sqlite3.connect('<PKA_ROOT>/pka.db')
# Read the personal.db path from settings, then attach.
personal_db_path = conn.execute(
    "SELECT value FROM settings WHERE key='personal_db_path'"
).fetchone()[0]
conn.execute(f"ATTACH DATABASE '{personal_db_path}' AS personal")

# All four observation tables now addressable via the `personal` alias.
pending_for_owner = conn.execute("""
    SELECT id, observation_type, body, captured_at
    FROM personal.orchestrator_observations
    WHERE status = 'pending-review'
    ORDER BY captured_at DESC
    LIMIT 10;
""").fetchall()

conn.execute("DETACH DATABASE personal")
conn.close()
```

**Discipline notes:**

- `ATTACH DATABASE` accepts relative paths resolved against the **process working directory**, not the location of the main DB. Use absolute paths or `chdir` first. The migration runner (`migrate.py`) handles this internally by chdir'ing to the directory containing the target DB before opening the connection (the `_chdir_to_db_dir()` mitigation).
- Foreign keys are not enforced across attached databases. Cross-tier integrity is the caller's responsibility (e.g., the `briefs.project_slug` → `projects.db.projects.slug` reference is application-layer soft-validated).
- Always `DETACH DATABASE` when done — or close the connection. Attaching to a held connection prevents the attached DB file from being safely opened in write mode by another process.
- FTS5 queries work against the attached schema, but the `MATCH` operator must reference the FTS table via an alias (or unqualified name in the FROM clause) — `WHERE projects.content_fts MATCH 'term'` fails with "no such column"; `JOIN projects.content_fts AS f ... WHERE f.content_fts MATCH 'term'` works.

---

## Extending the Schema

Add new tables as new use cases emerge. Document them here. Do not modify existing table structures without considering migration. Schema changes go through `migrations/NNN_<slug>.sql` (see `migrations/README.md`).

---

---

# Personal Database — personal.db

**File:** `personal.db` (SQLite 3, FTS5 enabled)
**Location:** `~/PKA-Data/personal.db` by default; configurable via `python3 setup.py --personal-data-dir <path>`. The chosen path is recorded in `pka.db.settings.personal_db_path` for helper-layer lookup.
**Git status:** NOT tracked. Lives outside the PKA working directory. Never committed.

This database holds the owner's personal-layer data, separate from team-operational records. Team members (e.g. PAX during research) may query records where `private=0`. Records default to `private=0` (available to team). Set `private=1` for entries the owner wants kept personal-only.

**Naming convention:** Personal-tier tables use `owner_*` prefix (`owner_journal` / `owner_tasks` / `owner_notes` / `owner_posture` / `owner_observations`) and the orchestrator's observation table is `orchestrator_observations`. This is the canonical naming from v1.2.0 onward.

---

### `owner_journal`
Personal journal entries — distinct from operational journal entries in `pka.db`.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| date | TEXT | Entry date (date only) |
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

---

## Owner-tier observability (in `personal.db`)

Four tables in `personal.db` carry the system's observability discipline. The
underlying primitive is **two trust shapes × N observer/subject pairings**:
the active-on-write shape applies when the principal (owner) authors;
the pending-review shape applies when anyone else authors and the owner's
review is the gate.

| Observer | Subject scope | Table | Default `status` |
|---|---|---|---|
| Owner | PKA-as-a-whole | `owner_posture` | `active` |
| Owner | anyone (`orchestrator`, team member, `pka_system`) | `owner_observations` | `active` |
| Orchestrator (Leroy) | anyone (`owner`, team member, `pka_system`) | `orchestrator_observations` | `pending-review` |
| Team member (sam/pax/etc) | anyone (primary: `orchestrator`) | `team_observations` | `pending-review` |

All four tables are bi-temporal (`valid_from`, `valid_to`), carry `captured_at` /
`source_session` / `created_at` / `updated_at`, and have FTS5 over `body` (and
`evidence` where present). `observation_type` and `subject` are **open strings** —
no CHECK constraint — so the taxonomy can grow without a migration. `status` is
a closed enum; that is the load-bearing trust gate.

### `orchestrator_observations`
The orchestrator's observations about any subject — owner by default, but team members and `pka_system` are first-class subjects.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| observation_type | TEXT | open string; e.g. `'decision-style'`, `'framing-tendency'`, `'handoff-hygiene'` |
| body | TEXT NOT NULL | The observation itself |
| evidence | TEXT | Anchor citations from chat / deliverables |
| subject | TEXT NOT NULL DEFAULT `'owner'` | Open string; conventional values: `'owner'`, team_member slugs, `'pka_system'`. |
| captured_at | TEXT | DEFAULT `datetime('now')` |
| valid_from | TEXT | DEFAULT `datetime('now')` |
| valid_to | TEXT | NULL until invalidated |
| status | TEXT NOT NULL DEFAULT `'pending-review'` | Enum: `pending-review`, `active`, `corrected`, `superseded`, `archived`, `promoted-to-memory` |
| levi_response | TEXT | Owner's reaction / correction on review. Column name preserved for historical continuity; reads as "owner-response" under the canonical naming convention. |
| source_session | TEXT | Session ref where observation was captured |
| superseded_by | INTEGER | Intra-table FK; set when a later row supersedes this one |
| promoted_to_memory_id | INTEGER | Cross-DB ref to `pka.db.memory.id` (application-layer integrity) |
| created_at | TEXT | DEFAULT `datetime('now')` |
| updated_at | TEXT | DEFAULT `datetime('now')`; touched by trigger |

**FTS5:** `orchestrator_observations_fts` indexes `body + evidence`.
**Subject is deliberately excluded** from FTS — it is a short categorical token
(low cardinality, enum-shaped in practice), so it lives in a btree index
(`orchestrator_observations_subject_status_idx` on `(subject, status)`) rather than
the tokenized FTS index.

**Indexes:** `(status)`, `(observation_type, status)`, `(captured_at DESC)`,
`(subject, status)`.

### `owner_posture`, `owner_observations`, `team_observations`
Same overall shape (bi-temporal, status-gated, FTS5 over `body` + `evidence`).
See `migrations/personal/001_owner_observability.sql` for the canonical schema.

**`team_observations.observer`** is an open `TEXT NOT NULL` column with
soft-validated convention (lowercase first-name slug sourced from
`lower(pka.db.team_members.name)`). Cross-DB FK enforcement is not possible
in SQLite — `team_members` lives in `pka.db`, `team_observations` lives in
`personal.db` — so soft-validation moves to application-layer code. The hiring
runbook does NOT require a CHECK-widen step on every hire. `subject` is open
per the same principle as `orchestrator_observations`.

### `schema_migrations` (personal)
Migration history for `personal.db`. Same shape as the Operations-tier version. On a fresh template install, the following row is seeded as already-applied:

- `001_owner_observability` — the consolidated v1.2.0-baseline migration that creates all seven owner-tier tables (three personal-data + four observability)
