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
LIT = A / "ailit.h"
RUN = A / "tooling" / "run_iteration.py"
DESIGN = A / "AILMZX48-DETAILED-DESIGN.md"

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

LIT_CODE = r'''
unsigned int ai_slotref(unsigned int slot)
{
    unsigned int gen;
    if (slot >= 8) return 0;
    gen = ai_litgen[slot];
    if (gen == 0 || gen > 4095) return 0;
    return 32768 + (gen * 8) + slot;
}

int ai_refvalid(unsigned int ref)
{
    unsigned int slot;
    unsigned int gen;
    if (ref < 32768) return 0;
    slot = ref & 7;
    gen = (ref - 32768) / 8;
    if (gen == 0 || gen > 4095) return 0;
    if (ai_litgen[slot] != gen) return 0;
    if (ai_litlen[slot] == 0 || ai_litlen[slot] > 31) {
        return 0;
    }
    return 1;
}

void ai_putref(unsigned int ref)
{
    unsigned int slot;
    unsigned int off;
    unsigned int i;
    if (!ai_refvalid(ref)) return;
    slot = ref & 7;
    off = slot * 31;
    i = 0;
    while (i < ai_litlen[slot]) {
        putchar(ai_litbuf[off + i]);
        i = i + 1;
    }
}

void ai_invref(unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int got;
    if (ref == 0) return;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] != 0) {
            got = ai_capget(ai_l1, o + 12);
            if (got == ref) {
                ai_l1[o + 12] = 0;
                ai_l1[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] != 0) {
            got = ai_capget(ai_l2, o + 12);
            if (got == ref) {
                ai_l2[o + 12] = 0;
                ai_l2[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
            }
        }
        i = i + 1;
    }
}

void ai_namesuper(void)
{
    unsigned int i;
    unsigned int o;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 3 &&
            (ai_l1[o] & 32) == 0) {
            ai_l1[o] = ai_l1[o] | 32;
            ai_l1[o + 14] = 0;
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 3 &&
            (ai_l2[o] & 32) == 0) {
            ai_l2[o] = ai_l2[o] | 32;
            ai_l2[o + 14] = 0;
        }
        i = i + 1;
    }
}

void ai_nameadd(unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int victim;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 0) {
            ai_capset(&ai_l1[o], 0, 3, 255, 0);
            ai_l1[o + 12] = ref & 255;
            ai_l1[o + 13] = ref / 256;
            ai_l1count = ai_l1count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l1, 48);
    o = ai_capoff(victim);
    ai_l2merge(&ai_l1[o]);
    if (ai_compact != 65535) {
        ai_compact = ai_compact + 1;
    }
    ai_capset(&ai_l1[o], 0, 3, 255, 0);
    ai_l1[o + 12] = ref & 255;
    ai_l1[o + 13] = ref / 256;
}

void ai_namesem(void)
{
    ai_capage();
    ai_namesuper();
    if (ai_litold != 0) ai_invref(ai_litold);
    ai_nameadd(ai_litcur);
}

unsigned int ai_namefind(void)
{
    unsigned int i;
    unsigned int o;
    unsigned int ref;
    unsigned int best;
    unsigned int imp;
    unsigned int age;
    unsigned int bimp;
    unsigned int bage;
    best = 0;
    bimp = 0;
    bage = 255;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 3 &&
            (ai_l1[o] & 32) == 0) {
            ref = ai_capget(ai_l1, o + 12);
            if (ref != 0 && !ai_refvalid(ref)) {
                ai_l1[o + 12] = 0;
                ai_l1[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
                ref = 0;
            }
            if (ref != 0) {
                imp = ai_l1[o + 14];
                age = ai_l1[o + 15];
                if (best == 0 || imp > bimp ||
                    (imp == bimp && age < bage)) {
                    best = ref;
                    bimp = imp;
                    bage = age;
                }
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 3 &&
            (ai_l2[o] & 32) == 0) {
            ref = ai_capget(ai_l2, o + 12);
            if (ref != 0 && !ai_refvalid(ref)) {
                ai_l2[o + 12] = 0;
                ai_l2[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
                ref = 0;
            }
            if (ref != 0) {
                imp = ai_l2[o + 14];
                age = ai_l2[o + 15];
                if (best == 0 || imp > bimp ||
                    (imp == bimp && age < bage)) {
                    best = ref;
                    bimp = imp;
                    bage = age;
                }
            }
        }
        i = i + 1;
    }
    return best;
}
'''

OLD_SET = r'''int ai_setname(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    unsigned int gen;
    pos = ai_find("my name is ");
    if (pos < 0) return 0;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return 0;
    gen = ai_litgen[0] + 1;
    if (gen == 0 || gen > 4095) gen = 1;
    ai_litgen[0] = gen;
    ai_litlen[0] = n;
    i = 0;
    while (i < n) {
        ai_litbuf[i] = ai_in[start + i];
        i = i + 1;
    }
    ai_litset = 1;
    return 1;
}
'''

NEW_SET = r'''int ai_setname(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    unsigned int gen;
    unsigned int slot;
    unsigned int off;
    pos = ai_find("my name is ");
    if (pos < 0) return 0;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return 0;
    slot = ai_litnext;
    ai_litnext = (ai_litnext + 1) % 8;
    ai_litold = ai_slotref(slot);
    gen = ai_litgen[slot] + 1;
    if (gen == 0 || gen > 4095) gen = 1;
    ai_litgen[slot] = gen;
    ai_litlen[slot] = n;
    off = slot * 31;
    i = 0;
    while (i < n) {
        ai_litbuf[off + i] = ai_in[start + i];
        i = i + 1;
    }
    ai_litcur = ai_slotref(slot);
    ai_litset = 1;
    return 1;
}
'''

OLD_PUT = r'''void ai_putname(void)
{
    unsigned int i;
    i = 0;
    while (i < ai_litlen[0]) {
        putchar(ai_litbuf[i]);
        i = i + 1;
    }
}

void ai_nameack(void)
{
    ai_putraw("I will remember ");
    ai_putname();
    puts(".");
}

void ai_nameans(void)
{
    if (ai_litlen[0] == 0) {
        puts("I do not have your name yet.");
        return;
    }
    ai_lituse = 1;
    ai_putraw("I remember your name as ");
    ai_putname();
    puts(".");
}
'''

NEW_PUT = r'''void ai_nameack(void)
{
    ai_putraw("I will remember ");
    ai_putref(ai_litcur);
    puts(".");
}

void ai_nameans(void)
{
    unsigned int ref;
    ref = ai_namefind();
    if (ref == 0) {
        puts("I do not have your name yet.");
        return;
    }
    ai_lituse = 1;
    ai_semuse = 1;
    ai_putraw("I remember your name as ");
    ai_putref(ref);
    puts(".");
}
'''

L2_OLD = r'''        if (ai_l2[o + 1] == rel) {
            if (ai_capget(ai_l2, o + 2) == topic) {
                if (imp > ai_l2[o + 14]) {
                    ai_l2[o + 14] = imp;
                }
                if (age < ai_l2[o + 15]) {
                    ai_l2[o + 15] = age;
                }
                return;
            }
        }
'''

L2_NEW = r'''        if (ai_l2[o + 1] == rel) {
            if (ai_capget(ai_l2, o + 2) == topic) {
                if (rel == 3) {
                    if ((src[0] & 32) == 0 ||
                        ((ai_l2[o] & 32) != 0 &&
                         age < ai_l2[o + 15])) {
                        ai_mcopy(&ai_l2[o], src, 16);
                    }
                    return;
                }
                if (imp > ai_l2[o + 14]) {
                    ai_l2[o + 14] = imp;
                }
                if (age < ai_l2[o + 15]) {
                    ai_l2[o + 15] = age;
                }
                return;
            }
        }
'''

NOTE24 = (
"\nImplementation measurement note (Revision 0.24): iteration 12 repeated "
"the retained 500-turn actual-SDK endurance scenario after replacing the "
"temporary printable L0 with the Section-7 token/literal wire. The C48 "
"program again accepted 500 turns plus `q`, emitted 501 beeps, processed "
"48,820 source-equivalent dialogue bytes, recovered the turn-2 memory topic "
"at turn 500, and completed in 266.794 seconds. The encoded L0 peak fell "
"from iteration 11's 884 bytes to 830 of 896 bytes; L1 reached 48 records, "
"L2 reached five, 436 L1-to-L2 compactions occurred, and the decoded "
"96-entry u16 LM-context ring reached its exact capacity without exceeding "
"it. This supersedes the raw-L0 endurance evidence for the implemented "
"wire slice while leaving punctuation-token coverage and richer semantic "
"capsules as open work.\n"
)

NOTE25 = (
"\nImplementation measurement note (Revision 0.25): the target session-"
"literal prototype now uses all eight designed 31-byte presentation slots "
"with 1..4095 generations and bit-15 session references. User-name "
"corrections rotate deterministically through the eight slots. Name state is "
"stored in the value field of relation-3 L1/L2 capsules rather than recalled "
"directly from slot zero; recall generation-checks the reference before "
"resolving bytes. A correction marks older name capsules superseded, and "
"reusing a slot scans both semantic tiers for the old generation reference, "
"clears it and increments `ai_litloss`. L2 merging preserves a current "
"relation-3 capsule over superseded history. This is the first target-side "
"generation-checked session-reference slice, but it is still specialized to "
"the user-name relation rather than the complete Candidate-A semantic "
"relation schema. The next retained conversation must force slot reuse, "
"observe stale-reference loss, compact across a long dialogue and recover "
"only the newest name.\n"
)


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_source() -> None:
    text = SRC.read_text(encoding="utf-8")
    if '#include "ailit.h"' in text:
        return
    text = once(
        text,
        "unsigned int ai_lituse;\n",
        "unsigned int ai_lituse;\n"
        "unsigned int ai_litcur;\n"
        "unsigned int ai_litold;\n"
        "unsigned int ai_litnext;\n",
        "literal globals",
    )
    text = once(
        text,
        "int ai_namecmd(void)\n",
        "unsigned int ai_slotref(unsigned int slot);\n"
        "unsigned int ai_namefind(void);\n"
        "void ai_namesem(void);\n"
        "void ai_putref(unsigned int ref);\n\n"
        "int ai_namecmd(void)\n",
        "literal prototypes",
    )
    text = once(text, OLD_SET, NEW_SET, "name setter")
    text = once(text, OLD_PUT, NEW_PUT, "name presentation")
    text = once(text, L2_OLD, L2_NEW, "L2 name merge")
    text = once(
        text,
        "void ai_descshift(void)\n",
        '#include "ailit.h"\n\nvoid ai_descshift(void)\n',
        "literal helper include",
    )
    text = once(
        text,
        "    ai_lituse = 0;\n    ai_drop_lf = 0;\n",
        "    ai_lituse = 0;\n"
        "    ai_litcur = 0;\n"
        "    ai_litold = 0;\n"
        "    ai_litnext = 0;\n"
        "    ai_drop_lf = 0;\n",
        "literal init",
    )
    text = once(
        text,
        "                if (ai_setname()) {\n"
        "                    ai_nameack();\n",
        "                if (ai_setname()) {\n"
        "                    ai_namesem();\n"
        "                    ai_nameack();\n",
        "name semantic commit",
    )
    bad = [
        (n, len(line), line)
        for n, line in enumerate(text.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise RuntimeError(f"C48 source exceeds 64 columns: {bad[:5]}")
    if len(text.encode("utf-8")) > 32768:
        raise RuntimeError("ailmzx48.c exceeds 32768-byte source object")
    SRC.write_text(text, encoding="utf-8")
    lit = HEADER + LIT_CODE
    bad = [
        (n, len(line), line)
        for n, line in enumerate(lit.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise RuntimeError(f"ailit.h exceeds 64 columns: {bad[:5]}")
    if len(lit.encode("utf-8")) > 32768:
        raise RuntimeError("ailit.h exceeds 32768-byte source object")
    LIT.write_text(lit, encoding="utf-8")


def patch_runner() -> None:
    text = RUN.read_text(encoding="utf-8")
    if '"literal_reference_losses"' in text:
        return
    text = once(
        text,
        "    semuse_total = sum(\n"
        "        turn[\"diag\"].get(\"ai_semuse\", 0) for turn in turns\n"
        "    )\n",
        "    semuse_total = sum(\n"
        "        turn[\"diag\"].get(\"ai_semuse\", 0) for turn in turns\n"
        "    )\n"
        "    litloss_total = sum(\n"
        "        turn[\"diag\"].get(\"ai_litloss\", 0) for turn in turns\n"
        "    )\n",
        "runner literal-loss aggregate",
    )
    text = once(
        text,
        "    if semuse_total < int(req.get(\"min_semantic_uses\", 0)):\n"
        "        raise RuntimeError(\"semantic retrieval gate failed\")\n",
        "    if semuse_total < int(req.get(\"min_semantic_uses\", 0)):\n"
        "        raise RuntimeError(\"semantic retrieval gate failed\")\n"
        "    if litloss_total < int(req.get(\"min_literal_losses\", 0)):\n"
        "        raise RuntimeError(\"literal invalidation gate failed\")\n",
        "runner literal-loss gate",
    )
    text = once(
        text,
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "max_l0bytes": max_l0bytes,\n',
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "literal_reference_losses": litloss_total,\n'
        '        "max_l0bytes": max_l0bytes,\n',
        "score literal-loss field",
    )
    text = once(
        text,
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "max_l0bytes": max_l0bytes,\n',
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "literal_reference_losses": litloss_total,\n'
        '        "max_l0bytes": max_l0bytes,\n',
        "run literal-loss field",
    )
    RUN.write_text(text, encoding="utf-8")


def patch_design() -> None:
    text = DESIGN.read_text(encoding="utf-8")
    if "Revision: 0.25-draft" in text:
        return
    text = once(
        text,
        "Revision: 0.23-draft",
        "Revision: 0.25-draft",
        "design revision",
    )
    anchor = (
        "Implementation measurement note (Revision 0.23): the target L0 "
    )
    pos = text.find(anchor)
    if pos < 0:
        raise RuntimeError("design Revision 0.23 note not found")
    end = text.find("\n\n### 6.1", pos)
    if end < 0:
        raise RuntimeError("design note insertion boundary not found")
    text = text[:end] + NOTE24 + NOTE25 + text[end:]
    DESIGN.write_text(text, encoding="utf-8")


def main() -> int:
    patch_source()
    patch_runner()
    patch_design()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
