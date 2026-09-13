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

GLOBALS = r'''
unsigned char ai_l0ring[896];
unsigned int ai_l0start[32];
unsigned char ai_l0len[32];
unsigned char ai_l0meta[32];
unsigned int ai_l0head;
unsigned int ai_l0bytes;
unsigned int ai_l0count;
unsigned char ai_l1[768];
unsigned char ai_l2[384];
unsigned int ai_l1count;
unsigned int ai_l2count;
unsigned int ai_compact;
unsigned int ai_l2evict;
unsigned int ai_l1drop;
unsigned int ai_litloss;
unsigned int ai_encfail;
unsigned int ai_semuse;
'''

FUNCS = r'''
unsigned int ai_strlen(char *s)
{
    unsigned int n;
    n = 0;
    while (s[n] != 0) n = n + 1;
    return n;
}

unsigned char ai_l0char(unsigned int d, unsigned int n)
{
    unsigned int p;
    p = ai_l0start[d] + n;
    p = p % 896;
    return ai_l0ring[p];
}

int ai_l0has(unsigned int d, char *s)
{
    unsigned int i;
    unsigned int j;
    unsigned int sl;
    int ok;
    sl = ai_strlen(s);
    if (sl == 0 || sl > ai_l0len[d]) return 0;
    i = 0;
    while (i + sl <= ai_l0len[d]) {
        j = 0;
        ok = 1;
        while (j < sl) {
            if (ai_lower(ai_l0char(d, i + j)) != s[j]) {
                ok = 0;
                break;
            }
            j = j + 1;
        }
        if (ok) return 1;
        i = i + 1;
    }
    return 0;
}

unsigned int ai_capoff(unsigned int n)
{
    return n * 16;
}

unsigned int ai_capget(unsigned char *p, unsigned int n)
{
    return p[n] + ((unsigned int)p[n + 1] * 256);
}

void ai_capset(unsigned char *p, unsigned int topic,
               unsigned int rel, unsigned int imp,
               unsigned int age)
{
    unsigned int i;
    i = 0;
    while (i < 16) {
        p[i] = 0;
        i = i + 1;
    }
    p[1] = rel;
    p[2] = topic & 255;
    p[3] = topic / 256;
    p[14] = imp;
    p[15] = age;
}

void ai_capage(void)
{
    unsigned int i;
    unsigned int o;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] != 0 && ai_l1[o + 15] < 255) {
            ai_l1[o + 15] = ai_l1[o + 15] + 1;
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] != 0 && ai_l2[o + 15] < 255) {
            ai_l2[o + 15] = ai_l2[o + 15] + 1;
        }
        i = i + 1;
    }
}

unsigned int ai_victim(unsigned char *p, unsigned int count)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bimp;
    unsigned int bage;
    unsigned int imp;
    unsigned int age;
    best = 0;
    bimp = 256;
    bage = 0;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        if (p[o + 1] != 0) {
            imp = p[o + 14];
            age = p[o + 15];
            if (imp < bimp) {
                best = i;
                bimp = imp;
                bage = age;
            } else if (imp == bimp && age > bage) {
                best = i;
                bage = age;
            }
        }
        i = i + 1;
    }
    return best;
}

void ai_l2merge(unsigned char *src)
{
    unsigned int i;
    unsigned int o;
    unsigned int rel;
    unsigned int topic;
    unsigned int imp;
    unsigned int age;
    unsigned int victim;
    rel = src[1];
    topic = ai_capget(src, 2);
    imp = src[14];
    age = src[15];
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == rel) {
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
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 0) {
            ai_mcopy(&ai_l2[o], src, 16);
            ai_l2count = ai_l2count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l2, 24);
    o = ai_capoff(victim);
    ai_mcopy(&ai_l2[o], src, 16);
    ai_l2evict = ai_l2evict + 1;
}

void ai_l1add(unsigned int topic, unsigned int rel,
              unsigned int imp, unsigned int age)
{
    unsigned int i;
    unsigned int o;
    unsigned int victim;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 0) {
            ai_capset(&ai_l1[o], topic, rel, imp, age);
            ai_l1count = ai_l1count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l1, 48);
    o = ai_capoff(victim);
    ai_l2merge(&ai_l1[o]);
    ai_compact = ai_compact + 1;
    ai_capset(&ai_l1[o], topic, rel, imp, age);
}

void ai_descshift(void)
{
    unsigned int i;
    i = 2;
    while (i < ai_l0count) {
        ai_l0start[i - 2] = ai_l0start[i];
        ai_l0len[i - 2] = ai_l0len[i];
        ai_l0meta[i - 2] = ai_l0meta[i];
        i = i + 1;
    }
    ai_l0count = ai_l0count - 2;
}

void ai_promote(void)
{
    unsigned int topic;
    unsigned int rel;
    unsigned int imp;
    topic = (ai_l0meta[0] / 2) & 7;
    rel = 2;
    imp = 32;
    if (ai_l0has(0, "remember this topic")) {
        rel = 1;
        imp = 255;
    }
    ai_l1add(topic, rel, imp, 1);
}

int ai_ctxevict(void)
{
    unsigned int n;
    if (ai_l0count < 2) return -1;
    ai_promote();
    n = ai_l0len[0] + ai_l0len[1];
    if (n > ai_l0bytes) return -1;
    ai_l0bytes = ai_l0bytes - n;
    ai_descshift();
    return 0;
}

int ai_ctxwrite(char *s, unsigned int speaker,
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

int ai_pinreq(void)
{
    if (ai_has("remember this topic")) return 1;
    if (ai_has("remember that topic")) return 1;
    return 0;
}

int ai_recallreq(void)
{
    if (ai_has("topic i asked you to remember")) return 1;
    if (ai_has("return to the remembered topic")) return 1;
    return 0;
}

unsigned int ai_semrecall(void)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bimp;
    unsigned int bage;
    unsigned int imp;
    unsigned int age;
    unsigned int topic;
    i = ai_l0count;
    while (i >= 2) {
        i = i - 2;
        if (ai_l0has(i, "remember this topic")) {
            return (ai_l0meta[i] / 2) & 7;
        }
    }
    best = 65535;
    bimp = 0;
    bage = 255;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 1) {
            imp = ai_l1[o + 14];
            age = ai_l1[o + 15];
            if (best == 65535 || imp > bimp ||
                (imp == bimp && age < bage)) {
                best = ai_capget(ai_l1, o + 2);
                bimp = imp;
                bage = age;
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 1) {
            imp = ai_l2[o + 14];
            age = ai_l2[o + 15];
            if (best == 65535 || imp > bimp ||
                (imp == bimp && age < bage)) {
                topic = ai_capget(ai_l2, o + 2);
                best = topic;
                bimp = imp;
                bage = age;
            }
        }
        i = i + 1;
    }
    return best;
}

void ai_settext(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0 && i < 255) {
        ai_out[i] = s[i];
        i = i + 1;
    }
    ai_out[i] = 0;
    ai_olen = i;
    ai_otokens = 0;
}

'''

NOTE = (
"\nImplementation measurement note (Revision 0.21): the target C48 "
"program now contains the first fixed-size semantic-context slice rather "
"than relying only on the six-topic controller history. It allocates the "
"896-byte L0 ring, exact 128-byte 32-entry descriptor directory, 48 x "
"16-byte L1 capsules, and 24 x 16-byte L2 capsules as fixed arrays, ages "
"capsules saturating at 255, promotes evicted L0 user turns into L1, and "
"compacts L1 victims into mergeable L2 summaries. An explicit `remember "
"this topic` controller operation is retained as a high-importance semantic "
"capsule and `return to the remembered topic` retrieves it after L0 "
"eviction. This slice deliberately stores normalized printable turn bytes "
"in L0 rather than the final Section-7 token wire and currently commits "
"ordinary model-answer turns rather than every controller-only turn. It is "
"therefore a target-resident compaction/retrieval prototype, not yet a "
"claim that Candidate-A canonical tokenization or the complete 4,336-byte "
"workspace is implemented. The runner records L0/L1/L2 occupancy, per-turn "
"compaction/eviction counters and semantic-retrieval use so a >32-KiB "
"source-equivalent actual SDK conversation can prove bounded distant "
"semantic recall before the final tokenizer wire replaces the temporary "
"L0 byte representation.\n"
)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_source() -> None:
    text = SRC.read_text(encoding="utf-8")
    if "unsigned char ai_l0ring[896];" in text:
        return
    text = replace_once(
        text,
        "unsigned char ai_mstage[64];\n",
        "unsigned char ai_mstage[64];\n" + GLOBALS,
        "source globals",
    )
    text = replace_once(
        text,
        "\nvoid ai_start(void)\n",
        "\n" + FUNCS + "void ai_start(void)\n",
        "source functions",
    )
    text = replace_once(
        text,
        "    ai_mreads = 0;\n    ai_start();\n",
        "    ai_mreads = 0;\n"
        "    ai_l0head = 0;\n"
        "    ai_l0bytes = 0;\n"
        "    ai_l0count = 0;\n"
        "    ai_l1count = 0;\n"
        "    ai_l2count = 0;\n"
        "    ai_compact = 0;\n"
        "    ai_l2evict = 0;\n"
        "    ai_l1drop = 0;\n"
        "    ai_litloss = 0;\n"
        "    ai_encfail = 0;\n"
        "    ai_semuse = 0;\n"
        "    ai_start();\n",
        "source init",
    )
    text = replace_once(
        text,
        "        ai_litset = 0;\n"
        "        ai_lituse = 0;\n"
        "        namecmd = ai_namecmd();\n",
        "        ai_litset = 0;\n"
        "        ai_lituse = 0;\n"
        "        ai_compact = 0;\n"
        "        ai_l2evict = 0;\n"
        "        ai_l1drop = 0;\n"
        "        ai_litloss = 0;\n"
        "        ai_encfail = 0;\n"
        "        ai_semuse = 0;\n"
        "        namecmd = ai_namecmd();\n",
        "source per turn reset",
    )
    text = replace_once(
        text,
        "        topic = ai_pick();\n        alt = 0;\n",
        "        if (ai_pinreq() && ai_havectx) {\n"
        "            topic = ai_lasttop;\n"
        "            ai_ctxuse = 1;\n"
        "            ai_settext(\"I will remember this topic.\");\n"
        "            puts(ai_out);\n"
        "            rc = ai_ctxpair(topic);\n"
        "            if (rc < 0) ai_error = 5;\n"
        "            if (ai_turns != 65535) {\n"
        "                ai_turns = ai_turns + 1;\n"
        "            }\n"
        "            ai_yields = 0;\n"
        "            yield();\n"
        "            ai_yields = ai_yields + 1;\n"
        "            continue;\n"
        "        }\n"
        "        if (ai_recallreq()) {\n"
        "            topic = ai_semrecall();\n"
        "            if (topic != 65535) {\n"
        "                ai_ctxuse = 1;\n"
        "                ai_semuse = 1;\n"
        "            } else {\n"
        "                topic = ai_pick();\n"
        "            }\n"
        "        } else {\n"
        "            topic = ai_pick();\n"
        "        }\n"
        "        alt = 0;\n",
        "source semantic controller",
    )
    text = replace_once(
        text,
        "        if (rc < 0) {\n"
        "            ai_error = 4;\n"
        "            puts(\"Model data unavailable.\");\n",
        "        if (rc < 0) {\n"
        "            ai_error = 4;\n"
        "            ai_settext(\"Model data unavailable.\");\n"
        "            puts(ai_out);\n",
        "source model error text",
    )
    text = replace_once(
        text,
        "        if (ai_histuse) {\n",
        "        rc = ai_ctxpair(topic);\n"
        "        if (rc < 0 && ai_error == 0) ai_error = 5;\n"
        "        if (ai_histuse) {\n",
        "source context commit",
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
    if '"ai_semuse"' in text:
        return
    text = replace_once(
        text,
        '                     "ai_mhits", "ai_mbytes",\n'
        '                     "ai_mreads"):\n',
        '                     "ai_mhits", "ai_mbytes",\n'
        '                     "ai_mreads", "ai_l0bytes",\n'
        '                     "ai_l1count", "ai_l2count",\n'
        '                     "ai_compact", "ai_l2evict",\n'
        '                     "ai_l1drop", "ai_litloss",\n'
        '                     "ai_encfail", "ai_semuse"):\n',
        "runner diagnostics",
    )
    anchor = '''        turns.append({
            "turn": i + 1,
            "user": prompt,
            "assistant_raw": event["text"],
            "assistant": reply,
            "diag": event["diag"],
            "expected_keyword": expected,
            "keyword_hit": hit,
            "expected_context": want_ctx,
            "context_used": used_ctx,
            "context_hit": ctx_hit,
            "expected_alternate": want_alt,
            "alternate_used": used_alt,
            "alternate_hit": alt_hit,
            "expected_history": want_hist,
            "history_used": used_hist,
            "history_hit": hist_hit,
            "expected_literal": want_lit,
            "literal_mode": used_lit,
            "literal_hit": lit_hit,
        })
    transcript = {
'''
    extra = '''        turns.append({
            "turn": i + 1,
            "user": prompt,
            "assistant_raw": event["text"],
            "assistant": reply,
            "diag": event["diag"],
            "expected_keyword": expected,
            "keyword_hit": hit,
            "expected_context": want_ctx,
            "context_used": used_ctx,
            "context_hit": ctx_hit,
            "expected_alternate": want_alt,
            "alternate_used": used_alt,
            "alternate_hit": alt_hit,
            "expected_history": want_hist,
            "history_used": used_hist,
            "history_hit": hist_hit,
            "expected_literal": want_lit,
            "literal_mode": used_lit,
            "literal_hit": lit_hit,
        })
    dialogue_bytes = sum(
        len(turn["user"].encode("ascii"))
        + len(turn["assistant"].encode("ascii"))
        for turn in turns
    )
    compact_total = sum(
        turn["diag"].get("ai_compact", 0) for turn in turns
    )
    l2evict_total = sum(
        turn["diag"].get("ai_l2evict", 0) for turn in turns
    )
    semuse_total = sum(
        turn["diag"].get("ai_semuse", 0) for turn in turns
    )
    max_l0bytes = max(
        (turn["diag"].get("ai_l0bytes", 0) for turn in turns),
        default=0,
    )
    max_l1count = max(
        (turn["diag"].get("ai_l1count", 0) for turn in turns),
        default=0,
    )
    max_l2count = max(
        (turn["diag"].get("ai_l2count", 0) for turn in turns),
        default=0,
    )
    if max_l0bytes > 896:
        raise RuntimeError("target L0 exceeded 896 bytes")
    if max_l1count > 48:
        raise RuntimeError("target L1 exceeded 48 capsules")
    if max_l2count > 24:
        raise RuntimeError("target L2 exceeded 24 capsules")
    if dialogue_bytes < int(req.get("min_dialogue_bytes", 0)):
        raise RuntimeError("dialogue byte endurance gate failed")
    if compact_total < int(req.get("min_compactions", 0)):
        raise RuntimeError("context compaction gate failed")
    if max_l2count < int(req.get("min_l2_count", 0)):
        raise RuntimeError("L2 occupancy gate failed")
    if semuse_total < int(req.get("min_semantic_uses", 0)):
        raise RuntimeError("semantic retrieval gate failed")
    transcript = {
'''
    text = replace_once(text, anchor, extra, "runner metrics")
    text = replace_once(
        text,
        '        "accepted_turns": feeder.diag().get("ai_turns"),\n'
        '    }\n',
        '        "accepted_turns": feeder.diag().get("ai_turns"),\n'
        '        "dialogue_source_bytes": dialogue_bytes,\n'
        '        "context_compactions": compact_total,\n'
        '        "context_l2_evictions": l2evict_total,\n'
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "max_l0bytes": max_l0bytes,\n'
        '        "max_l1count": max_l1count,\n'
        '        "max_l2count": max_l2count,\n'
        '    }\n',
        "runner score",
    )
    text = replace_once(
        text,
        '        "cold_model_max_request": vm.model_max_request,\n'
        '    }\n',
        '        "cold_model_max_request": vm.model_max_request,\n'
        '        "dialogue_source_bytes": dialogue_bytes,\n'
        '        "context_compactions": compact_total,\n'
        '        "context_l2_evictions": l2evict_total,\n'
        '        "semantic_retrieval_uses": semuse_total,\n'
        '        "max_l0bytes": max_l0bytes,\n'
        '        "max_l1count": max_l1count,\n'
        '        "max_l2count": max_l2count,\n'
        '    }\n',
        "runner run metadata",
    )
    RUN.write_text(text, encoding="utf-8")


def patch_design() -> None:
    text = DESIGN.read_text(encoding="utf-8")
    if "Revision: 0.21-draft" in text:
        return
    text = replace_once(
        text,
        "Revision: 0.20-draft",
        "Revision: 0.21-draft",
        "design revision",
    )
    anchor = (
        "Implementation measurement note (Revision 0.19): iteration 6 "
        "validated bounded recovery of earlier topics across intervening "
        "topic changes. The next prototype allocates the full designed "
        "272-byte session-literal storage as parallel C48 arrays (eight "
        "generation values, eight lengths, and 8 x 31 presentation bytes) "
        "while initially using slot 0 only for an exact user-name literal. "
        "Generation advances in the designed 1..4095 range on correction. "
        "This slice tests exact literal retention/correction; semantic refs, "
        "eight-slot eviction and L1/L2 invalidation remain future work.\n"
    )
    text = replace_once(text, anchor, anchor + NOTE, "design note")
    DESIGN.write_text(text, encoding="utf-8")


def main() -> int:
    patch_source()
    patch_runner()
    patch_design()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
