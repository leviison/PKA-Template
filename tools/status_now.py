#!/usr/bin/env python3
"""
status_now.py — PKA In-Flight Status Snapshot

Read-only snapshot of pka.db rendered for a ~40-column tmux pane. Intended
to be polled with `watch` so Levi can keep a corner of the screen showing
what's running across sessions and what just landed.

## Usage

One-time install — keep a tmux pane open with (from the PKA root):

    watch -n 5 python3 tools/status_now.py

Or absolute, replacing <PKA_ROOT> with this repo's installed path:

    watch -n 5 python3 <PKA_ROOT>/tools/status_now.py

The script accepts no arguments and writes nothing. If pka.db cannot be
opened (locked writer, missing file), the script prints the error and
exits 0 so `watch` continues to retry on the next tick rather than
freezing the pane.

## What it shows

- **Open briefs** — every brief in status='open', with assignee, age
  since `created_at`, and the first ~28 characters of the title. Briefs
  are the work commissioned but not yet closed; this is the queue.
- **In-flight deliverables** — open briefs that already have one or
  more deliverable rows. In PKA's lifecycle a deliverable lands before
  Leroy closes the brief, so a row here means "subagent has filed
  output, brief not yet compacted." Useful for spotting handoffs that
  stalled at the close step.
- **Done last 6h** — briefs marked status='complete' with completed_at
  in the last six hours. Glance-target for "what just shipped."
- **Active backlog** — backlog rows in status='active', sorted by
  priority then ref. The standing queue of approved-but-not-yet-briefed
  work.

The 6-hour and 8-row caps are tunable at the constants block near the
top of the file. Edit in place; no config layer.

## Demotion criterion

Event-based. Retire `status_now.py` when **either**:

  (a) PKA grows a native `sessions` table plus a Live viewer tab that
      registers active subagents at dispatch and reads them back —
      i.e., the production-direction-aligned C2 build that this script
      is the cheap-first stand-in for. At that point the watcher's
      information shape is subsumed by a richer surface and the script
      retires cleanly with a single `rm`.

  (b) The brief lifecycle changes such that the columns this script
      reads (briefs.status, briefs.completed_at, deliverables.brief_id,
      backlog.status) no longer carry the semantics this snapshot
      depends on — e.g., briefs become immutable-from-creation with no
      open/complete transition, or deliverables move to a separate
      tier.

If neither condition fires but Levi simply stops opening the pane for
two weeks of active sessions, that's the silent-erosion signal — flag
to Leroy at the next session open and reconfirm the script earns its
keep, per the periodic-revisit clause in CLAUDE.md productization
discipline.

The write/read split does not apply here: this tool has no write path
and produces no historical data that would need to remain interpretable
after the read path retires. Single retirement event, clean delete.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# -------- tunables --------

WIDTH = 40
DONE_WINDOW_HOURS = 6
MAX_OPEN_BRIEFS = 10
MAX_DONE_BRIEFS = 8
MAX_BACKLOG = 8
MAX_INFLIGHT = 8
TITLE_BUDGET = 28  # chars of title shown per row

# Resolve pka.db relative to this script so the watcher works regardless
# of the cwd `watch` was launched from.
DB_PATH = Path(__file__).resolve().parent.parent / "pka.db"


# -------- helpers --------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_db_ts(s: str | None) -> datetime | None:
    """SQLite datetime('now') stores UTC as 'YYYY-MM-DD HH:MM:SS' with no tz.

    Treat as UTC so age math against datetime.now(timezone.utc) is correct.
    Return None on parse failure rather than raising — a bad timestamp
    should degrade gracefully, not blank the pane.
    """
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _fmt_age(then: datetime | None, now: datetime) -> str:
    """Short human age — '3m', '2h12m', '4d', or '?' on parse failure.

    Goal is fixed-ish width that scans at a glance from a corner pane.
    Negative deltas (clock skew) render as '0m' rather than negative
    numbers, which would look like a bug.
    """
    if then is None:
        return "?"
    delta = now - then
    secs = int(delta.total_seconds())
    if secs < 0:
        return "0m"
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    rem_min = mins % 60
    if hours < 24:
        return f"{hours}h{rem_min:02d}m"
    days = hours // 24
    return f"{days}d"


def _truncate(s: str, n: int) -> str:
    """Truncate with an ellipsis marker. n includes the marker character."""
    if s is None:
        return ""
    s = s.replace("\n", " ").replace("\r", " ").strip()
    if len(s) <= n:
        return s
    if n <= 1:
        return s[:n]
    return s[: n - 1] + "…"  # single-char ellipsis


def _hr() -> str:
    return "─" * WIDTH  # box-drawing horizontal


# -------- queries --------


def _open_briefs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT brief_ref, assigned_to, title, created_at
        FROM briefs
        WHERE status = 'open'
        ORDER BY created_at ASC
        """
    ).fetchall()


def _inflight_deliverables(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Deliverable rows whose parent brief is still open.

    Semantics: in PKA the deliverable lands BEFORE Leroy marks the brief
    complete. A row here therefore means a subagent has filed output but
    the brief hasn't been closed — either work-in-progress (Leroy will
    close imminently) or a handoff that stalled at the close step.
    Either way, Levi wants to see it from a glance.
    """
    return conn.execute(
        """
        SELECT d.id, d.brief_id, d.created_by, d.file_path, d.created_at,
               b.brief_ref, b.assigned_to, b.title
        FROM deliverables d
        JOIN briefs b ON b.id = d.brief_id
        WHERE b.status = 'open'
        ORDER BY d.created_at DESC
        """
    ).fetchall()


def _recent_done(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Briefs completed within the DONE_WINDOW_HOURS window.

    Ordered most-recent-first so the freshest landings sit at the top
    of the block where the eye lands.
    """
    return conn.execute(
        f"""
        SELECT brief_ref, assigned_to, title, completed_at
        FROM briefs
        WHERE status = 'complete'
          AND completed_at IS NOT NULL
          AND completed_at > datetime('now', '-{DONE_WINDOW_HOURS} hours')
        ORDER BY completed_at DESC
        """
    ).fetchall()


def _active_backlog(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ref, title, priority
        FROM backlog
        WHERE status = 'active'
        ORDER BY priority ASC, ref ASC
        """
    ).fetchall()


# -------- rendering --------


def _render_open_briefs(rows: list[sqlite3.Row], now: datetime) -> list[str]:
    out = [f"OPEN BRIEFS ({len(rows)})"]
    if not rows:
        out.append("  (none open)")
        return out
    shown = rows[:MAX_OPEN_BRIEFS]
    for r in shown:
        age = _fmt_age(_parse_db_ts(r["created_at"]), now)
        # First line: ref / assignee / age — keep the structural bits
        # left-aligned so the eye can scan a column of refs.
        ref = r["brief_ref"] or "(no-ref)"
        who = (r["assigned_to"] or "?")[:8]
        out.append(f"  {ref:<10} {who:<8} {age:>6}")
        # Indented title line.
        out.append(f"    {_truncate(r['title'] or '', TITLE_BUDGET)}")
    if len(rows) > len(shown):
        out.append(f"  + {len(rows) - len(shown)} more")
    return out


def _render_inflight(rows: list[sqlite3.Row], now: datetime) -> list[str]:
    out = [f"IN-FLIGHT DELIVERABLES ({len(rows)})"]
    if not rows:
        out.append("  (none — no filed deliverables")
        out.append("   on open briefs)")
        return out
    shown = rows[:MAX_INFLIGHT]
    for r in shown:
        age = _fmt_age(_parse_db_ts(r["created_at"]), now)
        ref = r["brief_ref"] or "(no-ref)"
        who = (r["created_by"] or "?")[:8]
        out.append(f"  {ref:<10} {who:<8} {age:>6}")
        # Show file basename rather than full path — the path is long
        # and the basename is what disambiguates one deliverable from
        # another at a glance.
        fname = os.path.basename(r["file_path"] or "")
        out.append(f"    {_truncate(fname, TITLE_BUDGET)}")
    if len(rows) > len(shown):
        out.append(f"  + {len(rows) - len(shown)} more")
    return out


def _render_done(rows: list[sqlite3.Row], now: datetime) -> list[str]:
    out = [f"DONE LAST {DONE_WINDOW_HOURS}H ({len(rows)})"]
    if not rows:
        out.append("  (nothing landed)")
        return out
    shown = rows[:MAX_DONE_BRIEFS]
    for r in shown:
        age = _fmt_age(_parse_db_ts(r["completed_at"]), now)
        ref = r["brief_ref"] or "(no-ref)"
        who = (r["assigned_to"] or "?")[:8]
        out.append(f"  {ref:<10} {who:<8} {age:>6}")
        out.append(f"    {_truncate(r['title'] or '', TITLE_BUDGET)}")
    if len(rows) > len(shown):
        out.append(f"  + {len(rows) - len(shown)} more")
    return out


def _render_backlog(rows: list[sqlite3.Row]) -> list[str]:
    out = [f"ACTIVE BACKLOG ({len(rows)})"]
    if not rows:
        out.append("  (empty)")
        return out
    shown = rows[:MAX_BACKLOG]
    for r in shown:
        # Priority is an int; display as P1/P2/etc. P1 is highest.
        prio = f"P{r['priority']}"
        ref = r["ref"] or "(no-ref)"
        # Backlog refs are wider (e.g. BACKLOG-058) so the title budget
        # shrinks slightly to keep the line under WIDTH.
        # Width budget: 2 leading spaces + "P{n}" (2) + space + ref padded
        # to 12 + space = 18 chars of structure, leaving WIDTH - 19 for the
        # title so the row stays at or under WIDTH including the ellipsis.
        out.append(f"  {prio} {ref:<12} {_truncate(r['title'] or '', WIDTH - 19)}")
    if len(rows) > len(shown):
        out.append(f"  + {len(rows) - len(shown)} more")
    return out


def _render(conn: sqlite3.Connection) -> str:
    now = _now_utc()
    # Local-time header so the pane shows wall-clock time Levi recognises
    # rather than UTC, while age math stays UTC-correct internally.
    local_now = datetime.now().strftime("%H:%M:%S")

    sections: list[list[str]] = [
        [f"PKA STATUS · {local_now}", _hr()],
        _render_open_briefs(_open_briefs(conn), now),
        [""],
        _render_inflight(_inflight_deliverables(conn), now),
        [""],
        _render_done(_recent_done(conn), now),
        [""],
        _render_backlog(_active_backlog(conn)),
        [_hr(), "read-only · watch -n 5"],
    ]

    lines: list[str] = []
    for sec in sections:
        lines.extend(sec)
    return "\n".join(lines)


# -------- entrypoint --------


def main() -> int:
    if not DB_PATH.exists():
        # Don't crash watch — print a one-liner and exit 0.
        print(f"PKA STATUS\n{_hr()}\npka.db not found at {DB_PATH}")
        return 0
    try:
        # Open read-only via URI so a concurrent writer never blocks the
        # pane. SQLite read-only mode also makes the read-only constraint
        # in the brief mechanically enforced, not just convention.
        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro", uri=True, timeout=2.0
        )
        conn.row_factory = sqlite3.Row
        try:
            print(_render(conn))
        finally:
            conn.close()
    except sqlite3.Error as e:
        # A locked DB or transient I/O error should display the error,
        # not crash the watcher loop. The next tick will retry.
        print(f"PKA STATUS\n{_hr()}\nDB error: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
