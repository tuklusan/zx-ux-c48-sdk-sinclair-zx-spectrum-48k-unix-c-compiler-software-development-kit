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
# SANYALnet Labs." See LICENSE for full terms.
# ============================================================================
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
A = ROOT / "usr" / "src" / "ailmzx48"
E = A / "evaluation"
T = A / "training"
PATCH_B64 = """
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
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def git_blob_sha1(data: bytes) -> str:
    framed = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(framed).hexdigest()


def patch() -> None:
    raw = gzip.decompress(base64.b64decode(PATCH_B64))
    proc = subprocess.run(
        ["patch", "-p1", "--forward", "--batch"],
        input=raw, cwd=ROOT, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit("architecture patch failed")


def finalize() -> None:
    base = E / "sdk-conformance"
    parts_path = T / "evaluation-partitions.json"
    parts = json.loads(parts_path.read_text(encoding="utf-8"))
    reg = parts["regression"]["request_sha256"]
    for name in (
        "literal-context", "final-a", "final-b", "final-c"
    ):
        reg[name] = sha(base / name / "request.json")
    dump(parts_path, parts)

    source_sha = sha(A / "ailmzx48.c")
    binary_sha = sha(ROOT / "usr/bin/ailmzx48/ailmzx48.c48b")
    cold_sha = sha(A / "model/cold-seed.bin")
    expected = (
        "3dda3f6633cd8731e158970bf0658cd9"
        "126496e9d7c30ff14ab4cbcae25611ea"
    )
    if cold_sha != expected:
        raise SystemExit("unexpected architecture cold-model identity")
    model = json.loads((A / "model/current-model.json").read_text())
    if model.get("schema") != 3:
        raise SystemExit("unexpected schema-3 hot model")
    if len(model.get("trigram_contexts", [])) != 64:
        raise SystemExit("unexpected trigram-context count")

    status_path = E / "DESIGN-COMPLIANCE-STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["design_revision"] = "0.27-draft"
    status["source_sha256"] = source_sha
    status["sdk_c48b_sha256"] = binary_sha
    status["cold_model_sha256"] = cold_sha
    sdk = status["sdk_profile"]
    sdk["model_architecture"] = {
        "schema": 3,
        "max_order": 3,
        "trigram_contexts": 64,
        "unigram_fallback": 12,
        "topic_count": 7,
        "generic_unknown_topic": 0,
        "exact_trigger_spelling": True,
        "factual_anchor_policy":
            "subject-when-trigger-plus-predicate",
        "scan_yield_records": 8,
    }
    sdk["evaluation_partitioning"] = {
        "manifest": "training/evaluation-partitions.json",
        "blind_status": "RESERVED_UNSCORED_NOT_USED_FOR_TUNING",
        "blind_generalization_claimed": False,
    }
    lit = json.loads((base / "literal-context/score.json").read_text())
    sdk["literal_context"] = {
        key: lit[key] for key in (
            "turns", "keyword_ratio", "context_compactions",
            "max_l2count", "max_lmcount", "semantic_retrieval_uses",
            "literal_reference_losses", "final_keyword_hit",
            "trigram_uses", "cooperative_yields",
        )
    }
    finals = {}
    for name in ("final-a", "final-b", "final-c"):
        score = json.loads((base / name / "score.json").read_text())
        finals[name] = {
            key: score[key] for key in (
                "turns", "keyword_ratio", "clean_exit",
                "literal_reference_losses", "trigram_uses",
                "cooperative_yields",
            )
        }
    sdk["post_repair_final_regressions"] = finals
    route = json.loads(
        (base / "architecture-routing/score.json").read_text()
    )
    sdk["architecture_routing"] = {
        key: route[key] for key in (
            "turns", "keyword_ratio", "trigram_uses",
            "cooperative_yields", "semantic_retrieval_uses",
        )
    }

    design = A / "AILMZX48-DETAILED-DESIGN.md"
    data = design.read_bytes()
    design_sha = hashlib.sha256(data).hexdigest()
    design_blob = git_blob_sha1(data)
    status["design_sha256"] = design_sha
    status["design_git_blob_sha1"] = design_blob
    dump(status_path, status)

    cert_path = E / "DESIGN-REVIEW-CERTIFICATE.md"
    cert = cert_path.read_text(encoding="utf-8")
    cert = cert.replace(
        "current Revision-0.26 SDK implementation profile",
        "current Revision-0.27 SDK implementation profile",
    )
    lines = []
    for line in cert.splitlines():
        if line.startswith("- detailed-design revision:"):
            line = "- detailed-design revision: `0.27-draft`"
        elif line.startswith("- detailed-design Git blob:"):
            line = f"- detailed-design Git blob: `{design_blob}`"
        elif line.startswith("- detailed-design SHA-256:"):
            line = f"- detailed-design SHA-256: `{design_sha}`"
        elif line.startswith("- repaired C48 source SHA-256:"):
            line = f"- repaired C48 source SHA-256: `{source_sha}`"
        elif line.startswith("- SDK C48B1 artifact SHA-256:"):
            line = f"- SDK C48B1 artifact SHA-256: `{binary_sha}`"
        elif line.startswith("- cold A48M SHA-256:"):
            line = f"- cold A48M SHA-256: `{cold_sha}`"
        lines.append(line)
    cert = "\n".join(lines) + "\n"
    marker = (
        "The schema-3 hot plane is a bounded variable-order LM with a "
        "12-token unigram fallback, topic-conditioned bigrams and 64 "
        "sorted sparse trigram contexts. Cold retrieval requires exact "
        "trigger spelling after salted-ID lookup, factual answers combine "
        "learned lead wording with immutable subject/predicate anchors, "
        "topic 0 is generic/unknown, and cold scans yield after each eight "
        "records. The blind candidate remains reserved and unscored; no "
        "blind-generalization result is claimed."
    )
    boundary = "## Native release boundary\n"
    if marker not in cert:
        if cert.count(boundary) != 1:
            raise SystemExit("certificate native boundary anchor mismatch")
        cert = cert.replace(boundary, marker + "\n\n" + boundary, 1)
    cert_path.write_text(cert, encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("patch", "finalize"))
    ns = ap.parse_args()
    if ns.mode == "patch":
        patch()
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
