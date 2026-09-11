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
"""Independent fail-closed admission check for protected ZX-UX tests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_gate import (
    FALLBACK_MODEL,
    PRIMARY_MODEL,
    PROTOCOL_VERSION,
    authority_receipt_fields,
    build_authority_binding,
    code_packet,
    load_cr_scope,
    requirements_manifest_hash,
    resolve_inside,
    review_scope_paths,
    scope_manifest_hash,
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git operation failed")
    return result.stdout


def reject(reason: str) -> int:
    print(json.dumps({"admitted": False, "reason": reason}, sort_keys=True))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cr", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--requirements", action="append", required=True)
    parser.add_argument("--scope-file")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    try:
        receipt_path = root / "test-artefacts" / "reviewer" / "code-pass.json"
        if not receipt_path.is_file():
            return reject("missing CODE PASS receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("schema_version") != PROTOCOL_VERSION:
            return reject("unsupported receipt schema")
        if receipt.get("verdict") != "PASS" or receipt.get("review_complete") is not True:
            return reject("receipt is not a complete PASS")
        if receipt.get("cr_number") != args.cr:
            return reject("receipt CR mismatch")
        current_head = git(root, "rev-parse", "HEAD").strip()
        if args.head != current_head or receipt.get("reviewed_head") != current_head:
            return reject("reviewed head mismatch")
        if git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
            return reject("working tree is not clean")
        scope = load_cr_scope(root, args.cr, args.scope_file)
        records = []
        for value in sorted(set(args.requirements)):
            path = resolve_inside(root, value)
            data = path.read_bytes()
            import hashlib
            records.append({"source": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "content": data.decode("utf-8")})
        binding = build_authority_binding(root, scope, records)
        packet = code_packet(root, args.base, args.head, binding, review_scope_paths(scope))
        if receipt.get("snapshot_id") != packet.snapshot_id:
            return reject("snapshot identity mismatch")
        if receipt.get("packet_manifest_hash") != packet.packet_manifest_hash:
            return reject("packet identity mismatch")
        if receipt.get("requirements_manifest_hash") != requirements_manifest_hash(records):
            return reject("requirements identity mismatch")
        if receipt.get("scope_manifest_hash") != scope_manifest_hash(scope):
            return reject("scope identity mismatch")
        expected_authority = authority_receipt_fields(binding)
        actual_authority = {field: receipt.get(field) for field in expected_authority}
        if actual_authority != expected_authority:
            return reject("authority identity mismatch")
        expected_requirement_ids = {
            item["id"] for item in binding["implementation_authority"]["normative_requirements"]
        }
        coverage = receipt.get("requirement_coverage")
        if not isinstance(coverage, list) or {item.get("requirement_id") for item in coverage if isinstance(item, dict)} != expected_requirement_ids:
            return reject("requirement coverage identity mismatch")
        if any(not isinstance(item, dict) or item.get("status") != "PASS"
               or not all(isinstance(item.get(field), str) and item[field].strip()
                          for field in ("implementation_location", "proof", "falsification"))
               for item in coverage):
            return reject("requirement coverage is incomplete")
        if receipt.get("primary_model") != PRIMARY_MODEL or receipt.get("fallback_model") != FALLBACK_MODEL:
            return reject("model policy mismatch")
        print(json.dumps({"admitted": True, "head": current_head, "snapshot_id": packet.snapshot_id}, sort_keys=True))
        return 0
    except Exception as exc:
        return reject(type(exc).__name__ + ": " + str(exc))


if __name__ == "__main__":
    sys.exit(main())
