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
# SANYALnet Labs."
# ============================================================================
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
AILM = ROOT / "usr" / "src" / "ailmzx48"


def run(*args: str) -> None:
    subprocess.run(list(args), cwd=ROOT, check=True)


def rep(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing: {path}")
    if text.count(old) != 1:
        raise RuntimeError(f"patch anchor not unique: {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def patch_runtime() -> None:
    src = AILM / "ailmzx48.c"
    lit = AILM / "ailit.h"

    rep(
        src,
        "unsigned int ai_litold;\n"
        "unsigned int ai_litnext;\n"
        "char ai_in[192];\n",
        "unsigned int ai_litold;\n"
        "char ai_in[192];\n",
    )

    rep(
        src,
        "unsigned int ai_slotref(unsigned int slot);\n"
        "unsigned int ai_namefind(void);\n"
        "void ai_namesem(void);\n"
        "void ai_putref(unsigned int ref);\n",
        "unsigned int ai_slotref(unsigned int slot);\n"
        "unsigned int ai_namefind(void);\n"
        "unsigned int ai_litpick(char *s, unsigned int start,\n"
        "                        unsigned int n);\n"
        "int ai_refvalid(unsigned int ref);\n"
        "void ai_namesem(void);\n"
        "void ai_settext(char *s);\n",
    )

    rep(
        src,
        "    slot = ai_litnext;\n"
        "    ai_litnext = (ai_litnext + 1) % 8;\n"
        "    ai_litold = ai_slotref(slot);\n"
        "    gen = ai_litgen[slot] + 1;\n",
        "    slot = ai_litpick(ai_in, start, n);\n"
        "    if (slot >= 8) {\n"
        "        slot = slot - 8;\n"
        "        ai_litold = 0;\n"
        "        ai_litcur = ai_slotref(slot);\n"
        "        ai_litset = 1;\n"
        "        return 1;\n"
        "    }\n"
        "    ai_litold = ai_slotref(slot);\n"
        "    gen = ai_litgen[slot] + 1;\n",
    )

    rep(
        src,
        '''void ai_putraw(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0) {
        putchar(s[i]);
        i = i + 1;
    }
}

void ai_nameack(void)
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
''',
        '''int ai_catraw(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0) {
        if (ai_olen >= 255) return 0;
        ai_out[ai_olen] = s[i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    ai_out[ai_olen] = 0;
    return 1;
}

int ai_catref(unsigned int ref)
{
    unsigned int slot;
    unsigned int off;
    unsigned int i;
    if (!ai_refvalid(ref)) return 0;
    slot = ref & 7;
    if (ai_litlen[slot] > 255 - ai_olen) return 0;
    off = slot * 31;
    i = 0;
    while (i < ai_litlen[slot]) {
        ai_out[ai_olen] = ai_litbuf[off + i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    ai_out[ai_olen] = 0;
    return 1;
}

void ai_nameack(void)
{
    ai_settext("I will remember ");
    if (!ai_catref(ai_litcur) || !ai_catraw(".")) {
        ai_settext("I could not store that name.");
    }
    puts(ai_out);
}

void ai_nameans(void)
{
    unsigned int ref;
    ref = ai_namefind();
    if (ref == 0) {
        ai_settext("I do not have your name yet.");
        puts(ai_out);
        return;
    }
    ai_lituse = 1;
    ai_semuse = 1;
    ai_settext("I remember your name as ");
    if (!ai_catref(ref) || !ai_catraw(".")) {
        ai_settext("I could not recover your name.");
    }
    puts(ai_out);
}
''',
    )

    rep(
        src,
        '''unsigned int ai_victim(unsigned char *p, unsigned int count)
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
''',
        '''unsigned int ai_protect(unsigned char *p,
                        unsigned int o)
{
    unsigned int src;
    if ((p[o] & 4) != 0 || (p[o] & 16) != 0) return 3;
    src = (p[o] / 64) & 3;
    if (src == 0) return 2;
    if (src == 1) return 1;
    return 0;
}

unsigned int ai_victim(unsigned char *p, unsigned int count)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bprot;
    unsigned int bimp;
    unsigned int bage;
    unsigned int prot;
    unsigned int imp;
    unsigned int age;
    int found;
    best = 0;
    bprot = 0;
    bimp = 0;
    bage = 0;
    found = 0;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        if (p[o + 1] != 0) {
            prot = ai_protect(p, o);
            imp = p[o + 14];
            age = p[o + 15];
            if (!found || prot < bprot ||
                (prot == bprot && imp < bimp) ||
                (prot == bprot && imp == bimp &&
                 age > bage)) {
                best = i;
                bprot = prot;
                bimp = imp;
                bage = age;
                found = 1;
            }
        }
        i = i + 1;
    }
    return best;
}
''',
    )

    rep(
        src,
        '''int ai_ctxpair(unsigned int topic)
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
''',
        '''int ai_ctxcheck(unsigned int un, unsigned int an)
{
    unsigned int bytes;
    unsigned int count;
    unsigned int drop;
    unsigned int need;
    unsigned int n;
    if (un == 65535 || an == 65535) return -1;
    need = un + an;
    if (need > 896) return -1;
    if (ai_l0bytes > 896 || ai_l0count > 32) return -2;
    if ((ai_l0count & 1) != 0) return -2;
    bytes = ai_l0bytes;
    count = ai_l0count;
    drop = 0;
    while (bytes + need > 896 || count + 2 > 32) {
        if (count < 2 || drop + 1 >= ai_l0count) return -2;
        n = ai_l0len[drop] + ai_l0len[drop + 1];
        if (n == 0 || n > bytes) return -2;
        bytes = bytes - n;
        count = count - 2;
        drop = drop + 2;
    }
    return 0;
}

int ai_ctxpair(unsigned int topic)
{
    unsigned int un;
    unsigned int an;
    unsigned int need;
    un = ai_encsize(ai_in);
    an = ai_encsize(ai_out);
    if (ai_ctxcheck(un, an) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    need = un + an;
    ai_capage();
    while (ai_l0bytes + need > 896 ||
           ai_l0count + 2 > 32) {
        if (ai_ctxevict() != 0) {
            ai_error = 6;
            return -1;
        }
    }
    if (ai_ctxwrite(ai_in, 0, topic) != 0) {
        ai_error = 6;
        return -1;
    }
    if (ai_ctxwrite(ai_out, 1, topic) != 0) {
        ai_error = 6;
        return -1;
    }
    return 0;
}
''',
    )

    rep(
        src,
        "    int namecmd;\n"
        "    ai_turns = 0;\n",
        "    int namecmd;\n"
        "    int stored;\n"
        "    ai_turns = 0;\n",
    )
    rep(
        src,
        "    ai_litold = 0;\n"
        "    ai_litnext = 0;\n"
        "    ai_drop_lf = 0;\n",
        "    ai_litold = 0;\n"
        "    ai_drop_lf = 0;\n",
    )

    rep(
        src,
        '''        if (namecmd != 0) {
            ai_otokens = 0;
            ai_error = 0;
            if (namecmd == 1) {
                if (ai_setname()) {
                    ai_namesem();
                    ai_nameack();
                } else {
                    puts("I could not store that name.");
                }
            } else {
                ai_nameans();
            }
            if (ai_turns != 65535) {
                ai_turns = ai_turns + 1;
            }
            ai_yields = 0;
            yield();
            ai_yields = ai_yields + 1;
            continue;
        }
''',
        '''        if (namecmd != 0) {
            ai_otokens = 0;
            ai_error = 0;
            stored = 0;
            if (namecmd == 1) {
                if (ai_setname()) {
                    ai_nameack();
                    stored = 1;
                } else {
                    ai_settext("I could not store that name.");
                    puts(ai_out);
                }
            } else {
                ai_nameans();
            }
            rc = ai_ctxpair(ai_t_id);
            if (rc < 0 && ai_error == 0) ai_error = 5;
            if (stored && rc >= 0) ai_namesem();
            if (ai_turns != 65535) {
                ai_turns = ai_turns + 1;
            }
            ai_yields = 0;
            yield();
            ai_yields = ai_yields + 1;
            continue;
        }
''',
    )

    rep(
        lit,
        '''void ai_invref(unsigned int ref)
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
''',
        '''int ai_capref(unsigned char *p, unsigned int o,
              unsigned int ref)
{
    if (ai_capget(p, o + 4) == ref) return 1;
    if (ai_capget(p, o + 6) == ref) return 1;
    if (ai_capget(p, o + 8) == ref) return 1;
    if (ai_capget(p, o + 10) == ref) return 1;
    if (p[o + 1] == 3 &&
        ai_capget(p, o + 12) == ref) return 1;
    return 0;
}

void ai_clrref(unsigned char *p, unsigned int count,
               unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int at;
    int lost;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        lost = 0;
        if (p[o + 1] != 0) {
            at = 4;
            while (at <= 10) {
                if (ai_capget(p, o + at) == ref) {
                    p[o + at] = 0;
                    p[o + at + 1] = 0;
                    lost = 1;
                }
                at = at + 2;
            }
            if (p[o + 1] == 3 &&
                ai_capget(p, o + 12) == ref) {
                p[o + 12] = 0;
                p[o + 13] = 0;
                lost = 1;
            }
            if (lost && ai_litloss != 65535) {
                ai_litloss = ai_litloss + 1;
            }
        }
        i = i + 1;
    }
}

void ai_invref(unsigned int ref)
{
    if (ref == 0) return;
    ai_clrref(ai_l1, 48, ref);
    ai_clrref(ai_l2, 24, ref);
}

int ai_litmatch(unsigned int slot, char *s,
                unsigned int start, unsigned int n)
{
    unsigned int i;
    unsigned int off;
    if (slot >= 8 || ai_litlen[slot] != n) return 0;
    off = slot * 31;
    i = 0;
    while (i < n) {
        if (ai_lower(ai_litbuf[off + i]) !=
            ai_lower(s[start + i])) return 0;
        i = i + 1;
    }
    return 1;
}

unsigned int ai_litpick(char *s, unsigned int start,
                        unsigned int n)
{
    unsigned int slot;
    unsigned int ref;
    unsigned int i;
    unsigned int o;
    unsigned int prot;
    unsigned int imp;
    unsigned int age;
    unsigned int sp;
    unsigned int si;
    unsigned int sa;
    unsigned int best;
    unsigned int bp;
    unsigned int bi;
    unsigned int ba;
    int found;
    int any;
    slot = 0;
    while (slot < 8) {
        if (ai_slotref(slot) != 0 &&
            ai_litmatch(slot, s, start, n)) return slot + 8;
        slot = slot + 1;
    }
    slot = 0;
    while (slot < 8) {
        ref = ai_slotref(slot);
        any = 0;
        if (ref != 0) {
            i = 0;
            while (i < 48 && !any) {
                o = ai_capoff(i);
                if (ai_l1[o + 1] != 0 &&
                    ai_capref(ai_l1, o, ref)) any = 1;
                i = i + 1;
            }
            i = 0;
            while (i < 24 && !any) {
                o = ai_capoff(i);
                if (ai_l2[o + 1] != 0 &&
                    ai_capref(ai_l2, o, ref)) any = 1;
                i = i + 1;
            }
        }
        if (!any) return slot;
        slot = slot + 1;
    }
    best = 0;
    bp = 0;
    bi = 0;
    ba = 0;
    found = 0;
    slot = 0;
    while (slot < 8) {
        ref = ai_slotref(slot);
        sp = 0;
        si = 0;
        sa = 255;
        any = 0;
        i = 0;
        while (i < 48) {
            o = ai_capoff(i);
            if (ai_l1[o + 1] != 0 &&
                ai_capref(ai_l1, o, ref)) {
                prot = ai_protect(ai_l1, o);
                imp = ai_l1[o + 14];
                age = ai_l1[o + 15];
                if (!any || prot > sp ||
                    (prot == sp && imp > si) ||
                    (prot == sp && imp == si && age < sa)) {
                    sp = prot;
                    si = imp;
                    sa = age;
                    any = 1;
                }
            }
            i = i + 1;
        }
        i = 0;
        while (i < 24) {
            o = ai_capoff(i);
            if (ai_l2[o + 1] != 0 &&
                ai_capref(ai_l2, o, ref)) {
                prot = ai_protect(ai_l2, o);
                imp = ai_l2[o + 14];
                age = ai_l2[o + 15];
                if (!any || prot > sp ||
                    (prot == sp && imp > si) ||
                    (prot == sp && imp == si && age < sa)) {
                    sp = prot;
                    si = imp;
                    sa = age;
                    any = 1;
                }
            }
            i = i + 1;
        }
        if (!found || sp < bp ||
            (sp == bp && si < bi) ||
            (sp == bp && si == bi && sa > ba)) {
            best = slot;
            bp = sp;
            bi = si;
            ba = sa;
            found = 1;
        }
        slot = slot + 1;
    }
    return best;
}
''',
    )

    rep(
        lit,
        "void ai_namesem(void)\n"
        "{\n"
        "    ai_capage();\n"
        "    ai_namesuper();\n",
        "void ai_namesem(void)\n"
        "{\n"
        "    ai_namesuper();\n",
    )


def make_requests(tmp: Path) -> None:
    names = [
        "Alice",
        "Bob",
        "Carol",
        "Dave",
        "Erin",
        "Frank",
        "Grace",
        "Heidi",
        "Ivy",
    ]
    prompts = [f"my name is {name}" for name in names]
    expected = [name.lower() for name in names]
    prompts += [
        "where in 48k memory does the screen bitmap live"
    ] * 60
    expected += ["16384"] * 60
    prompts.append("what is my name")
    expected.append("ivy")
    req = {
        "schema": 1,
        "iteration": 9101,
        "scenario": "sdk-design-literal-context-v1",
        "purpose": (
            "Post-repair SDK proof for deterministic literal-slot selection, "
            "stale-reference invalidation, bounded context compaction, and "
            "newest-name recovery."
        ),
        "max_seconds": 1200,
        "prompts": prompts,
        "expected_keywords": expected,
        "min_keyword_ratio": 1.0,
        "min_compactions": 1,
        "min_l2_count": 1,
        "min_semantic_uses": 50,
        "min_literal_losses": 1,
        "min_lmcount": 96,
        "final_expected_keyword": "ivy",
    }
    (tmp / "literal.json").write_text(
        json.dumps(req, indent=2) + "\n", encoding="utf-8"
    )
    for src_iter, dst_iter, name in [
        (52, 9102, "final-a"),
        (53, 9103, "final-b"),
        (54, 9104, "final-c"),
    ]:
        path = AILM / "training" / "requests" / f"iter-{src_iter:04d}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["iteration"] = dst_iter
        data["purpose"] = (
            data.get("purpose", "")
            + " Post-design-gap-repair SDK requalification."
        ).strip()
        (tmp / f"{name}.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )


def retain_evidence(tmp: Path) -> None:
    base = AILM / "evaluation" / "sdk-conformance"
    base.mkdir(parents=True, exist_ok=True)
    items = [
        (9101, "literal-context", "literal.json"),
        (9102, "final-a", "final-a.json"),
        (9103, "final-b", "final-b.json"),
        (9104, "final-c", "final-c.json"),
    ]
    for iteration, name, reqname in items:
        source = AILM / "conversations" / f"iter-{iteration:04d}"
        target = base / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        shutil.copy2(tmp / reqname, target / "request.json")
        score = json.loads((target / "score.json").read_text())
        if score["keyword_ratio"] != 1.0 or not score["clean_exit"]:
            raise RuntimeError(f"{name}: post-repair score gate failed")
        shutil.rmtree(source)
        model = AILM / "model" / "iterations" / f"iter-{iteration:04d}.json"
        model.unlink()
    literal = json.loads(
        (base / "literal-context" / "score.json").read_text()
    )
    if literal["literal_reference_losses"] < 1:
        raise RuntimeError("literal-context: expected invalidation missing")
    if literal["context_compactions"] < 1 or literal["max_l2count"] < 1:
        raise RuntimeError("literal-context: compaction proof missing")
    for name in ("final-a", "final-b", "final-c"):
        score = json.loads((base / name / "score.json").read_text())
        if score["literal_reference_losses"] != 0:
            raise RuntimeError(f"{name}: unexpected literal loss")


def restore_model_and_compile() -> None:
    run(
        "git",
        "checkout",
        "HEAD",
        "--",
        "usr/src/ailmzx48/aimod.h",
        "usr/src/ailmzx48/model/current-model.json",
        "usr/src/ailmzx48/model/cold-seed.bin",
        "usr/src/ailmzx48/model/cold-seed.json",
    )
    run(
        sys.executable,
        "-B",
        "compiler/c48.py",
        "usr/src/ailmzx48/ailmzx48.c",
        "-o",
        "usr/bin/ailmzx48/ailmzx48.c48b",
    )


def check_evidence_identity() -> None:
    source_hash = hashlib.sha256((AILM / "ailmzx48.c").read_bytes()).hexdigest()
    base = AILM / "evaluation" / "sdk-conformance"
    for name in ("literal-context", "final-a", "final-b", "final-c"):
        data = json.loads((base / name / "run.json").read_text())
        if data["source_sha256"] != source_hash:
            raise RuntimeError(f"{name}: source identity mismatch")


def main() -> int:
    patch_runtime()
    run(sys.executable, "-B", "usr/src/ailmzx48/evaluation/test_context_reference.py")
    run(sys.executable, "-B", "usr/src/ailmzx48/evaluation/test_a48m_reference.py")
    run(
        sys.executable,
        "-B",
        "compiler/c48.py",
        "usr/src/ailmzx48/ailmzx48.c",
        "-o",
        "usr/bin/ailmzx48/ailmzx48.c48b",
    )
    run("git", "diff", "--check")

    tmp = Path("/tmp/ailmzx48-sdk-conformance")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    make_requests(tmp)
    for item in ("literal", "final-a", "final-b", "final-c"):
        run(
            sys.executable,
            "-B",
            "usr/src/ailmzx48/tooling/run_iteration.py",
            "--request",
            str(tmp / f"{item}.json"),
            "--max-seconds",
            "1200",
        )
    retain_evidence(tmp)
    restore_model_and_compile()
    check_evidence_identity()
    run(sys.executable, "-B", "usr/src/ailmzx48/evaluation/test_context_reference.py")
    run(sys.executable, "-B", "usr/src/ailmzx48/evaluation/test_a48m_reference.py")
    run("git", "diff", "--check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
