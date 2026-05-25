"""
projects_memory_io.py — markdown-mirror helper for `projects.db.memory`.

Sibling to `memory_io.py`. Same dual-mirror discipline applied to the
projects-tier substrate created by BRIEF-215.

Mirror layout (relative to this file's parent directory):
    memory/projects/<project_slug>/<slug>.md

The DB is authoritative. This module owns the contract from
`projects.db.memory` rows to their markdown mirror. All durable writes to
project memory should go through `write_project_memory_row()`.

Shared internals: this module imports `_atomic_write`, `_render_markdown`,
and `_row_to_dict` from `memory_io` (private re-use, NOT a shared base).
Per BRIEF-215 §8.2 and the CLAUDE.md design-shape rule-of-three
discipline, the empirical-adoption test for a `dual_mirror_io.py` shared
base has not yet fired — promote when a third tier actually adopts the
proposed shared base in production.

## Demotion criterion

Split criterion (mirrors `memory_io.py`).

Write-path: retire when either:
  (a) The projects-tier memory substrate is replaced by a different
      durable-knowledge model, OR
  (b) The dual-mirror discipline graduates to `dual_mirror_io.py` — at
      that point this file's mirror-writing is REFACTORED to wrap the
      shared base, not retired.

Read-path: permanent infrastructure as long as `projects.memory` exists.

Source: owners_inbox/projects_tier_memory_design_iris.md (BRIEF-215),
Levi-approved 2026-05-25.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Reuse the well-tested mirror primitives from memory_io. Private re-use,
# not a shared-base extraction (per BRIEF-215 §8.2).
from memory_io import _atomic_write, _render_markdown, _row_to_dict

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DB = REPO_ROOT / "projects.db"
DEFAULT_MIRROR_DIR = REPO_ROOT / "memory" / "projects"

# Enum-validation helpers — mirror the CHECK constraints in
# migrations/projects/001_projects_memory_substrate.sql.
_VALID_TYPES = frozenset(
    [
        "operational",
        "project",
        "feedback",
        "pattern_ref",
        "topology",
        "environment",
        "host_fact",
        "dependency",
    ]
)
_VALID_PROVENANCES = frozenset(
    ["human_confirmed", "orchestrator_inferred", "model_inferred"]
)
_VALID_STATUSES = frozenset(["active", "superseded", "deferred", "invalidated"])
_SCOPE_PATTERN = re.compile(
    r"^(project_global|host:[a-z][a-z0-9_-]*|team_member:[a-z][a-z0-9_-]*)$"
)


def _validate_enums(*, type: str, scope: str, provenance: str, status: str) -> None:
    if type not in _VALID_TYPES:
        raise ValueError(
            f"write_project_memory_row: invalid type {type!r}. "
            f"Must be one of: {sorted(_VALID_TYPES)}"
        )
    if not _SCOPE_PATTERN.match(scope):
        raise ValueError(
            f"write_project_memory_row: invalid scope {scope!r}. "
            f"Must be 'project_global', 'host:<role>', or 'team_member:<slug>'."
        )
    if provenance not in _VALID_PROVENANCES:
        raise ValueError(
            f"write_project_memory_row: invalid provenance {provenance!r}. "
            f"Must be one of: {sorted(_VALID_PROVENANCES)}"
        )
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"write_project_memory_row: invalid status {status!r}. "
            f"Must be one of: {sorted(_VALID_STATUSES)}"
        )


def _mirror_path(mirror_dir: Path, project_slug: str, slug: str) -> Path:
    return mirror_dir / project_slug / f"{slug}.md"


def _render_project_markdown(row: dict[str, Any]) -> str:
    """Render a project-memory row to markdown. Delegates to memory_io's
    `_render_markdown` for the common fields, but ensures project_slug
    appears in the YAML frontmatter (a project-memory file orphaned from
    its DB is otherwise indistinguishable from a pka-memory file)."""
    # Make a defensive copy so we can augment without mutating the caller's
    # dict. We rely on memory_io._frontmatter() filtering keys to its
    # known list; project_slug is not in that list, so we inject it via a
    # post-render string edit. Cleaner alternative would be a per-tier
    # _frontmatter() — deferred until a third caller earns the refactor.
    rendered = _render_markdown(row)
    # Inject project_slug into the frontmatter block (between the two `---`).
    project_slug = row.get("project_slug")
    if project_slug:
        rendered = rendered.replace(
            "---\nslug:", f"---\nproject_slug: {project_slug}\nslug:", 1
        )
    return rendered


def list_active_projects(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return active project rows (status='active'). Used by the universal
    Session Open loader to know which slugs to consider."""
    cur = conn.execute(
        "SELECT slug, name, description, status, primary_host, repo_url, repo_path "
        "FROM projects WHERE status = 'active' ORDER BY slug;"
    )
    return [_row_to_dict(cur, r) for r in cur.fetchall()]


def load_universal_topology(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Session Open universal-small-load. Loads type=topology/environment/host_fact
    rows across all active projects (BRIEF-215 §3.2 Read 1)."""
    cur = conn.execute(
        """
        SELECT p.slug AS project_slug, p.name AS project_name,
               m.type, m.scope, m.title, m.body, m.ingested_at
        FROM memory m
        JOIN projects p ON p.slug = m.project_slug
        WHERE m.status = 'active'
          AND (m.valid_to IS NULL OR m.valid_to > CURRENT_TIMESTAMP)
          AND p.status = 'active'
          AND m.type IN ('topology', 'environment', 'host_fact')
        ORDER BY p.slug, m.type, m.ingested_at DESC;
        """
    )
    return [_row_to_dict(cur, r) for r in cur.fetchall()]


def load_project_memory(
    conn: sqlite3.Connection, project_slug: str
) -> list[dict[str, Any]]:
    """Per-brief lazy load — all active rows for a single project
    (BRIEF-215 §3.2 Read 2)."""
    cur = conn.execute(
        """
        SELECT type, scope, title, body, source_ref, slug, ingested_at
        FROM memory
        WHERE project_slug = ?
          AND status = 'active'
          AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)
        ORDER BY type, ingested_at DESC;
        """,
        (project_slug,),
    )
    return [_row_to_dict(cur, r) for r in cur.fetchall()]


def write_project_memory_row(
    conn: sqlite3.Connection,
    *,
    project_slug: str,
    slug: str,
    type: str,
    title: str,
    body: str,
    scope: str = "project_global",
    provenance: str = "human_confirmed",
    source_ref: str | None = None,
    status: str = "active",
    superseded_by: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    approved_by: str | None = None,
    tags: str | None = None,
    mirror_dir: Path | None = None,
) -> int:
    """INSERT or UPDATE a project-memory row by (project_slug, slug), then
    write the markdown mirror at memory/projects/<project_slug>/<slug>.md.

    Validates enums up-front to surface caller errors before the SQL CHECK
    fires. The DB FK on memory.project_slug requires the project row to
    exist in projects.projects first.

    Returns the row's id.
    """
    _validate_enums(type=type, scope=scope, provenance=provenance, status=status)
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR

    # Defensive: ensure foreign_keys pragma is ON so the FK to projects.slug
    # actually fires rather than silently inserting an orphan row.
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.execute(
        """
        INSERT INTO memory (
            slug, project_slug, type, title, body, scope, source_ref,
            status, superseded_by, valid_from, valid_to, approved_by,
            provenance, tags
        )
        VALUES (
            :slug, :project_slug, :type, :title, :body, :scope, :source_ref,
            :status, :superseded_by,
            COALESCE(:valid_from, datetime('now')),
            :valid_to, :approved_by, :provenance, :tags
        )
        ON CONFLICT(project_slug, slug) DO UPDATE SET
            type          = excluded.type,
            title         = excluded.title,
            body          = excluded.body,
            scope         = excluded.scope,
            source_ref    = excluded.source_ref,
            status        = excluded.status,
            superseded_by = excluded.superseded_by,
            valid_to      = excluded.valid_to,
            approved_by   = excluded.approved_by,
            provenance    = excluded.provenance,
            tags          = excluded.tags,
            updated_at    = datetime('now')
        ;
        """,
        {
            "slug": slug,
            "project_slug": project_slug,
            "type": type,
            "title": title,
            "body": body,
            "scope": scope,
            "source_ref": source_ref,
            "status": status,
            "superseded_by": superseded_by,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "approved_by": approved_by,
            "provenance": provenance,
            "tags": tags,
        },
    )
    conn.commit()

    cur = conn.execute(
        "SELECT * FROM memory WHERE project_slug = ? AND slug = ?;",
        (project_slug, slug),
    )
    row = _row_to_dict(cur, cur.fetchone())
    md = _render_project_markdown(row)
    _atomic_write(_mirror_path(mirror_dir, project_slug, slug), md)
    return int(row["id"])


def supersede_project_memory(
    conn: sqlite3.Connection,
    *,
    project_slug: str,
    old_slug: str,
    new_slug: str,
    mirror_dir: Path | None = None,
) -> None:
    """Mark (project_slug, old_slug) as superseded by (project_slug, new_slug)
    and rewrite the old mirror. Caller must have already inserted the
    replacement row via `write_project_memory_row(...)`.
    """
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR
    cur = conn.execute(
        "SELECT 1 FROM memory WHERE project_slug = ? AND slug = ?;",
        (project_slug, new_slug),
    )
    if cur.fetchone() is None:
        raise ValueError(
            f"Cannot supersede ({project_slug!r}, {old_slug!r}) by "
            f"({project_slug!r}, {new_slug!r}): replacement slug not found."
        )

    conn.execute(
        """
        UPDATE memory
        SET status        = 'superseded',
            superseded_by = :new_slug,
            valid_to      = COALESCE(valid_to, datetime('now')),
            updated_at    = datetime('now')
        WHERE project_slug = :project_slug AND slug = :old_slug;
        """,
        {
            "new_slug": new_slug,
            "project_slug": project_slug,
            "old_slug": old_slug,
        },
    )
    conn.commit()

    cur = conn.execute(
        "SELECT * FROM memory WHERE project_slug = ? AND slug = ?;",
        (project_slug, old_slug),
    )
    row = _row_to_dict(cur, cur.fetchone())
    md = _render_project_markdown(row)
    _atomic_write(_mirror_path(mirror_dir, project_slug, old_slug), md)


def export_mirror(
    conn: sqlite3.Connection,
    *,
    project_slug: str,
    slug: str,
    mirror_dir: Path | None = None,
) -> Path:
    """Rewrite the markdown mirror for an existing row from current DB state.
    Useful when a row was written via raw SQL (or the data-migration script)
    and the mirror needs to be backfilled.

    Returns the path written to.
    """
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR
    cur = conn.execute(
        "SELECT * FROM memory WHERE project_slug = ? AND slug = ?;",
        (project_slug, slug),
    )
    row_tuple = cur.fetchone()
    if row_tuple is None:
        raise ValueError(
            f"export_mirror: no row for project_slug={project_slug!r}, slug={slug!r}"
        )
    row = _row_to_dict(cur, row_tuple)
    md = _render_project_markdown(row)
    out = _mirror_path(mirror_dir, project_slug, slug)
    _atomic_write(out, md)
    return out


# ---------------------------------------------------------------------------
# CLI entry point — minimal: `export-mirror` and `list-active`
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projects_memory_io",
        description="projects_memory_io — PKA projects-tier memory helper",
    )
    sub = parser.add_subparsers(dest="command")

    em = sub.add_parser(
        "export-mirror",
        help="Rewrite a project-memory row's markdown mirror from current DB state.",
    )
    em.add_argument("project_slug")
    em.add_argument("slug")
    em.add_argument("--db", default=str(DEFAULT_DB))
    em.add_argument("--mirror-dir", default=str(DEFAULT_MIRROR_DIR))

    la = sub.add_parser("list-active", help="List active projects.")
    la.add_argument("--db", default=str(DEFAULT_DB))

    return parser


def main(argv: list[str]) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "export-mirror":
        conn = sqlite3.connect(args.db)
        try:
            out = export_mirror(
                conn,
                project_slug=args.project_slug,
                slug=args.slug,
                mirror_dir=Path(args.mirror_dir),
            )
            print(f"Mirror written: {out}")
        finally:
            conn.close()
        return 0

    if args.command == "list-active":
        conn = sqlite3.connect(args.db)
        try:
            for p in list_active_projects(conn):
                print(f"{p['slug']:<32} {p['status']:<10} {p['name']}")
        finally:
            conn.close()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
