-- 006_briefs_project_slug.sql
-- BRIEF-215 — Add `project_slug` column to `briefs` table for cross-tier
-- project-context declaration.
--
-- The brief's design question 3 asks: how does a brief declare which project
-- it touches, so the team-member shim's lazy-load step can pull the right
-- project memory rows?
--
-- Decision: a `project_slug TEXT` column on `briefs`. Nullable. NULL = brief
-- is PKA-internal substrate work (no project context). Non-NULL = the slug
-- of the project this brief touches; team-member shim uses this to drive its
-- per-brief lazy load against `projects.db.memory`.
--
-- This is NOT an enforced FK to `projects.db.projects` — SQLite does not
-- enforce FKs across attached databases. The value is a text pointer with
-- application-layer soft-validation (projects_memory_io.py verifies the
-- slug exists in `projects.projects` before writing memory rows that
-- reference it). The dispatch convention in CLAUDE.md (per BRIEF-215 §8.3.2)
-- names that Leroy populates this at brief creation when the brief touches
-- a project, and that the slug must exist in `projects.db.projects`.
--
-- Schema change is constant-time on SQLite: ALTER TABLE ADD COLUMN with a
-- nullable column is a metadata-only operation. No data rewrite. No FTS
-- impact (briefs_fts indexes title + body only).
--
-- Index added so any future "all briefs that touched project X" query has
-- a btree to scan instead of a full table scan.

ALTER TABLE briefs ADD COLUMN project_slug TEXT;

CREATE INDEX IF NOT EXISTS briefs_project_idx ON briefs (project_slug);


-- +migrate Down

-- DOWN: drop the index then the column. SQLite supports DROP COLUMN
-- since 3.35.0 (released 2021); the pka.db runner runs against
-- sqlite_version >= 3.45 so this is safe.

DROP INDEX IF EXISTS briefs_project_idx;
ALTER TABLE briefs DROP COLUMN project_slug;

-- ROLLBACK (manual)
--   If the migration runner is unavailable:
--       BEGIN;
--       DROP INDEX IF EXISTS briefs_project_idx;
--       ALTER TABLE briefs DROP COLUMN project_slug;
--       DELETE FROM schema_migrations WHERE name = '006_briefs_project_slug';
--       COMMIT;
