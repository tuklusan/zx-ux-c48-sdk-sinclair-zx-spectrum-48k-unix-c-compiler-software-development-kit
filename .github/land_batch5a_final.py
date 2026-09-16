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

import importlib.util
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "batch5a_fast", HERE / "land_batch5a_fast.py"
)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load Batch-5A fast harness")
fast = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fast)
v2 = fast.v2

FINAL_SCRIPT = Path(".github/land_batch5a_final.py")
FINAL_WORKFLOW = Path(".github/workflows/land-batch5a-final.yml")
v2.TEMP.add(FINAL_SCRIPT)
v2.TEMP.add(FINAL_WORKFLOW)


def preverify():
    v2.target_checks()
    v2.c48_source_scan()
    v2.run([
        sys.executable, "-B", "-m", "unittest", "discover",
        "-s", "compiler/tests", "-p", "test_graphics_review.py", "-v",
    ])
    v2.run([
        sys.executable, "-B", "compiler/verify_graphics_demos.py", "--static",
    ])
    v2.run(["git", "diff", "--check"])
    print("BATCH-5A PRE-CLEANUP VERIFY PASS", flush=True)


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "land":
        raise SystemExit(
            "usage: land_batch5a_final.py land EVIDENCE_DIR"
        )
    evidence_dir = Path(sys.argv[2])
    if not evidence_dir.is_dir():
        raise SystemExit(f"missing evidence directory: {evidence_dir}")

    old_cleanup = v2.cleanup_temp

    def cleanup():
        old_cleanup()
        if evidence_dir.exists():
            shutil.rmtree(evidence_dir)
            print(f"removed temporary evidence {evidence_dir}", flush=True)

    v2.verify_all = preverify
    v2.cleanup_temp = cleanup
    v2.land(evidence_dir)


if __name__ == "__main__":
    main()
