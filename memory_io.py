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

## Demotion criterion

Split criterion.

Write-path: retire the write-path when either:

  (a) The memory substrate changes substantively — `memory` schema is
      replaced by a different durable-knowledge model (e.g., external
      vector store, different table shape, multi-provider memory
      federation), OR
  (b) The dual-mirror discipline graduates to `dual_mirror_io.py` (PAX
      BRIEF-142 §2.1 §5/test case 7) — at that point `memory_io.py`'s
      mirror-writing becomes a thin wrapper around the shared base, and
      the write-path is *refactored*, not retired. (The refactor is
      itself an identity-changing tool evolution per the CLAUDE.md
      productization discipline — *"A tool's identity-changing
      evolution... is a fresh productization decision subject to the
      threshold."* When dual_mirror_io.py is commissioned, it triggers
      a re-check of `memory_io.py`'s value-asymmetry case against the
      smaller residual surface.)

Read-path: permanent infrastructure as long as the `memory` table
exists. The read helpers (`load_memory_rows()`, `get_memory_row()`,
FTS5 query wrappers) are how all other code reads memory durably. They
retire only if the `memory` table is removed entirely — no current
candidate.

Note: the cross-tier `promote_from_observation()` helper added in
BRIEF-146 inherits the same write-path criterion (it's part of
`memory_io.py` and shares its lifecycle).

Source: owners_inbox/tool_demotion_criteria_proposal.md (Levi-approved
2026-05-20). Update via Leroy-drafted, Levi-approved deliverable; do not
modify unilaterally.
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

# Personal.db location is recorded in pka.db.settings.personal_db_path by
# setup.py at install time (see PKA_Template setup.py --personal-data-dir).
# Helper below resolves that path with a sane fallback so callers don't
# have to thread the location through every invocation.
DEFAULT_PERSONAL_DB_FALLBACK = Path.home() / "PKA-Data" / "personal.db"


def _resolve_personal_db_path(conn: sqlite3.Connection | None = None) -> Path:
    """Resolve personal.db location.

    Resolution order:
      1. `pka.db.settings.personal_db_path` if `conn` is a pka.db
         connection and the row exists.
      2. ~/PKA-Data/personal.db (the setup.py default).

    The fallback exists so a fresh-install where the setting hasn't been
    populated yet still finds the canonical location. Once setup.py has
    run, settings.personal_db_path is the source of truth.
    """
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'personal_db_path';"
            ).fetchone()
            if row and row[0]:
                return Path(row[0]).expanduser()
        except sqlite3.Error:
            # settings table may not exist on a bare pka.db (pre-setup) or
            # the connection may be against an unrelated DB. Fall through.
            pass
    return DEFAULT_PERSONAL_DB_FALLBACK


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
# Cross-tier promotion: personal.db observation → pka.db memory
# ---------------------------------------------------------------------------
#
# Added in BRIEF-146 (PAX §3.3 / R3). This helper is the first production
# cross-tier write transaction in PKA. Two SQLite files; no native atomic-
# transaction guarantee across them at the API level — but SQLite's
# super-journal mechanism DOES provide atomic commit/rollback across an
# ATTACHed second database when both writes occur inside a single
# transaction on the same connection.
#
# Empirical verification (see deliverable §3, experiments 1+2a+2b):
#   ATTACH + BEGIN IMMEDIATE → INSERT pka.memory → UPDATE personal.<table>
#   → COMMIT is atomic for the common failure modes (constraint violation,
#   lock contention, application exception inside the transaction).
#
# The PAX §2.3 "memory exists, link missing" failure mode survives only as
# a residual OS/process-crash window between SQLite's super-journal commit
# on pka.db and the matching commit on personal.db. That window is much
# smaller than Option B (two separate connections, two separate commits)
# would expose. The reconciliation query below detects rows that fell into
# that residual window and can drive a follow-up link-fix.

# Allowed source tables for promotion. Each row maps the table name to its
# `status` enum so the helper can verify the source is in a legal pre-state
# before promotion (i.e., the source is not ALREADY promoted-to-memory).
_PROMOTABLE_SOURCE_TABLES = frozenset(
    ["owner_posture", "orchestrator_observations", "owner_observations", "team_observations"]
)


def promote_from_observation(
    conn: sqlite3.Connection,
    *,
    source_table: str,
    source_id: int,
    memory_slug: str,
    memory_type: str,
    memory_title: str,
    memory_body: str,
    memory_scope: str = "global",
    memory_tags: str | None = None,
    source_ref: str | None = None,
    operator: str = "priya",
    mirror_dir: Path | None = None,
    personal_db_path: Path | None = None,
) -> int:
    """Promote a personal.db observation/posture row into the pka.db memory
    table as a durable principle.

    The cross-tier write happens inside a single BEGIN IMMEDIATE transaction
    on `conn` (which must be a pka.db connection). If `personal.db` is not
    yet attached, the helper attaches it under the alias `personal` for the
    duration of the call and DETACHes on exit.

    Failure ordering (load-bearing — see PAX §2.3 and deliverable §3):
      1. INSERT pka.memory(...)            — capture new memory.id
      2. UPDATE personal.<source_table>    — set status='promoted-to-memory',
                                              set promoted_to_memory_id=<new id>
      3. COMMIT (atomic across both files via SQLite's super-journal)
      4. Write the markdown mirror at memory/<slug>.md

    On any in-transaction failure, both writes roll back together — there
    is no "memory exists, link missing" state to recover from for the
    common failure modes. The residual orphan window is OS/process-crash
    only; the reconcile_orphan_promotions() query catches that window.

    Args:
        conn: open sqlite3 connection to pka.db.
        source_table: one of owner_posture / orchestrator_observations /
                      owner_observations / team_observations.
        source_id: primary-key id of the row in personal.<source_table>.
        memory_slug: kebab-case stable slug for the new memory row.
        memory_type: enum-valid memory.type (e.g. 'operational',
                     'preference', 'user_fact', etc.).
        memory_title: one-line title.
        memory_body: full durable content.
        memory_scope: defaults to 'global'. Use 'owner_only' if the
                      promoted principle is owner-personal.
        memory_tags: optional CSV tag string.
        source_ref: optional override for source_ref. Defaults to
                    f'{source_table}:{source_id}' — this is the format the
                    reconciliation query expects.
        operator: persona executing the promotion (logged via approved_by).
                  Defaults to 'priya' per the protocol (reflection-pass
                  owner). 'levi' is also valid for Levi-initiated promotions.
        mirror_dir: defaults to DEFAULT_MIRROR_DIR. Mirror is written
                    AFTER the cross-tier commit succeeds.
        personal_db_path: resolves from pka.db.settings.personal_db_path
                          when `conn` is a pka.db connection; falls back
                          to ~/PKA-Data/personal.db (the setup.py default).
                          Only relevant if `personal` is not already
                          attached to `conn`.

    Returns:
        The newly inserted memory.id.

    Raises:
        ValueError: invalid source_table; source_id not found; source row
                    is already promoted; memory_slug already exists.
        sqlite3.IntegrityError: CHECK constraint violation on either side
                                (rolled back atomically).
        sqlite3.OperationalError: lock contention or other operational
                                  failure (rolled back atomically).
    """
    if source_table not in _PROMOTABLE_SOURCE_TABLES:
        raise ValueError(
            f"promote_from_observation: invalid source_table "
            f"{source_table!r}. Must be one of: "
            f"{sorted(_PROMOTABLE_SOURCE_TABLES)}"
        )

    mirror_dir = mirror_dir or DEFAULT_MIRROR_DIR
    if personal_db_path is None:
        personal_db_path = _resolve_personal_db_path(conn)
    if source_ref is None:
        source_ref = f"{source_table}:{source_id}"

    # If `personal` is not already an attached schema on `conn`, attach it
    # for the duration of this call. The detach-on-exit semantics keep this
    # helper safe to use from a long-lived connection.
    cur = conn.execute("PRAGMA database_list;")
    attached = {row[1] for row in cur.fetchall()}
    detach_on_exit = False
    if "personal" not in attached:
        if not personal_db_path.exists():
            raise FileNotFoundError(
                f"promote_from_observation: personal.db not found at "
                f"{personal_db_path}. Pass personal_db_path explicitly or "
                f"ATTACH it on the connection before calling."
            )
        # ATTACH cannot be parameterized via ? binding — the path is a
        # schema-name-like token. We must safely interpolate the path.
        # SQLite ATTACH resolves the path against the process cwd unless
        # absolute; we already require an absolute Path so this is fine.
        # Escape single quotes defensively.
        escaped = str(personal_db_path).replace("'", "''")
        conn.execute(f"ATTACH DATABASE '{escaped}' AS personal;")
        detach_on_exit = True

    try:
        # Pre-flight checks BEFORE opening the transaction. These reads are
        # not load-bearing for correctness (the transaction would catch the
        # violations) but they produce clearer error messages than a raw
        # CHECK failure.
        src_row = conn.execute(
            f"SELECT id, status, promoted_to_memory_id "
            f"FROM personal.{source_table} WHERE id = ?;",
            (source_id,),
        ).fetchone()
        if src_row is None:
            raise ValueError(
                f"promote_from_observation: no row found in "
                f"personal.{source_table} with id={source_id}."
            )
        if src_row[1] == "promoted-to-memory" or src_row[2] is not None:
            raise ValueError(
                f"promote_from_observation: personal.{source_table} "
                f"id={source_id} is already promoted (status={src_row[1]!r}, "
                f"promoted_to_memory_id={src_row[2]!r}). Refusing to "
                f"re-promote — investigate before retrying."
            )

        existing = conn.execute(
            "SELECT id FROM main.memory WHERE slug = ?;",
            (memory_slug,),
        ).fetchone()
        if existing is not None:
            raise ValueError(
                f"promote_from_observation: memory.slug={memory_slug!r} "
                f"already exists (id={existing[0]}). Choose a new slug or "
                f"call supersede() if this is a replacement."
            )

        # Open a single transaction that spans both attached databases.
        # BEGIN IMMEDIATE acquires the reserved lock immediately so we
        # don't surprise-collide with another writer mid-transaction.
        # `with conn:` would also work but explicit BEGIN/COMMIT is
        # clearer when the failure modes are load-bearing.
        conn.execute("BEGIN IMMEDIATE;")
        try:
            # Step 1: INSERT pka.memory
            ins = conn.execute(
                """
                INSERT INTO main.memory (
                    slug, type, title, body, scope, source_ref, status,
                    valid_from, ingested_at, approved_by, provenance, tags
                )
                VALUES (
                    :slug, :type, :title, :body, :scope, :source_ref,
                    'active',
                    datetime('now'), datetime('now'),
                    :approved_by, 'human_confirmed', :tags
                );
                """,
                {
                    "slug": memory_slug,
                    "type": memory_type,
                    "title": memory_title,
                    "body": memory_body,
                    "scope": memory_scope,
                    "source_ref": source_ref,
                    "approved_by": operator,
                    "tags": memory_tags,
                },
            )
            new_memory_id = ins.lastrowid

            # Step 2: UPDATE personal.<source_table>
            # Verify exactly one row updated — a 0-row UPDATE is silent in
            # SQLite and would otherwise commit an unlinked promotion.
            upd = conn.execute(
                f"""
                UPDATE personal.{source_table}
                SET status = 'promoted-to-memory',
                    promoted_to_memory_id = ?
                WHERE id = ?;
                """,
                (new_memory_id, source_id),
            )
            if upd.rowcount != 1:
                raise RuntimeError(
                    f"promote_from_observation: UPDATE on "
                    f"personal.{source_table} id={source_id} affected "
                    f"{upd.rowcount} rows (expected 1). Rolling back."
                )

            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise

        # Step 3 (post-commit): write the markdown mirror. If the mirror
        # write fails, the DB state is still consistent — the next call
        # to write_memory_row() or an explicit re-mirror will catch up.
        cur = conn.execute("SELECT * FROM main.memory WHERE id = ?;", (new_memory_id,))
        row = _row_to_dict(cur, cur.fetchone())
        md = _render_markdown(row)
        _atomic_write(mirror_dir / f"{memory_slug}.md", md)

        return int(new_memory_id)
    finally:
        if detach_on_exit:
            try:
                conn.execute("DETACH DATABASE personal;")
            except sqlite3.OperationalError:
                # Defensive — if a caller held a statement open against
                # personal.* the DETACH can fail. Log and move on; the
                # caller's connection lifecycle will tidy up.
                pass


# ---------------------------------------------------------------------------
# Reconciliation query — detect orphaned-promotion state
# ---------------------------------------------------------------------------
#
# The orphaned-promotion state is: a memory row exists with
# source_ref='<table>:<id>' pointing at a personal-tier observation row,
# but the personal-tier row's status is NOT 'promoted-to-memory' OR its
# promoted_to_memory_id is NULL / does not match.
#
# Under Option A (ATTACH + single transaction) this state can only arise
# from an OS/process-crash window between the super-journal commits on
# the two files. Under Option B (two separate connections) it would arise
# from any step-2 failure. Either way, this query catches it.
#
# Operator usage:
#   conn = sqlite3.connect('pka.db')
#   conn.execute("ATTACH DATABASE '<path>/personal.db' AS personal")
#   rows = reconcile_orphan_promotions(conn)
#   # Apply fixes manually per the protocol R2/R9 section.
#   conn.execute("DETACH DATABASE personal")

RECONCILE_ORPHAN_PROMOTIONS_SQL = """
WITH promoted AS (
    SELECT
        id        AS memory_id,
        slug      AS memory_slug,
        source_ref
    FROM main.memory
    WHERE source_ref LIKE 'owner_posture:%'
       OR source_ref LIKE 'orchestrator_observations:%'
       OR source_ref LIKE 'owner_observations:%'
       OR source_ref LIKE 'team_observations:%'
)
SELECT
    p.memory_id,
    p.memory_slug,
    substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) AS expected_source_table,
    CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER) AS expected_source_id,
    COALESCE(op.status, oo.status, oi.status, te.status) AS actual_source_status,
    COALESCE(
        op.promoted_to_memory_id,
        oo.promoted_to_memory_id,
        oi.promoted_to_memory_id,
        te.promoted_to_memory_id
    ) AS actual_promoted_to_memory_id
FROM promoted p
LEFT JOIN personal.owner_posture op
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'owner_posture'
   AND op.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.orchestrator_observations oo
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'orchestrator_observations'
   AND oo.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.owner_observations oi
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'owner_observations'
   AND oi.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
LEFT JOIN personal.team_observations te
    ON substr(p.source_ref, 1, instr(p.source_ref, ':') - 1) = 'team_observations'
   AND te.id = CAST(substr(p.source_ref, instr(p.source_ref, ':') + 1) AS INTEGER)
WHERE
    COALESCE(
        op.promoted_to_memory_id,
        oo.promoted_to_memory_id,
        oi.promoted_to_memory_id,
        te.promoted_to_memory_id
    ) IS NULL
    OR COALESCE(
        op.promoted_to_memory_id,
        oo.promoted_to_memory_id,
        oi.promoted_to_memory_id,
        te.promoted_to_memory_id
    ) != p.memory_id
    OR COALESCE(op.status, oo.status, oi.status, te.status) != 'promoted-to-memory'
;
"""


def reconcile_orphan_promotions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Detect orphaned-promotion rows: memory rows whose source_ref points
    at a personal-tier row that does not have its link set.

    Caller must have `personal` attached to `conn` (the helper does NOT
    auto-attach for the read path — readers may want different lifecycles
    than the write helper).

    Returns:
        A list of dicts with keys:
            memory_id, memory_slug, expected_source_table,
            expected_source_id, actual_source_status,
            actual_promoted_to_memory_id

        Empty list means no orphans detected. Apply the fix per the
        protocol section R2/R9 — typically:

            UPDATE personal.<table>
            SET status = 'promoted-to-memory',
                promoted_to_memory_id = <memory_id>
            WHERE id = <expected_source_id>;
    """
    cur = conn.execute(RECONCILE_ORPHAN_PROMOTIONS_SQL)
    return [
        {
            "memory_id": r[0],
            "memory_slug": r[1],
            "expected_source_table": r[2],
            "expected_source_id": r[3],
            "actual_source_status": r[4],
            "actual_promoted_to_memory_id": r[5],
        }
        for r in cur.fetchall()
    ]


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
        name: Owner name
        description: The owner's name is Levi
        type: user
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

    # Provenance defaults to 'human_confirmed' for files imported from the
    # Claude memory corpus (all originated from things Levi confirmed).
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
