-- 001_projects_memory_substrate.sql
-- BRIEF-215 — Create the projects-tier memory substrate in projects.db.
--
-- Two tables + supporting indexes / triggers / FTS5:
--
--   projects        — registry of engagements (slug, name, description, status,
--                     primary_host, repo_url, repo_path). Minimal schema per the
--                     brief's out-of-scope clause. The PK `slug` is the FK target
--                     from `memory.project_slug`.
--
--   memory          — the projects-tier memory analog. Mirrors pka.db.memory
--                     closely with five named differences (see deliverable §2.3):
--                     (a) `project_slug TEXT NOT NULL` column + composite UNIQUE
--                         (project_slug, slug)
--                     (b) scope enum: `project_global` / `host:<role>` /
--                         `team_member:<slug>` — non-overlapping with pka.db
--                         scopes by design
--                     (c) type enum dropped pedagogy/preference/user_fact;
--                         added topology/environment/host_fact/dependency
--                     (d) provenance enum: `orchestrator_inferred` (templated
--                         rename of pka.db's `leroy_inferred`)
--                     (e) FK to projects via project_slug (intra-DB, enforced
--                         under PRAGMA foreign_keys=ON)
--
-- Background: this is migration 001 in the projects-tier series. The earlier
-- `'003_split_projects_db'` row in `projects.db.schema_migrations` was seeded
-- during the BRIEF-132 split (the bootstrap migration was numbered against
-- pka.db's series for historical reasons; the new projects-tier series starts
-- cleanly at 001). The runner reads both rows from the same table; the gap is
-- audit context, not a runner concern.
--
-- FK on memory.project_slug:
--   FOREIGN KEY (project_slug) REFERENCES projects (slug) ON DELETE RESTRICT
--   — RESTRICT prevents a `DELETE FROM projects` from silently orphaning
--   memory rows. To retire a project: set projects.status='archived' (loader
--   respects it) or delete its memory first.
--
-- FTS5:
--   memory_fts indexes (title, body) only. project_slug is deliberately
--   EXCLUDED from FTS — it's a low-cardinality categorical token better
--   served by the btree index `memory_project_idx`. Same shape as the
--   leroy_observations.subject decision in BRIEF-145.
--
-- Atomicity:
--   migrate.py wraps `executescript` in `with conn:` which BEGINs and COMMITs
--   around the script. SQLite supports DDL inside transactions — if any step
--   fails, the entire creation rolls back.

-- ============================================================
-- Table 1: projects (the registry)
-- ============================================================

CREATE TABLE projects (
    slug         TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    status       TEXT NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active', 'dormant', 'archived')),
    primary_host TEXT,
    repo_url     TEXT,
    repo_path    TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX projects_status_idx ON projects (status);

-- Auto-touch updated_at on UPDATE (mirror of memory_touch pattern).
CREATE TRIGGER projects_touch AFTER UPDATE ON projects
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE projects SET updated_at = datetime('now') WHERE slug = NEW.slug;
END;


-- ============================================================
-- Table 2: memory (the projects-tier memory analog)
-- ============================================================

CREATE TABLE memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL,
    project_slug    TEXT NOT NULL,
    type            TEXT NOT NULL
                        CHECK (type IN (
                            'operational',
                            'project',
                            'feedback',
                            'pattern_ref',
                            'topology',
                            'environment',
                            'host_fact',
                            'dependency'
                        )),
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    scope           TEXT NOT NULL
                        CHECK (
                            scope = 'project_global'
                            OR scope LIKE 'host:%'
                            OR scope LIKE 'team_member:%'
                        ),
    source_ref      TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN (
                            'active', 'superseded', 'deferred', 'invalidated'
                        )),
    superseded_by   TEXT,
    valid_from      TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to        TEXT,
    ingested_at     TEXT NOT NULL DEFAULT (datetime('now')),
    approved_by     TEXT,
    provenance      TEXT NOT NULL
                        CHECK (provenance IN (
                            'human_confirmed',
                            'orchestrator_inferred',
                            'model_inferred'
                        )),
    tags            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (project_slug) REFERENCES projects (slug) ON DELETE RESTRICT,
    UNIQUE (project_slug, slug),
    CHECK (
        (status = 'superseded' AND superseded_by IS NOT NULL)
        OR (status != 'superseded' AND superseded_by IS NULL)
    ),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX memory_project_idx       ON memory (project_slug, status);
CREATE INDEX memory_project_type_idx  ON memory (project_slug, type, status);
CREATE INDEX memory_scope_idx         ON memory (scope, status);
CREATE INDEX memory_type_status_idx   ON memory (type, status);
CREATE INDEX memory_ingested_at_idx   ON memory (ingested_at DESC);

-- Auto-touch updated_at on UPDATE.
CREATE TRIGGER memory_touch AFTER UPDATE ON memory
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE memory SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- ============================================================
-- FTS5 for memory (title + body; same shape as pka.db.memory_fts)
-- ============================================================

CREATE VIRTUAL TABLE memory_fts USING fts5 (
    title,
    body,
    content='memory',
    content_rowid='id'
);

CREATE TRIGGER memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, title, body)
        VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER memory_au AFTER UPDATE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body)
        VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO memory_fts(rowid, title, body)
        VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, body)
        VALUES ('delete', old.id, old.title, old.body);
END;


-- +migrate Down

-- ============================================================
-- DOWN: drop in reverse dependency order (FTS sync triggers,
-- FTS virtual table, memory indexes, memory triggers, memory,
-- projects triggers, projects).
--
-- Caveat: any rows inserted into memory or projects between UP and DOWN
-- will be lost (the tables are dropped wholesale). This is acceptable
-- for a substrate-creation migration — the rollback is meant to undo
-- an apply, not preserve data accumulated against it.
-- ============================================================

DROP TRIGGER IF EXISTS memory_ai;
DROP TRIGGER IF EXISTS memory_au;
DROP TRIGGER IF EXISTS memory_ad;
DROP TABLE IF EXISTS memory_fts;

DROP TRIGGER IF EXISTS memory_touch;
DROP INDEX IF EXISTS memory_project_idx;
DROP INDEX IF EXISTS memory_project_type_idx;
DROP INDEX IF EXISTS memory_scope_idx;
DROP INDEX IF EXISTS memory_type_status_idx;
DROP INDEX IF EXISTS memory_ingested_at_idx;
DROP TABLE IF EXISTS memory;

DROP TRIGGER IF EXISTS projects_touch;
DROP INDEX IF EXISTS projects_status_idx;
DROP TABLE IF EXISTS projects;

-- ROLLBACK (manual)
--   If the migration runner is unavailable:
--       BEGIN;
--       -- (repeat the DOWN block above)
--       DELETE FROM schema_migrations WHERE name = '001_projects_memory_substrate';
--       COMMIT;
