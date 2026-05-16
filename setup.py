#!/usr/bin/env python3
"""
PKA Setup Script
Creates pka.db with the full schema — run once when starting a new PKA project.
Usage: python3 setup.py

This script creates the database and seeds defaults. It deliberately does NOT
collect your name or preferences here — that happens when you first open a
Claude Code session in this folder and meet Leroy. Leroy's First-Run Protocol
(see CLAUDE.md, Session Open Protocol section) handles personalization
conversationally, storing your answers in the settings table.

Re-running on an existing pka.db will prompt before overwriting.
"""

import sqlite3
import os
import datetime

PKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PKA_ROOT, 'pka.db')


def create_database():
    if os.path.exists(DB_PATH):
        print(f"\npka.db already exists at {DB_PATH}")
        confirm = input("Overwrite? This will delete all existing data. (yes/no): ")
        if confirm.strip().lower() != 'yes':
            print("Aborted.")
            return
        os.remove(DB_PATH)

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    print("\nCreating schema...")

    db.executescript("""
    -- ── CORE OPERATIONAL TABLES ───────────────────────────────────────────────

    -- Assets: files dropped into team_inbox
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

    -- Content: structured content extracted from assets
    CREATE TABLE IF NOT EXISTS content (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id       INTEGER REFERENCES assets(id) ON DELETE CASCADE,
        content_type   TEXT,
        body           TEXT,
        extracted_at   TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Briefs: task briefs written by Leroy, picked up by team members
    CREATE TABLE IF NOT EXISTS briefs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_ref    TEXT UNIQUE,
        assigned_to  TEXT NOT NULL,
        created_by   TEXT NOT NULL DEFAULT 'Leroy',
        title        TEXT NOT NULL,
        body         TEXT NOT NULL,
        status       TEXT NOT NULL DEFAULT 'open'
                         CHECK(status IN ('open','active','complete')),
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    );

    -- Deliverables: completed work records
    CREATE TABLE IF NOT EXISTS deliverables (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_id     INTEGER REFERENCES briefs(id),
        file_path    TEXT,
        created_by   TEXT NOT NULL,
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        notes        TEXT,
        tokens_used  INTEGER,
        tool_uses    INTEGER,
        duration_ms  INTEGER
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
        ai_model_provider_id INTEGER REFERENCES model_providers(id)
    );

    -- Journal: personal journal entries
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

    -- ── FTS5 VIRTUAL TABLES ───────────────────────────────────────────────────

    CREATE VIRTUAL TABLE IF NOT EXISTS content_fts
        USING fts5(body, content='content', content_rowid='id');
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

    -- content
    CREATE TRIGGER IF NOT EXISTS content_ai AFTER INSERT ON content BEGIN
        INSERT INTO content_fts(rowid, body) VALUES (new.id, new.body);
    END;
    CREATE TRIGGER IF NOT EXISTS content_ad AFTER DELETE ON content BEGIN
        INSERT INTO content_fts(content_fts, rowid, body) VALUES ('delete', old.id, old.body);
    END;

    -- journal
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

    -- knowledge
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

    -- briefs
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

    -- backlog
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

    -- backlog updated_at auto-refresh
    CREATE TRIGGER IF NOT EXISTS backlog_updated_at AFTER UPDATE ON backlog
    WHEN new.updated_at = old.updated_at BEGIN
        UPDATE backlog SET updated_at = datetime('now') WHERE id = new.id;
    END;

    -- case_studies
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

    -- patterns
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
    """)

    # ── SEED: model_providers (Anthropic-only; non-Anthropic rows added later) ──
    # Insert in deferred-FK order: Sonnet first (no fallback), then others
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

    # ── SEED: settings ────────────────────────────────────────────────────────
    settings_seed = [
        ('feedback_model',           'ritual'),
        ('multi_model_enabled',      'false'),
        ('model_routing',            'member'),
        ('default_model_provider_id', '1'),
        # Epoch sentinel — Session Open Protocol pattern-surfacing query uses this
        # as the cutoff; an epoch value ensures the first session sees all patterns.
        ('last_session_close_at',    '1970-01-01T00:00:00'),
        # ── Install Experience Seeds ──────────────────────────────────────────
        # Empty values signal "not yet configured" to Leroy's First-Run Protocol
        # (see CLAUDE.md Session Open Protocol). Leroy collects these
        # conversationally on the first session and writes the answers back here.
        # Do not pre-fill values at install time.
        ('user_name',                ''),
        ('user_use_case',            ''),
        ('personal_db_separation',   ''),
    ]
    db.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        settings_seed
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

    db.commit()
    db.close()

    # ── VERIFY ────────────────────────────────────────────────────────────────
    db = sqlite3.connect(DB_PATH)
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    db.close()

    print(f"\n✓ pka.db created at {DB_PATH}")
    print(f"  Tables: {', '.join(tables)}")
    print("\nNext steps:")
    print("  1. Open owners_inbox/pka-viewer/index.html in Chrome")
    print("  2. Open owners_inbox/pka-workflow/index.html in Chrome")
    print("  3. Start a Claude Code session in this folder and introduce yourself to Leroy")


if __name__ == '__main__':
    create_database()
