#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# restricted model training is prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from check_project_banned_words import check_tree as check_banned_words

COPYRIGHT = "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs."
ATTRIBUTION_PREFIX = 'Attribution is required: \"Based on original work by Supratim Sanyal of'
ATTRIBUTION_SUFFIX = 'SANYALnet Labs.\" See LICENSE for full terms'
PROJECT = "ZX-UX C48 SDK"

# Header-safe source/document formats owned by this project.
HEADER_SUFFIXES = {".py", ".c", ".h", ".md", ".txt", ".bat", ".yml", ".yaml"}
HEADER_NAMES = {"c48", "c48run", ".gitignore", ".gitattributes"}

# Deliberate exemptions: adding text would corrupt the syntax/format/container,
# or LICENSE must remain the exact license text rather than recursively header itself.
EXEMPT_NAMES = {"LICENSE", "VERSION", "MANIFEST.sha256"}
EXEMPT_SUFFIXES = {".json", ".bin", ".dat", ".png", ".c48b", ".docx", ".zip", ".rom"}
EXEMPT_PATHS = {"usr/src/demos/dizzy4k.c"}


def classify(path: Path) -> str:
    if path.name in HEADER_NAMES or path.suffix.lower() in HEADER_SUFFIXES:
        return "header"
    if path.name in EXEMPT_NAMES or path.suffix.lower() in EXEMPT_SUFFIXES:
        return "exempt"
    return "unknown"


def _iter_project_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = sorted(
            name for name in dirnames if name not in {".git", "__pycache__"}
        )
        base = Path(dirpath)
        for name in sorted(filenames):
            yield base / name


def check_tree(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _iter_project_files(root):
        rel = path.relative_to(root).as_posix()
        # This port carries upstream provenance instead of the SDK source header.
        if rel in EXEMPT_PATHS:
            continue
        # Imported third-party reference material is preserved byte-for-byte
        # and is governed by its own provenance/licensing, not the SDK header.
        if rel.startswith("docs/reference/"):
            continue
        # Generated GUI release evidence is retained byte-for-byte. Injecting a
        # source header would corrupt images, PPM frames, JSONL probes, or
        # checksum files. README/.gitignore remain header-governed text.
        if rel.startswith("screenshots/gui-desktop/") and (
            path.name == "SHA256SUMS"
            or path.suffix.lower() in {".json", ".jsonl", ".png", ".ppm"}
        ):
            continue
        kind = classify(path)
        if kind == "unknown":
            errors.append(f"unclassified artifact: {rel}")
            continue
        if kind == "exempt":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            errors.append(f"header-eligible file is not UTF-8 text: {rel}: {exc}")
            continue
        # Header must be near the top; shebang/@echo-off may precede it.
        top = text[:3000]
        if rel.startswith("usr/src/") and path.suffix.lower() in {".c", ".h"}:
            # C48 artifacts use a deliberately compact <=64-column header.
            required_markers = (
                COPYRIGHT, PROJECT, "Non-Commercial License",
                "Attribution required: Based on original work by Supratim",
                "Sanyal of SANYALnet Labs. See root LICENSE for full terms.",
            )
        else:
            required_markers = (
                COPYRIGHT, PROJECT, ATTRIBUTION_PREFIX, ATTRIBUTION_SUFFIX,
                "root LICENSE file",
            )
        for required in required_markers:
            if required not in top:
                errors.append(
                    f"missing license header marker {required!r}: {rel}"
                )
        # The header itself must contain a copyright marker. User-facing CLI
        # --about text may legitimately repeat the same copyright notice later.
        if COPYRIGHT not in top[:1800]:
            errors.append(f"copyright marker is not in the header block: {rel}")
    # Attribution is a source/document requirement. User-facing CLI text
    # is intentionally outside this source-header gate.
    errors.extend(f"project policy: {error}" for error in check_banned_words(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforce ZX-UX C48 SDK license headers")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ns = ap.parse_args(argv)
    errors = check_tree(ns.root.resolve())
    if errors:
        for error in errors:
            print(f"LICENSE HEADER ERROR: {error}", file=sys.stderr)
        return 1
    print("LICENSE HEADER PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
