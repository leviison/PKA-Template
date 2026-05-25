-- 003_split_projects_db.sql
-- PKA-Template v1.2.0 baseline — Operations / Projects DB split.
--
-- Creates `projects.db` as a sibling of `pka.db` and establishes the
-- Projects tier with `assets` + `content` + `content_fts` tables. After
-- this migration, content-extraction work targets `projects.db.assets`
-- and `projects.db.content` instead of `pka.db.assets` and
-- `pka.db.content`.
--
-- Template-baseline note: PKA's `003_split_projects_db.sql` carries
-- data-movement DDL (copy assets/content rows from pka.db → projects.db,
-- then DROP the source). PKA-Template's variant skips the data-movement
-- because on a fresh install there is no data to move — `setup.py`
-- creates the v1.2.0 baseline directly with `assets` + `content` already
-- absent from `pka.db` and only present in `projects.db`. This migration
-- exists as the canonical schema-creation step for `projects.db`, and to
-- seed `projects.db.schema_migrations` with the historical bootstrap
-- row that pka.db's BRIEF-132 split established by convention.
--
-- Why one migration:
--   The projects.db substrate is one architectural step. Splitting it
--   across multiple migrations would create install-time windows where
--   the projects.db file exists but is empty of the canonical tables.
--
-- Idempotent on UP: every CREATE uses IF NOT EXISTS, every INSERT uses
-- OR IGNORE.
--
-- Reversible on DOWN: drops the tables in projects.db. The projects.db
-- file itself is left in place (empty of the moved tables) on DOWN —
-- the operator may delete it manually if desired.

-- ============================================================
-- UP
-- ============================================================

ATTACH DATABASE 'projects.db' AS projects;

-- ---------- projects.schema_migrations ----------
-- Each DB carries its own schema_migrations table. The runner records
-- THIS migration in main.schema_migrations (its --db target); we seed
-- projects.schema_migrations independently so projects.db can grow its
-- own migration history when Projects-tier work emerges later.

CREATE TABLE IF NOT EXISTS projects.schema_migrations (
    name        TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO projects.schema_migrations (name)
    VALUES ('003_split_projects_db');

-- ---------- projects.assets ----------

CREATE TABLE IF NOT EXISTS projects.assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    path        TEXT NOT NULL,
    type        TEXT,
    size_bytes  INTEGER,
    date_added  TEXT NOT NULL DEFAULT (datetime('now')),
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','processing','processed','archived')),
    tags        TEXT,
    notes       TEXT
);

-- ---------- projects.content ----------
-- Intra-DB FK to assets with CASCADE on delete.

CREATE TABLE IF NOT EXISTS projects.content (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id       INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    content_type   TEXT,
    body           TEXT,
    extracted_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------- projects.content_fts ----------

CREATE VIRTUAL TABLE IF NOT EXISTS projects.content_fts USING fts5(
    body,
    content='content',
    content_rowid='id'
);

-- ---------- projects.content sync triggers ----------
-- AI and AD triggers only (no AU). The intended pattern for body changes
-- is DELETE + INSERT, not UPDATE.

CREATE TRIGGER IF NOT EXISTS projects.content_ai
AFTER INSERT ON projects.content
BEGIN
    INSERT INTO content_fts(rowid, body) VALUES (new.id, new.body);
END;

CREATE TRIGGER IF NOT EXISTS projects.content_ad
AFTER DELETE ON projects.content
BEGIN
    INSERT INTO content_fts(content_fts, rowid, body)
    VALUES ('delete', old.id, old.body);
END;

DETACH DATABASE projects;


-- +migrate Down

-- ============================================================
-- DOWN — drop projects.db tables (file itself stays).
-- ============================================================

ATTACH DATABASE 'projects.db' AS projects;

DROP TRIGGER IF EXISTS projects.content_ai;
DROP TRIGGER IF EXISTS projects.content_ad;
DROP TABLE IF EXISTS projects.content_fts;
DROP TABLE IF EXISTS projects.content;
DROP TABLE IF EXISTS projects.assets;

DELETE FROM projects.schema_migrations WHERE name = '003_split_projects_db';

DETACH DATABASE projects;
