#!/usr/bin/env python3
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
"""One-shot final manifest reconciliation after workflow finalization."""
from __future__ import annotations

import hashlib
from pathlib import Path

SDK = Path(__file__).resolve().parents[1]


def file_hash(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() == ".bat":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    for rel in (
        ".github/stage_graphics_demos.py",
        ".github/manifest-trigger.txt",
    ):
        path = SDK / rel
        if path.exists():
            path.unlink()

    lines = []
    for path in sorted(SDK.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SDK)
        if ".git" in rel.parts:
            continue
        if rel.as_posix() == "MANIFEST.sha256":
            continue
        lines.append(f"{file_hash(path)}  {rel.as_posix()}")
    (SDK / "MANIFEST.sha256").write_text(
        "\n".join(lines) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
