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
"""Remove avoidable C wrapper AST after the primary one-shot transform."""
from __future__ import annotations

import json
from pathlib import Path


def section(value: str, start: str, end: str, replacement: str, label: str) -> str:
    a = value.find(start)
    b = value.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise SystemExit(f"{label}: structural anchors missing")
    return value[:a] + replacement + value[b:]


def once(value: str, old: str, new: str, label: str) -> str:
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return value.replace(old, new)


# The private ai_m* C wrappers are unnecessary. ai_readfull can use the
# generic read primitive and the main model scanner can open/seek directly.
p = Path("usr/src/ailmzx48/aimatch.h")
s = p.read_text(encoding="ascii")
s = section(
    s,
    "int open(char *path, int flags);\n",
    "int ai_readfull(unsigned char *p, unsigned int n)\n",
    "int ai_readfull(unsigned char *p, unsigned int n)\n",
    "remove model I/O wrappers",
)
s = once(
    s,
    "        got = ai_mread(&p[used], take);\n",
    "        got = read(ai_mfd, &p[used], take);\n",
    "ai_readfull generic read",
)
p.write_text(s, encoding="ascii", newline="\n")


# Replace application-private host declarations with the ordinary object API.
p = Path("usr/src/ailmzx48/ailmzx48.c")
s = p.read_text(encoding="ascii")ns = once(
    s,
    "unsigned int ai_mstat(void);\nint ai_mseek(unsigned int pos);\nint ai_mread(unsigned char *p, unsigned int n);\n",
    "int open(char *path, int flags);\nint close(int h);\nint read(int h, unsigned char *p, unsigned int n);\nint seek(int h, unsigned int pos);\nint ai_mfd;\n",
    "generic object declarations",
)
s = once(
    s,
    "    actual = ai_mstat();\n    if (actual < 40) return -1;\n    if (ai_mseek(0) != 0) return -1;\n",
    "    if (ai_mfd >= 3) close(ai_mfd);\n    ai_mfd = open(\"ailm.dat\", 1);\n    if (ai_mfd < 0) return -1;\n    actual = ai_clen;\n    if (actual < 40) return -1;\n    if (seek(ai_mfd, 0) != 0) return -1;\n",
    "model scan generic open",
)
p.write_text(s, encoding="ascii", newline="\n")


# Freeze the actual accepted logical length alongside the generated identities.
meta = json.loads(
    Path("usr/src/ailmzx48/model/cold-seed.json").read_text(encoding="utf-8")
)
length = meta.get("logical_length")
if isinstance(length, bool) or not isinstance(length, int) or not 40 <= length <= 65535:
    raise SystemExit("invalid cold model logical_length")
p = Path("usr/src/ailmzx48/aicold.h")
s = p.read_text(encoding="ascii")
s = once(
    s,
    "// ============================================================\nunsigned char ai_cvid[8] = {\n",
    "// ============================================================\nunsigned int ai_clen = " + str(length) + ";\nunsigned char ai_cvid[8] = {\n",
    "aicold logical length",
)
p.write_text(s, encoding="ascii", newline="\n")

print("C48 MODEL I/O AST REDUCTION PASS", length)
