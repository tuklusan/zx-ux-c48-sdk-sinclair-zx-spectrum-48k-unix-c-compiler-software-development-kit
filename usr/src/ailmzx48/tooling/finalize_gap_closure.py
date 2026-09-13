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
EVAL = AILM / "evaluation"
UP_MAIN = "8c8f918743897b352513b0545ff77487682c088f"
UP_SOURCE = "cb8e4ea0b68df693e5d4133fc906ed46234427b6"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    head = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(head + data).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one patch anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_design() -> tuple[str, str]:
    path = AILM / "AILMZX48-DETAILED-DESIGN.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "real-machine proof.  The upstream dependency is currently only at "
        "Phase-1\n"
        "durable certification (`P1.25` at the inspected upstream main identity "
        "above),\n"
        "so fabricating answers for those questions would violate the "
        "accuracy-first\n"
        "rule.  Full native-release compliance becomes eligible for its own "
        "three-pass\n"
        "zero-gap certificate only after those upstream facilities exist and "
        "the native\n"
        "proof is retained.\n"
    )
    new = (
        "real-machine proof.  The upstream dependency is currently only at "
        "Phase-1\n"
        "durable certification: `P1.26` is PASS at upstream main "
        f"`{UP_MAIN}`,\n"
        "certifying source commit "
        f"`{UP_SOURCE}`.  That evidence is still\n"
        "kernel wall-clock work, not the required native C48/MEX1/cassette "
        "path.\n"
        "Fabricating answers for those questions would violate the "
        "accuracy-first rule.\n"
        "Full native-release compliance becomes eligible for its own "
        "three-pass zero-gap\n"
        "certificate only after those upstream facilities exist and the native "
        "proof is\n"
        "retained.\n"
    )
    if old not in text:
        raise RuntimeError("Section 22.1 upstream snapshot anchor missing")
    text = text.replace(old, new, 1)

    start = text.index("## 23. Open design questions after Revision 0.12\n")
    end = text.index("## 24. Revision and durability discipline\n", start)
    section = f'''## 23. Resolved SDK parameters and remaining native questions

Revision 0.26 closes the SDK-side design questions that are now fixed by
implementation and retained evidence. They are not open tuning placeholders:

- the resident canonical vocabulary is 96 entries; alias retrieval uses
  collision-free salted trigger IDs in 224..4095 with accepted salt 23;
- A48M v2 is 8,432 logical bytes with 69 records, a 192-byte maximum record,
  a 64-byte maximum read request, and cold-model SHA-256
  `e2df4c13bc0b98999cec1e155bf0c7100d6ffd01965e6d2a4d05071c4da888db`;
- fixed context bounds are L0=896 bytes/32 descriptors, L1=48 capsules,
  L2=24 capsules, eight generation-checked literal slots in 272 bytes, and a
  96-token decoded LM window;
- the reference stress run covers 500 dialogue pairs, 444 L1-to-L2
  compactions, 376 L2 evictions, and 51,000 raw source-dialogue bytes without
  relaxing those fixed capacities;
- target context commit uses no-mutation preflight before age, eviction, or
  write mutation; semantic eviction orders retention protection before
  importance and age;
- literal storage reuses an exact spelling, prefers an unreferenced slot, and
  otherwise chooses the least-protected, least-important, oldest referenced
  slot with explicit stale-reference invalidation;
- literal-name turns use the same bounded output and L0/L1/L2 commit path as
  normal turns, and semantic name state is published only after commit success;
- retained post-repair literal/context iteration 9101 is 70/70 with 15
  compactions, L2 occupancy 2, 61 semantic retrieval uses, exactly one expected
  stale-reference invalidation, and successful newest-name recall;
- retained post-repair final A/B/C iterations 9102/9103/9104 are each 12/12,
  clean-exit, zero-unexpected-literal-loss runs against one repaired source,
  one rebuilt C48B1 binary, and one unchanged cold-model identity;
- the repaired primary `ailmzx48.c` remains below the unchanged 32,768-byte
  compiler source-object ceiling; helper logic moved to ordinary shipped C48
  headers instead of weakening the compiler gate;
- `compiler/verify_release.py` permanently invokes the three-pass design
  compliance checker, so source/binary/model/evidence/provenance drift fails
  the full SDK release gate.

The remaining questions are specifically native-release questions:

1. native OBJ1/MEX1 text, BSS, stack, heap, and arena-placement measurements;
2. RAW/PACKED model physical bytes and decoder-state coexistence under the
   native allocator;
3. Fuse/cycle and real-tty latency for repeated A48M scans and long context use;
4. canonical target object names, shell/process-replacement behavior, and M48O
   cassette ordering;
5. native build/save/reclaim/load/direct-exec commands proven by the implemented
   upstream system rather than inferred from architecture prose;
6. physical unexpanded-48K boot, multi-turn conversation, context compaction,
   model scanning, and clean `q` termination;
7. final source/development and runtime/distribution tape hashes and operator
   transcript.

As of this checkpoint, read-only upstream `main` is `{UP_MAIN}` and its latest
durable certification is P1.26 PASS from certified source `{UP_SOURCE}`. P1.26
is still Phase-1 kernel wall-clock work. It does not provide the later native
C48/OBJ1/MEX1/cassette execution path needed for the seven proofs above.
Therefore `FULL_NATIVE_RELEASE` remains `BLOCKED_EXTERNAL`; no command sequence
is invented to make that profile appear complete early.

'''
    path.write_text(text[:start] + section + text[end:], encoding="utf-8")
    data = path.read_bytes()
    return sha256(data), git_blob_sha1(data)


def patch_status(design_sha: str, blob_sha: str) -> None:
    path = EVAL / "DESIGN-COMPLIANCE-STATUS.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    native = data["full_native_release"]
    native["upstream_main"] = UP_MAIN
    native["latest_durable_evidence"] = "P1.26"
    native["upstream_certified_source_commit"] = UP_SOURCE
    data["design_sha256"] = design_sha
    data["design_git_blob_sha1"] = blob_sha
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def patch_checker() -> None:
    path = EVAL / "check_design_compliance.py"
    replace_once(
        path,
        'def pass2() -> dict:\n'
        '    source_hash = sha(A / "ailmzx48.c")\n'
        '    base = A / "evaluation" / "sdk-conformance"\n',
        'def pass2() -> dict:\n'
        '    source_hash = sha(A / "ailmzx48.c")\n'
        '    binary_hash = sha(ROOT / "usr/bin/ailmzx48/ailmzx48.c48b")\n'
        '    cold_hash = sha(A / "model" / "cold-seed.bin")\n'
        '    base = A / "evaluation" / "sdk-conformance"\n',
    )
    replace_once(
        path,
        '        require(run.get("source_sha256") == source_hash,\n'
        '                f"{name}: source identity mismatch")\n',
        '        require(run.get("source_sha256") == source_hash,\n'
        '                f"{name}: source identity mismatch")\n'
        '        require(run.get("c48b_sha256") == binary_hash,\n'
        '                f"{name}: binary identity mismatch")\n'
        '        require(run.get("cold_model_sha256") == cold_hash,\n'
        '                f"{name}: cold-model identity mismatch")\n',
    )
    replace_once(
        path,
        '    require(run.get("source_sha256") == source_hash,\n'
        '            "literal-context: source identity mismatch")\n\n'
        '    corpus = load(A / "training" / "seed_corpus.json")\n',
        '    require(run.get("source_sha256") == source_hash,\n'
        '            "literal-context: source identity mismatch")\n'
        '    require(run.get("c48b_sha256") == binary_hash,\n'
        '            "literal-context: binary identity mismatch")\n'
        '    require(run.get("cold_model_sha256") == cold_hash,\n'
        '            "literal-context: cold-model identity mismatch")\n\n'
        '    corpus = load(A / "training" / "seed_corpus.json")\n',
    )
    replace_once(
        path,
        '    require(native.get("upstream_main") ==\n'
        '            "cb8e4ea0b68df693e5d4133fc906ed46234427b6",\n'
        '            "upstream blocker identity mismatch")\n'
        '    require(native.get("latest_durable_evidence") == "P1.25",\n'
        '            "upstream durable evidence marker mismatch")\n',
        '    require(native.get("upstream_main") ==\n'
        f'            "{UP_MAIN}",\n'
        '            "upstream blocker identity mismatch")\n'
        '    require(native.get("latest_durable_evidence") == "P1.26",\n'
        '            "upstream durable evidence marker mismatch")\n'
        '    require(native.get("upstream_certified_source_commit") ==\n'
        f'            "{UP_SOURCE}",\n'
        '            "upstream certified source identity mismatch")\n',
    )
    replace_once(
        path,
        '    require(status.get("source_sha256") == sha(A / "ailmzx48.c"),\n'
        '            "status source identity mismatch")\n'
        '    require(status.get("design_sha256") ==\n',
        '    require(status.get("source_sha256") == sha(A / "ailmzx48.c"),\n'
        '            "status source identity mismatch")\n'
        '    require(status.get("sdk_c48b_sha256") ==\n'
        '            sha(ROOT / "usr/bin/ailmzx48/ailmzx48.c48b"),\n'
        '            "status binary identity mismatch")\n'
        '    require(status.get("cold_model_sha256") ==\n'
        '            sha(A / "model" / "cold-seed.bin"),\n'
        '            "status cold-model identity mismatch")\n'
        '    require(status.get("design_sha256") ==\n',
    )


def patch_certificate(design_sha: str, blob_sha: str) -> None:
    path = EVAL / "DESIGN-REVIEW-CERTIFICATE.md"
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("- detailed-design Git blob:"):
            line = f"- detailed-design Git blob: `{blob_sha}`"
        elif line.startswith("- detailed-design SHA-256:"):
            line = f"- detailed-design SHA-256: `{design_sha}`"
        elif line.startswith("- upstream ZX-UX main inspected read-only:"):
            line = f"- upstream ZX-UX main inspected read-only: `{UP_MAIN}`"
        elif line.startswith("- latest inspected upstream durable certification item:"):
            line = "- latest inspected upstream durable certification item: `P1.26`"
        lines.append(line)
    marker = "- latest inspected upstream durable certification item: `P1.26`"
    idx = lines.index(marker)
    source_line = f"- certified source named by P1.26: `{UP_SOURCE}`"
    if source_line not in lines:
        lines.insert(idx + 1, source_line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    design_sha, blob_sha = patch_design()
    patch_status(design_sha, blob_sha)
    patch_checker()
    patch_certificate(design_sha, blob_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
