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
RUN = A / "tooling" / "run_iteration.py"
DESIGN = A / "AILMZX48-DETAILED-DESIGN.md"

GLOBALS = '''unsigned int ai_lmring[96];
unsigned int ai_lmhead;
unsigned int ai_lmcount;
unsigned int ai_l0wire;
'''

WIRE = r'''
int ai_isalnum(int c)
{
    if (c >= '0' && c <= '9') return 1;
    if (c >= 'a' && c <= 'z') return 1;
    if (c >= 'A' && c <= 'Z') return 1;
    return 0;
}

unsigned int ai_tokid(char *s, unsigned int start,
                      unsigned int len)
{
    unsigned int id;
    unsigned int j;
    unsigned int off;
    int ok;
    id = 1;
    while (id < ai_vcnt) {
        if (ai_vlen[id] == len) {
            off = ai_voff[id];
            j = 0;
            ok = 1;
            while (j < len) {
                if (ai_lower(s[start + j]) != ai_vblob[off + j]) {
                    ok = 0;
                    break;
                }
                j = j + 1;
            }
            if (ok) return id;
        }
        id = id + 1;
    }
    return 65535;
}

int ai_numspan(char *s, unsigned int start,
               unsigned int len)
{
    unsigned int i;
    i = 0;
    while (i < len) {
        if (s[start + i] < '0' || s[start + i] > '9') {
            return 0;
        }
        i = i + 1;
    }
    return 1;
}

unsigned int ai_encsize(char *s)
{
    unsigned int i;
    unsigned int start;
    unsigned int len;
    unsigned int id;
    unsigned int n;
    n = 2;
    i = 0;
    while (s[i] != 0) {
        if (s[i] == ' ') {
            i = i + 1;
        } else if (ai_isalnum(s[i])) {
            start = i;
            while (s[i] != 0 && ai_isalnum(s[i])) {
                i = i + 1;
            }
            len = i - start;
            id = ai_tokid(s, start, len);
            if (id != 65535) {
                if (id < 224) n = n + 1;
                else n = n + 3;
            } else {
                if (ai_numspan(s, start, len)) {
                    if (len > 15) return 65535;
                } else {
                    if (len > 31) return 65535;
                }
                n = n + 2 + len;
            }
        } else {
            n = n + 3;
            i = i + 1;
        }
        if (n > 255) return 65535;
    }
    return n;
}

void ai_ringput(unsigned int v)
{
    ai_l0ring[ai_l0head] = v;
    ai_l0head = (ai_l0head + 1) % 896;
}

void ai_lmput(unsigned int ref)
{
    ai_lmring[ai_lmhead] = ref;
    ai_lmhead = (ai_lmhead + 1) % 96;
    if (ai_lmcount < 96) ai_lmcount = ai_lmcount + 1;
}

int ai_wirewrite(char *s, unsigned int speaker)
{
    unsigned int i;
    unsigned int start;
    unsigned int len;
    unsigned int id;
    unsigned int j;
    unsigned int code;
    if (speaker == 0) {
        ai_ringput(3);
        ai_lmput(4101);
    } else {
        ai_ringput(4);
        ai_lmput(4102);
    }
    i = 0;
    while (s[i] != 0) {
        if (s[i] == ' ') {
            i = i + 1;
        } else if (ai_isalnum(s[i])) {
            start = i;
            while (s[i] != 0 && ai_isalnum(s[i])) {
                i = i + 1;
            }
            len = i - start;
            id = ai_tokid(s, start, len);
            if (id != 65535) {
                if (id < 224) {
                    ai_ringput(16 + id);
                } else {
                    ai_ringput(240);
                    ai_ringput(id & 255);
                    ai_ringput(id / 256);
                }
                ai_lmput(id);
            } else {
                code = 241;
                if (ai_numspan(s, start, len)) code = 242;
                else if (s[start] >= 'A' && s[start] <= 'Z') {
                    code = 243;
                }
                ai_ringput(code);
                ai_ringput(len);
                j = 0;
                while (j < len) {
                    ai_ringput(s[start + j]);
                    j = j + 1;
                }
                if (code == 242) ai_lmput(4097);
                else if (code == 243) ai_lmput(4098);
                else ai_lmput(4096);
            }
        } else {
            ai_ringput(241);
            ai_ringput(1);
            ai_ringput(s[i]);
            ai_lmput(4096);
            i = i + 1;
        }
    }
    ai_ringput(5);
    ai_lmput(4103);
    return 0;
}

'''

OLD_CTX = r'''int ai_ctxwrite(char *s, unsigned int speaker,
                unsigned int topic)
{
    unsigned int n;
    unsigned int i;
    unsigned int p;
    n = ai_strlen(s);
    if (n == 0 || n > 255) return -1;
    if (ai_l0count >= 32) return -1;
    ai_l0start[ai_l0count] = ai_l0head;
    ai_l0len[ai_l0count] = n;
    ai_l0meta[ai_l0count] = speaker + (topic * 2);
    i = 0;
    while (i < n) {
        p = (ai_l0head + i) % 896;
        ai_l0ring[p] = s[i];
        i = i + 1;
    }
    ai_l0head = (ai_l0head + n) % 896;
    ai_l0bytes = ai_l0bytes + n;
    ai_l0count = ai_l0count + 1;
    return 0;
}

int ai_ctxpair(unsigned int topic)
{
    unsigned int un;
    unsigned int an;
    unsigned int need;
    un = ai_strlen(ai_in);
    an = ai_strlen(ai_out);
    if (un == 0 || an == 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    need = un + an;
    if (need > 896) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    ai_capage();
    while (ai_l0bytes + need > 896 ||
           ai_l0count + 2 > 32) {
        if (ai_ctxevict() != 0) {
            ai_encfail = ai_encfail + 1;
            return -1;
        }
    }
    if (ai_ctxwrite(ai_in, 0, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    if (ai_ctxwrite(ai_out, 1, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    return 0;
}
'''

NEW_CTX = r'''int ai_ctxwrite(char *s, unsigned int speaker,
                unsigned int topic)
{
    unsigned int n;
    unsigned int meta;
    n = ai_encsize(s);
    if (n == 65535 || n == 0 || n > 255) return -1;
    if (ai_l0count >= 32) return -1;
    ai_l0start[ai_l0count] = ai_l0head;
    ai_l0len[ai_l0count] = n;
    meta = speaker + (topic * 2);
    if (speaker == 0 && ai_pinreq()) meta = meta | 32;
    ai_l0meta[ai_l0count] = meta;
    if (ai_wirewrite(s, speaker) != 0) return -1;
    ai_l0bytes = ai_l0bytes + n;
    ai_l0count = ai_l0count + 1;
    return 0;
}

int ai_ctxpair(unsigned int topic)
{
    unsigned int un;
    unsigned int an;
    unsigned int need;
    un = ai_encsize(ai_in);
    an = ai_encsize(ai_out);
    if (un == 65535 || an == 65535) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    need = un + an;
    if (need > 896) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    ai_capage();
    while (ai_l0bytes + need > 896 ||
           ai_l0count + 2 > 32) {
        if (ai_ctxevict() != 0) {
            ai_encfail = ai_encfail + 1;
            return -1;
        }
    }
    if (ai_ctxwrite(ai_in, 0, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    if (ai_ctxwrite(ai_out, 1, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    return 0;
}
'''

NOTE22 = (
"\nImplementation measurement note (Revision 0.22): iteration 11 is the "
"first retained actual-SDK long semantic-context endurance result. The "
"real C48 program accepted 500 turns plus the terminating `q`, emitted "
"501 turn-start beeps, processed 48,820 source-equivalent dialogue bytes, "
"performed 443 L1-to-L2 compactions, reached the fixed 48-record L1 and "
"five L2 records while keeping L0 at or below 884 of 896 bytes, and then "
"recovered the memory topic pinned at turn 2 on turn 500 after 497 "
"intervening turns. The final answer was `Memory matters because every "
"byte deserves care.` The active SDK run took 275.815 seconds and remained "
"inside the 1,200-second session limit. This is distinct from the earlier "
"host-only 500-dialogue/51,000-byte context-reference stress. It proves "
"bounded target-resident semantic retention in the SDK VM, while the L0 "
"representation in that iteration was still the temporary normalized "
"printable-byte prototype.\n"
)

NOTE23 = (
"\nImplementation measurement note (Revision 0.23): the target L0 slice "
"now stores the Section-7 control/lexical/literal wire shape instead of raw "
"turn text. Known resident lexical IDs use the one-byte hot form (and the "
"extended form remains implemented for IDs >=224); unknown alphanumeric "
"spans use bounded F1/F2/F3 literals; user/assistant framing and turn-end "
"controls are stored explicitly. A 96-entry u16 decoded LM-context ring is "
"maintained simultaneously with lexical IDs, literal-class refs and speaker "
"framing refs. Pin state is now descriptor metadata rather than a raw-text "
"search during L0 eviction, so semantic promotion remains valid after wire "
"encoding. Printable punctuation that is not yet resident in the starter "
"vocabulary is retained through the F1 literal fallback; therefore the "
"starter tokenizer still does not satisfy the final preference that common "
"punctuation have ordinary lexical IDs. Encoding is two-pass (size/preflight "
"then direct ring write), so an oversized encoded speaker turn is rejected "
"before L0/L1/L2 mutation. The next measurement must re-run long semantic "
"endurance on this encoded target state before the temporary raw-L0 evidence "
"is superseded.\n"
)


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {n}")
    return text.replace(old, new, 1)


def patch_source() -> None:
    text = SRC.read_text(encoding="utf-8")
    if "unsigned int ai_lmring[96];" in text:
        return
    text = once(
        text,
        "unsigned int ai_semuse;\n",
        "unsigned int ai_semuse;\n" + GLOBALS,
        "source globals",
    )
    text = once(
        text,
        "int ai_ctxwrite(char *s, unsigned int speaker,\n",
        WIRE + "int ai_ctxwrite(char *s, unsigned int speaker,\n",
        "wire functions",
    )
    text = once(text, OLD_CTX, NEW_CTX, "context writer")
    text = once(
        text,
        '    if (ai_l0has(0, "remember this topic")) {\n'
        '        rel = 1;\n'
        '        imp = 255;\n'
        '    }\n',
        '    if ((ai_l0meta[0] & 32) != 0) {\n'
        '        rel = 1;\n'
        '        imp = 255;\n'
        '    }\n',
        "promotion pin marker",
    )
    text = once(
        text,
        '        if (ai_l0has(i, "remember this topic")) {\n'
        '            return (ai_l0meta[i] / 2) & 7;\n'
        '        }\n',
        '        if ((ai_l0meta[i] & 32) != 0) {\n'
        '            return (ai_l0meta[i] / 2) & 7;\n'
        '        }\n',
        "semantic L0 pin marker",
    )
    text = once(
        text,
        "    ai_semuse = 0;\n    ai_start();\n",
        "    ai_semuse = 0;\n"
        "    ai_lmhead = 0;\n"
        "    ai_lmcount = 0;\n"
        "    ai_l0wire = 1;\n"
        "    ai_start();\n",
        "wire init",
    )
    bad = [
        (n, len(line), line)
        for n, line in enumerate(text.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise RuntimeError(f"C48 source exceeds 64 columns: {bad[:5]}")
    SRC.write_text(text, encoding="utf-8")


def patch_runner() -> None:
    text = RUN.read_text(encoding="utf-8")
    if '"ai_lmcount"' in text:
        return
    text = once(
        text,
        '                     "ai_encfail", "ai_semuse"):\n',
        '                     "ai_encfail", "ai_semuse",\n'
        '                     "ai_lmcount", "ai_l0wire"):\n',
        "runner diagnostics",
    )
    text = once(
        text,
        '''    max_l2count = max(
        (turn["diag"].get("ai_l2count", 0) for turn in turns),
        default=0,
    )
''',
        '''    max_l2count = max(
        (turn["diag"].get("ai_l2count", 0) for turn in turns),
        default=0,
    )
    max_lmcount = max(
        (turn["diag"].get("ai_lmcount", 0) for turn in turns),
        default=0,
    )
''',
        "runner LM metric",
    )
    text = once(
        text,
        '''    if semuse_total < int(req.get("min_semantic_uses", 0)):
        raise RuntimeError("semantic retrieval gate failed")
''',
        '''    if semuse_total < int(req.get("min_semantic_uses", 0)):
        raise RuntimeError("semantic retrieval gate failed")
    if max_lmcount < int(req.get("min_lmcount", 0)):
        raise RuntimeError("decoded LM-context gate failed")
''',
        "runner LM gate",
    )
    old = '        "max_l2count": max_l2count,\n'
    new = (
        '        "max_l2count": max_l2count,\n'
        '        "max_lmcount": max_lmcount,\n'
    )
    if text.count(old) != 2:
        raise RuntimeError("runner metric anchors changed")
    text = text.replace(old, new, 2)
    RUN.write_text(text, encoding="utf-8")


def patch_design() -> None:
    text = DESIGN.read_text(encoding="utf-8")
    if "Revision: 0.23-draft" in text:
        return
    text = once(
        text,
        "Revision: 0.21-draft",
        "Revision: 0.23-draft",
        "design revision",
    )
    text = once(
        text,
        "\n### 6.1 No remote inference dependency\n",
        NOTE22 + NOTE23 + "\n### 6.1 No remote inference dependency\n",
        "design notes",
    )
    DESIGN.write_text(text, encoding="utf-8")


def main() -> int:
    patch_source()
    patch_runner()
    patch_design()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
