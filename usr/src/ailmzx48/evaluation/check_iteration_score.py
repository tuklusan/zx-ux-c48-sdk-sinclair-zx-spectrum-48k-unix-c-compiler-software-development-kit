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
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AILM = ROOT / "usr" / "src" / "ailmzx48"
CONV = AILM / "conversations"


def numeric_ratio(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{name} must be numeric")
    ratio = float(value)
    if ratio < 0.0 or ratio > 1.0:
        raise RuntimeError(f"{name} must be in 0..1")
    return ratio


def report_keyword_misses(out_dir: Path) -> None:
    path = out_dir / "transcript.json"
    if not path.is_file():
        print("keyword gate diagnostics: transcript.json is missing")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    misses = [
        turn for turn in data.get("turns", [])
        if turn.get("expected_keyword") is not None
        and not turn.get("keyword_hit", False)
    ]
    if not misses:
        print("keyword gate diagnostics: no per-turn misses recorded")
        return
    for turn in misses:
        diag = turn.get("diag") or {}
        print(
            "keyword miss: "
            f"turn={turn.get('turn')} "
            f"expected={turn.get('expected_keyword')!r} "
            f"topic={diag.get('ai_lasttop')} "
            f"mhits={diag.get('ai_mhits')} "
            f"mrecords={diag.get('ai_mrecords')} "
            f"mreads={diag.get('ai_mreads')} "
            f"lmcount={diag.get('ai_lmcount')} "
            f"user={turn.get('user')!r} "
            f"assistant={turn.get('assistant')!r}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", type=Path, required=True)
    ns = ap.parse_args()

    req = json.loads(ns.request.read_text(encoding="utf-8"))
    iteration = int(req["iteration"])
    if iteration < 1:
        raise RuntimeError("iteration must be positive")

    minimum = numeric_ratio(
        req.get("min_keyword_ratio", 0.0),
        "min_keyword_ratio",
    )
    out_dir = CONV / f"iter-{iteration:04d}"
    score_path = out_dir / "score.json"
    if not score_path.is_file():
        raise RuntimeError("iteration score.json is missing")

    score = json.loads(score_path.read_text(encoding="utf-8"))
    total = score.get("keyword_total")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise RuntimeError("keyword_total must be a non-negative integer")
    if minimum > 0.0 and total == 0:
        raise RuntimeError("keyword ratio gate has no scored keywords")

    actual = numeric_ratio(score.get("keyword_ratio"), "keyword_ratio")
    if actual < minimum:
        report_keyword_misses(out_dir)
        raise RuntimeError(
            "keyword ratio gate failed: "
            f"actual={actual:.6f} minimum={minimum:.6f}"
        )

    print(
        "keyword ratio gate passed: "
        f"actual={actual:.6f} minimum={minimum:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
