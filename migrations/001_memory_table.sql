-- 001_memory_table.sql
-- PKA-native memory layer.
-- Adds the `memory` table, FTS5 mirror, indexes, sync triggers, and
-- markdown-mirror helper plumbing (the mirror itself is written by
-- memory_io.py, not from SQL — see memory_io.py for the contract).
--
-- Idempotent: every CREATE uses IF NOT EXISTS.
-- Reversible: see the DOWN block below.
--
-- Note: in this template, the DDL below is also embedded in setup.py so
-- that a fresh `python3 setup.py` install ships with the memory table
-- already in place. setup.py records this migration as already-applied
-- in `schema_migrations`. Future migrations (002, 003, …) added by the
-- owner apply via `python3 migrations/migrate.py up` as normal.

-- ---------- memory table ----------

CREATE TABLE IF NOT EXISTS memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL
                        CHECK (type IN (
                            'user_fact',
                            'project',
                            'feedback',
                            'pedagogy',
                            'preference',
                            'pattern_ref',
                            'operational'
                        )),
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    scope           TEXT NOT NULL
                        CHECK (
                            scope = 'global'
                            OR scope = 'owner_only'
                            OR scope LIKE 'team_member:%'
                        ),
    source_ref      TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN (
                            'active',
                            'superseded',
                            'deferred',
                            'invalidated'
                        )),
    superseded_by   TEXT,
    valid_from      TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to        TEXT,
    ingested_at     TEXT NOT NULL DEFAULT (datetime('now')),
    approved_by     TEXT,
    provenance      TEXT NOT NULL
                        CHECK (provenance IN (
                            'human_confirmed',
                            'leroy_inferred',
                            'model_inferred'
                        )),
    tags            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),

    -- A row is `superseded` iff superseded_by is set. The mirror is
    -- meaningful only when both columns agree — enforce that here so the
    -- bi-temporal queries don't have to special-case it.
    CHECK (
        (status = 'superseded' AND superseded_by IS NOT NULL)
        OR (status != 'superseded' AND superseded_by IS NULL)
    ),

    -- If valid_to is set, it must be at-or-after valid_from. Cheap insurance.
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

-- ---------- indexes ----------
-- Drive the load-profile queries: filter by (scope, status) is the
-- primary access pattern; (status, type) backs the type-filtered profile.
-- valid_to is mostly NULL but supports the bi-temporal queries; an index on
-- (valid_from, valid_to) earns its keep only if those queries get hot —
-- skipping for now per "no premature optimisation."

CREATE INDEX IF NOT EXISTS memory_scope_status_idx
    ON memory (scope, status);

CREATE INDEX IF NOT EXISTS memory_status_type_idx
    ON memory (status, type);

CREATE INDEX IF NOT EXISTS memory_ingested_at_idx
    ON memory (ingested_at DESC);

-- ---------- FTS5 ----------
-- External content over title + body, matching content_fts / patterns_fts.

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title,
    body,
    content='memory',
    content_rowid='id'
);

-- ---------- triggers ----------
-- FTS5 sync (insert/update/delete) + updated_at touch, matching the
-- patterns_ai / patterns_au / patterns_ad / patterns_touch shape.

CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO memory_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;

CREATE TRIGGER IF NOT EXISTS memory_touch AFTER UPDATE ON memory
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE memory SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- +migrate Down

DROP TRIGGER IF EXISTS memory_touch;
DROP TRIGGER IF EXISTS memory_ad;
DROP TRIGGER IF EXISTS memory_au;
DROP TRIGGER IF EXISTS memory_ai;
DROP TABLE IF EXISTS memory_fts;
DROP INDEX IF EXISTS memory_ingested_at_idx;
DROP INDEX IF EXISTS memory_status_type_idx;
DROP INDEX IF EXISTS memory_scope_status_idx;
DROP TABLE IF EXISTS memory;
