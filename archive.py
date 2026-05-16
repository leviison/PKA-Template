#!/usr/bin/env python3
"""
archive.py — PKA Archive Utility

Moves completed ephemeral content (assets, briefs, deliverables) out of
active folders into archive/ and updates pka.db accordingly. Replaces
hard-delete compaction with move-to-archive so DB and disk stay in sync
and brief/deliverable files remain recoverable.

Usage:
    python3 archive.py asset <asset_id>
    python3 archive.py brief <brief_ref>           # e.g. BRIEF-050
    python3 archive.py deliverable <deliverable_id>
    python3 archive.py pattern <pattern_ref>       # e.g. PATTERN-001
    python3 archive.py --list assets|briefs|deliverables|patterns

Examples:
    python3 archive.py asset 1
    python3 archive.py brief BRIEF-050
    python3 archive.py deliverable 42
    python3 archive.py pattern PATTERN-001
    python3 archive.py --list briefs

Replaces archive_asset.py (v1, asset-only).
"""

import sys
import shutil
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

PKA_ROOT = Path(__file__).parent
DB_PATH = PKA_ROOT / "pka.db"
ARCHIVE_DIR = PKA_ROOT / "archive"
ARCHIVE_TEAM_INBOX = ARCHIVE_DIR / "team_inbox"
ARCHIVE_TEAM_COMMS = ARCHIVE_DIR / "team_comms"
ARCHIVE_OWNERS_INBOX = ARCHIVE_DIR / "owners_inbox"
ARCHIVE_PATTERNS     = ARCHIVE_DIR / "patterns"
PATTERNS_DIR         = PKA_ROOT / "patterns"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _collision_safe(dst: Path) -> Path:
    if dst.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return dst.with_name(f"{dst.stem}_{ts}{dst.suffix}")
    return dst


def _move(src: Path, dst: Path) -> bool:
    """Move src to dst. Returns True if the move occurred, False if src was missing."""
    if not src.exists():
        print(f"Warning: source file not found at {src.relative_to(PKA_ROOT)}")
        print("  Updating DB record only.")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    final_dst = _collision_safe(dst)
    shutil.move(str(src), str(final_dst))
    print(f"Moved: {src.relative_to(PKA_ROOT)} -> {final_dst.relative_to(PKA_ROOT)}")
    return True


# ---------- ASSETS ----------

def archive_asset(asset_id: int):
    conn = _connect()
    row = conn.execute(
        "SELECT id, filename, path, status FROM assets WHERE id = ?", (asset_id,)
    ).fetchone()
    if not row:
        print(f"Error: no asset found with id={asset_id}")
        sys.exit(1)
    _id, filename, current_path, status = row
    if status == "archived":
        print(f"Asset {_id} ({filename}) is already archived.")
        return

    src = PKA_ROOT / current_path
    dst = ARCHIVE_TEAM_INBOX / filename
    _move(src, dst)

    new_path = f"archive/team_inbox/{dst.name}"
    conn.execute(
        "UPDATE assets SET path = ?, status = 'archived' WHERE id = ?",
        (new_path, _id),
    )
    conn.commit()
    conn.close()
    print(f"DB updated: assets.id={_id} path='{new_path}' status='archived'")


# ---------- BRIEFS ----------

def archive_brief(brief_ref: str):
    conn = _connect()
    row = conn.execute(
        "SELECT brief_ref, status FROM briefs WHERE brief_ref = ?", (brief_ref,)
    ).fetchone()
    if not row:
        print(f"Error: no brief found with brief_ref={brief_ref}")
        sys.exit(1)
    _ref, status = row
    if status != "complete":
        print(f"Refusing to archive brief {_ref} — status is '{status}', not 'complete'.")
        print("  Mark the brief complete first.")
        sys.exit(1)

    file_num = brief_ref.split("-")[-1].lower()
    src = PKA_ROOT / "team_comms" / f"brief_{file_num}.md"
    dst = ARCHIVE_TEAM_COMMS / f"brief_{file_num}.md"
    _move(src, dst)
    conn.close()
    print(f"Brief {brief_ref} archived. DB body remains the source of truth.")


# ---------- DELIVERABLES ----------

def archive_deliverable(deliverable_id: int):
    conn = _connect()
    row = conn.execute(
        "SELECT id, file_path, created_by FROM deliverables WHERE id = ?",
        (deliverable_id,),
    ).fetchone()
    if not row:
        print(f"Error: no deliverable found with id={deliverable_id}")
        sys.exit(1)
    _id, file_path, created_by = row
    if file_path.startswith("archive/"):
        print(f"Deliverable {_id} is already archived (path='{file_path}').")
        return

    src = PKA_ROOT / file_path
    dst = ARCHIVE_DIR / file_path  # preserves the owners_inbox/... subpath
    _move(src, dst)

    new_path = f"archive/{file_path}"
    conn.execute(
        "UPDATE deliverables SET file_path = ? WHERE id = ?", (new_path, _id)
    )
    conn.commit()
    conn.close()
    print(f"DB updated: deliverables.id={_id} file_path='{new_path}'")


# ---------- PATTERNS ----------

def archive_pattern(pattern_ref: str):
    conn = _connect()
    row = conn.execute(
        "SELECT pattern_ref, slug, status FROM patterns WHERE pattern_ref = ?",
        (pattern_ref,)
    ).fetchone()
    if not row:
        print(f"Error: no pattern found with pattern_ref={pattern_ref}")
        sys.exit(1)
    _ref, slug, status = row
    if status == "deprecated":
        print(f"Pattern {_ref} ({slug}) is already deprecated/archived.")
        return

    src = PATTERNS_DIR / f"{slug}.md"
    dst = ARCHIVE_PATTERNS / f"{slug}.md"
    _move(src, dst)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE patterns SET status='deprecated', deprecated_at=? WHERE pattern_ref=?",
        (now, _ref),
    )
    conn.commit()
    conn.close()
    print(f"DB updated: patterns pattern_ref={_ref} status='deprecated' deprecated_at={now}")
    print(f"Note: deprecated_reason is NULL — set it manually if needed:")
    print(f"  UPDATE patterns SET deprecated_reason='...' WHERE pattern_ref='{_ref}';")


# ---------- LIST ----------

def list_items(item_type: str):
    conn = _connect()
    if item_type == "assets":
        rows = conn.execute(
            "SELECT id, filename, status FROM assets WHERE status != 'archived' ORDER BY id"
        ).fetchall()
        if not rows:
            print("No non-archived assets.")
            return
        print(f"{'ID':<5} {'Status':<12} Filename")
        print("-" * 60)
        for r in rows:
            print(f"{r[0]:<5} {r[2]:<12} {r[1]}")

    elif item_type == "briefs":
        rows = conn.execute(
            "SELECT brief_ref, assigned_to, status FROM briefs "
            "WHERE status='complete' ORDER BY brief_ref"
        ).fetchall()
        candidates = []
        for ref, assignee, status in rows:
            file_num = ref.split("-")[-1].lower()
            f = PKA_ROOT / "team_comms" / f"brief_{file_num}.md"
            if f.exists():
                candidates.append((ref, assignee, status))
        if not candidates:
            print("No complete briefs with un-archived files in team_comms/.")
            return
        print(f"{'Ref':<12} {'Assigned':<12} Status")
        print("-" * 50)
        for r in candidates:
            print(f"{r[0]:<12} {r[1]:<12} {r[2]}")

    elif item_type == "deliverables":
        rows = conn.execute(
            "SELECT id, file_path, created_by FROM deliverables "
            "WHERE file_path NOT LIKE 'archive/%' ORDER BY id DESC LIMIT 50"
        ).fetchall()
        if not rows:
            print("No non-archived deliverables.")
            return
        print(f"{'ID':<5} {'By':<10} File")
        print("-" * 80)
        for r in rows:
            print(f"{r[0]:<5} {r[2]:<10} {r[1]}")

    elif item_type == "patterns":
        rows = conn.execute(
            "SELECT pattern_ref, slug, status FROM patterns "
            "WHERE status != 'deprecated' ORDER BY pattern_ref"
        ).fetchall()
        if not rows:
            print("No non-deprecated patterns.")
            return
        print(f"{'Ref':<14} {'Status':<12} Slug")
        print("-" * 60)
        for r in rows:
            print(f"{r[0]:<14} {r[2]:<12} {r[1]}")

    else:
        print(f"Unknown type: {item_type}. Use 'assets', 'briefs', 'deliverables', or 'patterns'.")
        sys.exit(1)


# ---------- MAIN ----------

def main():
    parser = argparse.ArgumentParser(
        description="PKA Archive Utility — moves completed ephemeral content into archive/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--list", choices=["assets", "briefs", "deliverables", "patterns"],
        help="list non-archived items of a type"
    )
    sub = parser.add_subparsers(dest="cmd")

    sp_asset = sub.add_parser("asset", help="archive an asset by id")
    sp_asset.add_argument("asset_id", type=int)

    sp_brief = sub.add_parser("brief", help="archive a completed brief by ref (e.g. BRIEF-050)")
    sp_brief.add_argument("brief_ref")

    sp_deliv = sub.add_parser("deliverable", help="archive a deliverable by id")
    sp_deliv.add_argument("deliverable_id", type=int)

    sp_pat = sub.add_parser("pattern", help="archive (deprecate) a pattern by ref (e.g. PATTERN-001)")
    sp_pat.add_argument("pattern_ref")

    args = parser.parse_args()

    if args.list:
        list_items(args.list)
        return

    if args.cmd == "asset":
        archive_asset(args.asset_id)
    elif args.cmd == "brief":
        archive_brief(args.brief_ref)
    elif args.cmd == "deliverable":
        archive_deliverable(args.deliverable_id)
    elif args.cmd == "pattern":
        archive_pattern(args.pattern_ref)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
