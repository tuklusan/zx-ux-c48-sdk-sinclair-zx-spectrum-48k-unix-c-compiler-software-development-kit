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
PATH = ROOT / "usr/src/ailmzx48/tooling/run_iteration.py"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError("unexpected harness source while upgrading")
    return text.replace(old, new, 1)


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    old = '''    prompts = req.get("prompts") or [
        "who are you",
        "tell me about the spectrum",
        "what happened in 1982",
        "what about 48k memory",
        "why does memory matter",
        "can you chat locally",
    ]
    if not isinstance(prompts, list) or len(prompts) > 500:
        raise RuntimeError("prompts must be a list of at most 500 strings")
'''
    new = '''    prompts = req.get("prompts") or [
        "who are you",
        "tell me about the spectrum",
        "what happened in 1982",
        "what about 48k memory",
        "why does memory matter",
        "can you chat locally",
    ]
    repeat_count = req.get("repeat_count", 1)
    if isinstance(repeat_count, bool):
        raise RuntimeError("repeat_count must be an integer")
    if not isinstance(repeat_count, int):
        raise RuntimeError("repeat_count must be an integer")
    if repeat_count < 1 or repeat_count > 500:
        raise RuntimeError("repeat_count must be in 1..500")
    if not isinstance(prompts, list):
        raise RuntimeError("prompts must be a list")
    prompts = prompts * repeat_count
    if len(prompts) > 500:
        raise RuntimeError("expanded prompts exceed 500 turns")
'''
    text = replace_once(text, old, new)
    compile(text, str(PATH), "exec")
    PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
