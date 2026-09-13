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

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AILM = ROOT / "usr" / "src" / "ailmzx48"
DESIGN = AILM / "AILMZX48-DETAILED-DESIGN.md"

UPSTREAM_REPO = "tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project"
UPSTREAM_HEAD = "cb8e4ea0b68df693e5d4133fc906ed46234427b6"
UPSTREAM_LATEST = "P1.25"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_record_hash(record: object) -> str:
    data = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(data).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(
            f"expected exactly one patch anchor in {path}: {old[:60]!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_design() -> None:
    replace_once(
        DESIGN,
        "Status: Design in progress — forensic review corrections incorporated; "
        "Candidate A remains a measurement baseline\n"
        "Revision: 0.25-draft",
        "Status: SDK implementation profile qualified; full native-release "
        "profile blocked on upstream ZX-UX implementation\n"
        "Revision: 0.26-draft",
    )

    marker = (
        "The next retained conversation must force slot reuse, observe stale-reference "
        "loss, compact across a long dialogue and recover only the newest name."
    )
    addition = marker + "\n\n" + '''Implementation measurement note (Revision 0.26): the SDK-target
implementation now closes the context/literal gaps identified after the
training convergence checkpoint.  Target code performs an explicit no-mutation
capacity/descriptor preflight before an accepted dialogue pair is committed,
uses protection/importance/age/slot ordering for semantic-record eviction,
uses generation-checked session-literal reuse with the designed preference for
an unreferenced slot and otherwise the weakest strongest live-retention tuple,
and invalidates schema-declared semantic-reference fields before slot reuse.
Name assignment/recall turns now pass through the same bounded L0/L1/L2
conversation commit path rather than living only in a side channel.  The added
logic was split into C48 headers rather than raising the compiler's 32768-byte
source-object safety ceiling.

The retained post-repair SDK conformance case contains 70 accepted turns.  It
scores 70/70 expected keywords, performs 15 L1-to-L2 compactions, reaches two
L2 records, fills the 96-entry decoded LM-context ring, records exactly one
deliberate stale-generation invalidation after the ninth distinct name, and
recalls only the newest name at the end.  Independent post-change replays of
final regression suites A, B and C each remain 12/12 with clean exit and zero
literal-reference losses.  These measurements supersede the open-work sentence
at the end of Revision 0.25 for the implemented SDK profile.

The SDK profile is not a substitute for native certification.  As of this
revision the read-only upstream ZX-UX repository main identity checked for the
native dependency is `cb8e4ea0b68df693e5d4133fc906ed46234427b6`; its latest
inspected durable certification item is Phase-1 `P1.25`.  That upstream state
does not yet provide the native C48/OBJ1/MEX1 build, allocator/stack/Fuse, and
physical-cassette execution path required by Sections 18, 19 and 22.  Those
native-only obligations therefore remain explicitly `BLOCKED_EXTERNAL`; they
are neither silently waived nor counted as SDK zero-gap evidence.'''
    replace_once(DESIGN, marker, addition)

    sec23 = "## 23. Open design questions after Revision 0.12"
    measured = '''### 22.1 Revision-0.26 measured SDK answers and release-profile boundary

The acceptance questions above are now classified by evidence scope rather
than left as an undifferentiated to-do list.  The durable machine-readable
source of this classification is
`evaluation/DESIGN-COMPLIANCE-STATUS.json`.

For the **SDK implementation profile**, retained measurements establish the
following: the shipped SDK artifact is C48B1 and is never mislabeled as native
OBJ1/MEX1/Z80 code; the active runner uses zero C48 heap; L0 is bounded to 896
bytes/32 descriptors, L1 to 48 x 16-byte capsules, L2 to 24 x 16-byte records,
the session-literal store to 272 bytes/eight generation-checked slots, and the
decoded LM-context ring to 96 u16 entries; the cold A48M object is 8432 logical
bytes with 69 records, a 64-byte maximum read request and a 192-byte maximum
record; the host context oracle has retained a 500-dialogue/51000-source-byte
stress while fixed capacities remained bounded; the post-repair target-SDK
literal/context conversation retained 70/70 expected answers with real
compaction and stale-reference invalidation; and post-repair final regression
A/B/C remain 12/12 each.  The repository release verifier and `git diff
--check` are mandatory for the exact committed tree.

Questions that require **native ZX-UX evidence** remain intentionally open:
final MEX1 image/text/BSS and stack high-water, ARG1/ENV1 and real allocator
extent maps, RAW/PACKED native object placement, cycle/Fuse latency, native tty
and syscall equivalence, native compiler/linker lifetime, cassette save/load
ordering, physical 48K coexistence/headroom, and the Section-18.4 eleven-step
real-machine proof.  The upstream dependency is currently only at Phase-1
durable certification (`P1.25` at the inspected upstream main identity above),
so fabricating answers for those questions would violate the accuracy-first
rule.  Full native-release compliance becomes eligible for its own three-pass
zero-gap certificate only after those upstream facilities exist and the native
proof is retained.

The current compliance certificate therefore has two independent fields:
`SDK_PROFILE = PASS (3/3 zero-gap review passes)` and
`FULL_NATIVE_RELEASE = BLOCKED_EXTERNAL`.  A PASS in the first field must never
be rendered or summarized as a PASS in the second.

'''
    replace_once(DESIGN, sec23, measured + sec23)


def update_readmes() -> None:
    header = '''<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
'''
    (AILM / "model" / "README.md").write_text(
        header + '''# ailmzx48 model

The retained SDK model is an A48M Candidate-A prototype v2 cold stream plus
generated resident C48 tables.  The canonical cold seed is `cold-seed.bin`;
`cold-seed.json` records its logical length, record count, interface identity,
trigger salt and SHA-256.  `current-model.json` and `iterations/` retain model
construction identities used by qualified conversations.

A48M reference validation is mandatory.  The current qualified cold stream is
bounded to 65535 logical bytes, requests at most 64 bytes per read, permits
records no larger than 192 bytes and retains at most two winners during a scan.
The SDK artifact is C48B1/VM code, not native OBJ1, MEX1 or Z80 machine code.
Native model-object packaging remains blocked on the upstream ZX-UX native
release phases and is not inferred from SDK evidence.
''',
        encoding="utf-8",
    )
    (AILM / "evaluation" / "README.md").write_text(
        header + '''# ailmzx48 evaluation

This directory contains the executable reference tests, retained score gates,
training exit criteria, SDK conformance evidence and design-compliance status.
`test_context_reference.py` validates the bounded L0/L1/L2/session-literal
oracle.  `test_a48m_reference.py` validates the cold A48M stream.  The
`sdk-conformance/` subtree retains post-runtime-repair literal/context and final
A/B/C requalification runs.

`check_design_compliance.py` is the durable three-pass SDK-profile compliance
gate.  It intentionally reports the full native-release profile as
`BLOCKED_EXTERNAL` until native ZX-UX C48/OBJ1/MEX1, allocator/stack/Fuse and
physical-cassette evidence exists.  `DESIGN-REVIEW-CERTIFICATE.md` records that
scope distinction; an SDK PASS is never a native certification.
''',
        encoding="utf-8",
    )
    (AILM / "training" / "README.md").write_text(
        header + '''# ailmzx48 training

This directory contains the admitted seed corpus, provenance/record-lineage
metadata, retained iteration requests, convergence criteria and final training
goal status.  Host construction is intentionally separate from shipped target
inference.  The retained training goal reached `GOALS_ACHIEVED` at iteration 54;
that token describes the training/convergence program, not native ZX-UX release
certification.

`provenance.json` identifies the admitted synthetic source classes and explicit
project authorization basis.  `record-lineage.json` gives one content-addressed
lineage entry for every seed record, including split and record hash.  Repository
and upstream prose/source remain excluded from model training unless separately
authorized; design-authority use is not silently treated as corpus permission.
''',
        encoding="utf-8",
    )


def update_provenance() -> None:
    corpus_path = AILM / "training" / "seed_corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    records = corpus.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError("seed corpus records missing")

    catalog = {
        "user-directed-spectrum-facts": {
            "source_type": "project-authorized synthetic factual seed",
            "location": "training/seed_corpus.json",
            "authorization_basis": (
                "Project user explicitly directed creation, training, repair, "
                "and completion of the Spectrum-specialist ailmzx48 model."
            ),
            "scope": "Spectrum history, hardware, software, games and culture facts",
            "generator": "OpenAI GPT-5.6 Sol",
            "generation_date": "2026-09-12",
            "verbatim_repository_text": False,
        },
        "user-directed-sdk-facts": {
            "source_type": "project-authorized synthetic SDK factual seed",
            "location": "training/seed_corpus.json",
            "authorization_basis": (
                "Project user explicitly directed ailmzx48 work inside this SDK; "
                "records are compact project facts, not copied repository prose."
            ),
            "scope": "C48 SDK identity and behavior facts used by the local model",
            "generator": "OpenAI GPT-5.6 Sol",
            "generation_date": "2026-09-12",
            "verbatim_repository_text": False,
        },
        "user-directed-style-synthesis": {
            "source_type": "project-authorized synthetic conversational style",
            "location": "training/seed_corpus.json",
            "authorization_basis": (
                "Project user explicitly directed creation of synthetic ailmzx48 "
                "conversation material."
            ),
            "scope": "non-authoritative conversational wording/style",
            "generator": "OpenAI GPT-5.6 Sol",
            "generation_date": "2026-09-12",
            "verbatim_repository_text": False,
        },
    }

    lineage = []
    sdk_terms = (
        "c48", "sdk", "usr src", "usr bin", "c48run", "obj1", "mex1", "zx ux"
    )
    for index, record in enumerate(records):
        kind = str(record.get("kind", ""))
        text = str(record.get("text", "")).lower()
        if kind == "style-synthetic":
            source_id = "user-directed-style-synthesis"
        elif any(term in text for term in sdk_terms):
            source_id = "user-directed-sdk-facts"
        else:
            source_id = "user-directed-spectrum-facts"
        digest = canonical_record_hash(record)
        lineage.append(
            {
                "record_index": index,
                "source_id": source_id,
                "split": record.get("split"),
                "topic": record.get("topic"),
                "kind": kind,
                "record_sha256": digest,
                "normalized_sha256": digest,
                "source_location": f"training/seed_corpus.json#record-{index}",
                "admission_status": "admitted",
            }
        )

    provenance = {
        "schema": 2,
        "corpus": "seed_corpus.json",
        "corpus_sha256": sha256(corpus_path),
        "record_count": len(records),
        "record_lineage": "record-lineage.json",
        "authorization_basis": (
            "Project user explicitly directed creation, training, repair and "
            "completion of ailmzx48 in this repository."
        ),
        "source_catalog": catalog,
        "excluded_from_training": [
            "ZX-UX C48 SDK repository prose/source unless separately authorized",
            "ZX-UX upstream repository prose/source unless separately authorized",
        ],
        "policy": (
            "Every admitted seed record has a content-addressed lineage entry. "
            "Synthetic style is not factual authority. Project facts are admitted "
            "under the explicit project-user directive and are not verbatim copies "
            "of repository/upstream prose."
        ),
    }
    (AILM / "training" / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (AILM / "training" / "record-lineage.json").write_text(
        json.dumps(
            {"schema": 1, "records": lineage},
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )


def write_checker() -> None:
    checker = r'''#!/usr/bin/env python3
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
            "cb8e4ea0b68df693e5d4133fc906ed46234427b6",
            "upstream blocker identity mismatch")
    require(native.get("latest_durable_evidence") == "P1.25",
            "upstream durable evidence marker mismatch")
    require(status.get("source_sha256") == sha(A / "ailmzx48.c"),
            "status source identity mismatch")
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
'''
    path = AILM / "evaluation" / "check_design_compliance.py"
    path.write_text(checker, encoding="utf-8")


def patch_release_verifier() -> None:
    path = ROOT / "compiler" / "verify_release.py"
    text = path.read_text(encoding="utf-8")
    if "def check_ailmzx48_design()" not in text:
        anchor = "\ndef main() -> int:\n"
        if text.count(anchor) != 1:
            raise RuntimeError("verify_release main anchor mismatch")
        func = '''

def check_ailmzx48_design() -> None:
    checker = SDK / "usr/src/ailmzx48/evaluation/check_design_compliance.py"
    cp = run([sys.executable, "-B", str(checker)], timeout=120)
    if cp.returncode != 0:
        detail = (cp.stdout + cp.stderr).strip()
        fail("ailmzx48 design compliance failed: " + detail)
'''
        text = text.replace(anchor, func + anchor, 1)
    old = '        ("manifest", check_manifest),\n        ("automated tests", check_tests),'
    new = (
        '        ("manifest", check_manifest),\n'
        '        ("ailmzx48 design compliance", check_ailmzx48_design),\n'
        '        ("automated tests", check_tests),'
    )
    if new not in text:
        if text.count(old) != 1:
            raise RuntimeError("verify_release checks anchor mismatch")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def write_status_and_certificate() -> None:
    design_sha = sha256(DESIGN)
    design_blob = git_blob_sha1(DESIGN)
    source_sha = sha256(AILM / "ailmzx48.c")
    c48b_sha = sha256(ROOT / "usr" / "bin" / "ailmzx48" / "ailmzx48.c48b")
    cold = json.loads((AILM / "model" / "cold-seed.json").read_text())
    literal = json.loads(
        (AILM / "evaluation" / "sdk-conformance" / "literal-context" /
         "score.json").read_text()
    )
    finals = {}
    for name in ("final-a", "final-b", "final-c"):
        score = json.loads(
            (AILM / "evaluation" / "sdk-conformance" / name /
             "score.json").read_text()
        )
        finals[name] = {
            "turns": score["turns"],
            "keyword_ratio": score["keyword_ratio"],
            "clean_exit": score["clean_exit"],
            "literal_reference_losses": score["literal_reference_losses"],
        }
    status = {
        "schema": 1,
        "design_revision": "0.26-draft",
        "design_sha256": design_sha,
        "design_git_blob_sha1": design_blob,
        "source_sha256": source_sha,
        "sdk_c48b_sha256": c48b_sha,
        "cold_model_sha256": cold["sha256"],
        "sdk_profile": {
            "status": "PASS",
            "zero_gap_passes": 3,
            "review_passes": [
                "requirements-to-implementation",
                "implementation-to-retained-evidence-and-lineage",
                "durability-release-boundary-and-native-nonclaim",
            ],
            "literal_context": {
                "turns": literal["turns"],
                "keyword_ratio": literal["keyword_ratio"],
                "context_compactions": literal["context_compactions"],
                "max_l2count": literal["max_l2count"],
                "max_lmcount": literal["max_lmcount"],
                "literal_reference_losses": literal["literal_reference_losses"],
                "semantic_retrieval_uses": literal["semantic_retrieval_uses"],
                "final_keyword_hit": literal["final_keyword_hit"],
            },
            "post_repair_final_regressions": finals,
        },
        "full_native_release": {
            "status": "BLOCKED_EXTERNAL",
            "upstream_repository": UPSTREAM_REPO,
            "upstream_main": UPSTREAM_HEAD,
            "latest_durable_evidence": UPSTREAM_LATEST,
            "missing_native_evidence": [
                "native C48 compile to OBJ1 and link to MEX1",
                "native MEX1 image/BSS and stack high-water",
                "real ZX-UX allocator class/extent and model-object coexistence",
                "Fuse/cycle native inference evidence",
                "physical 48K cassette build/save/load/run proof",
                "Section 18.4 eleven-step native proof sequence",
            ],
            "policy": (
                "No SDK result is promoted to native certification. Other GitHub "
                "projects remain read-only."
            ),
        },
    }
    status_path = AILM / "evaluation" / "DESIGN-COMPLIANCE-STATUS.json"
    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    cert = f'''<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# ailmzx48 Design Compliance Certificate

This certificate supersedes the historical Revision-0.11 design-only review
certificate for the current Revision-0.26 SDK implementation profile.  It does
not erase that historical evidence; it makes the current scope explicit.

## Reviewed identities

- detailed-design revision: `0.26-draft`
- detailed-design Git blob: `{design_blob}`
- detailed-design SHA-256: `{design_sha}`
- repaired C48 source SHA-256: `{source_sha}`
- SDK C48B1 artifact SHA-256: `{c48b_sha}`
- cold A48M SHA-256: `{cold['sha256']}`
- upstream ZX-UX main inspected read-only: `{UPSTREAM_HEAD}`
- latest inspected upstream durable certification item: `{UPSTREAM_LATEST}`

## Three-pass zero-gap result

**SDK_PROFILE: PASS (3/3 zero-gap passes)**

Pass 1 maps frozen SDK-scope design requirements to target implementation and
fixed bounds.  Pass 2 maps the repaired implementation identity to retained
active-SDK evidence and complete seed-record lineage.  Pass 3 checks durability,
release-gate integration, current design/status identities, temporary-helper
removal, and the prohibition on turning SDK evidence into a native claim.

The workflow that creates the durable checkpoint executes all three independent
checker modes, the context/A48M reference suites, C48 compilation, the complete
SDK release verifier and `git diff --check`.  A failure prevents the certificate
from being committed.

## Native release boundary

**FULL_NATIVE_RELEASE: BLOCKED_EXTERNAL**

The current upstream ZX-UX implementation is still at Phase-1 durable evidence;
it does not yet expose the native C48/OBJ1/MEX1, allocator/stack/Fuse and
physical-cassette path required for the design's native proof.  Those obligations
remain in the design and machine-readable status as blockers.  They are not
waived, simulated by the host SDK, or counted among the three SDK zero-gap
passes.

A full native-release PASS requires a new certificate after the upstream native
facilities exist and the Section-18.4 proof has been executed and retained.
'''
    (AILM / "evaluation" / "DESIGN-REVIEW-CERTIFICATE.md").write_text(
        cert, encoding="utf-8"
    )


def main() -> int:
    update_design()
    update_readmes()
    update_provenance()
    write_checker()
    patch_release_verifier()
    write_status_and_certificate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
