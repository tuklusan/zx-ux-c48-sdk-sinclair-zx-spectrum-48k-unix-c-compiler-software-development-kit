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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
A = ROOT / "usr" / "src" / "ailmzx48"
SRC = A / "ailmzx48.c"
HDR = A / "aictx.h"

HEADER = '''// ============================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and AI/ML
// model training prohibited unless separately authorized.
//
// Attribution required: Based on original work by Supratim
// Sanyal of SANYALnet Labs. See root LICENSE for full terms.
// ============================================================
'''


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    begin = "\nint ai_isalnum(int c)\n"
    finish = "\nint ai_ctxwrite(char *s, unsigned int speaker,\n"
    if text.count(begin) != 1:
        raise RuntimeError("wire-helper start anchor mismatch")
    if text.count(finish) != 1:
        raise RuntimeError("wire-helper end anchor mismatch")
    start = text.index(begin) + 1
    end = text.index(finish, start) + 1
    block = text[start:end]
    if "int ai_wirewrite(char *s, unsigned int speaker)" not in block:
        raise RuntimeError("wire-helper block incomplete")
    header = HEADER + block
    source = text[:start] + '#include "aictx.h"\n\n' + text[end:]
    for label, data in (("source", source), ("header", header)):
        bad = [
            (n, len(line), line)
            for n, line in enumerate(data.splitlines(), 1)
            if len(line) > 64
        ]
        if bad:
            raise RuntimeError(f"{label} exceeds 64 columns: {bad[:5]}")
    source_bytes = len(source.encode("utf-8"))
    header_bytes = len(header.encode("utf-8"))
    if source_bytes > 32768:
        raise RuntimeError(
            f"source object still exceeds 32768 bytes: {source_bytes}"
        )
    if header_bytes > 32768:
        raise RuntimeError(
            f"header object exceeds 32768 bytes: {header_bytes}"
        )
    SRC.write_text(source, encoding="utf-8")
    HDR.write_text(header, encoding="utf-8")
    print(
        f"split canonical wire helpers: source={source_bytes} "
        f"header={header_bytes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
