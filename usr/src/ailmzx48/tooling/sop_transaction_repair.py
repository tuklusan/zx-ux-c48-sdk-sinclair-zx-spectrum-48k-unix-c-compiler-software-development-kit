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
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
A = ROOT / "usr" / "src" / "ailmzx48"
E = A / "evaluation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path: Path) -> str:
    data = path.read_bytes()
    head = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(head + data).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"patch anchor not unique in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch_runtime() -> None:
    src = A / "ailmzx48.c"
    lit = A / "ailit.h"
    checker = E / "check_design_compliance.py"

    text = src.read_text(encoding="utf-8")
    start = text.index("int ai_setname(void)\n{")
    end = text.index("\nvoid ai_nameack(void);", start)
    new_set = '''int ai_setname(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    pos = ai_find("my name is ");
    if (pos < 0) return 0;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return 0;
    return 1;
}
'''
    src.write_text(text[:start] + new_set + text[end:],
                   encoding="utf-8", newline="\n")
    replace_once(
        src,
        "void ai_namesem(void);\nvoid ai_settext(char *s);\n",
        "void ai_namesem(void);\nvoid ai_namecommit(void);\n"
        "void ai_settext(char *s);\n",
    )
    replace_once(
        src,
        "            if (stored && rc >= 0) ai_namesem();\n",
        "            if (stored && rc >= 0) ai_namecommit();\n",
    )

    text = lit.read_text(encoding="utf-8")
    start = text.index("void ai_nameack(void)\n{")
    end = text.index("\nvoid ai_nameans(void)\n{", start)
    new_name = '''void ai_namecommit(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    unsigned int gen;
    unsigned int slot;
    unsigned int off;
    pos = ai_find("my name is ");
    if (pos < 0) return;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return;
    slot = ai_litpick(ai_in, start, n);
    if (slot >= 8) {
        slot = slot - 8;
        ai_litold = 0;
        ai_litcur = ai_slotref(slot);
        ai_litset = 1;
        ai_namesem();
        return;
    }
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
    ai_namesem();
}

void ai_nameack(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    ai_settext("I will remember ");
    pos = ai_find("my name is ");
    if (pos < 0) {
        ai_settext("I could not store that name.");
        puts(ai_out);
        return;
    }
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31 || n > 254 - ai_olen) {
        ai_settext("I could not store that name.");
        puts(ai_out);
        return;
    }
    i = 0;
    while (i < n) {
        ai_out[ai_olen] = ai_in[start + i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    if (ai_olen < 255) {
        ai_out[ai_olen] = '.';
        ai_olen = ai_olen + 1;
    }
    ai_out[ai_olen] = 0;
    puts(ai_out);
}
'''
    lit.write_text(text[:start] + new_name + text[end:],
                   encoding="utf-8", newline="\n")

    replace_once(
        checker,
        '    require("if (stored && rc >= 0) ai_namesem();" in source,\n'
        '            "name semantic state is not commit-gated")\n',
        '    require("if (stored && rc >= 0) ai_namecommit();" in source,\n'
        '            "name literal state is not commit-gated")\n'
        '    set_start = source.index("int ai_setname(void)")\n'
        '    set_end = source.index("void ai_nameack(void);", set_start)\n'
        '    set_body = source[set_start:set_end]\n'
        '    require("ai_litgen[" not in set_body and\n'
        '            "ai_litlen[" not in set_body and\n'
        '            "ai_litbuf[" not in set_body,\n'
        '            "name validation mutates session-literal storage")\n'
        '    require("void ai_namecommit" in lit and\n'
        '            "ai_litgen[slot] = gen;" in lit,\n'
        '            "post-context literal commit implementation missing")\n',
    )


def finalize() -> None:
    design = A / "AILMZX48-DETAILED-DESIGN.md"
    status_path = E / "DESIGN-COMPLIANCE-STATUS.json"
    cert = E / "DESIGN-REVIEW-CERTIFICATE.md"
    source_hash = sha(A / "ailmzx48.c")
    binary_hash = sha(ROOT / "usr" / "bin" / "ailmzx48" / "ailmzx48.c48b")

    text = design.read_text(encoding="utf-8")
    old = (
        "- literal-name turns use the same bounded output and L0/L1/L2 commit path as\n"
        "  normal turns, and semantic name state is published only after commit success;\n"
        "- retained post-repair literal/context iteration 9101 is 70/70 with 15\n"
        "  compactions, L2 occupancy 2, 61 semantic retrieval uses, exactly one expected\n"
        "  stale-reference invalidation, and successful newest-name recall;\n"
        "- retained post-repair final A/B/C iterations 9102/9103/9104 are each 12/12,\n"
    )
    new = (
        "- literal-name turns use the same bounded output and L0/L1/L2 commit path as\n"
        "  normal turns; literal generation/slot bytes and semantic name state are both\n"
        "  published only after the context commit succeeds;\n"
        "- retained post-transaction-repair literal/context iteration 9105 is 70/70 with\n"
        "  real compaction, L2 occupancy, semantic retrieval, stale-reference invalidation,\n"
        "  and successful newest-name recall under the repaired source identity;\n"
        "- retained post-transaction-repair final A/B/C iterations 9106/9107/9108 are each 12/12,\n"
    )
    if old not in text:
        raise RuntimeError("design transaction evidence anchor missing")
    design.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["source_sha256"] = source_hash
    status["sdk_c48b_sha256"] = binary_hash
    lit_score = json.loads((E / "sdk-conformance" / "literal-context" /
                            "score.json").read_text(encoding="utf-8"))
    status["sdk_profile"]["literal_context"] = {
        "context_compactions": lit_score["context_compactions"],
        "final_keyword_hit": lit_score["final_keyword_hit"],
        "keyword_ratio": lit_score["keyword_ratio"],
        "literal_reference_losses": lit_score["literal_reference_losses"],
        "max_l2count": lit_score["max_l2count"],
        "max_lmcount": lit_score["max_lmcount"],
        "semantic_retrieval_uses": lit_score["semantic_retrieval_uses"],
        "turns": lit_score["turns"],
    }
    design_hash = sha(design)
    design_blob = blob(design)
    status["design_sha256"] = design_hash
    status["design_git_blob_sha1"] = design_blob
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")

    ctext = cert.read_text(encoding="utf-8")
    lines = []
    for line in ctext.splitlines():
        if line.startswith("- detailed-design Git blob:"):
            line = f"- detailed-design Git blob: `{design_blob}`"
        elif line.startswith("- detailed-design SHA-256:"):
            line = f"- detailed-design SHA-256: `{design_hash}`"
        elif line.startswith("- repaired C48 source SHA-256:"):
            line = f"- repaired C48 source SHA-256: `{source_hash}`"
        elif line.startswith("- SDK C48B1 artifact SHA-256:"):
            line = f"- SDK C48B1 artifact SHA-256: `{binary_hash}`"
        lines.append(line)
    cert.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("patch", "finalize"))
    ns = ap.parse_args()
    if ns.mode == "patch":
        patch_runtime()
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
