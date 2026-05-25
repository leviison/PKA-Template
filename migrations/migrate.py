#!/usr/bin/env python3
"""
PKA migration runner — unified (BRIEF-214 R7).

Convention:
  - Migrations live in a directory as NNN_<slug>.sql.
  - Each file has an UP block, then a line matching `-- +migrate Down`,
    then a DOWN block.
  - UP blocks must be idempotent. DOWN blocks must drop cleanly.
  - Applied migrations are recorded in the schema_migrations table.

Usage:
  python3 migrate.py up     [--to <name>] [--db <path>] [--dir <path>]
  python3 migrate.py down   [--to <name>] [--db <path>] [--dir <path>]
  python3 migrate.py status [--db <path>] [--dir <path>]

If --db is omitted, defaults to <repo_root>/pka.db.
If --dir is omitted, defaults to the directory containing this script
(`migrations/`), which is the pka.db migration set.

Examples:
  # pka.db migrations (default behaviour)
  python3 migrations/migrate.py up

  # personal.db migrations (replaces migrate_personal.py)
  python3 migrations/migrate.py up \\
      --dir migrations/personal \\
      --db ~/Documents/PKA-Data/personal.db

  # projects.db migrations (when BRIEF-A lands)
  python3 migrations/migrate.py up \\
      --dir migrations/projects \\
      --db projects.db

History:
  Pre-BRIEF-214 this runner was hardcoded to scan its own parent
  directory. The sibling `migrate_personal.py` existed because mixing
  pka.db and personal.db SQL files in one folder would cross-apply
  schemas. BRIEF-214 generalises the runner via `--dir`; sibling runners
  are now thin shims that forward into this entry point with their
  --dir / --db pair pre-filled.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

# DEFAULT_MIGRATIONS_DIR is the directory containing THIS file. Each
# sibling runner (migrate_personal.py and any future tier shim) sets
# --dir to its own directory before forwarding here.
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DEFAULT_MIGRATIONS_DIR.parent / "pka.db"
DOWN_MARKER = re.compile(r"^\s*--\s*\+migrate\s+Down\s*$", re.IGNORECASE | re.MULTILINE)
FILENAME_RE = re.compile(r"^(\d{3,})_[a-z0-9_]+\.sql$")


def list_migration_files(migrations_dir: Path) -> list[Path]:
    files = []
    for p in sorted(migrations_dir.glob("*.sql")):
        if FILENAME_RE.match(p.name):
            files.append(p)
    return files


def split_up_down(sql_text: str) -> tuple[str, str]:
    parts = DOWN_MARKER.split(sql_text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(
            "Migration file is missing `-- +migrate Down` marker; "
            "every migration must declare both UP and DOWN blocks."
        )
    return parts[0].strip(), parts[1].strip()


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name        TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def applied_migrations(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT name FROM schema_migrations ORDER BY name ASC;")
    return [row[0] for row in cur.fetchall()]


def migration_stem(path: Path) -> str:
    return path.stem  # e.g. "001_memory_table"


def cmd_status(db_path: Path, migrations_dir: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        ensure_migrations_table(conn)
        done = set(applied_migrations(conn))
    finally:
        conn.close()
    files = list_migration_files(migrations_dir)
    if not files:
        print(f"No migration files found in {migrations_dir}.")
        return 0
    print(f"DB:  {db_path}")
    print(f"Dir: {migrations_dir}")
    print(f"{'STATUS':<10} MIGRATION")
    for f in files:
        stem = migration_stem(f)
        flag = "applied" if stem in done else "pending"
        print(f"{flag:<10} {stem}")
    return 0


def _chdir_to_db_dir(db_path: Path) -> None:
    """Chdir to the directory containing the target DB so any
    ATTACH DATABASE statements in migrations resolve as siblings of the
    main DB rather than against the process cwd. Migration 003 relies
    on this — it attaches `projects.db` as a sibling of `pka.db`.
    Earlier migrations (001, 002) are pure intra-DB DDL and unaffected.
    """
    target_dir = db_path.resolve().parent
    os.chdir(target_dir)


def cmd_up(db_path: Path, migrations_dir: Path, to: str | None) -> int:
    _chdir_to_db_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_migrations_table(conn)
        done = set(applied_migrations(conn))
        files = list_migration_files(migrations_dir)
        applied_this_run = 0
        for f in files:
            stem = migration_stem(f)
            if stem in done:
                continue
            up_sql, _ = split_up_down(f.read_text())
            print(f"[up] {stem} …", end=" ", flush=True)
            with conn:  # transaction
                conn.executescript(up_sql)
                conn.execute(
                    "INSERT INTO schema_migrations (name) VALUES (?);", (stem,)
                )
            applied_this_run += 1
            print("ok")
            if to is not None and stem == to:
                break
        if applied_this_run == 0:
            print("Nothing to apply.")
        else:
            print(f"Applied {applied_this_run} migration(s).")
        return 0
    finally:
        conn.close()


def cmd_down(db_path: Path, migrations_dir: Path, to: str | None) -> int:
    _chdir_to_db_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_migrations_table(conn)
        done = applied_migrations(conn)
        if not done:
            print("No migrations to roll back.")
            return 0
        # Roll back in reverse order
        stems_by_name = {migration_stem(f): f for f in list_migration_files(migrations_dir)}
        rolled = 0
        for stem in reversed(done):
            if to is not None and stem == to:
                # `to` is the floor we roll back to — don't include it.
                break
            f = stems_by_name.get(stem)
            if f is None:
                # Cross-tier bootstrap row: the stem is recorded in
                # `schema_migrations` but its file is in a different
                # `--dir` (e.g. `'003_split_projects_db'` was seeded
                # into `projects.db.schema_migrations` by the BRIEF-132
                # split, but the file lives in `migrations/`, not
                # `migrations/projects/`). Skip such rows — they belong
                # to the other tier's migration series and are not ours
                # to reverse. Continue to the next applied migration
                # rather than aborting the rollback chain.
                print(
                    f"[down] {stem} — file not in --dir; treating as "
                    f"cross-tier bootstrap row, skipping.",
                    file=sys.stderr,
                )
                continue
            _, down_sql = split_up_down(f.read_text())
            print(f"[down] {stem} …", end=" ", flush=True)
            with conn:
                conn.executescript(down_sql)
                conn.execute(
                    "DELETE FROM schema_migrations WHERE name = ?;", (stem,)
                )
            rolled += 1
            print("ok")
            if to is None:
                # Default: roll back exactly one migration.
                break
        if rolled == 0:
            print("Nothing to roll back.")
        else:
            print(f"Rolled back {rolled} migration(s).")
        return 0
    finally:
        conn.close()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="PKA migration runner (unified)")
    ap.add_argument("command", choices=["up", "down", "status"])
    ap.add_argument(
        "--to",
        default=None,
        help="Migration stem to stop at (inclusive for up, exclusive floor for down).",
    )
    ap.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"SQLite DB path (default: {DEFAULT_DB}).",
    )
    ap.add_argument(
        "--dir",
        default=str(DEFAULT_MIGRATIONS_DIR),
        help=(
            f"Directory containing the migration .sql files "
            f"(default: {DEFAULT_MIGRATIONS_DIR}). Each tier — pka, "
            f"personal, projects — points --dir at its own sub-directory."
        ),
    )
    args = ap.parse_args(argv)
    db_path = Path(args.db).expanduser()
    migrations_dir = Path(args.dir).expanduser().resolve()
    if not migrations_dir.is_dir():
        raise SystemExit(f"Migration directory not found: {migrations_dir}")
    if args.command == "status":
        return cmd_status(db_path, migrations_dir)
    if args.command == "up":
        return cmd_up(db_path, migrations_dir, args.to)
    if args.command == "down":
        return cmd_down(db_path, migrations_dir, args.to)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
