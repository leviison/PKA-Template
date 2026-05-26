#!/usr/bin/env python3
"""
PKA Setup Script — v1.2.0 (three-tier architecture)

Creates the three PKA databases:
  - pka.db       (Operations tier — briefs, deliverables, patterns, memory, etc.)
  - projects.db  (Projects tier  — assets, content, projects, project-memory)
  - personal.db  (Owner tier     — journal, tasks, notes, four observation tables)

Run once when starting a new PKA project.

Usage:
  python3 setup.py
  python3 setup.py --personal-data-dir ~/MyName-Data    # override personal.db location

This script creates the databases and seeds defaults. It deliberately does NOT
collect your name or preferences here — that happens when you first open a
Claude Code session in this folder and meet Leroy. Leroy's First-Run Protocol
(see CLAUDE.md, Session Open Protocol section) handles personalization
conversationally, storing your answers in the settings table.

Re-running on an existing installation will prompt before overwriting any
database file.

Personal database location:
  By default the personal.db file lives at  ~/PKA-Data/personal.db  — outside
  this repo, so it is never committed to git. Override with --personal-data-dir
  (e.g. for owners who prefer ~/Documents/MyName-Data/personal.db).
  setup.py records the chosen path in `pka.db.settings.personal_db_path` for
  reference by helpers.
"""

import argparse
import sqlite3
import os
import datetime

PKA_ROOT = os.path.dirname(os.path.abspath(__file__))
PKA_DB_PATH = os.path.join(PKA_ROOT, 'pka.db')
PROJECTS_DB_PATH = os.path.join(PKA_ROOT, 'projects.db')

DEFAULT_PERSONAL_DATA_DIR = os.path.expanduser('~/PKA-Data')


def confirm_overwrite(path):
    """Prompt the operator before overwriting an existing DB file."""
    if not os.path.exists(path):
        return True
    print(f"\n{path} already exists.")
    confirm = input("Overwrite? This will delete all existing data. (yes/no): ")
    if confirm.strip().lower() != 'yes':
        print(f"  Skipped: {path}")
        return False
    os.remove(path)
    return True


def create_pka_db():
    """Create pka.db (Operations tier)."""
    if not confirm_overwrite(PKA_DB_PATH):
        return False

    db = sqlite3.connect(PKA_DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    print("\nCreating pka.db (Operations tier)...")

    db.executescript("""
    -- ── OPERATIONAL TABLES ────────────────────────────────────────────────────
    --
    -- assets and content live in projects.db (Projects tier), NOT here. The
    -- three-tier split established by migration 003 moved them out of pka.db.

    -- Briefs: task briefs written by Leroy, picked up by team members
    CREATE TABLE IF NOT EXISTS briefs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_ref       TEXT UNIQUE,
        assigned_to     TEXT NOT NULL,
        created_by      TEXT NOT NULL DEFAULT 'Leroy',
        title           TEXT NOT NULL,
        body            TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'open'
                            CHECK(status IN ('open','active','complete')),
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at    TEXT,
        source_material TEXT,                       -- v1.2.0: file path, URL, video title + date
        project_slug    TEXT                        -- v1.2.0: cross-tier project context pointer
    );

    CREATE INDEX IF NOT EXISTS briefs_project_idx ON briefs (project_slug);

    -- Deliverables: completed work records
    CREATE TABLE IF NOT EXISTS deliverables (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_id        INTEGER REFERENCES briefs(id),
        file_path       TEXT,
        created_by      TEXT NOT NULL,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        notes           TEXT,
        tokens_used     INTEGER,
        tool_uses       INTEGER,
        duration_ms     INTEGER,
        source_material TEXT                        -- v1.2.0: default-copies from briefs
    );

    -- Feedback: ratings on deliverables
    CREATE TABLE IF NOT EXISTS feedback (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_ref            TEXT NOT NULL,
        deliverable_id       INTEGER REFERENCES deliverables(id),
        team_member          TEXT NOT NULL,
        rating               INTEGER CHECK(rating BETWEEN 1 AND 5),
        notes                TEXT,
        model                TEXT NOT NULL DEFAULT 'ritual',
        created_at           TEXT NOT NULL DEFAULT (datetime('now')),
        ai_model_provider_id INTEGER REFERENCES model_providers(id),
        rater                TEXT NOT NULL DEFAULT 'levi'
                                CHECK (rater IN ('levi','leroy'))
    );

    -- Journal: operational/session journal entries (NOT the personal journal —
    -- that lives in personal.db.owner_journal)
    CREATE TABLE IF NOT EXISTS journal (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        date       TEXT NOT NULL DEFAULT (date('now')),
        title      TEXT,
        body       TEXT NOT NULL,
        tags       TEXT,
        mood       TEXT,
        project    TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Knowledge: knowledge base items
    CREATE TABLE IF NOT EXISTS knowledge (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        body       TEXT NOT NULL,
        source     TEXT,
        tags       TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Settings: system configuration
    CREATE TABLE IF NOT EXISTS settings (
        key        TEXT PRIMARY KEY,
        value      TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Team members: active team roster (used by workflow diagram)
    CREATE TABLE IF NOT EXISTS team_members (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        name              TEXT NOT NULL,
        role              TEXT NOT NULL,
        short_role        TEXT,
        profile_file      TEXT,
        hired_date        TEXT,
        active            INTEGER NOT NULL DEFAULT 1,
        model_provider_id INTEGER REFERENCES model_providers(id)
    );

    -- Backlog: deferred ideas, architectural tasks, tracked future work
    CREATE TABLE IF NOT EXISTS backlog (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ref        TEXT UNIQUE,
        title      TEXT NOT NULL,
        body       TEXT,
        priority   INTEGER NOT NULL DEFAULT 2
                       CHECK(priority IN (1, 2, 3)),
        status     TEXT NOT NULL DEFAULT 'idea'
                       CHECK(status IN ('idea','active','complete','deferred')),
        tags       TEXT,
        source     TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Case studies: HBS-style teaching artifacts from the Learning Layer
    CREATE TABLE IF NOT EXISTS case_studies (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        case_ref           TEXT UNIQUE,
        deliverable_id     INTEGER REFERENCES deliverables(id) ON DELETE RESTRICT,
        team_member        TEXT,
        aar_what_supposed  TEXT,
        aar_what_actually  TEXT,
        aar_difference     TEXT,
        aar_generalises    TEXT,
        aar_date           TEXT,
        case_body          TEXT,
        teaching_point     TEXT,
        principles_tags    TEXT,
        author             TEXT,
        status             TEXT NOT NULL DEFAULT 'aar_pending'
                               CHECK(status IN ('aar_pending','aar_captured','draft','published','deferred')),
        published_date     TEXT,
        created_at         TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Patterns: validated operational templates (Intent layer)
    CREATE TABLE IF NOT EXISTS patterns (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_ref         TEXT UNIQUE,
        slug                TEXT UNIQUE,
        title               TEXT NOT NULL,
        body                TEXT,
        status              TEXT NOT NULL DEFAULT 'proposed'
                                CHECK(status IN ('proposed','validated','deprecated')),
        proposed_by         TEXT NOT NULL DEFAULT 'Leroy',
        approved_by         TEXT,
        deprecated_reason   TEXT,
        superseded_by       TEXT,
        validated_instances TEXT,
        proposed_at         TEXT NOT NULL DEFAULT (datetime('now')),
        approved_at         TEXT,
        deprecated_at       TEXT,
        created_at          TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Model providers: AI provider/model registry for multi-model routing
    CREATE TABLE IF NOT EXISTS model_providers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        provider     TEXT NOT NULL,
        model_id     TEXT NOT NULL,
        endpoint     TEXT,
        api_key_env  TEXT,
        fallback_id  INTEGER REFERENCES model_providers(id) DEFERRABLE INITIALLY DEFERRED,
        active       INTEGER NOT NULL DEFAULT 1,
        notes        TEXT,
        created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Task type models: task-type → provider routing table
    CREATE TABLE IF NOT EXISTS task_type_models (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type         TEXT NOT NULL,
        model_provider_id INTEGER NOT NULL REFERENCES model_providers(id),
        description       TEXT,
        active            INTEGER NOT NULL DEFAULT 1,
        created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Token economics (migration 002 — embedded for first-install simplicity)
    CREATE TABLE IF NOT EXISTS model_pricing (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        provider                    TEXT NOT NULL,
        model                       TEXT NOT NULL,
        input_price_per_1m          REAL NOT NULL,
        output_price_per_1m         REAL NOT NULL,
        cache_write_price_per_1m    REAL NOT NULL,
        cache_read_price_per_1m     REAL NOT NULL,
        currency                    TEXT NOT NULL DEFAULT 'USD',
        effective_from              TEXT NOT NULL,
        last_verified_at            TEXT NOT NULL,
        source_url                  TEXT,
        notes                       TEXT,
        created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (provider, model, effective_from)
    );

    CREATE INDEX IF NOT EXISTS model_pricing_lookup_idx
        ON model_pricing (provider, model, effective_from DESC);

    CREATE TABLE IF NOT EXISTS economics (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        deliverable_id          INTEGER NOT NULL UNIQUE
                                    REFERENCES deliverables(id) ON DELETE CASCADE,
        provider                TEXT NOT NULL DEFAULT 'anthropic',
        model                   TEXT NOT NULL,
        input_tokens            INTEGER NOT NULL DEFAULT 0,
        output_tokens           INTEGER NOT NULL DEFAULT 0,
        cache_creation_tokens   INTEGER NOT NULL DEFAULT 0,
        cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
        estimated_cost_usd      REAL NOT NULL,
        model_pricing_id        INTEGER NOT NULL
                                    REFERENCES model_pricing(id) ON DELETE RESTRICT,
        cache_hit_rate          REAL,
        created_at              TEXT NOT NULL DEFAULT (datetime('now')),
        CHECK (input_tokens >= 0),
        CHECK (output_tokens >= 0),
        CHECK (cache_creation_tokens >= 0),
        CHECK (cache_read_tokens >= 0),
        CHECK (estimated_cost_usd >= 0)
    );

    CREATE INDEX IF NOT EXISTS economics_deliverable_idx
        ON economics (deliverable_id);
    CREATE INDEX IF NOT EXISTS economics_model_idx
        ON economics (model);
    CREATE INDEX IF NOT EXISTS economics_created_at_idx
        ON economics (created_at DESC);

    -- ── FTS5 VIRTUAL TABLES ───────────────────────────────────────────────────

    CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts
        USING fts5(title, body, content='journal', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
        USING fts5(title, body, content='knowledge', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS briefs_fts
        USING fts5(title, body, content='briefs', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS backlog_fts
        USING fts5(title, body, content='backlog', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS case_studies_fts
        USING fts5(case_body, teaching_point,
                   aar_what_supposed, aar_what_actually, aar_difference, aar_generalises,
                   content='case_studies', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts
        USING fts5(title, body, content='patterns', content_rowid='id');

    -- ── FTS SYNC TRIGGERS ─────────────────────────────────────────────────────

    CREATE TRIGGER IF NOT EXISTS journal_ai AFTER INSERT ON journal BEGIN
        INSERT INTO journal_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS journal_au AFTER UPDATE ON journal BEGIN
        INSERT INTO journal_fts(journal_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
        INSERT INTO journal_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS journal_ad AFTER DELETE ON journal BEGIN
        INSERT INTO journal_fts(journal_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    END;

    CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
        INSERT INTO knowledge_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
        INSERT INTO knowledge_fts(knowledge_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
        INSERT INTO knowledge_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
        INSERT INTO knowledge_fts(knowledge_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    END;

    CREATE TRIGGER IF NOT EXISTS briefs_ai AFTER INSERT ON briefs BEGIN
        INSERT INTO briefs_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS briefs_au AFTER UPDATE ON briefs BEGIN
        INSERT INTO briefs_fts(briefs_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
        INSERT INTO briefs_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS briefs_ad AFTER DELETE ON briefs BEGIN
        INSERT INTO briefs_fts(briefs_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    END;

    CREATE TRIGGER IF NOT EXISTS backlog_ai AFTER INSERT ON backlog BEGIN
        INSERT INTO backlog_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS backlog_au AFTER UPDATE ON backlog BEGIN
        INSERT INTO backlog_fts(backlog_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
        INSERT INTO backlog_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS backlog_ad AFTER DELETE ON backlog BEGIN
        INSERT INTO backlog_fts(backlog_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    END;

    CREATE TRIGGER IF NOT EXISTS backlog_updated_at AFTER UPDATE ON backlog
    WHEN new.updated_at = old.updated_at BEGIN
        UPDATE backlog SET updated_at = datetime('now') WHERE id = new.id;
    END;

    CREATE TRIGGER IF NOT EXISTS case_studies_ai AFTER INSERT ON case_studies BEGIN
        INSERT INTO case_studies_fts(rowid, case_body, teaching_point,
                                     aar_what_supposed, aar_what_actually, aar_difference, aar_generalises)
        VALUES (new.id, new.case_body, new.teaching_point,
                new.aar_what_supposed, new.aar_what_actually, new.aar_difference, new.aar_generalises);
    END;
    CREATE TRIGGER IF NOT EXISTS case_studies_au AFTER UPDATE ON case_studies BEGIN
        INSERT INTO case_studies_fts(case_studies_fts, rowid, case_body, teaching_point,
                                     aar_what_supposed, aar_what_actually, aar_difference, aar_generalises)
        VALUES ('delete', old.id, old.case_body, old.teaching_point,
                old.aar_what_supposed, old.aar_what_actually, old.aar_difference, old.aar_generalises);
        INSERT INTO case_studies_fts(rowid, case_body, teaching_point,
                                     aar_what_supposed, aar_what_actually, aar_difference, aar_generalises)
        VALUES (new.id, new.case_body, new.teaching_point,
                new.aar_what_supposed, new.aar_what_actually, new.aar_difference, new.aar_generalises);
    END;
    CREATE TRIGGER IF NOT EXISTS case_studies_ad AFTER DELETE ON case_studies BEGIN
        INSERT INTO case_studies_fts(case_studies_fts, rowid, case_body, teaching_point,
                                     aar_what_supposed, aar_what_actually, aar_difference, aar_generalises)
        VALUES ('delete', old.id, old.case_body, old.teaching_point,
                old.aar_what_supposed, old.aar_what_actually, old.aar_difference, old.aar_generalises);
    END;
    CREATE TRIGGER IF NOT EXISTS case_studies_updated_at AFTER UPDATE ON case_studies
    WHEN new.updated_at = old.updated_at BEGIN
        UPDATE case_studies SET updated_at = datetime('now') WHERE id = new.id;
    END;

    CREATE TRIGGER IF NOT EXISTS patterns_ai AFTER INSERT ON patterns BEGIN
        INSERT INTO patterns_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS patterns_au AFTER UPDATE ON patterns BEGIN
        INSERT INTO patterns_fts(patterns_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
        INSERT INTO patterns_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS patterns_ad AFTER DELETE ON patterns BEGIN
        INSERT INTO patterns_fts(patterns_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
    END;
    CREATE TRIGGER IF NOT EXISTS patterns_updated_at AFTER UPDATE ON patterns
    WHEN new.updated_at = old.updated_at BEGIN
        UPDATE patterns SET updated_at = datetime('now') WHERE id = new.id;
    END;

    -- ── MEMORY LAYER (migration 001 — embedded for first-install simplicity) ──

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

        CHECK (
            (status = 'superseded' AND superseded_by IS NOT NULL)
            OR (status != 'superseded' AND superseded_by IS NULL)
        ),
        CHECK (valid_to IS NULL OR valid_to >= valid_from)
    );

    CREATE INDEX IF NOT EXISTS memory_scope_status_idx
        ON memory (scope, status);
    CREATE INDEX IF NOT EXISTS memory_status_type_idx
        ON memory (status, type);
    CREATE INDEX IF NOT EXISTS memory_ingested_at_idx
        ON memory (ingested_at DESC);

    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        title,
        body,
        content='memory',
        content_rowid='id'
    );

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

    -- ── MEMORY EPISODIC VIEW (migration 004 — embedded) ───────────────────────
    -- Read-only view that projects briefs/deliverables/feedback/journal rows
    -- into the memory-row shape, so consumers can UNION ALL with `memory`.
    -- The `projected` provenance value is reserved for view rows and is NOT
    -- accepted by the memory table's CHECK constraint — view rows are
    -- read-only and not meant to be materialized into `memory`.

    CREATE VIEW IF NOT EXISTS memory_episodic_view AS
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

    -- ── MIGRATION FRAMEWORK ───────────────────────────────────────────────────
    -- The pka.db migration history table. Each tier carries its own
    -- schema_migrations. We seed the v1.2.0-baseline migrations as
    -- already-applied below, so `python3 migrations/migrate.py status`
    -- reports them as `applied` (not `pending`) on a fresh install.

    CREATE TABLE IF NOT EXISTS schema_migrations (
        name        TEXT PRIMARY KEY,
        applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    # ── SEED: model_providers (Anthropic-only at install time) ──
    db.execute("""
        INSERT INTO model_providers (id, name, provider, model_id, endpoint, api_key_env, fallback_id, active, notes)
        VALUES (1, 'Claude Sonnet 4.6', 'anthropic', 'claude-sonnet-4-6', NULL, NULL, NULL, 1,
                'Default tier — implementation work, code review, research synthesis')
    """)
    db.execute("""
        INSERT INTO model_providers (id, name, provider, model_id, endpoint, api_key_env, fallback_id, active, notes)
        VALUES (2, 'Claude Opus 4.7', 'anthropic', 'claude-opus-4-7', NULL, NULL, 1, 1,
                'High tier — synthesis under ambiguity, architecture decisions, pedagogical writing')
    """)
    db.execute("""
        INSERT INTO model_providers (id, name, provider, model_id, endpoint, api_key_env, fallback_id, active, notes)
        VALUES (3, 'Claude Haiku 4.5', 'anthropic', 'claude-haiku-4-5', NULL, NULL, 1, 1,
                'Low tier — mechanical ops: DB inserts, archive moves, status queries')
    """)

    # ── SEED: model_pricing (Anthropic, last verified 2026-05-19) ──
    db.executemany(
        """INSERT INTO model_pricing (
               provider, model,
               input_price_per_1m, output_price_per_1m,
               cache_write_price_per_1m, cache_read_price_per_1m,
               effective_from, last_verified_at, source_url, notes
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ('anthropic', 'claude-opus-4-7',
             15.00, 75.00, 18.75, 1.50,
             '2026-05-19', '2026-05-19',
             'https://www.anthropic.com/pricing',
             'Opus 4.7. Cache write = 1.25x input, cache read = 0.10x input.'),
            ('anthropic', 'claude-sonnet-4-6',
             3.00, 15.00, 3.75, 0.30,
             '2026-05-19', '2026-05-19',
             'https://www.anthropic.com/pricing',
             'Sonnet 4.6. Cache write = 1.25x input, cache read = 0.10x input.'),
            ('anthropic', 'claude-haiku-4-5-20251001',
             0.80, 4.00, 1.00, 0.08,
             '2026-05-19', '2026-05-19',
             'https://www.anthropic.com/pricing',
             'Haiku 4.5. Cache write = 1.25x input, cache read = 0.10x input.'),
        ]
    )

    # ── SEED: settings ────────────────────────────────────────────────────────
    settings_seed = [
        # Feedback model — v1.2.0 default is leroy_rates_levi_audits (orchestrator
        # auto-rates routine deliveries; owner audits a sample at audit_cadence_days).
        # Owners who prefer the simpler ritual model can change with:
        #   UPDATE settings SET value='ritual' WHERE key='feedback_model';
        ('feedback_model',           'leroy_rates_levi_audits'),
        ('audit_cadence_days',       '7'),
        ('multi_model_enabled',      'false'),
        ('model_routing',            'member'),
        ('default_model_provider_id', '1'),
        # Epoch sentinels for the Session Open Protocol surfacing queries.
        ('last_session_close_at',    '1970-01-01T00:00:00'),
        ('last_reflection_pass_at',  '1970-01-01T00:00:00'),
        # Install Experience Seeds. Empty = First-Run Protocol collects them.
        ('user_name',                ''),
        ('user_use_case',            ''),
        ('personal_db_separation',   ''),
    ]
    db.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        settings_seed
    )

    # ── SEED: schema_migrations (mark v1.2.0 baseline as already-applied) ──
    # The migrations whose DDL is embedded above are marked as already-applied
    # so future `python3 migrations/migrate.py up` does not try to re-apply
    # them on a fresh install.
    pka_baseline_migrations = [
        '001_memory_table',
        '002_token_economics',
        '003_split_projects_db',
        '004_memory_episodic_view',
        '006_briefs_project_slug',
        '007_feedback_rater',
    ]
    db.executemany(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
        [(m,) for m in pka_baseline_migrations]
    )

    # ── SEED: founding team members ───────────────────────────────────────────
    now = datetime.datetime.now().isoformat()
    db.executemany(
        """INSERT INTO team_members
           (name, role, short_role, profile_file, hired_date, active, model_provider_id)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        [
            ('Sam', 'HR Director',      'HR Director',       'team/SAM.md', now[:10], 1),
            ('PAX', 'Senior Researcher', 'Senior Researcher', 'team/PAX.md', now[:10], 1),
        ]
    )

    # ── SEED: validated patterns (Intent layer) ───────────────────────────────
    # The 6 validated patterns shipped with the template. Bodies are stored
    # in the matching `patterns/*.md` files (the Intent-layer artifact);
    # `pka.db.patterns` carries the state record (status, approval, validated
    # instances). On install, body is left NULL — the markdown file IS the body.
    # Forked instances may UPDATE patterns SET body=... if they want full-text
    # search against the validated-pattern text via patterns_fts.
    pattern_seeds = [
        # (pattern_ref, slug, title, status, proposed_by, approved_by, validated_instances, proposed_at, approved_at)
        ('PATTERN-001', 'sequential-overnight-build',
         'Sequential Overnight Build',
         'validated', 'Leroy', 'owner',
         '["BRIEF-078", "BRIEF-079"]',
         '2026-05-14T00:00:00', '2026-05-15T00:00:00'),
        ('PATTERN-002', 'single-consumer-event-stream',
         'Single-Consumer Event-Stream Architecture',
         'validated', 'Sam', 'owner',
         '["BRIEF-079"]',
         '2026-05-15T17:41:59', '2026-05-15T17:48:29'),
        ('PATTERN-003', 'persona-gap-triggered-hire',
         'Persona-Gap-Triggered Hire',
         'validated', 'Leroy', 'owner',
         'BRIEF-104 (2026-05-16)',
         '2026-05-16T18:50:15', '2026-05-18T17:28:10'),
        ('PATTERN-004', 'multi-lens-parallel-critique',
         'Multi-Lens Parallel Critique',
         'validated', 'Leroy', 'owner',
         'Three-lens review of novel-persona first deliverable, 2026-05-16',
         '2026-05-16T18:50:15', '2026-05-18T17:28:10'),
        ('PATTERN-005', 'audit-then-execute-structural',
         'Audit-Then-Execute on Structural Surfaces',
         'validated', 'Leroy', 'owner',
         'BRIEF-115, BRIEF-116, BRIEF-117 (2026-05-16; case CASE-006)',
         '2026-05-17T04:06:25', '2026-05-17T04:14:47'),
        ('PATTERN-006', 'empirical-probe-before-design',
         'Empirical Probe Before Design',
         'validated', 'Leroy', 'owner (pre-approved 2026-05-16, judgment delegated to Leroy)',
         'BRIEF-078 (2026-05-14; case study CASE-003)',
         '2026-05-17T04:15:57', '2026-05-17T04:15:57'),
        ('PATTERN-007', 'domain-engagement-template',
         'Domain-Engagement Template',
         'proposed', 'Leroy', None,
         '[]',
         '2026-05-25T00:00:00', None),
        ('PATTERN-011', 'probe-validity-discipline',
         'Probe-Validity Discipline',
         'proposed', 'Leroy', None,
         '[]',
         '2026-05-25T00:00:00', None),
        ('PATTERN-013', 'scope-validity-discipline',
         'Scope-Validity Discipline',
         'proposed', 'Leroy', None,
         '[]',
         '2026-05-25T00:00:00', None),
    ]
    db.executemany(
        """INSERT OR IGNORE INTO patterns
           (pattern_ref, slug, title, status, proposed_by, approved_by,
            validated_instances, proposed_at, approved_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        pattern_seeds
    )

    db.commit()
    db.close()
    print(f"  pka.db tables: {_list_tables(PKA_DB_PATH)}")
    return True


def create_projects_db():
    """Create projects.db (Projects tier)."""
    if not confirm_overwrite(PROJECTS_DB_PATH):
        return False

    db = sqlite3.connect(PROJECTS_DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    print("\nCreating projects.db (Projects tier)...")

    db.executescript("""
    -- ── Migration 003 (split) — projects-tier assets + content ────────────────

    CREATE TABLE IF NOT EXISTS assets (
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

    CREATE TABLE IF NOT EXISTS content (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id       INTEGER REFERENCES assets(id) ON DELETE CASCADE,
        content_type   TEXT,
        body           TEXT,
        extracted_at   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
        body, content='content', content_rowid='id'
    );

    CREATE TRIGGER IF NOT EXISTS content_ai AFTER INSERT ON content BEGIN
        INSERT INTO content_fts(rowid, body) VALUES (new.id, new.body);
    END;

    CREATE TRIGGER IF NOT EXISTS content_ad AFTER DELETE ON content BEGIN
        INSERT INTO content_fts(content_fts, rowid, body)
        VALUES ('delete', old.id, old.body);
    END;

    -- ── Projects-tier migration 001 — projects registry + memory substrate ────

    CREATE TABLE IF NOT EXISTS projects (
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

    CREATE INDEX IF NOT EXISTS projects_status_idx ON projects (status);

    CREATE TRIGGER IF NOT EXISTS projects_touch AFTER UPDATE ON projects
    WHEN OLD.updated_at = NEW.updated_at
    BEGIN
        UPDATE projects SET updated_at = datetime('now') WHERE slug = NEW.slug;
    END;

    CREATE TABLE IF NOT EXISTS memory (
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

    CREATE INDEX IF NOT EXISTS memory_project_idx       ON memory (project_slug, status);
    CREATE INDEX IF NOT EXISTS memory_project_type_idx  ON memory (project_slug, type, status);
    CREATE INDEX IF NOT EXISTS memory_scope_idx         ON memory (scope, status);
    CREATE INDEX IF NOT EXISTS memory_type_status_idx   ON memory (type, status);
    CREATE INDEX IF NOT EXISTS memory_ingested_at_idx   ON memory (ingested_at DESC);

    CREATE TRIGGER IF NOT EXISTS memory_touch AFTER UPDATE ON memory
    WHEN OLD.updated_at = NEW.updated_at
    BEGIN
        UPDATE memory SET updated_at = datetime('now') WHERE id = NEW.id;
    END;

    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
        title, body, content='memory', content_rowid='id'
    );

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

    -- ── Migration framework (projects tier) ──────────────────────────────────

    CREATE TABLE IF NOT EXISTS schema_migrations (
        name        TEXT PRIMARY KEY,
        applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    # Seed the projects.db migration history. '003_split_projects_db' is the
    # historical bootstrap convention from BRIEF-132; '001_projects_memory_substrate'
    # is the projects-tier-native first migration.
    db.executemany(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
        [
            ('003_split_projects_db',),
            ('001_projects_memory_substrate',),
        ]
    )

    db.commit()
    db.close()
    print(f"  projects.db tables: {_list_tables(PROJECTS_DB_PATH)}")
    return True


def create_personal_db(personal_data_dir):
    """Create personal.db (Owner tier) at the configured location."""
    os.makedirs(personal_data_dir, exist_ok=True)
    personal_db_path = os.path.join(personal_data_dir, 'personal.db')

    if not confirm_overwrite(personal_db_path):
        return personal_db_path, False

    db = sqlite3.connect(personal_db_path)
    db.execute("PRAGMA foreign_keys = ON")
    print(f"\nCreating personal.db (Owner tier) at {personal_db_path}...")

    # Read the consolidated personal-tier migration and execute its UP block.
    personal_migration = os.path.join(
        PKA_ROOT, 'migrations', 'personal', '001_owner_observability.sql'
    )
    with open(personal_migration, 'r') as f:
        sql = f.read()
    # Split off the DOWN block at the marker.
    up_sql = sql.split('-- +migrate Down')[0]
    db.executescript(up_sql)

    # Seed the personal.db migration history.
    db.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name        TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    db.execute(
        "INSERT OR IGNORE INTO schema_migrations (name) VALUES (?)",
        ('001_owner_observability',)
    )

    db.commit()
    db.close()
    print(f"  personal.db tables: {_list_tables(personal_db_path)}")
    return personal_db_path, True


def record_personal_db_path(personal_db_path):
    """Save the personal.db path into pka.db.settings for reference."""
    db = sqlite3.connect(PKA_DB_PATH)
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ('personal_db_path', personal_db_path)
    )
    db.commit()
    db.close()


def _list_tables(db_path):
    db = sqlite3.connect(db_path)
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    db.close()
    return ', '.join(tables)


def main():
    parser = argparse.ArgumentParser(description='PKA three-tier setup')
    parser.add_argument(
        '--personal-data-dir',
        default=DEFAULT_PERSONAL_DATA_DIR,
        help=(
            f'Directory for personal.db (default: {DEFAULT_PERSONAL_DATA_DIR}). '
            'Lives outside the PKA repo; never committed to git.'
        )
    )
    args = parser.parse_args()
    personal_data_dir = os.path.expanduser(args.personal_data_dir)

    print(f"PKA setup — v1.2.0 three-tier architecture")
    print(f"  PKA root:        {PKA_ROOT}")
    print(f"  pka.db:          {PKA_DB_PATH}")
    print(f"  projects.db:     {PROJECTS_DB_PATH}")
    print(f"  personal.db dir: {personal_data_dir}")

    pka_created = create_pka_db()
    projects_created = create_projects_db()
    personal_db_path, personal_created = create_personal_db(personal_data_dir)

    # Record personal.db location in pka.db.settings (so helpers find it).
    if pka_created or os.path.exists(PKA_DB_PATH):
        record_personal_db_path(personal_db_path)

    print("\n" + "=" * 60)
    print("Setup complete.")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Open owners_inbox/pka-viewer/index.html in Chrome")
    print("  2. Open owners_inbox/pka-workflow/index.html in Chrome")
    print("  3. Start a Claude Code session in this folder and introduce yourself to Leroy")
    print("     (Leroy's First-Run Protocol will collect your name and preferences)")


if __name__ == '__main__':
    main()
