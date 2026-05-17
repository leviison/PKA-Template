"""
memory_io.py — markdown-mirror helper for the `memory` table.

The DB is authoritative. This module owns the contract from `memory` row
to `memory/<slug>.md` markdown file. All durable writes to the memory
layer should go through `write_memory_row()`; bare `INSERT INTO memory`
will write the row but skip the mirror, which is fine for tests but not
fine for operational writes.

Contract (see deliverable §3 for full spec):
  - INSERT  → also creates `memory/<slug>.md`
  - UPDATE  → also rewrites `memory/<slug>.md` from current DB state
  - DELETE  → leaves the markdown file in place (audit trail); a separate
              `prune_orphans()` helper removes files for rows that no
              longer exist if/when that is desired
  - External edits to `memory/<slug>.md` are NOT automatically synced
    back to the DB. To roundtrip a manual edit, run:
      python3 memory_io.py import <slug>
    which calls `import_markdown()` to parse the file and UPDATE the row.
    The next DB write via `write_memory_row()` will otherwise overwrite
    the file edit.

Import path (markdown → DB):
  - `import_markdown(conn, path_or_slug, mirror_dir)` — parse a single
    markdown file's frontmatter + body and UPSERT the corresponding row.
  - `import_directory(conn, dir_path, mirror_dir)` — walk a directory and
    call import_markdown on every *.md file except MEMORY.md and INDEX.md.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parent / "pka.db"
DEFAULT_MIRROR_DIR = Path(__file__).resolve().parent / "memory"


def _frontmatter(row: dict[str, Any]) -> str:
    """Render the YAML frontmatter for a memory row.

    Fields included are the ones a reader needs to make sense of the file
    without opening the DB: slug, type, scope, status, valid_from/to,
    source_ref, approved_by, provenance, tags, superseded_by, plus the
    ingested/updated timestamps for audit.
    """
    keys = [
        "slug",
        "type",
        "scope",
        "status",
        "source_ref",
        "approved_by",
        "provenance",
        "tags",
        "superseded_by",
        "valid_from",
        "valid_to",
        "ingested_at",
        "updated_at",
    ]
    lines = ["---"]
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        # Slug-safe values only — no multi-line bodies in frontmatter.
        # Defensive: replace embedded newlines/colons in case a future
        # caller puts something weird in tags.
        s = str(v).replace("\n", " ").replace("\r", " ")
        lines.append(f"{k}: {s}")
    lines.append(f"title: {row['title']}")
    lines.append("---")
    return "\n".join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` atomically (tmp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")
        os.replace(tmp, path)
    except Exception:
        # Best-effort cleanup
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _render_markdown(row: dict[str, Any]) -> str:
    fm = _frontmatter(row)
    return f"{fm}\n\n# {row['title']}\n\n{row['body']}\n"


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def write_memory_row(
    conn: sqlite3.Connection,
    *,
    slug: str,
    type: str,
    title: str,
    body: str,
    scope: str,
    provenance: str,
    source_ref: str | None = None,
    status: str = "active",
    superseded_by: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    approved_by: str | None = None,
    tags: str | None = None,
    mirror_dir: Path | None = None,
) -> int:
    """INSERT or UPDATE a memory row by slug, then write the markdown mirror.

    Returns the row's `id`.
    """
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR
    # Upsert by slug. Using INSERT ... ON CONFLICT instead of two queries
    # so the write is a single SQL statement.
    conn.execute(
        """
        INSERT INTO memory (
            slug, type, title, body, scope, source_ref, status,
            superseded_by, valid_from, valid_to, approved_by,
            provenance, tags
        )
        VALUES (
            :slug, :type, :title, :body, :scope, :source_ref, :status,
            :superseded_by,
            COALESCE(:valid_from, datetime('now')),
            :valid_to, :approved_by, :provenance, :tags
        )
        ON CONFLICT(slug) DO UPDATE SET
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
    cur = conn.execute("SELECT * FROM memory WHERE slug = ?;", (slug,))
    row = _row_to_dict(cur, cur.fetchone())
    md = _render_markdown(row)
    _atomic_write(mirror_dir / f"{slug}.md", md)
    return int(row["id"])


def supersede(
    conn: sqlite3.Connection,
    *,
    old_slug: str,
    new_slug: str,
    mirror_dir: Path | None = None,
) -> None:
    """Mark `old_slug` as superseded by `new_slug` and rewrite its mirror.

    Caller is expected to have already inserted the replacement row via
    `write_memory_row(...)`. We don't insert it here — supersession is a
    transition that needs the new row's full content, which only the
    caller has.
    """
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR
    # Verify the replacement exists. The DB's CHECK constraint already
    # requires superseded_by to be non-NULL when status='superseded', but
    # it doesn't verify the slug resolves — do that here.
    cur = conn.execute("SELECT 1 FROM memory WHERE slug = ?;", (new_slug,))
    if cur.fetchone() is None:
        raise ValueError(
            f"Cannot supersede {old_slug!r} by {new_slug!r}: "
            f"replacement slug not found in memory table."
        )
    conn.execute(
        """
        UPDATE memory
        SET status        = 'superseded',
            superseded_by = :new_slug,
            valid_to      = COALESCE(valid_to, datetime('now')),
            updated_at    = datetime('now')
        WHERE slug = :old_slug;
        """,
        {"new_slug": new_slug, "old_slug": old_slug},
    )
    conn.commit()
    cur = conn.execute("SELECT * FROM memory WHERE slug = ?;", (old_slug,))
    row = _row_to_dict(cur, cur.fetchone())
    md = _render_markdown(row)
    _atomic_write(mirror_dir / f"{old_slug}.md", md)


# ---------------------------------------------------------------------------
# Import path: markdown file → DB row
# ---------------------------------------------------------------------------

# Valid enum values (mirrors the CHECK constraints in the schema).
_VALID_TYPES = frozenset(
    ["user_fact", "project", "feedback", "pedagogy", "preference", "pattern_ref", "operational"]
)
_VALID_PROVENANCES = frozenset(["human_confirmed", "leroy_inferred", "model_inferred"])
_VALID_STATUSES = frozenset(["active", "superseded", "deferred", "invalidated"])

_SCOPE_PATTERN = re.compile(
    r"^(global|owner_only|team_member:[a-z][a-z0-9_-]*)$"
)


def _parse_markdown_file(path: Path) -> dict[str, Any]:
    """Parse a memory markdown file (frontmatter + body) into a dict.

    Handles two frontmatter shapes:
      Flat (older):
        ---
        name: user-name
        description: The owner's name is <name>
        type: user_fact
        ---
      Nested (newer):
        ---
        name: feedback-brief-behavior-over-lines
        description: "..."
        metadata:
          node_type: memory
          type: feedback
          originSessionId: ...
        ---

    Returns a dict with keys: name, description, type, body.
    The `type` field is taken from `metadata.type` if present, else the
    top-level `type` field.

    Body is everything after the closing `---`, stripped of leading/trailing
    whitespace, and with a leading `# <any heading>` line removed (render
    artifact from `_render_markdown`).
    """
    text = path.read_text(encoding="utf-8")

    # Extract frontmatter block between the first pair of `---` delimiters.
    # The file may or may not start with `---\n`.
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not fm_match:
        raise ValueError(f"No valid frontmatter block found in {path}")

    fm_raw = fm_match.group(1)
    body_raw = fm_match.group(2)

    # --- Parse frontmatter as simple key: value pairs ---
    # We parse manually rather than importing PyYAML (not in stdlib).
    # The frontmatter is deliberately simple: no lists, no complex nesting
    # beyond the one-level `metadata:` block we need.
    fm: dict[str, Any] = {}
    metadata: dict[str, str] = {}
    in_metadata = False
    for line in fm_raw.splitlines():
        if not line.strip():
            in_metadata = False
            continue
        if line == "metadata:":
            in_metadata = True
            continue
        if in_metadata:
            # Lines under `metadata:` are indented with 2 spaces.
            stripped = line.lstrip()
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                metadata[k.strip()] = v.strip().strip('"').strip("'")
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            # Strip quotes for quoted description values like `description: "..."`.
            fm[k.strip()] = v.strip().strip('"').strip("'")

    # Resolve `type`: nested metadata wins over top-level.
    resolved_type = metadata.get("type") or fm.get("type", "")

    # Resolve `description` and `name`.
    description = fm.get("description", "")
    name = fm.get("name", "")

    # --- Body: strip leading H1 heading if present (render artifact). ---
    body = body_raw.strip()
    body = re.sub(r"^#[^\n]*\n+", "", body).strip()

    return {
        "name": name,
        "description": description,
        "type": resolved_type,
        "body": body,
    }


def import_markdown(
    conn: sqlite3.Connection,
    path_or_slug: str | Path,
    mirror_dir: Path | None = None,
) -> int:
    """Parse a single memory markdown file and UPSERT the corresponding DB row.

    `path_or_slug` may be:
      - A full path to a markdown file (absolute or relative).
      - A bare slug string — resolved to `mirror_dir/<slug>.md`.

    Validates: type, scope (always 'global' for imported files unless the
    frontmatter carries a scope field), and provenance (defaults to
    'human_confirmed'). Raises ValueError on enum violation.

    Returns the resulting row id.
    """
    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR

    path = Path(path_or_slug)
    if not path.suffix:
        # Bare slug — resolve to mirror_dir/<slug>.md
        path = mirror_dir / f"{path}.md"

    if not path.exists():
        raise FileNotFoundError(f"Memory file not found: {path}")

    parsed = _parse_markdown_file(path)

    # Derive slug from filename stem (kebab-case).
    slug = path.stem  # already kebab-case from our convention

    # Derive title: description preferred, fall back to name.
    title = parsed["description"] or parsed["name"] or slug

    # Scope defaults to 'global'; importers can override by extending this
    # function or by pre-setting the field in the parsed dict.
    scope = "global"

    # Provenance defaults to 'human_confirmed' for files imported through
    # this path (the importer assumes the markdown was hand-authored or
    # blessed by the owner — overridable in a wrapper if needed).
    provenance = "human_confirmed"

    # Type validation.
    mem_type = parsed["type"]
    if mem_type not in _VALID_TYPES:
        raise ValueError(
            f"import_markdown: invalid type {mem_type!r} for slug {slug!r}. "
            f"Must be one of: {sorted(_VALID_TYPES)}"
        )

    # Scope validation.
    if not _SCOPE_PATTERN.match(scope):
        raise ValueError(
            f"import_markdown: invalid scope {scope!r} for slug {slug!r}."
        )

    # Provenance validation.
    if provenance not in _VALID_PROVENANCES:
        raise ValueError(
            f"import_markdown: invalid provenance {provenance!r} for slug {slug!r}."
        )

    row_id = write_memory_row(
        conn,
        slug=slug,
        type=mem_type,
        title=title,
        body=parsed["body"],
        scope=scope,
        provenance=provenance,
        mirror_dir=mirror_dir,
    )
    return row_id


def import_directory(
    conn: sqlite3.Connection,
    dir_path: str | Path,
    mirror_dir: Path | None = None,
) -> list[int]:
    """Walk `dir_path` and import every *.md file except MEMORY.md / INDEX.md.

    Returns a list of row ids in deterministic order (sorted by filename).
    Tolerates per-file errors: logs to stderr and continues; returns ids
    of successful imports only.
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"import_directory: {dir_path} is not a directory")

    skip = {"MEMORY.md", "INDEX.md"}
    files = sorted(p for p in dir_path.glob("*.md") if p.name not in skip)

    ids: list[int] = []
    for f in files:
        try:
            row_id = import_markdown(conn, f, mirror_dir=mirror_dir)
            ids.append(row_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[import_directory] SKIP {f.name}: {exc}", file=sys.stderr)

    return ids


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory_io",
        description="memory_io — PKA memory layer helper",
    )
    sub = parser.add_subparsers(dest="command")

    imp = sub.add_parser(
        "import",
        help="Import a markdown file (or directory) into the memory table.",
    )
    imp.add_argument(
        "path",
        help=(
            "Path to a .md file (or bare slug resolved against the default "
            "mirror dir), or a directory of .md files."
        ),
    )
    imp.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"Path to pka.db (default: {DEFAULT_DB})",
    )
    imp.add_argument(
        "--mirror-dir",
        default=str(DEFAULT_MIRROR_DIR),
        help=f"Path to the memory mirror directory (default: {DEFAULT_MIRROR_DIR})",
    )
    return parser


if __name__ == "__main__":
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.command == "import":
        db_path = Path(args.db)
        mirror = Path(args.mirror_dir)
        target = Path(args.path)

        conn = sqlite3.connect(str(db_path))
        try:
            if target.is_dir():
                ids = import_directory(conn, target, mirror_dir=mirror)
                print(f"Imported {len(ids)} file(s): ids {ids}")
            else:
                row_id = import_markdown(conn, target, mirror_dir=mirror)
                print(f"Imported: id={row_id}")
        finally:
            conn.close()
    else:
        parser.print_help()
        sys.exit(0)
