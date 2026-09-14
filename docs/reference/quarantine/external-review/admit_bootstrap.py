#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
"""Independent admission check for reviewer-maintenance validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_gate import FALLBACK_MODEL, PRIMARY_MODEL, code_packet, requirement_records
from legacy_bootstrap_gate import scoped_bootstrap_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cr", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--requirements", action="append", required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--line-start", type=int)
    parser.add_argument("--line-end", type=int)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    try:
        receipt_path = root / "test-artefacts" / "reviewer" / "bootstrap-pass.json"
        if not receipt_path.is_file():
            raise RuntimeError("missing bootstrap PASS receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("verdict") != "PASS" or receipt.get("review_complete") is not True:
            raise RuntimeError("bootstrap receipt is not a complete PASS")
        if receipt.get("cr_number") != args.cr:
            raise RuntimeError("bootstrap CR mismatch")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        if args.head != head or receipt.get("reviewed_head") != head:
            raise RuntimeError("bootstrap reviewed head mismatch")
        packet = scoped_bootstrap_packet(
            code_packet(root, args.base, args.head, scope_paths=args.path),
            args.path,
            args.line_start,
            args.line_end,
        )
        if receipt.get("snapshot_id") != packet.snapshot_id:
            raise RuntimeError("bootstrap snapshot mismatch")
        requirements = requirement_records(root, args.requirements)
        expected = [{"source": item["source"], "sha256": item["sha256"]} for item in requirements]
        if receipt.get("requirement_sources") != expected:
            raise RuntimeError("bootstrap requirement identity mismatch")
        if receipt.get("primary_model") != PRIMARY_MODEL or receipt.get("fallback_model") != FALLBACK_MODEL:
            raise RuntimeError("bootstrap model policy mismatch")
        print(json.dumps({"admitted": True, "snapshot_id": packet.snapshot_id}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"admitted": False, "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
