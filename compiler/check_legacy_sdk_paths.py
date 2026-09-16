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
"""Reject the explicitly retired dev tree and dev_src/dev_bin spellings."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

_RETIRED = "de" + "v"
_BINARY_SUFFIXES = {".bin", ".c48b", ".png", ".zip"}


def _patterns() -> tuple[re.Pattern[str], ...]:
    root = re.escape(_RETIRED)
    flags = re.IGNORECASE
    return (
        re.compile(root + r"[/\\](?:src|bin)(?=$|[^A-Za-z0-9_.-])", flags),
        re.compile(
            r"(?<![A-Za-z0-9_.-])" + root +
            r"[/\\](?![A-Za-z0-9_.-])",
            flags,
        ),
        re.compile(r"\b" + root + r"_(?:src|bin)\b", flags),
        re.compile(
            r"[\"']" + root + r"[\"']\s*/\s*[\"'](?:src|bin)[\"']",
            flags,
        ),
    )


_PATTERNS = _patterns()


def _matches(text: str) -> list[str]:
    found: list[str] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            token = match.group(0)
            if token not in found:
                found.append(token)
    return found


def _short(text: str, limit: int = 140) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 3] + "..."


def _scan_text(path: Path, rel: str, data: bytes) -> list[str]:
    if b"\0" in data:
        return []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    errors: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        tokens = _matches(line)
        if tokens:
            errors.append(
                f"{rel}:{lineno}: retired SDK token(s) {tokens!r}: {_short(line)!r}"
            )
    return errors


def _scan_docx(path: Path, rel: str) -> list[str]:
    errors: list[str] = []
    try:
        with ZipFile(path) as archive:
            for name in archive.namelist():
                if not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                data = archive.read(name)
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    errors.append(f"{rel}!{name}: non-UTF-8 OOXML part: {exc}")
                    continue
                direct = _matches(text)
                if direct:
                    errors.append(
                        f"{rel}!{name}: retired SDK token(s) {direct!r} in OOXML"
                    )
                try:
                    root = ET.fromstring(data)
                except ET.ParseError as exc:
                    errors.append(f"{rel}!{name}: malformed OOXML: {exc}")
                    continue
                for element in root.iter():
                    if element.tag.rsplit("}", 1)[-1] != "p":
                        continue
                    visible = "".join(element.itertext())
                    tokens = _matches(visible)
                    if tokens:
                        errors.append(
                            f"{rel}!{name}: retired SDK token(s) {tokens!r} "
                            f"in paragraph {_short(visible)!r}"
                        )
    except (BadZipFile, OSError) as exc:
        errors.append(f"{rel}: unreadable DOCX container: {exc}")
    return errors


def _self_test() -> list[str]:
    d = _RETIRED
    positives = (
        d + "/src/x.c",
        d + "\\bin\\x.c48b",
        "|-- " + d + "/",
        d + "_src = root",
        'SDK / "' + d + '" / "src"',
    )
    negatives = (
        "0.9.0-" + d,
        "/" + d + "/null",
        "development profile",
        "device driver",
    )
    errors = []
    for sample in positives:
        if not _matches(sample):
            errors.append(f"self-test missed positive sample: {sample!r}")
    for sample in negatives:
        if _matches(sample):
            errors.append(f"self-test rejected safe sample: {sample!r}")
    return errors


def check_tree(root: Path) -> list[str]:
    root = root.resolve()
    errors = _self_test()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root)
        if ".git" in rel_path.parts:
            continue
        rel = rel_path.as_posix()
        suffix = path.suffix.lower()
        if suffix == ".docx":
            errors.extend(_scan_docx(path, rel))
            continue
        if suffix in _BINARY_SUFFIXES:
            continue
        errors.extend(_scan_text(path, rel, path.read_bytes()))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject retired C48 SDK tree names in text and DOCX OOXML"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    args = parser.parse_args(argv)
    errors = check_tree(args.root)
    if errors:
        for error in errors:
            print(f"LEGACY SDK PATH ERROR: {error}")
        return 1
    print("LEGACY SDK PATH PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
