-- 001_owner_observability.sql
-- PKA-Template v1.2.0 baseline — Owner-tier observability substrate.
--
-- Creates the four-axis observability discipline in personal.db at the
-- final canonical names from day one:
--
--   owner_posture              — Owner about PKA over time
--   owner_observations         — Owner about anyone (team_member, orchestrator, pka_system)
--   orchestrator_observations  — Orchestrator (Leroy) about anyone (default: owner)
--   team_observations          — Team member about anyone (primary: team → orchestrator)
--
-- Consolidation note (template-baseline migration):
--   PKA-current arrived at these table names via a series of
--   substrate migrations and one big rename pass:
--     - PKA personal/001 created `levi_posture` + `leroy_observations`
--     - PKA personal/002 added `levi_observations` + `team_observations`
--     - PKA personal/003 added `subject` to `leroy_observations`
--     - PKA personal/004 widened `leroy_observations.status` enum
--     - PKA personal/005 renamed everything to the canonical owner_*/
--       orchestrator_* form, dropped the closed CHECK on
--       team_observations.observer, and rewrote captured_by values
--   On a fresh template install there is no historical state to migrate
--   from, so this single migration creates the final canonical shape
--   directly. The five-migration history is preserved in PKA's repo as
--   audit context; template-instance owners inherit the result without
--   the rebuild churn.
--
-- The two trust shapes:
--   - active-on-write — the principal (owner) authors; their authority
--     IS the gate. Default `status = 'active'`. Applies to:
--       owner_posture, owner_observations.
--   - pending-review  — anyone else authors; principal's review is the
--     gate. Default `status = 'pending-review'`. Applies to:
--       orchestrator_observations, team_observations.
--
-- Design constraints carried forward from PKA:
--   - `observation_type` and `subject` are OPEN strings (no CHECK enum) so
--     the taxonomy can grow without a migration. `status` IS a closed
--     enum — that is the load-bearing trust gate.
--   - `observer` on `team_observations` is also an OPEN string (PAX R5,
--     applied 2026-05-25): cross-DB FK to pka.db.team_members.name is
--     not enforceable in SQLite, so the discipline is "lowercase first-
--     name slug sourced from `lower(pka.db.team_members.name)`",
--     soft-validated at the application layer. This means the hiring
--     runbook does NOT require a CHECK-widen migration on every hire.
--   - Bi-temporal (`valid_from` / `valid_to`) for consistency with the
--     memory table in pka.db.
--   - FTS5 over `body` (and `evidence` where applicable) — searchable
--     from day one because the value of these tables is in the
--     historical lookup. `subject` is deliberately EXCLUDED from FTS
--     and lives in a btree index instead (low-cardinality categorical
--     token; see PKA personal/003 for the defense).
--   - `captured_by` on `owner_posture` uses the canonical
--     ('owner','orchestrator') enum — NOT the historical ('levi','leroy')
--     pre-rename form.
--   - `subject` defaults to 'owner' on `orchestrator_observations`,
--     preserving the historical semantic ("observation about the owner")
--     under the canonical naming.

-- ============================================================
-- Table 1: owner_journal — personal journal entries
-- ============================================================

CREATE TABLE IF NOT EXISTS owner_journal (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL DEFAULT (date('now')),
    title      TEXT,
    body       TEXT NOT NULL,
    tags       TEXT,
    mood       TEXT,
    private    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS owner_journal_fts USING fts5(
    title, body, content='owner_journal', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS owner_journal_ai AFTER INSERT ON owner_journal BEGIN
    INSERT INTO owner_journal_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_journal_au AFTER UPDATE ON owner_journal BEGIN
    INSERT INTO owner_journal_fts(owner_journal_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO owner_journal_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_journal_ad AFTER DELETE ON owner_journal BEGIN
    INSERT INTO owner_journal_fts(owner_journal_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;


-- ============================================================
-- Table 2: owner_tasks — personal task list
-- ============================================================

CREATE TABLE IF NOT EXISTS owner_tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT,
    status     TEXT NOT NULL DEFAULT 'open'
                   CHECK(status IN ('open','in_progress','done','deferred')),
    priority   INTEGER NOT NULL DEFAULT 2,
    due_date   TEXT,
    tags       TEXT,
    private    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS owner_tasks_fts USING fts5(
    title, body, content='owner_tasks', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS owner_tasks_ai AFTER INSERT ON owner_tasks BEGIN
    INSERT INTO owner_tasks_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_tasks_au AFTER UPDATE ON owner_tasks BEGIN
    INSERT INTO owner_tasks_fts(owner_tasks_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO owner_tasks_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_tasks_ad AFTER DELETE ON owner_tasks BEGIN
    INSERT INTO owner_tasks_fts(owner_tasks_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;


-- ============================================================
-- Table 3: owner_notes — personal reference notes
-- ============================================================

CREATE TABLE IF NOT EXISTS owner_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT,
    source     TEXT,
    tags       TEXT,
    private    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS owner_notes_fts USING fts5(
    title, body, content='owner_notes', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS owner_notes_ai AFTER INSERT ON owner_notes BEGIN
    INSERT INTO owner_notes_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_notes_au AFTER UPDATE ON owner_notes BEGIN
    INSERT INTO owner_notes_fts(owner_notes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
    INSERT INTO owner_notes_fts(rowid, title, body)
    VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_notes_ad AFTER DELETE ON owner_notes BEGIN
    INSERT INTO owner_notes_fts(owner_notes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;


-- ============================================================
-- Table 4: owner_posture — Owner's framing/posture about PKA
-- ============================================================
-- captured_by enum uses canonical ('owner','orchestrator') from day 1.

CREATE TABLE IF NOT EXISTS owner_posture (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    posture_type    TEXT,                       -- open string; e.g. 'framing', 're-engagement', 'pattern-recognition'
    body            TEXT NOT NULL,
    captured_by     TEXT NOT NULL
                        CHECK (captured_by IN ('owner', 'orchestrator')),
    captured_at     TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from      TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to        TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN (
                            'active',
                            'superseded',
                            'promoted-to-memory',
                            'archived'
                        )),
    source_session  TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    superseded_by   INTEGER REFERENCES owner_posture(id),
    promoted_to_memory_id INTEGER,              -- cross-DB ref to pka.db.memory.id

    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS owner_posture_status_idx
    ON owner_posture (status);

CREATE INDEX IF NOT EXISTS owner_posture_type_status_idx
    ON owner_posture (posture_type, status);

CREATE INDEX IF NOT EXISTS owner_posture_captured_at_idx
    ON owner_posture (captured_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS owner_posture_fts USING fts5(
    body,
    content='owner_posture',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS owner_posture_ai AFTER INSERT ON owner_posture BEGIN
    INSERT INTO owner_posture_fts(rowid, body)
    VALUES (new.id, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_posture_au AFTER UPDATE ON owner_posture BEGIN
    INSERT INTO owner_posture_fts(owner_posture_fts, rowid, body)
    VALUES ('delete', old.id, old.body);
    INSERT INTO owner_posture_fts(rowid, body)
    VALUES (new.id, new.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_posture_ad AFTER DELETE ON owner_posture BEGIN
    INSERT INTO owner_posture_fts(owner_posture_fts, rowid, body)
    VALUES ('delete', old.id, old.body);
END;

CREATE TRIGGER IF NOT EXISTS owner_posture_touch AFTER UPDATE ON owner_posture
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE owner_posture SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- ============================================================
-- Table 5: owner_observations — Owner about anyone
-- ============================================================
-- Default status 'active' — owner's authority IS the gate.
-- Subject open string; typical values: 'orchestrator', team-member slug,
-- 'pka_system'.

CREATE TABLE IF NOT EXISTS owner_observations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    subject                 TEXT NOT NULL,
    observation_type        TEXT,
    body                    TEXT NOT NULL,
    evidence                TEXT,
    captured_at             TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from              TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to                TEXT,
    status                  TEXT NOT NULL DEFAULT 'active'
                                CHECK (status IN (
                                    'active',
                                    'superseded',
                                    'archived',
                                    'promoted-to-memory'
                                )),
    notes                   TEXT,
    source_session          TEXT,
    superseded_by           INTEGER REFERENCES owner_observations(id),
    promoted_to_memory_id   INTEGER,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS owner_observations_status_idx
    ON owner_observations (status);

CREATE INDEX IF NOT EXISTS owner_observations_subject_status_idx
    ON owner_observations (subject, status);

CREATE INDEX IF NOT EXISTS owner_observations_type_status_idx
    ON owner_observations (observation_type, status);

CREATE INDEX IF NOT EXISTS owner_observations_captured_at_idx
    ON owner_observations (captured_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS owner_observations_fts USING fts5(
    body,
    evidence,
    content='owner_observations',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS owner_observations_ai AFTER INSERT ON owner_observations BEGIN
    INSERT INTO owner_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS owner_observations_au AFTER UPDATE ON owner_observations BEGIN
    INSERT INTO owner_observations_fts(owner_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
    INSERT INTO owner_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS owner_observations_ad AFTER DELETE ON owner_observations BEGIN
    INSERT INTO owner_observations_fts(owner_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
END;

CREATE TRIGGER IF NOT EXISTS owner_observations_touch AFTER UPDATE ON owner_observations
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE owner_observations SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- ============================================================
-- Table 6: orchestrator_observations — Orchestrator about anyone
-- ============================================================
-- Default status 'pending-review' — owner's review IS the gate.
-- Subject defaults to 'owner' (the historical default).
-- Status enum includes 'promoted-to-memory' from day 1
-- (PKA personal/004 widened the enum after the fact; template ships the
-- final shape).

CREATE TABLE IF NOT EXISTS orchestrator_observations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_type  TEXT,
    body              TEXT NOT NULL,
    evidence          TEXT,
    captured_at       TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from        TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to          TEXT,
    status            TEXT NOT NULL DEFAULT 'pending-review'
                        CHECK (status IN (
                            'pending-review',
                            'active',
                            'corrected',
                            'superseded',
                            'archived',
                            'promoted-to-memory'
                        )),
    levi_response     TEXT,
                            -- column name preserved from PKA for continuity;
                            -- "levi_response" reads as "owner-response" under
                            -- the canonical naming convention. A future
                            -- generic rename (levi_response → owner_response)
                            -- is a separate cosmetic call.
    source_session    TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    superseded_by     INTEGER REFERENCES orchestrator_observations(id),
    promoted_to_memory_id INTEGER,
    subject           TEXT NOT NULL DEFAULT 'owner',

    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS orchestrator_observations_status_idx
    ON orchestrator_observations (status);

CREATE INDEX IF NOT EXISTS orchestrator_observations_type_status_idx
    ON orchestrator_observations (observation_type, status);

CREATE INDEX IF NOT EXISTS orchestrator_observations_captured_at_idx
    ON orchestrator_observations (captured_at DESC);

CREATE INDEX IF NOT EXISTS orchestrator_observations_subject_status_idx
    ON orchestrator_observations (subject, status);

CREATE VIRTUAL TABLE IF NOT EXISTS orchestrator_observations_fts USING fts5(
    body,
    evidence,
    content='orchestrator_observations',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS orchestrator_observations_ai AFTER INSERT ON orchestrator_observations BEGIN
    INSERT INTO orchestrator_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS orchestrator_observations_au AFTER UPDATE ON orchestrator_observations BEGIN
    INSERT INTO orchestrator_observations_fts(orchestrator_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
    INSERT INTO orchestrator_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS orchestrator_observations_ad AFTER DELETE ON orchestrator_observations BEGIN
    INSERT INTO orchestrator_observations_fts(orchestrator_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
END;

CREATE TRIGGER IF NOT EXISTS orchestrator_observations_touch AFTER UPDATE ON orchestrator_observations
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE orchestrator_observations SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- ============================================================
-- Table 7: team_observations — Team member about anyone
-- ============================================================
-- Default status 'pending-review' — owner's review IS the gate.
-- observer is an OPEN string (no closed CHECK enum): convention is
-- lowercase first-name slug sourced from `lower(pka.db.team_members.name)`,
-- soft-validated at the application layer. Cross-DB FK is not enforceable
-- in SQLite, so the hiring runbook does NOT require a CHECK-widen
-- migration on every roster change.
-- subject is open per the same principle.

CREATE TABLE IF NOT EXISTS team_observations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    observer                TEXT NOT NULL,
                                -- open string. Convention: lowercase first-
                                -- name slug from lower(pka.db.team_members.name).
                                -- The orchestrator persona is intentionally NOT
                                -- a valid observer here — its observations live
                                -- in orchestrator_observations.
    subject                 TEXT NOT NULL,
                                -- open string. Primary expected: 'orchestrator'
                                -- (or 'owner' for team→owner observations).
    observation_type        TEXT,
    body                    TEXT NOT NULL,
    evidence                TEXT,
    captured_at             TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from              TEXT NOT NULL DEFAULT (datetime('now')),
    valid_to                TEXT,
    status                  TEXT NOT NULL DEFAULT 'pending-review'
                                CHECK (status IN (
                                    'pending-review',
                                    'active',
                                    'corrected',
                                    'superseded',
                                    'archived',
                                    'promoted-to-memory'
                                )),
    levi_response           TEXT,
    source_deliverable_id   INTEGER,            -- cross-DB ref to pka.db.deliverables.id
    source_session          TEXT,
    superseded_by           INTEGER REFERENCES team_observations(id),
    promoted_to_memory_id   INTEGER,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS team_observations_status_idx
    ON team_observations (status);

CREATE INDEX IF NOT EXISTS team_observations_observer_status_idx
    ON team_observations (observer, status);

CREATE INDEX IF NOT EXISTS team_observations_subject_status_idx
    ON team_observations (subject, status);

CREATE INDEX IF NOT EXISTS team_observations_type_status_idx
    ON team_observations (observation_type, status);

CREATE INDEX IF NOT EXISTS team_observations_captured_at_idx
    ON team_observations (captured_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS team_observations_fts USING fts5(
    body,
    evidence,
    content='team_observations',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS team_observations_ai AFTER INSERT ON team_observations BEGIN
    INSERT INTO team_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS team_observations_au AFTER UPDATE ON team_observations BEGIN
    INSERT INTO team_observations_fts(team_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
    INSERT INTO team_observations_fts(rowid, body, evidence)
    VALUES (new.id, new.body, new.evidence);
END;

CREATE TRIGGER IF NOT EXISTS team_observations_ad AFTER DELETE ON team_observations BEGIN
    INSERT INTO team_observations_fts(team_observations_fts, rowid, body, evidence)
    VALUES ('delete', old.id, old.body, old.evidence);
END;

CREATE TRIGGER IF NOT EXISTS team_observations_touch AFTER UPDATE ON team_observations
WHEN OLD.updated_at = NEW.updated_at
BEGIN
    UPDATE team_observations SET updated_at = datetime('now') WHERE id = NEW.id;
END;


-- +migrate Down

-- ============================================================
-- DOWN — drop all seven tables in reverse dependency order.
-- ============================================================

DROP TRIGGER IF EXISTS team_observations_touch;
DROP TRIGGER IF EXISTS team_observations_ad;
DROP TRIGGER IF EXISTS team_observations_au;
DROP TRIGGER IF EXISTS team_observations_ai;
DROP TABLE IF EXISTS team_observations_fts;
DROP INDEX IF EXISTS team_observations_captured_at_idx;
DROP INDEX IF EXISTS team_observations_type_status_idx;
DROP INDEX IF EXISTS team_observations_subject_status_idx;
DROP INDEX IF EXISTS team_observations_observer_status_idx;
DROP INDEX IF EXISTS team_observations_status_idx;
DROP TABLE IF EXISTS team_observations;

DROP TRIGGER IF EXISTS orchestrator_observations_touch;
DROP TRIGGER IF EXISTS orchestrator_observations_ad;
DROP TRIGGER IF EXISTS orchestrator_observations_au;
DROP TRIGGER IF EXISTS orchestrator_observations_ai;
DROP TABLE IF EXISTS orchestrator_observations_fts;
DROP INDEX IF EXISTS orchestrator_observations_subject_status_idx;
DROP INDEX IF EXISTS orchestrator_observations_captured_at_idx;
DROP INDEX IF EXISTS orchestrator_observations_type_status_idx;
DROP INDEX IF EXISTS orchestrator_observations_status_idx;
DROP TABLE IF EXISTS orchestrator_observations;

DROP TRIGGER IF EXISTS owner_observations_touch;
DROP TRIGGER IF EXISTS owner_observations_ad;
DROP TRIGGER IF EXISTS owner_observations_au;
DROP TRIGGER IF EXISTS owner_observations_ai;
DROP TABLE IF EXISTS owner_observations_fts;
DROP INDEX IF EXISTS owner_observations_captured_at_idx;
DROP INDEX IF EXISTS owner_observations_type_status_idx;
DROP INDEX IF EXISTS owner_observations_subject_status_idx;
DROP INDEX IF EXISTS owner_observations_status_idx;
DROP TABLE IF EXISTS owner_observations;

DROP TRIGGER IF EXISTS owner_posture_touch;
DROP TRIGGER IF EXISTS owner_posture_ad;
DROP TRIGGER IF EXISTS owner_posture_au;
DROP TRIGGER IF EXISTS owner_posture_ai;
DROP TABLE IF EXISTS owner_posture_fts;
DROP INDEX IF EXISTS owner_posture_captured_at_idx;
DROP INDEX IF EXISTS owner_posture_type_status_idx;
DROP INDEX IF EXISTS owner_posture_status_idx;
DROP TABLE IF EXISTS owner_posture;

DROP TRIGGER IF EXISTS owner_notes_ad;
DROP TRIGGER IF EXISTS owner_notes_au;
DROP TRIGGER IF EXISTS owner_notes_ai;
DROP TABLE IF EXISTS owner_notes_fts;
DROP TABLE IF EXISTS owner_notes;

DROP TRIGGER IF EXISTS owner_tasks_ad;
DROP TRIGGER IF EXISTS owner_tasks_au;
DROP TRIGGER IF EXISTS owner_tasks_ai;
DROP TABLE IF EXISTS owner_tasks_fts;
DROP TABLE IF EXISTS owner_tasks;

DROP TRIGGER IF EXISTS owner_journal_ad;
DROP TRIGGER IF EXISTS owner_journal_au;
DROP TRIGGER IF EXISTS owner_journal_ai;
DROP TABLE IF EXISTS owner_journal_fts;
DROP TABLE IF EXISTS owner_journal;
