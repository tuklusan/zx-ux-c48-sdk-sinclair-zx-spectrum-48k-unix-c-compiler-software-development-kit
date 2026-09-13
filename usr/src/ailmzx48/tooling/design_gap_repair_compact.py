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
# Attribution required: Based on original work by Supratim Sanyal of
# SANYALnet Labs. See root LICENSE for full terms.
# ============================================================================
from __future__ import annotations

import sys
from pathlib import Path

import design_gap_repair as d

ROOT = d.ROOT
AILM = d.AILM

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


def move_runtime_blocks() -> None:
    src = AILM / "ailmzx48.c"
    lit = AILM / "ailit.h"
    ctx = AILM / "aictx.h"
    text = src.read_text(encoding="utf-8")

    start = text.index("int ai_catraw(char *s)\n")
    end = text.index("void ai_histpush", start)
    name_block = text[start:end]
    text = text[:start] + (
        "void ai_nameack(void);\n"
        "void ai_nameans(void);\n\n"
    ) + text[end:]

    start = text.index("unsigned int ai_protect")
    end = text.index("void ai_l2merge", start)
    evict_block = text[start:end]
    text = text[:start] + '#include "aievict.h"\n\n' + text[end:]

    start = text.index("int ai_ctxcheck")
    end = text.index("int ai_ctxpair", start)
    ctx_block = text[start:end]
    text = text[:start] + text[end:]
    src.write_text(text, encoding="utf-8")

    evict = AILM / "aievict.h"
    evict.write_text(HEADER + "\n" + evict_block, encoding="utf-8")

    ltext = lit.read_text(encoding="utf-8")
    anchor = "void ai_namesuper(void)\n"
    if anchor not in ltext:
        raise RuntimeError("ailit insertion anchor missing")
    ltext = ltext.replace(anchor, name_block + anchor, 1)
    lit.write_text(ltext, encoding="utf-8")

    ctext = ctx.read_text(encoding="utf-8")
    if not ctext.endswith("}\n"):
        raise RuntimeError("aictx end anchor missing")
    ctx.write_text(ctext + "\n" + ctx_block, encoding="utf-8")

    if src.stat().st_size > 32768:
        raise RuntimeError(
            f"primary source still exceeds ceiling: {src.stat().st_size}"
        )


def main() -> int:
    d.patch_runtime()
    move_runtime_blocks()
    d.run(
        sys.executable,
        "-B",
        "usr/src/ailmzx48/evaluation/test_context_reference.py",
    )
    d.run(
        sys.executable,
        "-B",
        "usr/src/ailmzx48/evaluation/test_a48m_reference.py",
    )
    d.run(
        sys.executable,
        "-B",
        "compiler/c48.py",
        "usr/src/ailmzx48/ailmzx48.c",
        "-o",
        "usr/bin/ailmzx48/ailmzx48.c48b",
    )
    d.run("git", "diff", "--check")

    tmp = Path("/tmp/ailmzx48-sdk-conformance")
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    d.make_requests(tmp)
    for item in ("literal", "final-a", "final-b", "final-c"):
        d.run(
            sys.executable,
            "-B",
            "usr/src/ailmzx48/tooling/run_iteration.py",
            "--request",
            str(tmp / f"{item}.json"),
            "--max-seconds",
            "1200",
        )
    d.retain_evidence(tmp)
    d.restore_model_and_compile()
    d.check_evidence_identity()
    d.run(
        sys.executable,
        "-B",
        "usr/src/ailmzx48/evaluation/test_context_reference.py",
    )
    d.run(
        sys.executable,
        "-B",
        "usr/src/ailmzx48/evaluation/test_a48m_reference.py",
    )
    d.run("git", "diff", "--check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
