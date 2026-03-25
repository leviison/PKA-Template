#!/usr/bin/env python3
"""
PKA Naming Convention Checker
Scans the PKA directory for files and folders with spaces in their names.
Run at the start of each session or after adding new files.
Usage: python3 check_names.py
"""

import os

PKA_ROOT = os.path.dirname(os.path.abspath(__file__))

# Folders to skip entirely
# team_inbox/ is a drop zone for external files — naming not enforced there
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'team_inbox'}

violations = []

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
        if ' ' in f:
            violations.append(('file', os.path.join(rel, f)))

if violations:
    print(f"⚠️  {len(violations)} naming violation(s) found:\n")
    for kind, path in sorted(violations):
        print(f"  [{kind}] {path}")
    print("\nRename to snake_case before proceeding.")
else:
    print("✓ No naming violations found. All clear.")
