#!/usr/bin/env python3
"""
PKA Setup Script
Creates pka.db with the full schema — run once when starting a new PKA project.
Usage: python3 setup.py
"""

import sqlite3
import os
import datetime

PKA_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PKA_ROOT, 'pka.db')

def create_database():
    if os.path.exists(DB_PATH):
        print(f"pka.db already exists at {DB_PATH}")
        confirm = input("Overwrite? This will delete all existing data. (yes/no): ")
        if confirm.strip().lower() != 'yes':
            print("Aborted.")
            return
        os.remove(DB_PATH)

    db = sqlite3.connect(DB_PATH)
    print("Creating schema...")

    db.executescript("""
    -- Assets: files dropped into team_inbox
    CREATE TABLE IF NOT EXISTS assets (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        filename    TEXT NOT NULL,
        path        TEXT NOT NULL,
        type        TEXT,
        size_bytes  INTEGER,
        date_added  TEXT NOT NULL DEFAULT (datetime('now')),
        status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','processed','archived')),
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
        status       TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','active','complete')),
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
        notes        TEXT
    );

    -- Feedback: ratings on deliverables
    CREATE TABLE IF NOT EXISTS feedback (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        brief_ref       TEXT NOT NULL,
        deliverable_id  INTEGER REFERENCES deliverables(id),
        team_member     TEXT NOT NULL,
        rating          INTEGER CHECK(rating BETWEEN 1 AND 5),
        notes           TEXT,
        model           TEXT NOT NULL DEFAULT 'ritual',
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
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
        key         TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Team members: active team roster (used by workflow diagram)
    CREATE TABLE IF NOT EXISTS team_members (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL,
        role         TEXT NOT NULL,
        short_role   TEXT,
        profile_file TEXT,
        hired_date   TEXT,
        active       INTEGER NOT NULL DEFAULT 1
    );

    -- FTS5 virtual tables for full-text search
    CREATE VIRTUAL TABLE IF NOT EXISTS content_fts
        USING fts5(body, content='content', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts
        USING fts5(title, body, content='journal', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
        USING fts5(title, body, content='knowledge', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS briefs_fts
        USING fts5(title, body, content='briefs', content_rowid='id');

    -- FTS sync triggers
    CREATE TRIGGER IF NOT EXISTS content_ai AFTER INSERT ON content BEGIN
        INSERT INTO content_fts(rowid, body) VALUES (new.id, new.body);
    END;
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
    CREATE TRIGGER IF NOT EXISTS content_ad AFTER DELETE ON content BEGIN
        INSERT INTO content_fts(content_fts, rowid, body) VALUES ('delete', old.id, old.body);
    END;
    """)

    # Seed default settings
    db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('feedback_model', 'ritual')")

    # Seed founding team members
    now = datetime.datetime.now().isoformat()
    db.executemany(
        "INSERT INTO team_members (name, role, short_role, profile_file, hired_date, active) VALUES (?,?,?,?,?,1)",
        [
            ('Sam',   'HR Director',                   'HR Director',       'team/SAM.md',   now[:10]),
            ('PAX',   'Senior Researcher',             'Senior Researcher', 'team/PAX.md',   now[:10]),
        ]
    )

    db.commit()
    db.close()

    # Verify
    db = sqlite3.connect(DB_PATH)
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    db.close()

    print(f"\n✓ pka.db created at {DB_PATH}")
    print(f"  Tables: {', '.join(tables)}")
    print("\nNext steps:")
    print("  1. Open owners_inbox/pka-viewer/index.html in Chrome")
    print("  2. Open owners_inbox/pka-workflow/index.html in Chrome")
    print("  3. Start a Claude Code session in this folder and talk to Leroy")

if __name__ == '__main__':
    create_database()
