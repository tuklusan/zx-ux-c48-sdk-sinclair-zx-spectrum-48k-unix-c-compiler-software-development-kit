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
import re

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
    gen = (A / "aigen.h").read_text(encoding="utf-8")
    match = (A / "aimatch.h").read_text(encoding="utf-8")
    cold_header = (A / "aicold.h").read_text(encoding="utf-8")
    cold_bytes = (A / "model" / "cold-seed.bin").read_bytes()
    require("Revision: 0.27-draft" in design, "design revision mismatch")
    require("SDK implementation profile qualified" in design, "design status mismatch")
    require("BLOCKED_EXTERNAL" in design, "native blocker not explicit in design")
    require((A / "ailmzx48.c").stat().st_size <= 32768,
            "primary C48 source-object ceiling exceeded")
    require('#include "aievict.h"' in source, "eviction policy header not wired")
    require('#include "aicold.h"' in source, "cold identity header not wired")
    require('#include "aigen.h"' in source, "variable-order LM header not wired")
    require("ai_mtrusted" not in source,
            "cached model trust bypasses per-scan integrity")
    require("ai_mhead[8+i]!=ai_cvid[i]" in source and
            "ai_mhead[16+i]!=ai_ciid[i]" in source,
            "target hot/cold identity comparison missing")
    def target_id(name: str) -> bytes:
        match = re.search(
            rf"unsigned char {name}\[8\] = \{{([^}}]+)\}};",
            cold_header, re.S
        )
        require(match is not None, f"generated identity array missing {name}")
        values = [int(v.strip()) for v in match.group(1).split(",")
                  if v.strip()]
        require(len(values) == 8 and all(0 <= v <= 255 for v in values),
                f"generated identity width/value mismatch {name}")
        return bytes(values)
    require(target_id("ai_cvid") == cold_bytes[8:16],
            "target vocabulary identity differs from A48M header")
    require(target_id("ai_ciid") == cold_bytes[16:24],
            "target interface identity differs from A48M header")
    require("ai_litnext" not in source, "round-robin literal selector remains")
    require("rc = ai_ctxpair(ai_t_id);" in source,
            "name turns do not use normal context commit")
    require("if (stored) ai_namecommit();" in source,
            "name literal state is not commit-gated")
    require(source.count("if (ai_ctxready() < 0)") >= 3,
            "pre-output context preflight is not universal")
    require("puts(ai_out)" not in lit,
            "name response helper prints before preflight")
    set_start = source.index("int ai_setname(void)")
    set_end = source.index("void ai_nameack(void);", set_start)
    set_body = source[set_start:set_end]
    require("ai_litgen[" not in set_body and
            "ai_litlen[" not in set_body and
            "ai_litbuf[" not in set_body,
            "name validation mutates session-literal storage")
    require("void ai_namecommit" in lit and
            "ai_litgen[slot] = gen;" in lit,
            "post-context literal commit implementation missing")
    require("persistent session-literal allocation is needed only when an evicted L0 turn" not in design,
            "stale literal-allocation rule remains in design")
    require("The explicit name-memory command is the measured exception" in design,
            "post-context name-literal design rule missing")
    require("int ai_ctxcheck" in ctx, "target context preflight missing")
    require("int ai_ctxready" in ctx,
            "pre-output context readiness check missing")
    require("unsigned int ai_trifind" in gen and
            "unsigned int ai_unext" in gen and
            "unsigned int ai_next" in gen,
            "variable-order LM lookup/fallback missing")
    require("ai_triuse = ai_triuse + 1" in gen,
            "trigram-use instrumentation missing")
    require("unsigned int ai_hfind" in match and
            "int ai_hsame" in match,
            "exact trigger spelling verification missing")
    require("if ((rn & 7) == 0)" in source and
            "ai_yields = ai_yields + 1" in source,
            "bounded model-scan yield cadence missing")
    require("topic = ai_t_unknown;" in source,
            "generic unknown routing missing")
    require("unsigned int ai_litpick" in lit, "literal victim policy missing")
    require("int ai_capref" in lit and "void ai_clrref" in lit,
            "schema-aware literal invalidation missing")
    require("unsigned int ai_protect" in evict and "unsigned int ai_victim" in evict,
            "protection-aware semantic eviction missing")
    model = load(A / "model" / "current-model.json")
    require(model.get("schema") == 3, "hot-model schema mismatch")
    topics = model.get("topics")
    require(isinstance(topics, list) and topics and
            topics[0] == "unknown" and len(topics) == 7,
            "generic topic map mismatch")
    tri = model.get("trigram_contexts")
    require(isinstance(tri, list) and 1 <= len(tri) <= 64,
            "bounded trigram plane missing")
    require(len(model.get("unigram_fallback", [])) == 12,
            "unigram fallback bound mismatch")
    words = model.get("trigger_words")
    require(isinstance(words, list) and len(words) > 100 and
            len(words) == len(set(words)),
            "resident exact trigger lexicon missing")
    salt = cold_bytes[34] + (cold_bytes[35] * 256)
    require(model.get("trigger_salt") == salt,
            "hot/cold trigger salt mismatch")
    parts = load(A / "training" / "evaluation-partitions.json")
    require(parts.get("schema") == 1,
            "evaluation partition schema mismatch")
    require(parts.get("blind_candidate", {}).get("status") ==
            "RESERVED_UNSCORED_NOT_USED_FOR_TUNING",
            "blind candidate is not explicitly unscored")
    require("No blind score" in
            parts.get("blind_candidate", {}).get("claim", ""),
            "blind nonclaim missing")
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
    require(a48m.get("logical_length") == 8458, "A48M logical length mismatch")
    require(a48m.get("record_count") == 69, "A48M record count mismatch")
    require(a48m.get("max_read_request") == 64, "A48M read bound mismatch")
    require(a48m.get("max_record_bytes") == 192, "A48M record bound mismatch")
    require("predicate-anchor-not-full-sentence" in
            a48m.get("tests", []),
            "predicate-anchor reference test missing")
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
        require(score.get("trigram_uses", 0) > 0,
                f"{name}: trigram generation absent")
        require(score.get("cooperative_yields", 0) >= 24,
                f"{name}: cooperative scan yields absent")
        require(run.get("source_sha256") == source_hash,
                f"{name}: source identity mismatch")
        require(run.get("c48b_sha256") == binary_hash,
                f"{name}: binary identity mismatch")
        require(run.get("cold_model_sha256") == cold_hash,
                f"{name}: cold-model identity mismatch")
    expected_iters = {"final-a": 9118, "final-b": 9119,
                      "final-c": 9120}
    for name, iteration in expected_iters.items():
        run = load(base / name / "run.json")
        require(run.get("iteration") == iteration,
                f"{name}: architecture iteration mismatch")
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
    require(run.get("iteration") == 9117,
            "literal-context: architecture iteration mismatch")
    require(score.get("trigram_uses", 0) > 0,
            "literal-context: trigram use absent")
    require(score.get("cooperative_yields", 0) >= 100,
            "literal-context: cooperative yields absent")

    route_score = load(base / "architecture-routing" / "score.json")
    route_run = load(base / "architecture-routing" / "run.json")
    route_tx = load(base / "architecture-routing" / "transcript.json")
    require(route_score.get("keyword_ratio") == 1.0 and
            route_score.get("turns") == 2,
            "architecture-routing: score mismatch")
    require(route_score.get("trigram_uses", 0) >= 2 and
            route_score.get("cooperative_yields", 0) >= 18,
            "architecture-routing: LM/yield evidence missing")
    require(route_run.get("iteration") == 9121,
            "architecture-routing: iteration mismatch")
    require(route_run.get("source_sha256") == source_hash and
            route_run.get("c48b_sha256") == binary_hash and
            route_run.get("cold_model_sha256") == cold_hash,
            "architecture-routing: identity mismatch")
    turns = route_tx.get("turns", [])
    require(len(turns) == 2,
            "architecture-routing: transcript turn count")
    second = turns[1].get("diag", {})
    require(second.get("ai_semuse") == 0 and
            second.get("ai_mhits") == 0 and
            second.get("ai_lasttop") == 0,
            "hash-collision unknown route was not rejected")

    corpus = load(A / "training" / "seed_corpus.json")
    provenance = load(A / "training" / "provenance.json")
    lineage = load(A / "training" / "record-lineage.json")
    records = corpus.get("records")
    lines = lineage.get("records")
    require(provenance.get("schema") == 3, "provenance schema mismatch")
    require(lineage.get("schema") == 3, "lineage schema mismatch")
    require(isinstance(records, list) and isinstance(lines, list),
            "corpus/lineage lists missing")
    require(len(records) == len(lines) == provenance.get("record_count"),
            "record-lineage coverage mismatch")
    corpus_hash = sha(A / "training" / "seed_corpus.json")
    require(provenance.get("corpus_sha256") == corpus_hash and
            lineage.get("corpus_sha256") == corpus_hash,
            "provenance corpus hash mismatch")
    catalog = provenance.get("source_catalog")
    require(isinstance(catalog, dict) and catalog, "source catalog missing")
    required_source_fields = (
        "title", "source_role", "source_type", "location",
        "license_or_authorization", "scope", "acquisition_date",
        "transformation_version", "transformation_method",
        "split_assignment", "record_indexes", "generated_material",
        "training_authorized", "normalized_output_sha256",
    )
    claimed = []
    for source_id, src in catalog.items():
        require(all(field in src for field in required_source_fields),
                f"source metadata incomplete {source_id}")
        require(src.get("training_authorized") is True,
                f"source training use not authorized {source_id}")
        idxs = src.get("record_indexes")
        require(isinstance(idxs, list) and idxs,
                f"source dependency list missing {source_id}")
        require(len(idxs) == len(set(idxs)),
                f"source dependency duplicate {source_id}")
        require(all(isinstance(i, int) and not isinstance(i, bool) and
                    0 <= i < len(records) for i in idxs),
                f"source dependency index invalid {source_id}")
        claimed.extend(idxs)
        dep = [rec_hash(records[i]) for i in idxs]
        dep_raw = json.dumps(dep, separators=(",", ":")).encode("ascii")
        require(src.get("normalized_output_sha256") ==
                hashlib.sha256(dep_raw).hexdigest(),
                f"source dependency hash mismatch {source_id}")
        require("immutable_revision" in src or "source_content_hash" in src or
                src.get("source_type") == "project factual authority" or
                src.get("source_role") == "style-only",
                f"source lacks immutable/hash authority {source_id}")
    require(sorted(claimed) == list(range(len(records))) and
            len(claimed) == len(set(claimed)),
            "source catalog is not exact one-to-one record coverage")
    seen = set()
    for index, (record, line) in enumerate(zip(records, lines)):
        require(line.get("record_index") == index, f"lineage index {index}")
        require(line.get("record_sha256") == rec_hash(record) and
                line.get("normalized_sha256") == rec_hash(record),
                f"lineage record hash {index}")
        source_id = line.get("source_id")
        require(source_id in catalog, f"lineage source id {index}")
        src = catalog[source_id]
        require(index in src.get("record_indexes", []),
                f"source dependency omission {index}")
        require(line.get("source_location") == src.get("location"),
                f"lineage authority location {index}")
        require(line.get("split") == record.get("split") ==
                src.get("split_assignment"),
                f"lineage split {index}")
        if record.get("kind") == "fact-user":
            require(src.get("source_role") == "factual-authority",
                    f"factual record lacks factual authority {index}")
            require(src.get("generated_material") is False,
                    f"generated material used as factual authority {index}")
        else:
            require(src.get("source_role") == "style-only",
                    f"style record source role mismatch {index}")
        seen.add(index)
    require(seen == set(range(len(records))), "lineage exact coverage mismatch")
    parts = load(A / "training" / "evaluation-partitions.json")
    reg = parts.get("regression", {}).get("request_sha256", {})
    for name in ("literal-context", "final-a", "final-b",
                 "final-c"):
        require(reg.get(name) == sha(base / name / "request.json"),
                f"evaluation partition request hash {name}")
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
    integ = sdk.get("cold_scan_integrity", {})
    require(integ.get("checksum") == "fletcher16-every-scan" and
            integ.get("vocabulary_identity_checked") is True and
            integ.get("interface_identity_checked") is True,
            "cold-scan integrity status missing")
    arch = sdk.get("model_architecture", {})
    require(arch.get("schema") == 3 and
            arch.get("max_order") == 3 and
            arch.get("trigram_contexts") == 64 and
            arch.get("exact_trigger_spelling") is True and
            arch.get("generic_unknown_topic") == 0,
            "model architecture status missing")
    require(sdk.get("evaluation_partitioning", {}).get("blind_status") ==
            "RESERVED_UNSCORED_NOT_USED_FOR_TUNING",
            "evaluation partition status missing")
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
    require("Every cold scan recomputes Fletcher-16" in cert,
            "cold-scan integrity certificate marker missing")
    require("variable-order LM" in cert and
            "exact trigger spelling" in cert and
            "blind candidate remains reserved and unscored" in cert,
            "architecture certificate markers missing")
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
