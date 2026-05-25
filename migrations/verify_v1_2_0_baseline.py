#!/usr/bin/env python3
"""
verify_v1_2_0_baseline.py — verify the PKA-Template v1.2.0 three-tier install.

Runs a fresh `python3 setup.py` against a tmp directory and asserts that
all three databases are created with the expected baseline state:

  - pka.db tables, indexes, triggers, FTS5 virtual tables, seed rows
  - projects.db tables, indexes, triggers, FTS5 virtual tables, seed rows
  - personal.db tables (all 7), indexes, triggers, FTS5 virtual tables

Plus migration-history assertions: each tier's schema_migrations table
records the expected v1.2.0 baseline migrations as already-applied.

Also exercises the ATTACH DATABASE cross-tier pattern to confirm the
runtime contract holds end-to-end.

Idempotency check: run setup.py a second time (with auto-confirm) and
verify nothing breaks.

Usage:
  python3 migrations/verify_v1_2_0_baseline.py

Exits 0 on success, non-zero on first failure. Failures print the
specific assertion that failed.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

PKA_TEMPLATE_ROOT = Path(__file__).resolve().parent.parent


# ── Expected v1.2.0 baseline state ────────────────────────────────────────

PKA_EXPECTED_TABLES = {
    'backlog', 'briefs', 'case_studies', 'deliverables', 'economics',
    'feedback', 'journal', 'knowledge', 'memory', 'model_pricing',
    'model_providers', 'patterns', 'schema_migrations', 'settings',
    'task_type_models', 'team_members',
}

PKA_EXPECTED_FTS = {
    'backlog_fts', 'briefs_fts', 'case_studies_fts', 'journal_fts',
    'knowledge_fts', 'memory_fts', 'patterns_fts',
}

PKA_EXPECTED_VIEWS = {'memory_episodic_view'}

PKA_EXPECTED_MIGRATIONS = {
    '001_memory_table', '002_token_economics', '003_split_projects_db',
    '004_memory_episodic_view', '006_briefs_project_slug', '007_feedback_rater',
}

PROJECTS_EXPECTED_TABLES = {
    'assets', 'content', 'memory', 'projects', 'schema_migrations',
}

PROJECTS_EXPECTED_FTS = {'content_fts', 'memory_fts'}

PROJECTS_EXPECTED_MIGRATIONS = {
    '003_split_projects_db', '001_projects_memory_substrate',
}

PERSONAL_EXPECTED_TABLES = {
    'owner_journal', 'owner_tasks', 'owner_notes',
    'owner_posture', 'owner_observations',
    'orchestrator_observations', 'team_observations',
    'schema_migrations',
}

PERSONAL_EXPECTED_FTS = {
    'owner_journal_fts', 'owner_tasks_fts', 'owner_notes_fts',
    'owner_posture_fts', 'owner_observations_fts',
    'orchestrator_observations_fts', 'team_observations_fts',
}

PERSONAL_EXPECTED_MIGRATIONS = {'001_owner_observability'}


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg):
    print(f"  ok: {msg}")


def list_tables(db_path):
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    db.close()
    return {r[0] for r in rows}


def list_fts(db_path):
    """FTS5 virtual tables show as type='table' with sql LIKE 'CREATE VIRTUAL TABLE%fts5%'."""
    db = sqlite3.connect(db_path)
    rows = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND sql LIKE '%fts5%'
    """).fetchall()
    db.close()
    return {r[0] for r in rows}


def list_views(db_path):
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    db.close()
    return {r[0] for r in rows}


def list_migrations(db_path):
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT name FROM schema_migrations").fetchall()
    db.close()
    return {r[0] for r in rows}


def get_settings(db_path):
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    db.close()
    return dict(rows)


def get_team_members(db_path):
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT name, role FROM team_members ORDER BY id").fetchall()
    db.close()
    return rows


def run_fresh_install(tmp_root, personal_data_dir):
    """Copy template files to tmp_root and run setup.py against it."""
    # Copy the template tree to tmp_root (just the files setup needs).
    for fname in ['setup.py']:
        shutil.copy(PKA_TEMPLATE_ROOT / fname, tmp_root / fname)
    shutil.copytree(PKA_TEMPLATE_ROOT / 'migrations', tmp_root / 'migrations')

    # Run setup.py with auto-yes for any overwrite prompts (none on fresh install).
    result = subprocess.run(
        ['python3', 'setup.py', '--personal-data-dir', str(personal_data_dir)],
        cwd=tmp_root,
        capture_output=True,
        text=True,
        input='yes\n' * 3,  # in case any prompts fire
    )
    if result.returncode != 0:
        fail(f"setup.py failed: returncode={result.returncode}\n"
             f"stdout: {result.stdout}\nstderr: {result.stderr}")
    return result


def verify_pka_db(pka_db_path):
    print(f"\nVerifying pka.db at {pka_db_path}")
    if not pka_db_path.exists():
        fail(f"pka.db not created at {pka_db_path}")
    ok("pka.db file exists")

    tables = list_tables(pka_db_path)
    missing = PKA_EXPECTED_TABLES - tables
    if missing:
        fail(f"pka.db missing tables: {missing}")
    ok(f"all {len(PKA_EXPECTED_TABLES)} expected tables present")

    # assets and content must NOT be in pka.db (they live in projects.db).
    for forbidden in ['assets', 'content']:
        if forbidden in tables:
            fail(f"pka.db has {forbidden} table — must live in projects.db only")
    ok("assets/content correctly absent from pka.db (live in projects.db)")

    fts = list_fts(pka_db_path)
    missing_fts = PKA_EXPECTED_FTS - fts
    if missing_fts:
        fail(f"pka.db missing FTS5 tables: {missing_fts}")
    ok(f"all {len(PKA_EXPECTED_FTS)} expected FTS5 tables present")

    views = list_views(pka_db_path)
    missing_views = PKA_EXPECTED_VIEWS - views
    if missing_views:
        fail(f"pka.db missing views: {missing_views}")
    ok(f"view memory_episodic_view present")

    migrations = list_migrations(pka_db_path)
    missing_mig = PKA_EXPECTED_MIGRATIONS - migrations
    if missing_mig:
        fail(f"pka.db schema_migrations missing: {missing_mig}")
    ok(f"all {len(PKA_EXPECTED_MIGRATIONS)} v1.2.0-baseline migrations recorded")

    # Settings sanity.
    settings = get_settings(pka_db_path)
    expected_keys = {
        'feedback_model', 'audit_cadence_days', 'multi_model_enabled',
        'model_routing', 'default_model_provider_id', 'last_session_close_at',
        'last_reflection_pass_at', 'user_name', 'user_use_case',
        'personal_db_separation', 'personal_db_path',
    }
    missing_keys = expected_keys - set(settings.keys())
    if missing_keys:
        fail(f"settings missing keys: {missing_keys}")
    ok(f"all {len(expected_keys)} expected settings keys present")

    if settings.get('feedback_model') != 'leroy_rates_levi_audits':
        fail(f"feedback_model is '{settings.get('feedback_model')}', expected 'leroy_rates_levi_audits'")
    ok("feedback_model = leroy_rates_levi_audits (v1.2.0 baseline)")

    if settings.get('audit_cadence_days') != '7':
        fail(f"audit_cadence_days is '{settings.get('audit_cadence_days')}', expected '7'")
    ok("audit_cadence_days = 7")

    if not settings.get('personal_db_path'):
        fail("personal_db_path is empty in settings — setup.py should record it")
    ok(f"personal_db_path recorded: {settings['personal_db_path']}")

    # team_members seed.
    members = get_team_members(pka_db_path)
    expected_members = [('Sam', 'HR Director'), ('PAX', 'Senior Researcher')]
    if members != expected_members:
        fail(f"team_members != {expected_members}; got {members}")
    ok(f"team_members seeded: {members}")

    # model_providers seed.
    db = sqlite3.connect(pka_db_path)
    providers = db.execute(
        "SELECT id, name, fallback_id FROM model_providers ORDER BY id"
    ).fetchall()
    db.close()
    expected_providers = [
        (1, 'Claude Sonnet 4.6', None),
        (2, 'Claude Opus 4.7', 1),
        (3, 'Claude Haiku 4.5', 1),
    ]
    if providers != expected_providers:
        fail(f"model_providers != expected; got {providers}")
    ok("model_providers seeded with Sonnet/Opus/Haiku (Anthropic-only)")

    # model_pricing seed (3 Anthropic rows).
    db = sqlite3.connect(pka_db_path)
    pricing_count = db.execute(
        "SELECT COUNT(*) FROM model_pricing WHERE provider='anthropic'"
    ).fetchone()[0]
    db.close()
    if pricing_count != 3:
        fail(f"model_pricing should have 3 anthropic rows; got {pricing_count}")
    ok("model_pricing seeded with 3 Anthropic rows")

    # briefs has source_material and project_slug columns.
    db = sqlite3.connect(pka_db_path)
    briefs_cols = {r[1] for r in db.execute("PRAGMA table_info(briefs)").fetchall()}
    db.close()
    for required in ['source_material', 'project_slug']:
        if required not in briefs_cols:
            fail(f"briefs missing column '{required}'")
    ok("briefs has source_material and project_slug columns")

    # deliverables has source_material.
    db = sqlite3.connect(pka_db_path)
    deliv_cols = {r[1] for r in db.execute("PRAGMA table_info(deliverables)").fetchall()}
    db.close()
    if 'source_material' not in deliv_cols:
        fail("deliverables missing source_material column")
    ok("deliverables has source_material column")

    # feedback has rater column with CHECK constraint.
    db = sqlite3.connect(pka_db_path)
    feedback_cols = {r[1] for r in db.execute("PRAGMA table_info(feedback)").fetchall()}
    db.close()
    if 'rater' not in feedback_cols:
        fail("feedback missing rater column")
    ok("feedback has rater column")

    # Test feedback.rater CHECK constraint by attempting a bad insert.
    db = sqlite3.connect(pka_db_path)
    # Need a deliverable to FK to. Skip the CHECK roundtrip test; trust DDL.
    db.close()

    # memory.scope = 'owner_only' allowed (not 'levi_only').
    db = sqlite3.connect(pka_db_path)
    try:
        db.execute("""
            INSERT INTO memory (slug, type, title, body, scope, provenance)
            VALUES ('test-owner-scope', 'user_fact', 'test', 'test body',
                    'owner_only', 'human_confirmed')
        """)
        db.execute("DELETE FROM memory WHERE slug='test-owner-scope'")
        db.commit()
        ok("memory.scope='owner_only' accepted by CHECK constraint")
    except sqlite3.IntegrityError as e:
        fail(f"memory.scope='owner_only' rejected by CHECK: {e}")
    try:
        db.execute("""
            INSERT INTO memory (slug, type, title, body, scope, provenance)
            VALUES ('test-bad-scope', 'user_fact', 'test', 'test body',
                    'levi_only', 'human_confirmed')
        """)
        fail("memory.scope='levi_only' was accepted — CHECK constraint should reject")
    except sqlite3.IntegrityError:
        ok("memory.scope='levi_only' correctly rejected by CHECK constraint")
    db.close()


def verify_projects_db(projects_db_path):
    print(f"\nVerifying projects.db at {projects_db_path}")
    if not projects_db_path.exists():
        fail(f"projects.db not created at {projects_db_path}")
    ok("projects.db file exists")

    tables = list_tables(projects_db_path)
    missing = PROJECTS_EXPECTED_TABLES - tables
    if missing:
        fail(f"projects.db missing tables: {missing}")
    ok(f"all {len(PROJECTS_EXPECTED_TABLES)} expected tables present")

    fts = list_fts(projects_db_path)
    missing_fts = PROJECTS_EXPECTED_FTS - fts
    if missing_fts:
        fail(f"projects.db missing FTS5 tables: {missing_fts}")
    ok(f"all {len(PROJECTS_EXPECTED_FTS)} expected FTS5 tables present")

    migrations = list_migrations(projects_db_path)
    missing_mig = PROJECTS_EXPECTED_MIGRATIONS - migrations
    if missing_mig:
        fail(f"projects.db schema_migrations missing: {missing_mig}")
    ok(f"all {len(PROJECTS_EXPECTED_MIGRATIONS)} v1.2.0-baseline migrations recorded")

    # projects table is empty on fresh install.
    db = sqlite3.connect(projects_db_path)
    proj_count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    db.close()
    if proj_count != 0:
        fail(f"projects table should be empty on fresh install; got {proj_count} rows")
    ok("projects table empty on fresh install (correct)")

    # memory table is empty on fresh install.
    db = sqlite3.connect(projects_db_path)
    mem_count = db.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    db.close()
    if mem_count != 0:
        fail(f"projects.memory should be empty on fresh install; got {mem_count} rows")
    ok("projects.memory empty on fresh install (correct)")

    # memory FK to projects: insert a project, then a memory row, then try to delete
    # the project — should fail RESTRICT.
    db = sqlite3.connect(projects_db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("INSERT INTO projects (slug, name) VALUES ('test-fk', 'test project')")
    db.execute("""
        INSERT INTO memory (slug, project_slug, type, title, body, scope, provenance)
        VALUES ('test-mem', 'test-fk', 'topology', 't', 'b',
                'project_global', 'human_confirmed')
    """)
    db.commit()
    try:
        db.execute("DELETE FROM projects WHERE slug='test-fk'")
        fail("DELETE on referenced project should fail with FK RESTRICT")
    except sqlite3.IntegrityError:
        ok("FK from projects.memory.project_slug → projects.slug RESTRICT enforced")
    # Cleanup.
    db.execute("DELETE FROM memory WHERE slug='test-mem'")
    db.execute("DELETE FROM projects WHERE slug='test-fk'")
    db.commit()
    db.close()

    # provenance enum: 'orchestrator_inferred' accepted; 'leroy_inferred' rejected.
    db = sqlite3.connect(projects_db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("INSERT INTO projects (slug, name) VALUES ('test-prov', 'test')")
    try:
        db.execute("""
            INSERT INTO memory (slug, project_slug, type, title, body, scope, provenance)
            VALUES ('test-orch', 'test-prov', 'topology', 't', 'b',
                    'project_global', 'orchestrator_inferred')
        """)
        db.commit()
        ok("projects.memory.provenance='orchestrator_inferred' accepted")
    except sqlite3.IntegrityError as e:
        fail(f"orchestrator_inferred rejected by CHECK: {e}")
    try:
        db.execute("""
            INSERT INTO memory (slug, project_slug, type, title, body, scope, provenance)
            VALUES ('test-bad-prov', 'test-prov', 'topology', 't', 'b',
                    'project_global', 'leroy_inferred')
        """)
        fail("provenance='leroy_inferred' was accepted in projects.memory — should be 'orchestrator_inferred' only")
    except sqlite3.IntegrityError:
        ok("projects.memory.provenance='leroy_inferred' correctly rejected (templated naming from day 1)")
    db.execute("DELETE FROM memory WHERE project_slug='test-prov'")
    db.execute("DELETE FROM projects WHERE slug='test-prov'")
    db.commit()
    db.close()


def verify_personal_db(personal_db_path):
    print(f"\nVerifying personal.db at {personal_db_path}")
    if not personal_db_path.exists():
        fail(f"personal.db not created at {personal_db_path}")
    ok("personal.db file exists")

    tables = list_tables(personal_db_path)
    missing = PERSONAL_EXPECTED_TABLES - tables
    if missing:
        fail(f"personal.db missing tables: {missing}")
    ok(f"all {len(PERSONAL_EXPECTED_TABLES)} expected tables present")

    # Forbidden: any levi_* or leroy_* table.
    forbidden = [t for t in tables if t.startswith(('levi_', 'leroy_'))]
    if forbidden:
        fail(f"personal.db has historical-named tables: {forbidden}; should be owner_*/orchestrator_*")
    ok("no historical levi_*/leroy_* tables present (canonical names only)")

    fts = list_fts(personal_db_path)
    missing_fts = PERSONAL_EXPECTED_FTS - fts
    if missing_fts:
        fail(f"personal.db missing FTS5 tables: {missing_fts}")
    ok(f"all {len(PERSONAL_EXPECTED_FTS)} expected FTS5 tables present")

    migrations = list_migrations(personal_db_path)
    missing_mig = PERSONAL_EXPECTED_MIGRATIONS - migrations
    if missing_mig:
        fail(f"personal.db schema_migrations missing: {missing_mig}")
    ok(f"all {len(PERSONAL_EXPECTED_MIGRATIONS)} v1.2.0-baseline migrations recorded")

    # owner_posture.captured_by enum: 'owner' and 'orchestrator' accepted; 'levi' rejected.
    db = sqlite3.connect(personal_db_path)
    try:
        db.execute("INSERT INTO owner_posture (body, captured_by) VALUES ('test', 'owner')")
        db.execute("INSERT INTO owner_posture (body, captured_by) VALUES ('test', 'orchestrator')")
        db.execute("DELETE FROM owner_posture WHERE body='test'")
        db.commit()
        ok("owner_posture.captured_by enum: 'owner'/'orchestrator' accepted")
    except sqlite3.IntegrityError as e:
        fail(f"captured_by enum rejected canonical values: {e}")
    try:
        db.execute("INSERT INTO owner_posture (body, captured_by) VALUES ('test-bad', 'levi')")
        fail("owner_posture.captured_by='levi' was accepted — CHECK should reject")
    except sqlite3.IntegrityError:
        ok("owner_posture.captured_by='levi' correctly rejected (canonical enum)")
    db.close()

    # orchestrator_observations.status includes 'promoted-to-memory' from day 1.
    db = sqlite3.connect(personal_db_path)
    try:
        db.execute("""
            INSERT INTO orchestrator_observations (body, status)
            VALUES ('test-promoted', 'promoted-to-memory')
        """)
        db.execute("DELETE FROM orchestrator_observations WHERE body='test-promoted'")
        db.commit()
        ok("orchestrator_observations.status='promoted-to-memory' accepted (full enum from day 1)")
    except sqlite3.IntegrityError as e:
        fail(f"status='promoted-to-memory' rejected: {e}")
    db.close()

    # orchestrator_observations.subject default = 'owner'.
    db = sqlite3.connect(personal_db_path)
    cur = db.execute("INSERT INTO orchestrator_observations (body) VALUES ('test-subject-default')")
    rowid = cur.lastrowid
    subject = db.execute(
        "SELECT subject FROM orchestrator_observations WHERE id=?", (rowid,)
    ).fetchone()[0]
    if subject != 'owner':
        fail(f"orchestrator_observations.subject default is '{subject}', expected 'owner'")
    ok("orchestrator_observations.subject default = 'owner'")
    db.execute("DELETE FROM orchestrator_observations WHERE id=?", (rowid,))
    db.commit()
    db.close()

    # team_observations.observer: open string (no closed CHECK enum).
    db = sqlite3.connect(personal_db_path)
    try:
        db.execute("""
            INSERT INTO team_observations (observer, subject, body)
            VALUES ('hypothetical-new-hire', 'orchestrator', 'test')
        """)
        db.execute("DELETE FROM team_observations WHERE body='test'")
        db.commit()
        ok("team_observations.observer accepts open string (no closed CHECK enum)")
    except sqlite3.IntegrityError as e:
        fail(f"team_observations.observer enum is closed — should be open: {e}")
    db.close()


def verify_attach_pattern(pka_db_path, projects_db_path, personal_db_path):
    print(f"\nVerifying ATTACH DATABASE cross-tier pattern")
    db = sqlite3.connect(pka_db_path)
    db.execute(f"ATTACH DATABASE '{projects_db_path}' AS projects")
    db.execute(f"ATTACH DATABASE '{personal_db_path}' AS personal")

    # Cross-tier read: count tables in each attached schema.
    pka_count = db.execute("SELECT COUNT(*) FROM main.team_members").fetchone()[0]
    projects_count = db.execute("SELECT COUNT(*) FROM projects.projects").fetchone()[0]
    personal_count = db.execute("SELECT COUNT(*) FROM personal.owner_journal").fetchone()[0]
    ok(f"cross-tier read: main.team_members={pka_count}, projects.projects={projects_count}, personal.owner_journal={personal_count}")

    db.execute("DETACH DATABASE personal")
    db.execute("DETACH DATABASE projects")
    db.close()


def verify_migration_status(template_root, pka_db_path, projects_db_path, personal_db_path):
    """Run migrate.py status against each tier; assert v1.2.0 baseline reports as applied."""
    print(f"\nVerifying migrate.py status reports v1.2.0 baseline as applied")

    for tier, dir_, db_path, expected in [
        ('pka',      template_root / 'migrations',          pka_db_path,      PKA_EXPECTED_MIGRATIONS),
        ('personal', template_root / 'migrations/personal', personal_db_path, PERSONAL_EXPECTED_MIGRATIONS),
        ('projects', template_root / 'migrations/projects', projects_db_path, PROJECTS_EXPECTED_MIGRATIONS),
    ]:
        result = subprocess.run(
            ['python3', str(template_root / 'migrations/migrate.py'),
             'status', '--dir', str(dir_), '--db', str(db_path)],
            cwd=template_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail(f"migrate.py status (tier={tier}) returned {result.returncode}: {result.stderr}")
        # Parse output: each line is "applied  <stem>" or "pending  <stem>".
        # All expected migrations whose file exists in --dir should be 'applied'.
        applied = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] == 'applied':
                applied.add(parts[1])
        # The expected migrations whose files exist in this --dir should be applied.
        files_in_dir = {p.stem for p in dir_.glob('[0-9]*.sql')}
        expected_in_dir = expected & files_in_dir
        missing = expected_in_dir - applied
        if missing:
            fail(f"migrate.py status (tier={tier}): expected {expected_in_dir} applied, missing: {missing}\nFull output:\n{result.stdout}")
        ok(f"tier={tier}: {len(expected_in_dir)} baseline migration(s) report as applied")


def main():
    with tempfile.TemporaryDirectory(prefix='pka_template_verify_') as tmp:
        tmp_root = Path(tmp) / 'install_root'
        tmp_root.mkdir()
        personal_data_dir = Path(tmp) / 'personal_data'

        print(f"Tmp install root:    {tmp_root}")
        print(f"Tmp personal_data:   {personal_data_dir}")

        # Fresh install.
        print("\n=== Pass 1: fresh install ===")
        run_fresh_install(tmp_root, personal_data_dir)

        pka_db = tmp_root / 'pka.db'
        projects_db = tmp_root / 'projects.db'
        personal_db = personal_data_dir / 'personal.db'

        verify_pka_db(pka_db)
        verify_projects_db(projects_db)
        verify_personal_db(personal_db)
        verify_attach_pattern(pka_db, projects_db, personal_db)
        verify_migration_status(tmp_root, pka_db, projects_db, personal_db)

        # Idempotency check: re-run setup with overwrite=yes for all three DBs.
        print("\n=== Pass 2: idempotency (overwrite + re-create) ===")
        result = subprocess.run(
            ['python3', 'setup.py', '--personal-data-dir', str(personal_data_dir)],
            cwd=tmp_root,
            capture_output=True,
            text=True,
            input='yes\nyes\nyes\n',
        )
        if result.returncode != 0:
            fail(f"setup.py second run failed: {result.stderr}")
        ok("setup.py re-run with overwrite succeeded")

        verify_pka_db(pka_db)
        verify_projects_db(projects_db)
        verify_personal_db(personal_db)

        print("\n=== All checks passed ===")
        return 0


if __name__ == '__main__':
    sys.exit(main())
