#!/usr/bin/env python3
"""
PKA Naming Convention Checker
Scans the PKA directory for files and folders with spaces in their names.
Run at the start of each session or after adding new files.
Usage:
  python3 check_names.py                            # normal scan
  python3 check_names.py --evaluate-demotion-criterion
                                                    # evaluate criterion (b)
                                                    # against logs/check_names.jsonl

## Demotion criterion

Single criterion (no historical-data interpretability — `check_names.py`
is a validator that produces no historical data; the output is the
validation result, not a dataset).

Retire `check_names.py` when either:

  (a) The naming convention is enforced by a different mechanism —
      pre-commit hook in `.git/hooks/`, IDE integration, CI step, OR
  (b) A 90-day window passes with zero violations detected while the
      team continues to create new files at a normal rate (signal that
      the discipline is internalized and the check is no longer earning
      its keep — magnitude-of-value falls below the standing-tool
      threshold).

Source: owners_inbox/tool_demotion_criteria_proposal.md (Levi-approved
2026-05-20). Update via Leroy-drafted, Levi-approved deliverable; do not
modify unilaterally.

## Instrumentation

Each run appends one JSON line to `logs/check_names.jsonl` (gitignored)
capturing timestamp, files scanned, violation count, and violation
detail. The append is best-effort — log write failures print a warning
but do not affect the primary validation exit. See
`owners_inbox/check_names_instrumentation_iris.md` (BRIEF-151) for the
format defense and the demotion-criterion evaluation procedure.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

PKA_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PKA_ROOT, "logs")
LOG_PATH = os.path.join(LOG_DIR, "check_names.jsonl")

# Folders to skip entirely
# team_inbox/ is a drop zone for external files — naming not enforced there
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'team_inbox'}


def scan() -> tuple[list[tuple[str, str]], int]:
    """Walk PKA_ROOT and return (violations, files_scanned).

    A violation is a (kind, relative_path) tuple where kind is 'file' or
    'folder'. files_scanned counts every file encountered (excluding this
    script itself and contents of SKIP_DIRS) — used by the evaluation
    helper as a sanity check that the tree was not dormant during the
    90-day window.
    """
    violations: list[tuple[str, str]] = []
    files_scanned = 0

    for dirpath, dirnames, filenames in os.walk(PKA_ROOT):
        # Prune skipped dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel = os.path.relpath(dirpath, PKA_ROOT)

        # Check folder names
        for d in dirnames:
            if ' ' in d:
                violations.append(('folder', os.path.join(rel, d)))

        # Check file names (skip this script itself)
        for f in filenames:
            if f == 'check_names.py':
                continue
            files_scanned += 1
            if ' ' in f:
                violations.append(('file', os.path.join(rel, f)))

    return violations, files_scanned


def write_log_line(violations: list[tuple[str, str]], files_scanned: int) -> None:
    """Append one JSON line to LOG_PATH. Best-effort: any failure prints a
    warning to stderr and returns; the primary validation path is not
    affected.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files_scanned": files_scanned,
        "violations": len(violations),
        "violations_detail": [path for _kind, path in sorted(violations)],
    }
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        print(
            f"warning: could not write check_names log to {LOG_PATH}: {exc}",
            file=sys.stderr,
        )


def evaluate_demotion_criterion(window_days: int = 90) -> int:
    """Read LOG_PATH and report whether demotion criterion (b) is
    satisfied. Returns a process exit code: 0 in all evaluation cases
    (the evaluation itself succeeded). The verdict is reported on stdout.
    """
    if not os.path.exists(LOG_PATH):
        print(
            f"Demotion criterion (b) [NOT SATISFIED]: "
            f"no log at {LOG_PATH} — instrumentation has not yet recorded "
            f"any runs. The {window_days}-day window cannot be evaluated."
        )
        return 0

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    total_runs_in_window = 0
    zero_violation_runs = 0
    violation_runs = 0
    malformed_lines = 0
    total_files_scanned = 0
    earliest_logged_run: datetime | None = None  # across the whole log, not just window
    latest_violation_in_window: datetime | None = None

    with open(LOG_PATH, "r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
                ts = datetime.strptime(row["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                malformed_lines += 1
                continue

            if earliest_logged_run is None or ts < earliest_logged_run:
                earliest_logged_run = ts

            if ts < cutoff:
                continue

            total_runs_in_window += 1
            total_files_scanned += int(row.get("files_scanned", 0))

            if int(row.get("violations", 0)) == 0:
                zero_violation_runs += 1
            else:
                violation_runs += 1
                if latest_violation_in_window is None or ts > latest_violation_in_window:
                    latest_violation_in_window = ts

    print(f"Window: last {window_days} days (cutoff {cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')})")
    print(f"  Total runs in window:        {total_runs_in_window}")
    print(f"  Runs with zero violations:   {zero_violation_runs}")
    print(f"  Runs with violations:        {violation_runs}")
    print(f"  Cumulative files scanned:    {total_files_scanned}")
    if earliest_logged_run is not None:
        print(f"  Earliest log entry overall:  {earliest_logged_run.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    if malformed_lines:
        print(f"  Malformed log lines ignored: {malformed_lines}")
    print()

    if total_runs_in_window == 0:
        print(
            f"Demotion criterion (b) [NOT SATISFIED]: no runs recorded in the "
            f"last {window_days} days. The tool has not been exercised during "
            f"the window."
        )
        return 0

    if violation_runs > 0:
        last_v = latest_violation_in_window.strftime("%Y-%m-%dT%H:%M:%SZ") if latest_violation_in_window else "?"
        print(
            f"Demotion criterion (b) [NOT SATISFIED]: {violation_runs} run(s) "
            f"in the window recorded violations (most recent {last_v}). "
            f"Zero-violation window restarts from that timestamp forward."
        )
        return 0

    # Coverage check: we need evidence the log existed at or before the
    # cutoff. If the earliest log entry overall is after the cutoff, the
    # log itself is younger than the window and we cannot yet claim 90
    # days of coverage — only the elapsed portion.
    if earliest_logged_run is None or earliest_logged_run > cutoff:
        coverage_days = (now - earliest_logged_run).days if earliest_logged_run else 0
        print(
            f"Demotion criterion (b) [NOT SATISFIED]: window not yet fully "
            f"covered. Log has {coverage_days} day(s) of history; need "
            f"{window_days}-day continuous zero-violation coverage. Instrumentation "
            f"likely started after the criterion was written — that is expected; "
            f"the criterion becomes evaluable once the log itself has {window_days} "
            f"days of continuous history."
        )
        return 0

    print(
        f"Demotion criterion (b) [SATISFIED — pending judgment]: "
        f"{total_runs_in_window} run(s) over the last {window_days} days, all "
        f"with zero violations, and log history extends back to "
        f"{earliest_logged_run.strftime('%Y-%m-%dT%H:%M:%SZ')} (covers the full "
        f"window). The 'normal rate of file creation' qualifier is a judgment "
        f"Levi makes — cumulative files_scanned in the window is "
        f"{total_files_scanned}; confirm this reflects normal PKA activity "
        f"before invoking retirement."
    )
    return 0


def main(argv: list[str]) -> int:
    if "--evaluate-demotion-criterion" in argv:
        return evaluate_demotion_criterion()

    violations, files_scanned = scan()
    write_log_line(violations, files_scanned)

    if violations:
        print(f"⚠️  {len(violations)} naming violation(s) found:\n")
        for kind, path in sorted(violations):
            print(f"  [{kind}] {path}")
        print("\nRename to snake_case before proceeding.")
        return 1
    else:
        print("✓ No naming violations found. All clear.")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
