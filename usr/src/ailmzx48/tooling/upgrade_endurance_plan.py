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
RUN = ROOT / "usr" / "src" / "ailmzx48" / "tooling" / "run_iteration.py"


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {n}")
    return text.replace(old, new, 1)


def main() -> int:
    text = RUN.read_text(encoding="utf-8")
    if 'prompt_plan = req.get("prompt_plan")' in text:
        return 0
    old = '''    prompts = req.get("prompts") or [
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
    new = '''    prompt_plan = req.get("prompt_plan")
    if prompt_plan is None:
        prompts = req.get("prompts") or [
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
    else:
        if not isinstance(prompt_plan, dict):
            raise RuntimeError("prompt_plan must be an object")
        prefix = prompt_plan.get("prefix", [])
        cycle = prompt_plan.get("cycle", [])
        suffix = prompt_plan.get("suffix", [])
        cycle_count = prompt_plan.get("cycle_count", 0)
        if not all(isinstance(x, list) for x in (prefix, cycle, suffix)):
            raise RuntimeError("prompt_plan lists are required")
        if isinstance(cycle_count, bool) or not isinstance(cycle_count, int):
            raise RuntimeError("cycle_count must be an integer")
        if cycle_count < 0 or cycle_count > 500:
            raise RuntimeError("cycle_count must be in 0..500")
        if cycle_count and not cycle:
            raise RuntimeError("prompt_plan cycle is empty")
        prompts = prefix + (cycle * cycle_count) + suffix
    if len(prompts) > 500:
        raise RuntimeError("expanded prompts exceed 500 turns")
'''
    text = once(text, old, new, "prompt plan")
    old = '''    if semuse_total < int(req.get("min_semantic_uses", 0)):
        raise RuntimeError("semantic retrieval gate failed")
    transcript = {
'''
    new = '''    if semuse_total < int(req.get("min_semantic_uses", 0)):
        raise RuntimeError("semantic retrieval gate failed")
    final_keyword = req.get("final_expected_keyword")
    final_keyword_hit = True
    if final_keyword is not None:
        if not isinstance(final_keyword, str) or not final_keyword:
            raise RuntimeError("final_expected_keyword must be text")
        final_keyword_hit = (
            bool(turns)
            and final_keyword.lower() in turns[-1]["assistant"].lower()
        )
        if not final_keyword_hit:
            raise RuntimeError("final keyword endurance gate failed")
    transcript = {
'''
    text = once(text, old, new, "final keyword gate")
    old = '''        "max_l2count": max_l2count,
    }
'''
    new = '''        "max_l2count": max_l2count,
        "final_keyword_hit": final_keyword_hit,
    }
'''
    if text.count(old) != 2:
        raise RuntimeError("expected score and run metric anchors")
    text = text.replace(old, new, 2)
    RUN.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
