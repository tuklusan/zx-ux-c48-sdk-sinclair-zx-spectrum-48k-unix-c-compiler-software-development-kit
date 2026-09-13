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


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain an object")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rec_hash(record: object) -> str:
    data = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def pass1() -> dict:
    design = (A / "AILMZX48-DETAILED-DESIGN.md").read_text(encoding="utf-8")
    source = (A / "ailmzx48.c").read_text(encoding="utf-8")
    ctx = (A / "aictx.h").read_text(encoding="utf-8")
    lit = (A / "ailit.h").read_text(encoding="utf-8")
    evict = (A / "aievict.h").read_text(encoding="utf-8")
    require("Revision: 0.26-draft" in design, "design revision mismatch")
    require("SDK implementation profile qualified" in design, "design status mismatch")
    require("BLOCKED_EXTERNAL" in design, "native blocker not explicit in design")
    require((A / "ailmzx48.c").stat().st_size <= 32768,
            "primary C48 source-object ceiling exceeded")
    require('#include "aievict.h"' in source, "eviction policy header not wired")
    require("ai_litnext" not in source, "round-robin literal selector remains")
    require("rc = ai_ctxpair(ai_t_id);" in source,
            "name turns do not use normal context commit")
    require("if (stored && rc >= 0) ai_namesem();" in source,
            "name semantic state is not commit-gated")
    require("int ai_ctxcheck" in ctx, "target context preflight missing")
    require("unsigned int ai_litpick" in lit, "literal victim policy missing")
    require("int ai_capref" in lit and "void ai_clrref" in lit,
            "schema-aware literal invalidation missing")
    require("unsigned int ai_protect" in evict and "unsigned int ai_victim" in evict,
            "protection-aware semantic eviction missing")
    cref = load(A / "evaluation" / "context-reference-report.json")
    require(cref.get("status") == "PASS", "context reference not PASS")
    require(cref.get("l0_bytes") == 896 and cref.get("l0_descriptors") == 32,
            "L0 bounds mismatch")
    require(cref.get("l1_records") == 48 and cref.get("l2_records") == 24,
            "L1/L2 bounds mismatch")
    require(cref.get("session_literal_bytes") == 272,
            "session literal bytes mismatch")
    stress = cref.get("stress", {})
    require(stress.get("raw_source_bytes", 0) > 32768,
            "context stress does not exceed arena-sized source history")
    a48m = load(A / "evaluation" / "a48m-reference-report.json")
    require(a48m.get("status") == "PASS", "A48M reference not PASS")
    require(a48m.get("logical_length") == 8432, "A48M logical length mismatch")
    require(a48m.get("record_count") == 69, "A48M record count mismatch")
    require(a48m.get("max_read_request") == 64, "A48M read bound mismatch")
    require(a48m.get("max_record_bytes") == 192, "A48M record bound mismatch")
    goal = load(A / "training" / "goal-status.json")
    require(goal.get("goals_achieved") is True and goal.get("status") == "GOALS_ACHIEVED",
            "retained training goal no longer achieved")
    return {
        "pass": 1,
        "scope": "requirements-to-implementation",
        "status": "PASS",
        "source_sha256": sha(A / "ailmzx48.c"),
    }


def pass2() -> dict:
    source_hash = sha(A / "ailmzx48.c")
    binary_hash = sha(ROOT / "usr/bin/ailmzx48/ailmzx48.c48b")
    cold_hash = sha(A / "model" / "cold-seed.bin")
    base = A / "evaluation" / "sdk-conformance"
    for name in ("final-a", "final-b", "final-c"):
        score = load(base / name / "score.json")
        run = load(base / name / "run.json")
        require(score.get("keyword_ratio") == 1.0, f"{name}: keyword ratio")
        require(score.get("clean_exit") is True, f"{name}: clean exit")
        require(score.get("literal_reference_losses") == 0,
                f"{name}: literal losses")
        require(score.get("turns") == 12, f"{name}: turn count")
        require(run.get("source_sha256") == source_hash,
                f"{name}: source identity mismatch")
        require(run.get("c48b_sha256") == binary_hash,
                f"{name}: binary identity mismatch")
        require(run.get("cold_model_sha256") == cold_hash,
                f"{name}: cold-model identity mismatch")
    score = load(base / "literal-context" / "score.json")
    run = load(base / "literal-context" / "run.json")
    require(score.get("keyword_ratio") == 1.0, "literal-context: keyword ratio")
    require(score.get("clean_exit") is True, "literal-context: clean exit")
    require(score.get("turns") == 70, "literal-context: turn count")
    require(score.get("context_compactions", 0) >= 1,
            "literal-context: compaction absent")
    require(score.get("max_l2count", 0) >= 1, "literal-context: L2 absent")
    require(score.get("max_lmcount") == 96, "literal-context: LM ring bound")
    require(score.get("literal_reference_losses") == 1,
            "literal-context: deliberate stale-reference loss mismatch")
    require(score.get("final_keyword_hit") is True,
            "literal-context: newest-name recall failed")
    require(run.get("source_sha256") == source_hash,
            "literal-context: source identity mismatch")
    require(run.get("c48b_sha256") == binary_hash,
            "literal-context: binary identity mismatch")
    require(run.get("cold_model_sha256") == cold_hash,
            "literal-context: cold-model identity mismatch")

    corpus = load(A / "training" / "seed_corpus.json")
    provenance = load(A / "training" / "provenance.json")
    lineage = load(A / "training" / "record-lineage.json")
    records = corpus.get("records")
    lines = lineage.get("records")
    require(provenance.get("schema") == 2, "provenance schema mismatch")
    require(isinstance(records, list) and isinstance(lines, list),
            "corpus/lineage lists missing")
    require(len(records) == len(lines) == provenance.get("record_count"),
            "record-lineage coverage mismatch")
    require(provenance.get("corpus_sha256") == sha(A / "training" / "seed_corpus.json"),
            "provenance corpus hash mismatch")
    catalog = provenance.get("source_catalog")
    require(isinstance(catalog, dict) and catalog, "source catalog missing")
    for index, (record, line) in enumerate(zip(records, lines)):
        require(line.get("record_index") == index, f"lineage index {index}")
        require(line.get("record_sha256") == rec_hash(record),
                f"lineage record hash {index}")
        require(line.get("source_id") in catalog,
                f"lineage source id {index}")
        require(line.get("split") == record.get("split"),
                f"lineage split {index}")
    return {
        "pass": 2,
        "scope": "implementation-to-retained-evidence-and-lineage",
        "status": "PASS",
        "source_sha256": source_hash,
    }


def pass3() -> dict:
    status = load(A / "evaluation" / "DESIGN-COMPLIANCE-STATUS.json")
    require(status.get("schema") == 1, "compliance status schema")
    sdk = status.get("sdk_profile", {})
    native = status.get("full_native_release", {})
    require(sdk.get("status") == "PASS", "SDK profile status is not PASS")
    require(sdk.get("zero_gap_passes") == 3, "SDK zero-gap pass count")
    require(native.get("status") == "BLOCKED_EXTERNAL",
            "native blocker status must remain explicit")
    require(native.get("upstream_repository") ==
            "tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project",
            "upstream blocker repository mismatch")
    require(native.get("upstream_main") ==
            "8c8f918743897b352513b0545ff77487682c088f",
            "upstream blocker identity mismatch")
    require(native.get("latest_durable_evidence") == "P1.26",
            "upstream durable evidence marker mismatch")
    require(native.get("upstream_certified_source_commit") ==
            "cb8e4ea0b68df693e5d4133fc906ed46234427b6",
            "upstream certified source identity mismatch")
    require(status.get("source_sha256") == sha(A / "ailmzx48.c"),
            "status source identity mismatch")
    require(status.get("sdk_c48b_sha256") ==
            sha(ROOT / "usr/bin/ailmzx48/ailmzx48.c48b"),
            "status binary identity mismatch")
    require(status.get("cold_model_sha256") ==
            sha(A / "model" / "cold-seed.bin"),
            "status cold-model identity mismatch")
    require(status.get("design_sha256") ==
            sha(A / "AILMZX48-DETAILED-DESIGN.md"),
            "status design identity mismatch")
    cert = (A / "evaluation" / "DESIGN-REVIEW-CERTIFICATE.md").read_text(
        encoding="utf-8"
    )
    require("SDK_PROFILE: PASS (3/3 zero-gap passes)" in cert,
            "SDK certificate result missing")
    require("FULL_NATIVE_RELEASE: BLOCKED_EXTERNAL" in cert,
            "native certificate boundary missing")
    verify = (ROOT / "compiler" / "verify_release.py").read_text(encoding="utf-8")
    require("check_ailmzx48_design" in verify,
            "release verifier does not invoke design compliance")
    require(not (ROOT / ".github" / "workflows" /
                 "ailmzx48-design-compliance-finalize.yml").exists(),
            "temporary compliance workflow remains")
    require(not (A / "tooling" / "finalize_design_compliance.py").exists(),
            "temporary finalizer remains")
    return {
        "pass": 3,
        "scope": "durability-release-boundary-and-native-nonclaim",
        "status": "PASS",
        "design_sha256": status.get("design_sha256"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-id", type=int, choices=(1, 2, 3))
    ns = ap.parse_args()
    funcs = {1: pass1, 2: pass2, 3: pass3}
    ids = (ns.pass_id,) if ns.pass_id else (1, 2, 3)
    results = [funcs[index]() for index in ids]
    print(json.dumps({"schema": 1, "results": results}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
