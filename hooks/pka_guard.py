#!/usr/bin/env python3
"""
pka_guard.py — Claude Code hook handler for PKA cross-session safety.

Registered against `SessionStart`, `PreToolUse`, `Stop`, and `SubagentStop`
in `~/.claude/settings.json`. Prevents the three cross-session pain events
observed on 2026-05-22:

  1. BRIEF-189 surprise — another instance commissioned a brief while this
     one was offline. `SessionStart` surfaces foreign-session and recent
     open-brief context as informational additionalContext.
  2. BRIEF-191 collision — both instances tried to write the same
     `brief_ref`. `PreToolUse` on Write/Edit against `team_comms/brief_*.md`
     blocks with the next-free brief_ref suggested in the rejection
     message.
  3. Accidental `mv`/`rm` during collision recovery clobbering a peer
     session's file. `PreToolUse` on Bash with mv/rm/cp/dd targeting
     `team_comms/brief_*.md` blocks unless this session has claimed the
     ref (or is operating on a closed/archived brief).

## Trust boundary (per Mara's BRIEF-194 framing)

- Local-only. No network egress, no daemon, no auth surface.
- Runs as the user. Reads pka.db read-only (URI mode=ro).
- Session state lives on the filesystem at `tools/.sessions/<pid>.json` —
  NOT in pka.db. Hooks never write durable state to pka.db.
- Fast. <50ms typical for PreToolUse: one sqlite open + one indexed query
  + one regex match. Heavy checks live in SessionStart, not PreToolUse.

## Hook events handled

| Event           | Purpose                                                       |
|-----------------|---------------------------------------------------------------|
| SessionStart    | Register session, surface foreign sessions + recent briefs    |
| PreToolUse      | Block colliding brief writes, block mv/rm of peer brief files |
| Stop            | Clear this session's registration file                        |
| SubagentStop    | Clear this session's registration file                        |

All output conforms to the Claude Code hooks JSON contract:
- SessionStart returns `hookSpecificOutput.additionalContext` as
  informational text injected into the model's context.
- PreToolUse returns `hookSpecificOutput.permissionDecision = "deny"`
  with `permissionDecisionReason` to block-with-message.
- Stop / SubagentStop exit silently (exit 0, no JSON).

## Demotion criterion (per CLAUDE.md productization discipline)

Event-based. Retire `hooks/pka_guard.py` when **either**:

  (a) PKA grows a native `sessions` table plus a dispatch-time session
      registration mechanism — the C2-tier build that Mara's BRIEF-194
      named as the rule-of-three-pending C2 substrate. At that point a
      single shared substrate replaces the filesystem-based session
      registration, and the brief-collision check should live in the
      dispatch layer (Leroy's brief writer) rather than in a hook
      intercepting the file-write. The hook retires; `pka.db`'s
      `briefs.brief_ref` UNIQUE constraint plus dispatch-time allocation
      carries the load.

  (b) Claude Code ships native cross-session locking or a brief/task
      ownership primitive that subsumes the protections this hook
      provides — i.e., the harness solves the problem we built this for.

Silent-erosion check: if neither event fires but the three pain classes
this hook prevents stop occurring even when it's disabled for a session,
that's the signal to retire it. Per the periodic-revisit clause, the
"would we build this today?" question fires at the next Session Open
quarterly checkpoint.

Write/read split does not apply: this tool produces no historical data.
Single retirement event, clean `rm hooks/pka_guard.py` plus a
`~/.claude/settings.json` edit removing the hook block.

## Installation

See `owners_inbox/pka_guard_rowan.md` for the `~/.claude/settings.json`
edit Levi applies. The hook is a no-op until that registration lands.

## Failure mode

If anything in this script raises, it must NOT block tool use — better
to let the user proceed without protection than to deadlock the harness.
The top-level handler catches all exceptions and exits 0 with no JSON,
which the harness treats as "no opinion from the hook."
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# -------- paths --------

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "pka.db"
SESSIONS_DIR = REPO_ROOT / "tools" / ".sessions"
TEAM_COMMS = REPO_ROOT / "team_comms"
ARCHIVE_TEAM_COMMS = REPO_ROOT / "archive" / "team_comms"

# -------- tunables --------

# SessionStart surfaces briefs created in this window if status='open'.
RECENT_BRIEF_HOURS = 24

# A session's registration file is considered "stale" (and therefore
# safe to ignore on SessionStart) after this many hours. Protects against
# Stop/SubagentStop never firing — e.g., a terminal kill -9.
SESSION_STALE_HOURS = 12

# Hard ceiling on registered foreign-session count surfaced in
# additionalContext — defensive against a dir full of stale files.
MAX_FOREIGN_SESSIONS_SURFACED = 5

# brief_ref pattern. Matches both the canonical "BRIEF-NNN" form in
# pka.db and the snake_case "brief_NNN.md" form on disk.
BRIEF_REF_RE = re.compile(r"BRIEF-(\d+)", re.IGNORECASE)
BRIEF_FILE_RE = re.compile(r"brief_(\d+)\.md$", re.IGNORECASE)

# Bash commands we treat as "writes" against team_comms/brief_*.md.
# Order matters only for clarity — the check is membership in this set.
MUTATING_BASH_VERBS = {"mv", "rm", "cp", "dd", "tee", ">", ">>"}


# -------- session registration (filesystem) --------


def _session_id_from_event(event: dict) -> str:
    """Stable identifier for this Claude Code session.

    Prefer the harness-provided `session_id` (stable across the session
    lifecycle and across subagent dispatches within it). Fall back to
    pid if absent — older harness versions or test contexts may not
    pass session_id.
    """
    sid = event.get("session_id")
    if sid:
        return str(sid)
    return f"pid-{os.getpid()}"


def _session_file(session_id: str) -> Path:
    # Sanitize: session_id should be alnum + dash + underscore only.
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", session_id)
    return SESSIONS_DIR / f"{safe}.json"


def _register_session(event: dict) -> None:
    """Write this session's registration file.

    Body captures session_id, pid, cwd, started_at, source (startup vs
    resume vs compact), and a `claimed_brief_refs` list which the
    PreToolUse handler can populate when the session writes a brief.
    The file is small (<1KB) and rewritten on every claim — race-free
    enough for two sessions; not a substitute for a real lock.
    """
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_id = _session_id_from_event(event)
    body = {
        "session_id": session_id,
        "pid": os.getpid(),
        "cwd": event.get("cwd") or os.getcwd(),
        "source": event.get("source"),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claimed_brief_refs": [],
    }
    _session_file(session_id).write_text(json.dumps(body, indent=2))


def _read_session(session_id: str) -> dict | None:
    p = _session_file(session_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _claim_brief_ref(session_id: str, brief_ref: str) -> None:
    """Append brief_ref to this session's claimed list.

    Best-effort — if the file is missing (Stop fired prematurely), we
    quietly skip. The downstream check is conservative: if a session
    isn't registered, every brief looks foreign, which biases toward
    blocking rather than collision.
    """
    body = _read_session(session_id)
    if body is None:
        return
    refs = set(body.get("claimed_brief_refs", []))
    refs.add(brief_ref.upper())
    body["claimed_brief_refs"] = sorted(refs)
    try:
        _session_file(session_id).write_text(json.dumps(body, indent=2))
    except OSError:
        pass


def _clear_session(event: dict) -> None:
    session_id = _session_id_from_event(event)
    p = _session_file(session_id)
    try:
        if p.exists():
            p.unlink()
    except OSError:
        pass


def _foreign_sessions(my_session_id: str) -> list[dict]:
    """List other sessions' registration files that are not stale.

    Stale = older than SESSION_STALE_HOURS. Stale files are surfaced
    NOT as foreign sessions but as a separate diagnostic — the user
    may want to clean them up.
    """
    if not SESSIONS_DIR.exists():
        return []
    out: list[dict] = []
    now = datetime.now(timezone.utc)
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            body = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if body.get("session_id") == my_session_id:
            continue
        started = body.get("started_at")
        age_hours = None
        if started:
            try:
                started_dt = datetime.fromisoformat(started)
                age_hours = (now - started_dt).total_seconds() / 3600.0
            except ValueError:
                age_hours = None
        if age_hours is not None and age_hours > SESSION_STALE_HOURS:
            continue
        out.append(body)
    return out


# -------- pka.db read-only access --------


def _open_db() -> sqlite3.Connection | None:
    """Open pka.db read-only, with a short timeout so the hook never
    deadlocks behind a writer. Returns None if the DB is unreachable —
    the hook must still let tool calls through in that case (fail-open).
    """
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(
            f"file:{DB_PATH}?mode=ro", uri=True, timeout=1.0
        )
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None


def _brief_exists(conn: sqlite3.Connection, brief_ref: str) -> dict | None:
    """Return the brief row if `brief_ref` is present in pka.db, else None.

    Used to detect whether a write target collides with an existing brief.
    """
    row = conn.execute(
        "SELECT id, brief_ref, assigned_to, status, title, created_at FROM briefs WHERE brief_ref = ?",
        (brief_ref,),
    ).fetchone()
    return dict(row) if row else None


def _next_free_brief_ref(conn: sqlite3.Connection) -> str:
    """Compute the next free BRIEF-NNN ref.

    Reads the max numeric component of `briefs.brief_ref` and adds one.
    Matches what a careful Leroy would do at brief-allocation time; the
    hook surfaces this in its rejection message so the caller can
    redirect without a second round-trip.
    """
    rows = conn.execute(
        "SELECT brief_ref FROM briefs WHERE brief_ref LIKE 'BRIEF-%'"
    ).fetchall()
    max_n = 0
    for r in rows:
        m = BRIEF_REF_RE.match(r["brief_ref"] or "")
        if m:
            try:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
            except ValueError:
                continue
    return f"BRIEF-{max_n + 1:03d}"


def _recent_open_briefs(conn: sqlite3.Connection, hours: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT brief_ref, assigned_to, title, created_at
        FROM briefs
        WHERE status = 'open'
          AND created_at > datetime('now', '-{int(hours)} hours')
        ORDER BY created_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


# -------- path / command parsing --------


def _brief_ref_from_path(path: str | None) -> str | None:
    """Extract canonical BRIEF-NNN from a file path that looks like a
    team_comms brief file.

    Returns the canonical form even if the path is lowercase snake_case
    (`brief_191.md` → `BRIEF-191`). Callers compare against pka.db
    which stores the canonical form.
    """
    if not path:
        return None
    m = BRIEF_FILE_RE.search(path)
    if m:
        try:
            n = int(m.group(1))
            return f"BRIEF-{n:03d}" if n < 1000 else f"BRIEF-{n}"
        except ValueError:
            return None
    return None


def _is_team_comms_brief_path(path: str | None) -> bool:
    """True if the path is a brief_*.md file under team_comms/ or its
    archive. Only those paths are subject to collision protection;
    other paths under team_comms/ (rare today, possible tomorrow) pass
    through.
    """
    if not path:
        return False
    p = Path(path)
    if not p.is_absolute():
        # Resolve relative to cwd if necessary — Claude Code usually
        # passes absolute paths, but defensive.
        p = (Path.cwd() / p).resolve()
    try:
        rel = p.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return (
        rel.parts[:1] == ("team_comms",) and BRIEF_FILE_RE.search(rel.name) is not None
    ) or (
        rel.parts[:2] == ("archive", "team_comms")
        and BRIEF_FILE_RE.search(rel.name) is not None
    )


def _bash_brief_targets(command: str) -> list[tuple[str, str]]:
    """Inspect a Bash command for mv/rm/cp/dd/redirection targeting
    team_comms/brief_*.md files.

    Returns list of (verb, path) tuples. Paths are returned as-written
    (may be relative) — caller resolves to absolute via
    _is_team_comms_brief_path.

    This is intentionally a simple parser, not a full shell tokenizer.
    The cases we need to catch are the ones humans actually write:
    `mv team_comms/brief_191.md ...`, `rm team_comms/brief_*.md`,
    redirections via `>` and `>>`. Complex pipelines that hide a
    destructive write inside a $(...) substitution will slip through;
    those are also rare and the user-error patterns we're protecting
    against (BRIEF-191 collision recovery) are simple.
    """
    if not command:
        return []
    out: list[tuple[str, str]] = []
    # Split on whitespace; not perfect for quoted args with spaces, but
    # brief filenames never contain spaces (CLAUDE.md naming rule).
    tokens = command.split()
    for i, tok in enumerate(tokens):
        # Direct verbs: any token in the set, look at the rest of the line.
        bare = tok.lstrip("-")
        if bare in {"mv", "rm", "cp", "dd"}:
            # All subsequent non-flag tokens are candidate paths.
            for arg in tokens[i + 1 :]:
                if arg.startswith("-"):
                    continue
                if BRIEF_FILE_RE.search(arg):
                    out.append((bare, arg))
        # Redirections: `> path` and `>> path` and `cmd > path`. The
        # token may be `>file` (no space) or just `>`.
        if tok in (">", ">>"):
            if i + 1 < len(tokens):
                arg = tokens[i + 1]
                if BRIEF_FILE_RE.search(arg):
                    out.append((tok, arg))
        elif tok.startswith(">"):
            arg = tok.lstrip(">")
            if arg and BRIEF_FILE_RE.search(arg):
                out.append((">", arg))
    return out


# -------- hook handlers --------


def _emit(payload: dict) -> None:
    """Print JSON to stdout for the harness, then exit 0."""
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def _emit_pretooluse_deny(reason: str) -> None:
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def _emit_sessionstart_context(text: str) -> None:
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }
    )


def handle_session_start(event: dict) -> None:
    """SessionStart: register this session, surface foreign-session and
    recent-brief context.

    The information here is the cure for the BRIEF-189 surprise class:
    if another Claude Code session has registered, or if briefs landed
    in the last 24h while this session was offline, we want the model
    to know up front rather than discover it mid-task. The harness
    injects `additionalContext` into the first model turn.
    """
    _register_session(event)
    session_id = _session_id_from_event(event)

    lines: list[str] = []

    foreign = _foreign_sessions(session_id)
    if foreign:
        lines.append(
            f"PKA-guard: {len(foreign)} other Claude Code session(s) registered."
        )
        for s in foreign[:MAX_FOREIGN_SESSIONS_SURFACED]:
            claimed = s.get("claimed_brief_refs") or []
            claimed_str = ", ".join(claimed) if claimed else "no briefs claimed yet"
            lines.append(
                f"  - pid={s.get('pid')} cwd={s.get('cwd')} ({claimed_str})"
            )
        if len(foreign) > MAX_FOREIGN_SESSIONS_SURFACED:
            lines.append(
                f"  + {len(foreign) - MAX_FOREIGN_SESSIONS_SURFACED} more (see tools/.sessions/)"
            )
        lines.append(
            "  Cross-session work is in play. Confirm brief ownership before writing."
        )

    conn = _open_db()
    if conn is not None:
        try:
            recent = _recent_open_briefs(conn, RECENT_BRIEF_HOURS)
        finally:
            conn.close()
        if recent:
            lines.append("")
            lines.append(
                f"PKA-guard: {len(recent)} open brief(s) created in last {RECENT_BRIEF_HOURS}h:"
            )
            for b in recent[:10]:
                title = (b.get("title") or "")[:60]
                lines.append(
                    f"  - {b['brief_ref']} → {b.get('assigned_to') or '?'} | {title}"
                )

    if not lines:
        # No foreign sessions, no recent briefs — silent success. Exit
        # 0 with no JSON; the harness treats this as no-context-added.
        sys.exit(0)

    _emit_sessionstart_context("\n".join(lines))
    sys.exit(0)


def handle_stop(event: dict) -> None:
    """Stop / SubagentStop: clear this session's registration file.

    Conservative cleanup: only this session's file is removed.
    Foreign-session files are left alone — they're managed by their
    own sessions. Stale files are filtered at read time.
    """
    _clear_session(event)
    sys.exit(0)


def _pretooluse_check_write(
    conn: sqlite3.Connection, file_path: str, session_id: str
) -> str | None:
    """Return a deny-reason string if the Write/Edit should be blocked,
    else None.
    """
    if not _is_team_comms_brief_path(file_path):
        return None
    brief_ref = _brief_ref_from_path(file_path)
    if brief_ref is None:
        return None

    existing = _brief_exists(conn, brief_ref)
    my_session = _read_session(session_id) or {}
    claimed = set(my_session.get("claimed_brief_refs", []))

    if existing is None:
        # Fresh brief_ref — allow the write and claim it for this session.
        _claim_brief_ref(session_id, brief_ref)
        return None

    # The brief exists in pka.db.
    if brief_ref.upper() in claimed:
        # This session already claimed it — re-writing is fine (edits to
        # the brief body, status updates rewriting the file, etc.).
        return None

    # Brief exists, and this session has NOT claimed it. That's a
    # collision. Block with the next-free ref suggested.
    next_ref = _next_free_brief_ref(conn)
    return (
        f"PKA-guard: {brief_ref} already exists in pka.db "
        f"(status='{existing.get('status')}', assigned_to='{existing.get('assigned_to')}'). "
        f"This session has not claimed {brief_ref}, so the write looks like a collision "
        f"with another session that did. Next free brief_ref is {next_ref}. "
        f"Use {next_ref} instead, or — if you are intentionally editing the existing "
        f"brief — restart claiming it via Leroy's brief-write flow."
    )


def _pretooluse_check_bash(
    conn: sqlite3.Connection, command: str, session_id: str
) -> str | None:
    """Return a deny-reason if a Bash command targets a team_comms brief
    file that this session hasn't claimed.

    The check is symmetric with Write/Edit: same trust model, same
    suggestion. mv/rm against a peer session's brief is exactly the
    BRIEF-191 collision-recovery failure mode.
    """
    targets = _bash_brief_targets(command)
    if not targets:
        return None
    my_session = _read_session(session_id) or {}
    claimed = set(my_session.get("claimed_brief_refs", []))

    for verb, path in targets:
        if not _is_team_comms_brief_path(path):
            continue
        brief_ref = _brief_ref_from_path(path)
        if brief_ref is None:
            continue
        existing = _brief_exists(conn, brief_ref)
        if existing is None:
            # Path looks like a brief file but no such ref in pka.db.
            # That's a separate kind of mistake (deleting a never-created
            # file?), but not the collision we're protecting against.
            continue
        if brief_ref.upper() in claimed:
            continue
        return (
            f"PKA-guard: Bash `{verb}` targets {path}, which corresponds to "
            f"{brief_ref} (assigned_to='{existing.get('assigned_to')}', "
            f"status='{existing.get('status')}'). This session has not claimed "
            f"{brief_ref}, so this looks like it would clobber another session's "
            f"work — exactly the BRIEF-191 / collision-recovery pattern this hook "
            f"exists to prevent. Confirm ownership in chat before retrying. If "
            f"you intend to operate on this brief, claim it by writing the file "
            f"through Leroy's standard flow first."
        )
    return None


def handle_pre_tool_use(event: dict) -> None:
    """PreToolUse: dispatch by tool_name.

    Only Write/Edit/Bash are inspected — the cost of opening pka.db on
    every Read/Grep/Glob is not justified. If the tool is anything else,
    exit 0 silently.
    """
    tool_name = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}
    session_id = _session_id_from_event(event)

    # Cheap gate: bail out early if this isn't a tool we care about.
    if tool_name not in ("Write", "Edit", "Bash"):
        sys.exit(0)

    # For Write/Edit, the relevant target path is `file_path` in tool_input.
    # For Bash, it's parsed out of `command`.
    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path") or ""
        # Cheap pre-check: skip pka.db entirely if the path isn't a
        # team_comms brief file. Stays well under 50ms.
        if not _is_team_comms_brief_path(file_path):
            sys.exit(0)

    conn = _open_db()
    if conn is None:
        # Fail-open: no DB, no enforcement. The harness will still warn
        # the user via permission flow if anything is genuinely off.
        sys.exit(0)

    try:
        deny: str | None = None
        if tool_name in ("Write", "Edit"):
            deny = _pretooluse_check_write(
                conn, tool_input.get("file_path") or "", session_id
            )
        elif tool_name == "Bash":
            command = tool_input.get("command") or ""
            deny = _pretooluse_check_bash(conn, command, session_id)
    finally:
        conn.close()

    if deny:
        _emit_pretooluse_deny(deny)
        sys.exit(0)

    # No issue — exit 0 with no JSON, defer to normal permission flow.
    sys.exit(0)


# -------- entrypoint --------


def main() -> int:
    """Read the event from stdin, dispatch by `hook_event_name`.

    Top-level try/except guarantees we never block a tool call on an
    internal error — the hook is a safety belt, not a tripwire.
    """
    started = time.monotonic()
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        event = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return 0

    try:
        name = event.get("hook_event_name") or ""
        if name == "SessionStart":
            handle_session_start(event)
        elif name == "PreToolUse":
            handle_pre_tool_use(event)
        elif name in ("Stop", "SubagentStop"):
            handle_stop(event)
        # Unknown event — exit 0 silently.
    except SystemExit:
        # Handlers exit via sys.exit; let that propagate.
        raise
    except Exception:
        # Fail-open. Optional: log to a debug file if we ever need to
        # diagnose hook misbehavior. Today, silence is the right
        # behavior — a hook that crashes mid-tool-call must not block.
        pass

    # Safety net: ensure we never spend more than a budget worth of
    # wall time. If we did, log to stderr so it's surfaced; harness
    # treats non-zero-exit + stderr as a non-blocking warning.
    elapsed_ms = (time.monotonic() - started) * 1000.0
    if elapsed_ms > 200:
        sys.stderr.write(
            f"pka_guard: slow hook ({elapsed_ms:.0f}ms) — investigate\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
