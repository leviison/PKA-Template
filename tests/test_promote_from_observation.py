"""
tests/test_promote_from_observation.py — BRIEF-146 / BRIEF-214

Tests for memory_io.promote_from_observation() and
memory_io.reconcile_orphan_promotions().

Run:
    python3 tests/test_promote_from_observation.py

This script is a standalone runner (no pytest dependency). It copies the
live pka.db and personal.db into a temp directory, exercises the helper
against the copies, and asserts the expected DB shape after each call.
The live DBs are NEVER touched.

Schema reference (post BRIEF-214 substrate-pass rename):
  - owner_posture (was levi_posture); captured_by enum is ('owner','orchestrator')
  - orchestrator_observations (was leroy_observations); subject default 'owner'
  - owner_observations (was levi_observations)
  - team_observations (observer is now an open TEXT NOT NULL string)

Tests:
  1. happy_path                — INSERT memory + UPDATE personal succeed atomically;
                                  markdown mirror is written.
  2. step2_zero_row_update_guard — Rowcount guard fires when source row is missing.
  3. step2_check_violation_rollback — CHECK violation in step 2 rolls back step 1.
  4. already_promoted_refused  — Calling on a row already promoted raises
                                  ValueError without touching either DB.
  5. invalid_source_table      — Helper rejects unknown source_table.
  6. duplicate_slug_refused    — Helper rejects a slug that already exists.
  7. all_four_tables_work      — Helper works for each of the four
                                  promotable source tables (post-rename, all
                                  four CHECK enums include 'promoted-to-memory';
                                  the historical leroy_observations schema gap
                                  was closed by personal-migration 004).
  8. orphan_reconciliation     — Simulate an orphan by directly inserting a
                                  memory row WITHOUT updating personal,
                                  then verify reconcile_orphan_promotions()
                                  detects it and the suggested fix resolves it.
  9. helper_attaches_when_personal_missing — Auto-ATTACH path.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Make the parent dir importable as `memory_io`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import memory_io  # noqa: E402

LIVE_PKA = ROOT / "pka.db"


def _resolve_live_personal() -> Path:
    """Look up personal.db location from pka.db.settings.personal_db_path
    (set by setup.py at install) with a sane fallback to the install
    default. Resolved at module import so the rest of the test file can
    stay declarative.
    """
    try:
        c = sqlite3.connect(
            f"file:{LIVE_PKA}?mode=ro", uri=True, timeout=1.0
        )
        try:
            row = c.execute(
                "SELECT value FROM settings WHERE key = 'personal_db_path';"
            ).fetchone()
            if row and row[0]:
                return Path(row[0]).expanduser()
        finally:
            c.close()
    except sqlite3.Error:
        pass
    return Path.home() / "PKA-Data" / "personal.db"


LIVE_PERSONAL = _resolve_live_personal()


class TestEnv:
    """Per-test scratch dir with copies of both DBs and a fresh mirror dir."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="iris_brief_146_"))
        self.pka = self.tmp / "pka.db"
        self.personal = self.tmp / "personal.db"
        self.mirror_dir = self.tmp / "memory_mirror"
        self.mirror_dir.mkdir()
        shutil.copy(LIVE_PKA, self.pka)
        shutil.copy(LIVE_PERSONAL, self.personal)
        # Connection on pka.db with personal attached.
        self.conn = sqlite3.connect(str(self.pka), isolation_level=None)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        escaped = str(self.personal).replace("'", "''")
        self.conn.execute(f"ATTACH DATABASE '{escaped}' AS personal;")

    def insert_observation(self, table: str, **kwargs) -> int:
        """Insert a fresh observation row for the test; returns new id."""
        defaults = {
            "owner_posture": dict(
                posture_type="test",
                body="test body",
                captured_by="orchestrator",
                status="active",
            ),
            "orchestrator_observations": dict(
                observation_type="test",
                body="test body",
                evidence="test evidence",
                status="pending-review",
            ),
            "owner_observations": dict(
                subject="orchestrator",
                observation_type="test",
                body="test body",
                evidence="test evidence",
                status="active",
            ),
            "team_observations": dict(
                observer="iris",
                subject="orchestrator",
                observation_type="test",
                body="test body",
                evidence="test evidence",
                status="pending-review",
            ),
        }[table]
        defaults.update(kwargs)
        cols = ", ".join(defaults.keys())
        placeholders = ", ".join("?" for _ in defaults)
        cur = self.conn.execute(
            f"INSERT INTO personal.{table} ({cols}) VALUES ({placeholders});",
            tuple(defaults.values()),
        )
        return cur.lastrowid

    def cleanup(self):
        try:
            self.conn.execute("DETACH DATABASE personal;")
        except sqlite3.OperationalError:
            pass
        self.conn.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Test runner machinery
# ---------------------------------------------------------------------------

_failures: list[str] = []
_passes: list[str] = []


def _run(name: str, fn):
    env = TestEnv()
    try:
        fn(env)
        _passes.append(name)
        print(f"  PASS  {name}")
    except AssertionError as e:
        _failures.append(f"{name}: {e}")
        print(f"  FAIL  {name}: {e}")
    except Exception as e:
        _failures.append(f"{name}: unexpected {type(e).__name__}: {e}")
        print(f"  FAIL  {name}: unexpected {type(e).__name__}: {e}")
    finally:
        env.cleanup()


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_happy_path(env: TestEnv):
    src_id = env.insert_observation("owner_posture")

    new_id = memory_io.promote_from_observation(
        env.conn,
        source_table="owner_posture",
        source_id=src_id,
        memory_slug="test-iris-happy",
        memory_type="operational",
        memory_title="Test happy-path principle",
        memory_body="A principle promoted from observation.",
        mirror_dir=env.mirror_dir,
    )
    _assert(new_id is not None, "new memory id should be returned")
    _assert(isinstance(new_id, int), "new memory id should be int")

    # Verify the memory row landed
    mrow = env.conn.execute(
        "SELECT slug, title, source_ref, approved_by, scope, provenance "
        "FROM main.memory WHERE id = ?;",
        (new_id,),
    ).fetchone()
    _assert(mrow is not None, "memory row must exist")
    _assert(mrow[0] == "test-iris-happy", f"slug mismatch: {mrow[0]}")
    _assert(mrow[2] == f"owner_posture:{src_id}", f"source_ref: {mrow[2]}")
    _assert(mrow[3] == "priya", f"approved_by should default to priya: {mrow[3]}")
    _assert(mrow[4] == "global", f"scope: {mrow[4]}")
    _assert(mrow[5] == "human_confirmed", f"provenance: {mrow[5]}")

    # Verify the source row was linked
    srow = env.conn.execute(
        "SELECT status, promoted_to_memory_id FROM personal.owner_posture WHERE id = ?;",
        (src_id,),
    ).fetchone()
    _assert(srow[0] == "promoted-to-memory", f"status: {srow[0]}")
    _assert(srow[1] == new_id, f"promoted_to_memory_id: {srow[1]}")

    # Verify the markdown mirror was written
    md_path = env.mirror_dir / "test-iris-happy.md"
    _assert(md_path.exists(), f"markdown mirror missing: {md_path}")
    md = md_path.read_text()
    _assert("Test happy-path principle" in md, "title missing in mirror")
    _assert("owner_posture:" in md, "source_ref missing in mirror")


def test_step2_zero_row_update_guard(env: TestEnv):
    """
    Verify the rowcount-guard inside the helper trips when the source
    row vanishes between pre-flight and UPDATE. We simulate this by
    DELETEing the source row from a second connection AFTER the helper
    finishes pre-flight but BEFORE it begins the txn. Easier proxy:
    pass a source_id that exists at pre-flight but is then targeted by
    a concurrent delete. In practice the cleanest test is to bypass
    pre-flight by simulating the bare update manually — that's already
    covered by step2_check_violation_rollback. So this test instead
    confirms the rowcount guard itself, by directly calling a minimal
    transaction with the same shape as the helper but targeting a
    non-existent source_id.
    """
    env.conn.execute("BEGIN IMMEDIATE;")
    raised = False
    try:
        env.conn.execute(
            """
            INSERT INTO main.memory (slug, type, title, body, scope,
                source_ref, status, valid_from, ingested_at, provenance)
            VALUES ('test-iris-zero-row', 'operational', 't', 'b', 'global',
                'owner_posture:999999999', 'active', datetime('now'),
                datetime('now'), 'human_confirmed');
            """
        )
        upd = env.conn.execute(
            "UPDATE personal.owner_posture "
            "SET status = 'promoted-to-memory', promoted_to_memory_id = 1 "
            "WHERE id = ?",
            (999999999,),
        )
        if upd.rowcount != 1:
            raise RuntimeError(f"UPDATE affected {upd.rowcount} rows")
        env.conn.execute("COMMIT;")
    except RuntimeError:
        raised = True
        env.conn.execute("ROLLBACK;")

    _assert(raised, "expected RuntimeError on 0-row UPDATE")
    mrow = env.conn.execute(
        "SELECT id FROM main.memory WHERE slug = 'test-iris-zero-row';"
    ).fetchone()
    _assert(mrow is None, f"memory row should be rolled back; got: {mrow}")


def test_step2_check_violation_rollback(env: TestEnv):
    """
    A more direct atomicity test: cause an actual CHECK constraint
    violation on the personal side by manually running the equivalent
    in-transaction sequence, then assert pka.db rolls back too.

    This duplicates the helper's logic to confirm SQLite's documented
    cross-DB transaction atomicity behaves as expected on this host.
    """
    src_id = env.insert_observation("owner_posture")

    env.conn.execute("BEGIN IMMEDIATE;")
    raised = False
    try:
        env.conn.execute(
            """
            INSERT INTO main.memory (slug, type, title, body, scope,
                source_ref, status, valid_from, ingested_at, provenance)
            VALUES ('test-iris-violation', 'operational', 't', 'b', 'global',
                'owner_posture:%d', 'active', datetime('now'),
                datetime('now'), 'human_confirmed');
            """ % src_id
        )
        # Force CHECK violation
        env.conn.execute(
            "UPDATE personal.owner_posture SET status='not-a-valid-status' WHERE id=?",
            (src_id,),
        )
        env.conn.execute("COMMIT;")
    except sqlite3.IntegrityError:
        raised = True
        env.conn.execute("ROLLBACK;")

    _assert(raised, "expected IntegrityError on CHECK violation")
    mrow = env.conn.execute(
        "SELECT id FROM main.memory WHERE slug = 'test-iris-violation';"
    ).fetchone()
    _assert(
        mrow is None,
        f"memory write should be rolled back across ATTACHed DBs; got {mrow}",
    )


def test_already_promoted_refused(env: TestEnv):
    src_id = env.insert_observation(
        "owner_posture",
        status="promoted-to-memory",
        promoted_to_memory_id=999999,  # bogus FK — refused by pre-flight
    )

    raised = False
    try:
        memory_io.promote_from_observation(
            env.conn,
            source_table="owner_posture",
            source_id=src_id,
            memory_slug="test-iris-already",
            memory_type="operational",
            memory_title="should not run",
            memory_body="should not run",
            mirror_dir=env.mirror_dir,
        )
    except ValueError as e:
        raised = True
        _assert("already promoted" in str(e), f"unexpected msg: {e}")

    _assert(raised, "expected ValueError on already-promoted source")
    mrow = env.conn.execute(
        "SELECT id FROM main.memory WHERE slug = 'test-iris-already';"
    ).fetchone()
    _assert(mrow is None, "no memory row should exist on rejection")


def test_invalid_source_table(env: TestEnv):
    raised = False
    try:
        memory_io.promote_from_observation(
            env.conn,
            source_table="not_a_table",
            source_id=1,
            memory_slug="test-iris-invalid",
            memory_type="operational",
            memory_title="x",
            memory_body="x",
            mirror_dir=env.mirror_dir,
        )
    except ValueError as e:
        raised = True
        _assert("invalid source_table" in str(e), f"unexpected msg: {e}")
    _assert(raised, "expected ValueError on invalid source_table")


def test_duplicate_slug_refused(env: TestEnv):
    src_id_1 = env.insert_observation("owner_posture")
    src_id_2 = env.insert_observation("owner_posture")

    memory_io.promote_from_observation(
        env.conn,
        source_table="owner_posture",
        source_id=src_id_1,
        memory_slug="test-iris-dup-slug",
        memory_type="operational",
        memory_title="first",
        memory_body="first",
        mirror_dir=env.mirror_dir,
    )

    raised = False
    try:
        memory_io.promote_from_observation(
            env.conn,
            source_table="owner_posture",
            source_id=src_id_2,
            memory_slug="test-iris-dup-slug",  # same slug
            memory_type="operational",
            memory_title="second",
            memory_body="second",
            mirror_dir=env.mirror_dir,
        )
    except ValueError as e:
        raised = True
        _assert("already exists" in str(e), f"unexpected msg: {e}")
    _assert(raised, "expected ValueError on duplicate slug")


def test_all_four_tables_work(env: TestEnv):
    """
    All four observation tables accept 'promoted-to-memory' as a valid
    status post-rename: owner_posture, orchestrator_observations,
    owner_observations, team_observations.

    The historical schema gap on leroy_observations (now
    orchestrator_observations) was closed by personal-migration 004
    (status-enum widening). This test asserts the closed-gap state.
    """
    working = [
        ("owner_posture", "test-iris-op"),
        ("orchestrator_observations", "test-iris-oo"),
        ("owner_observations", "test-iris-oi"),
        ("team_observations", "test-iris-te"),
    ]
    for table, slug in working:
        src_id = env.insert_observation(table)
        new_id = memory_io.promote_from_observation(
            env.conn,
            source_table=table,
            source_id=src_id,
            memory_slug=slug,
            memory_type="operational",
            memory_title=f"promoted from {table}",
            memory_body="body",
            mirror_dir=env.mirror_dir,
        )
        srow = env.conn.execute(
            f"SELECT status, promoted_to_memory_id FROM personal.{table} WHERE id = ?;",
            (src_id,),
        ).fetchone()
        _assert(
            srow[0] == "promoted-to-memory",
            f"{table}: status not promoted: {srow[0]}",
        )
        _assert(
            srow[1] == new_id,
            f"{table}: promoted_to_memory_id mismatch: {srow[1]} vs {new_id}",
        )


def test_orchestrator_observations_promotable(env: TestEnv):
    """
    Confirms the historical schema gap on leroy_observations (now
    orchestrator_observations) is closed: promoting a row from that
    table now succeeds atomically.

    Pre-personal-migration-004: 'promoted-to-memory' was not in the
    status CHECK enum and this promotion path raised IntegrityError.
    Post-004 + post-BRIEF-214 rename: the enum includes the value and
    the table is named orchestrator_observations. This test asserts
    the closed-gap state.
    """
    src_id = env.insert_observation("orchestrator_observations")

    new_id = memory_io.promote_from_observation(
        env.conn,
        source_table="orchestrator_observations",
        source_id=src_id,
        memory_slug="test-iris-oo-promotable",
        memory_type="operational",
        memory_title="gap-closed",
        memory_body="gap-closed",
        mirror_dir=env.mirror_dir,
    )
    _assert(new_id is not None, "promotion should succeed")

    srow = env.conn.execute(
        "SELECT status, promoted_to_memory_id FROM personal.orchestrator_observations WHERE id = ?;",
        (src_id,),
    ).fetchone()
    _assert(srow[0] == "promoted-to-memory", f"status: {srow[0]}")
    _assert(srow[1] == new_id, f"promoted_to_memory_id: {srow[1]}")


def test_orphan_reconciliation(env: TestEnv):
    """Simulate an orphan by writing the memory row but skipping the
    personal-side link, then verify reconcile_orphan_promotions()
    catches it and the suggested fix resolves it."""
    src_id = env.insert_observation("owner_posture")

    # Manually create the orphan: memory exists, source row's status stays
    # 'active' and promoted_to_memory_id stays NULL.
    cur = env.conn.execute(
        """
        INSERT INTO main.memory (slug, type, title, body, scope,
            source_ref, status, valid_from, ingested_at, provenance)
        VALUES ('test-iris-orphan', 'operational', 't', 'b', 'global',
            ?, 'active', datetime('now'), datetime('now'), 'human_confirmed');
        """,
        (f"owner_posture:{src_id}",),
    )
    new_memory_id = cur.lastrowid

    orphans = memory_io.reconcile_orphan_promotions(env.conn)
    _assert(len(orphans) >= 1, f"expected at least 1 orphan; got {orphans}")
    # Find our test orphan
    ours = [o for o in orphans if o["memory_slug"] == "test-iris-orphan"]
    _assert(len(ours) == 1, f"expected exactly 1 matching orphan; got {ours}")
    o = ours[0]
    _assert(o["memory_id"] == new_memory_id, f"memory_id mismatch: {o}")
    _assert(o["expected_source_table"] == "owner_posture", f"table: {o}")
    _assert(o["expected_source_id"] == src_id, f"src id: {o}")
    _assert(o["actual_source_status"] == "active", f"status: {o}")
    _assert(o["actual_promoted_to_memory_id"] is None, f"link: {o}")

    # Apply the suggested fix
    env.conn.execute(
        f"UPDATE personal.{o['expected_source_table']} "
        f"SET status = 'promoted-to-memory', "
        f"    promoted_to_memory_id = ? "
        f"WHERE id = ?;",
        (o["memory_id"], o["expected_source_id"]),
    )

    # Re-run reconciliation — our orphan should be gone.
    orphans_after = memory_io.reconcile_orphan_promotions(env.conn)
    ours_after = [o for o in orphans_after if o["memory_slug"] == "test-iris-orphan"]
    _assert(len(ours_after) == 0, f"orphan still detected after fix: {ours_after}")


def test_helper_attaches_when_personal_missing(env: TestEnv):
    """
    Helper should auto-attach personal.db if the caller hasn't.
    """
    # Detach personal from the helper-env connection
    env.conn.execute("DETACH DATABASE personal;")

    # Insert a source row using a one-shot personal connection
    p = sqlite3.connect(str(env.personal))
    cur = p.execute(
        "INSERT INTO owner_posture (posture_type, body, captured_by, status) "
        "VALUES ('test', 'auto-attach test', 'orchestrator', 'active');"
    )
    src_id = cur.lastrowid
    p.commit()
    p.close()

    new_id = memory_io.promote_from_observation(
        env.conn,
        source_table="owner_posture",
        source_id=src_id,
        memory_slug="test-iris-auto-attach",
        memory_type="operational",
        memory_title="auto-attach",
        memory_body="body",
        mirror_dir=env.mirror_dir,
        personal_db_path=env.personal,
    )
    _assert(new_id is not None, "new memory id should be returned")

    # Confirm personal was detached on exit
    schemas = {r[1] for r in env.conn.execute("PRAGMA database_list;").fetchall()}
    _assert("personal" not in schemas, f"personal should be detached: {schemas}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not LIVE_PKA.exists():
        print(f"ERROR: live pka.db not found at {LIVE_PKA}", file=sys.stderr)
        return 1
    if not LIVE_PERSONAL.exists():
        print(f"ERROR: live personal.db not found at {LIVE_PERSONAL}", file=sys.stderr)
        return 1

    print("Running promote_from_observation tests against scratch copies…\n")

    tests = [
        ("happy_path", test_happy_path),
        ("step2_zero_row_update_guard", test_step2_zero_row_update_guard),
        ("step2_check_violation_rollback", test_step2_check_violation_rollback),
        ("already_promoted_refused", test_already_promoted_refused),
        ("invalid_source_table", test_invalid_source_table),
        ("duplicate_slug_refused", test_duplicate_slug_refused),
        ("all_four_tables_work", test_all_four_tables_work),
        ("orchestrator_observations_promotable", test_orchestrator_observations_promotable),
        ("orphan_reconciliation", test_orphan_reconciliation),
        ("helper_attaches_when_personal_missing", test_helper_attaches_when_personal_missing),
    ]
    for name, fn in tests:
        _run(name, fn)

    print()
    print(f"{len(_passes)} passed, {len(_failures)} failed")
    if _failures:
        for f in _failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
