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
"""Compact the C48 model-I/O/input changes under the C48B1 AST ceiling."""
from __future__ import annotations

import json
import re
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


p = Path("usr/src/ailmzx48/aimatch.h")
s = p.read_text(encoding="ascii")
s = section(
    s,
    "int open(char *path, int flags);\n",
    "int ai_readfull(unsigned char *p, unsigned int n)\n",
    "",
    "remove model I/O wrappers",
)
s = once(
    s,
    "        got = ai_mread(&p[done], ask);\n",
    "        got = read(ai_mfd, &p[done], ask);\n",
    "ai_readfull generic read",
)
p.write_text(s, encoding="ascii", newline="\n")


p = Path("usr/src/ailmzx48/ailmzx48.c")
s = p.read_text(encoding="ascii")
s = once(
    s,
    "unsigned int ai_mstat(void);\nint ai_mseek(unsigned int pos);\nint ai_mread(unsigned char *p, unsigned int n);\n",
    "int open(char *path, int flags);\n"
    "int read(int h, unsigned char *p, unsigned int n);\n"
    "int seek(int h, unsigned int pos);\n"
    "unsigned int strlen(char *s);\n"
    "int ai_mfd;\n",
    "generic object declarations",
)
s = once(
    s,
    "    actual = ai_mstat();\n    if (actual < 40) return -1;\n    if (ai_mseek(0) != 0) return -1;\n",
    "    if (ai_mfd < 3) return -1;\n"
    "    actual = AI_CLEN;\n"
    "    if (actual < 40) return -1;\n"
    "    if (seek(ai_mfd, 0) != 0) return -1;\n",
    "model scan generic rewind",
)
s = once(
    s,
    "    ai_l0wire = 1;\n    ai_start();\n",
    "    ai_l0wire = 1;\n"
    "    ai_mfd = open(\"ailm.dat\", 1);\n"
    "    ai_start();\n",
    "model open at process start",
)
s = section(
    s,
    "int ai_has(char *s)\n",
    "int ai_find(char *s)\n",
    "int ai_find(char *s);\n\n"
    "int ai_has(char *s)\n"
    "{\n"
    "    return ai_find(s) >= 0;\n"
    "}\n\n",
    "deduplicate substring search",
)
s = section(
    s,
    "unsigned int ai_strlen(char *s)\n",
    "unsigned char ai_l0char(unsigned int d, unsigned int n)\n",
    "",
    "remove private strlen",
)
s = once(s, "    sl = ai_strlen(s);\n", "    sl = strlen(s);\n", "use runtime strlen")
give = '''void ai_give(void)
{
    yield();
    ai_yields = ai_yields + 1;
}

'''
s = once(s, "int main(void)\n", give + "int main(void)\n", "yield helper insertion")
pattern = re.compile(r"yield\(\);\n(?P<i> +)ai_yields = ai_yields \+ 1;")
s, replaced = pattern.subn("ai_give();", s)
if replaced != 8:
    raise SystemExit(f"yield pair compaction: expected 8, got {replaced}")
old = '''        if (c == 13) {
            ai_drop_lf = 1;
            putchar(10);
            break;
        }
        if (c == 10) {
            putchar(10);
            break;
        }
'''
new = '''        if (c == 13) {
            ai_drop_lf = 1;
            c = 10;
        }
        if (c == 10) {
            putchar(10);
            break;
        }
'''
s = once(s, old, new, "compact Enter handling")
p.write_text(s, encoding="ascii", newline="\n")


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
    "// ============================================================\n#define AI_CLEN " + str(length) + "\nunsigned char ai_cvid[8] = {\n",
    "aicold logical length",
)
p.write_text(s, encoding="ascii", newline="\n")

print("C48 MODEL I/O AST COMPACTION PASS", length)
