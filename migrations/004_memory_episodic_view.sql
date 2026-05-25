-- 004_memory_episodic_view.sql
-- BRIEF-140 (follows BRIEF-136 Path B — episodic memory as a SQL view).
--
-- Creates `memory_episodic_view` in pka.db: a read-only SQL view that
-- projects rows from `briefs` + `deliverables` + `feedback` + `journal`
-- into the `memory` row shape, so a consumer that wants episodic context
-- can UNION ALL it with `memory` without column-shape drift.
--
-- Two projections, UNION ALL'd:
--   A. briefs projection — one row per (completed brief, deliverable)
--      pair, with feedback LEFT JOINed onto the deliverable. Briefs that
--      completed without a recorded deliverable produce one row with the
--      slug suffix `open` (per BRIEF-140 §1 spec). 138 completed briefs +
--      145 deliverables under them + 5 deliverable-less completed briefs
--      → 150 brief-projection rows at the time of writing.
--   B. journal projection — one row per journal entry. 9 rows at the
--      time of writing.
--
-- Total expected view rowcount at apply time: 159. Recomputable from the
-- source tables; no data movement.
--
-- ------------------------------------------------------------
-- Design decisions (full reasoning in
-- /home/bzadmin/Documents/PKA/owners_inbox/memory_episodic_view_migration_iris.md):
--
--   * Path B (episodic-as-view), not Path A (duplicate into memory.type).
--     The operational tables already are the authoritative store for
--     "what happened." A view exposes them in the memory-row shape
--     without paying the curation + staleness cost of duplication.
--
--   * Provenance enum: ADD `projected` (Option α), not nullable
--     (Option β). The view's provenance is "computed from operational
--     state" — that IS honest provenance, and a NOT NULL invariant on
--     every result row of any UNION over memory + view is worth keeping.
--     One CHECK constraint replacement; no helper-function changes.
--     Defended in the deliverable.
--
--   * WHERE clause filters to `briefs.status = 'complete'`. Open and
--     active briefs are "what we are doing now," not "what happened."
--     Episodic memory is the past, not the present. A re-opened brief
--     would need its own design — flagged as out-of-scope.
--
--   * Slug pattern: stable + reproducible across recomputations.
--     `episodic-brief-<brief_ref>-<deliverable_id_or_open>` for projection A;
--     `episodic-journal-<journal_id>` for projection B.
--     A future deliverable insert against a previously-deliverable-less
--     brief WILL change that brief's slug (suffix goes from `open` to
--     `<deliverable_id>`). This is acceptable because the view is
--     recomputable and slugs are not durable identifiers in the view —
--     the operational id columns are.
--
--   * id column: NULL. Views in SQLite have no INTEGER PK; projecting
--     NULL keeps the UNION ALL shape compatible with `memory.id`
--     (INTEGER PRIMARY KEY, which tolerates NULL when read through a
--     UNION). Consumers that need a stable per-row id should use `slug`.
--
--   * No CHECK constraints on view rows. SQLite views do not enforce
--     CHECK constraints on returned values; the projection is
--     responsible for producing values that would satisfy the `memory`
--     table's CHECKs if inserted (e.g., status='active' / superseded_by
--     IS NULL agrees with the XOR invariant; valid_to IS NULL agrees
--     with `valid_to >= valid_from`).
--
--   * No FTS over the view. SQLite FTS5 cannot index views. The source
--     tables already have FTS (`briefs_fts`, `journal_fts`); episodic
--     full-text search routes there. Documented as deferred in
--     BRIEF-136 §3 / §7 out-of-scope.
--
--   * No new helper in memory_io.py. The view is read-only; callers
--     `SELECT FROM memory_episodic_view` directly.
--
--   * No `memory_unified_view` (UNION ALL of memory + episodic). Per
--     BRIEF-136 §3 flag 3 / §7, defer to a concrete consumer.
--
-- ------------------------------------------------------------
-- Provenance enum update (Option α — included on UP):
--
--   ALTER TABLE memory DROP CONSTRAINT is not supported by SQLite. The
--   CHECK constraint on memory.provenance is part of the table
--   definition and can only be changed by table reconstruction (the
--   standard "12-step ALTER" — CREATE new, copy, drop old, rename).
--   That is a more invasive migration than the view itself warrants,
--   especially for adding a single enum value used only by view rows.
--
--   Resolution: the enum extension happens at the SQL projection layer,
--   not at the table-DDL layer. The view emits 'projected' as a
--   string-literal provenance; the memory table's CHECK constraint
--   continues to allow only the three original values
--   (human_confirmed / leroy_inferred / model_inferred). Any consumer
--   doing `INSERT INTO memory SELECT * FROM memory_episodic_view` would
--   fail the CHECK — which is the correct behaviour, because the
--   episodic view is read-only and view rows are not meant to be
--   materialised into the memory table.
--
--   The DB_SCHEMA.md update (separate brief) will document the
--   four-value provenance vocabulary explicitly: three are valid for
--   `memory` row inserts; the fourth (`projected`) is reserved for
--   read-side view projections and is not insertable into `memory`.
--
--   This is materially the same as Option α in BRIEF-140 §2 (the
--   `projected` value exists in the system's vocabulary) but executed
--   without paying the table-rebuild cost. The deliverable explains the
--   trade-off and asks Levi to ratify or override.
--
-- ------------------------------------------------------------
-- Idempotent on UP: CREATE VIEW IF NOT EXISTS.
-- Reversible on DOWN: DROP VIEW IF EXISTS. Non-destructive in both
-- directions — no source-table data is touched.

-- ============================================================
-- UP
-- ============================================================

DROP VIEW IF EXISTS memory_episodic_view;

CREATE VIEW memory_episodic_view AS

-- ---------- Projection A: briefs + deliverables + feedback ----------
-- One row per (completed brief, deliverable). Briefs that completed
-- without a recorded deliverable produce one row with suffix 'open'.
-- Feedback LEFT JOINs onto the deliverable (no observed deliverable has
-- >1 feedback row in the operational data — verified at write time;
-- the verify script asserts this invariant holds post-apply).

SELECT
    NULL                                                AS id,
    'episodic-brief-' || b.brief_ref || '-' ||
        coalesce(CAST(d.id AS TEXT), 'open')            AS slug,
    'operational'                                       AS type,
    b.title                                             AS title,
    'Brief ' || b.brief_ref ||
        ' (assigned to ' || b.assigned_to || '): ' ||
        b.title ||
        CASE
            WHEN d.id IS NOT NULL
                THEN ' — delivered ' || coalesce(d.file_path, '(path unset)')
            ELSE ' — completed without a recorded deliverable'
        END ||
        CASE
            WHEN f.id IS NOT NULL
                THEN ' — rated ' || coalesce(CAST(f.rating AS TEXT), '?') ||
                     '/5' ||
                     CASE WHEN f.notes IS NOT NULL AND f.notes != ''
                          THEN ': ' || f.notes
                          ELSE ''
                     END
            ELSE ''
        END                                             AS body,
    'global'                                            AS scope,
    b.brief_ref                                         AS source_ref,
    'active'                                            AS status,
    NULL                                                AS superseded_by,
    b.created_at                                        AS valid_from,
    NULL                                                AS valid_to,
    b.created_at                                        AS ingested_at,
    NULL                                                AS approved_by,
    'projected'                                         AS provenance,
    'episodic,brief' ||
        CASE WHEN d.id IS NOT NULL THEN ',delivered' ELSE '' END ||
        CASE WHEN f.id IS NOT NULL THEN ',rated'     ELSE '' END
                                                        AS tags,
    b.created_at                                        AS created_at,
    coalesce(b.completed_at, b.created_at)              AS updated_at
FROM briefs b
LEFT JOIN deliverables d ON d.brief_id = b.id
LEFT JOIN feedback      f ON f.deliverable_id = d.id
WHERE b.status = 'complete'

UNION ALL

-- ---------- Projection B: journal ----------
-- One row per journal entry. Journal entries are events as written;
-- there is no completion gate analogous to briefs.status='complete'.

SELECT
    NULL                                                AS id,
    'episodic-journal-' || CAST(j.id AS TEXT)           AS slug,
    'operational'                                       AS type,
    coalesce(j.title, 'Journal entry ' || j.date)       AS title,
    coalesce(j.title || char(10) || char(10) || j.body,
             j.body)                                    AS body,
    'global'                                            AS scope,
    'journal:' || CAST(j.id AS TEXT)                    AS source_ref,
    'active'                                            AS status,
    NULL                                                AS superseded_by,
    j.created_at                                        AS valid_from,
    NULL                                                AS valid_to,
    j.created_at                                        AS ingested_at,
    NULL                                                AS approved_by,
    'projected'                                         AS provenance,
    'episodic,journal' ||
        CASE WHEN j.project IS NOT NULL AND j.project != ''
             THEN ',project:' || j.project
             ELSE ''
        END                                             AS tags,
    j.created_at                                        AS created_at,
    coalesce(j.updated_at, j.created_at)                AS updated_at
FROM journal j;


-- +migrate Down

-- ============================================================
-- DOWN — drop the view. Non-destructive (no source data touched).
-- ============================================================

DROP VIEW IF EXISTS memory_episodic_view;


-- ============================================================
-- ROLLBACK (manual, not auto-applied)
-- ============================================================
--
-- This migration is non-destructive: it only adds a view. The DOWN block
-- above is sufficient for a clean rollback (DROP VIEW). No source data
-- needs to be restored; no helper code needs to be reverted; no other
-- migrations depend on this one.
--
-- If applied to production by accident or with a defective projection:
--
--   1. Run: python3 migrations/migrate.py down --db pka.db
--      (rolls back the most recent migration, which will be 004)
--   2. Verify the view is gone: confirm sqlite_master has no row
--      where type='view' and name='memory_episodic_view'.
--   3. If a consumer was already querying the view: they will get a
--      "no such table: memory_episodic_view" error. That error is loud
--      and immediate — no silent data corruption is possible.
--
-- No CHECK constraint changes were applied (per the design decision
-- documented in the UP comment block), so no constraint-revert step is
-- needed.
