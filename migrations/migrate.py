#!/usr/bin/env python3
"""
PKA migration runner.

Convention:
  - Migrations live in this directory as NNN_<slug>.sql.
  - Each file has an UP block, then a line matching `-- +migrate Down`,
    then a DOWN block.
  - UP blocks must be idempotent. DOWN blocks must drop cleanly.
  - Applied migrations are recorded in the schema_migrations table.

Usage:
  python3 migrate.py up [--to <name>] [--db <path>]
  python3 migrate.py down [--to <name>] [--db <path>]
  python3 migrate.py status [--db <path>]

If --db is omitted, defaults to ../pka.db relative to this file.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent
DEFAULT_DB = MIGRATIONS_DIR.parent / "pka.db"
DOWN_MARKER = re.compile(r"^\s*--\s*\+migrate\s+Down\s*$", re.IGNORECASE | re.MULTILINE)
FILENAME_RE = re.compile(r"^(\d{3,})_[a-z0-9_]+\.sql$")


def list_migration_files() -> list[Path]:
    files = []
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
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


def cmd_status(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        ensure_migrations_table(conn)
        done = set(applied_migrations(conn))
    finally:
        conn.close()
    files = list_migration_files()
    if not files:
        print("No migration files found.")
        return 0
    print(f"DB: {db_path}")
    print(f"{'STATUS':<10} MIGRATION")
    for f in files:
        stem = migration_stem(f)
        flag = "applied" if stem in done else "pending"
        print(f"{flag:<10} {stem}")
    return 0


def cmd_up(db_path: Path, to: str | None) -> int:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_migrations_table(conn)
        done = set(applied_migrations(conn))
        files = list_migration_files()
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


def cmd_down(db_path: Path, to: str | None) -> int:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        ensure_migrations_table(conn)
        done = applied_migrations(conn)
        if not done:
            print("No migrations to roll back.")
            return 0
        # Roll back in reverse order
        stems_by_name = {migration_stem(f): f for f in list_migration_files()}
        rolled = 0
        for stem in reversed(done):
            if to is not None and stem == to:
                # `to` is the floor we roll back to — don't include it.
                break
            f = stems_by_name.get(stem)
            if f is None:
                print(
                    f"[down] {stem} — file missing from disk; cannot reverse. "
                    f"Aborting.",
                    file=sys.stderr,
                )
                return 2
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
    ap = argparse.ArgumentParser(description="PKA migration runner")
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
    args = ap.parse_args(argv)
    db_path = Path(args.db)
    if args.command == "status":
        return cmd_status(db_path)
    if args.command == "up":
        return cmd_up(db_path, args.to)
    if args.command == "down":
        return cmd_down(db_path, args.to)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
