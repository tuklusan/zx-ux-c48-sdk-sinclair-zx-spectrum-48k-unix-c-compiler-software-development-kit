# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
"""Reject project-wide forbidden ASCII terms without embedding them literally."""

from __future__ import annotations

import sys
from pathlib import Path

# Hex keeps this checker self-clean while preserving one authoritative set.
_TERM_HEX = (
    "636c61756465",
    "616e7468726f706963",
    "636f646578",
    "6f70656e6169",
    "63686174677074",
    "73706478",
)
_TERMS = tuple(bytes.fromhex(item) for item in _TERM_HEX)
_SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}
_SKIP_NAMES = {".coverage"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}


def check_tree(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _SKIP_PARTS for part in rel.parts):
            continue
        if path.name in _SKIP_NAMES or path.suffix in _SKIP_SUFFIXES:
            continue
        try:
            data = path.read_bytes().lower()
        except OSError as exc:
            errors.append(f"{rel}: unreadable: {exc}")
            continue
        for index, term in enumerate(_TERMS, start=1):
            if term in data:
                errors.append(f"{rel}: forbidden project term #{index}")
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parents[1]
    errors = check_tree(root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("project-wide forbidden-term gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
