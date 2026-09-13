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
    text = replace_once(
        text,
        "import json\nfrom pathlib import Path\n",
        "import json\nimport signal\nfrom pathlib import Path\n",
    )
    text = replace_once(
        text,
        "if not isinstance(prompts, list) or len(prompts) > 24:\n"
        "        raise RuntimeError(\"prompts must be a list of at most 24 strings\")",
        "if not isinstance(prompts, list) or len(prompts) > 500:\n"
        "        raise RuntimeError(\"prompts must be a list of at most 500 strings\")",
    )
    text = replace_once(
        text,
        "    program = read(BIN)\n",
        "    max_steps = 2000000 + len(prompts) * 250000\n"
        "    program = read(BIN)\n",
    )
    text = replace_once(
        text,
        "                   max_steps=2000000,\n",
        "                   max_steps=max_steps,\n",
    )
    text = replace_once(
        text,
        "    feeder.vm = vm\n    status = vm.run()\n",
        "    feeder.vm = vm\n"
        "    remaining = limit - int(time.monotonic() - started)\n"
        "    if remaining < 1:\n"
        "        raise TimeoutError(\"active session time exhausted\")\n"
        "    def session_timeout(signum, frame):\n"
        "        raise TimeoutError(\"active session exceeded limit\")\n"
        "    old_handler = signal.signal(signal.SIGALRM, session_timeout)\n"
        "    signal.alarm(remaining)\n"
        "    try:\n"
        "        status = vm.run()\n"
        "    finally:\n"
        "        signal.alarm(0)\n"
        "        signal.signal(signal.SIGALRM, old_handler)\n",
    )
    text = replace_once(
        text,
        "    turns = []\n    keyword_hits = 0\n",
        "    turns = []\n    keyword_hits = 0\n    keyword_total = 0\n",
    )
    text = replace_once(
        text,
        "        hit = expected is None or expected in reply.lower()\n"
        "        if hit:\n"
        "            keyword_hits += 1\n",
        "        hit = expected is None or expected in reply.lower()\n"
        "        if expected is not None:\n"
        "            keyword_total += 1\n"
        "            if hit:\n"
        "                keyword_hits += 1\n",
    )
    text = replace_once(
        text,
        "        \"keyword_hits\": keyword_hits,\n"
        "        \"keyword_total\": len(turns),\n"
        "        \"keyword_ratio\": keyword_hits / len(turns),\n",
        "        \"keyword_hits\": keyword_hits,\n"
        "        \"keyword_total\": keyword_total,\n"
        "        \"keyword_ratio\": (\n"
        "            keyword_hits / keyword_total\n"
        "            if keyword_total else 1.0\n"
        "        ),\n",
    )
    text = replace_once(
        text,
        "        \"max_steps\": 2000000,\n",
        "        \"max_steps\": max_steps,\n",
    )
    compile(text, str(PATH), "exec")
    PATH.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
