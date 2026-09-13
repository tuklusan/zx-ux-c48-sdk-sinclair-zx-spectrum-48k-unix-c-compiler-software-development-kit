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
SDK = EVAL / "sdk-conformance"

REPAIR_COMMIT = "fbf963ccdbdff63d6cc2201ebf6bfff88e7ea6ee"
UPSTREAM_MAIN = "8c8f918743897b352513b0545ff77487682c088f"
UPSTREAM_SOURCE = "cb8e4ea0b68df693e5d4133fc906ed46234427b6"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one patch anchor in {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_checker() -> None:
    path = EVAL / "check_sdk_conformance.py"
    path.write_text(r'''#!/usr/bin/env python3
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
EVID = AILM / "evaluation" / "sdk-conformance"
STATUS = EVID / "status.json"


def fail(message: str) -> None:
    raise SystemExit(f"AILMZX48 SDK CONFORMANCE FAIL: {message}")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path.relative_to(ROOT)} is not a JSON object")
    return data


def require(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def main() -> int:
    status = load(STATUS)
    require(status.get("schema") == 1, "unsupported status schema")
    require(status.get("status") == "SDK_GAPS_CLOSED_NATIVE_BLOCKED",
            "unexpected closure status")
    require(status.get("sdk_gaps_closed") is True,
            "SDK gap closure is not asserted")
    require(status.get("native_release_ready") is False,
            "native readiness must remain false without native proof")

    runtime_files = status.get("runtime_files")
    require(isinstance(runtime_files, dict) and runtime_files,
            "runtime_files is missing")
    for rel, expected in sorted(runtime_files.items()):
        require(isinstance(rel, str) and isinstance(expected, str),
                "runtime_files entry is malformed")
        path = ROOT / rel
        require(path.is_file(), f"runtime file missing: {rel}")
        require(sha(path) == expected, f"runtime identity drift: {rel}")

    source_sha = sha(AILM / "ailmzx48.c")
    binary_sha = sha(ROOT / "usr" / "bin" / "ailmzx48" /
                     "ailmzx48.c48b")
    cold_sha = sha(AILM / "model" / "cold-seed.bin")

    expected = {
        "literal-context": (9101, "sdk-design-literal-context-v1"),
        "final-a": (9102, "final-regression-a-v1"),
        "final-b": (9103, "final-regression-b-v1"),
        "final-c": (9104, "final-regression-c-v1"),
    }
    final_names = ("final-a", "final-b", "final-c")
    for name, (iteration, scenario) in expected.items():
        root = EVID / name
        req = load(root / "request.json")
        run = load(root / "run.json")
        score = load(root / "score.json")
        require(req.get("iteration") == iteration,
                f"{name}: request iteration drift")
        require(req.get("scenario") == scenario,
                f"{name}: request scenario drift")
        require(run.get("iteration") == iteration,
                f"{name}: run iteration drift")
        require(score.get("iteration") == iteration,
                f"{name}: score iteration drift")
        require(run.get("source_sha256") == source_sha,
                f"{name}: repaired source evidence is stale")
        require(run.get("c48b_sha256") == binary_sha,
                f"{name}: repaired binary evidence is stale")
        require(run.get("cold_model_sha256") == cold_sha,
                f"{name}: cold-model evidence is stale")
        require(run.get("cold_model_logical_length") == 8432,
                f"{name}: cold-model length drift")
        require(run.get("cold_model_max_request") == 64,
                f"{name}: cold read bound drift")
        require(run.get("cold_record_count") == 69,
                f"{name}: cold record-count drift")
        require(score.get("clean_exit") is True,
                f"{name}: clean exit not proven")
        require(score.get("final_keyword_hit") is True,
                f"{name}: final keyword not proven")
        require(score.get("keyword_ratio") == 1.0,
                f"{name}: keyword ratio regressed")
        require(score.get("accepted_turns") == score.get("turns"),
                f"{name}: accepted-turn count mismatch")
        require(score.get("max_lmcount") == 96,
                f"{name}: decoded LM context did not reach bound")

    for name in final_names:
        score = load(EVID / name / "score.json")
        require(score.get("turns") == 12,
                f"{name}: final regression turn count drift")
        require(score.get("keyword_hits") == 12,
                f"{name}: final regression is not 12/12")
        require(score.get("literal_reference_losses") == 0,
                f"{name}: unexpected literal reference loss")
        limit = score.get("vm_step_limit")
        steps = score.get("vm_steps")
        require(isinstance(limit, int) and limit > 0,
                f"{name}: invalid VM limit")
        require(isinstance(steps, int) and steps <= limit * 85 // 100,
                f"{name}: VM utilization exceeds 85 percent")

    literal = load(EVID / "literal-context" / "score.json")
    require(literal.get("turns") == 70,
            "literal-context: turn count drift")
    require(literal.get("keyword_hits") == 70,
            "literal-context: not 70/70")
    require(literal.get("context_compactions", 0) >= 1,
            "literal-context: no L1 compaction")
    require(literal.get("max_l2count", 0) >= 1,
            "literal-context: no L2 occupancy")
    require(literal.get("semantic_retrieval_uses", 0) >= 50,
            "literal-context: semantic retrieval evidence too low")
    require(literal.get("literal_reference_losses") == 1,
            "literal-context: stale-reference invalidation drift")

    final_runs = [load(EVID / name / "run.json") for name in final_names]
    require(len({item["source_sha256"] for item in final_runs}) == 1,
            "final A/B/C repaired source identities differ")
    require(len({item["c48b_sha256"] for item in final_runs}) == 1,
            "final A/B/C repaired binary identities differ")
    require(len({item["cold_model_sha256"] for item in final_runs}) == 1,
            "final A/B/C cold-model identities differ")

    upstream = status.get("upstream_snapshot")
    require(isinstance(upstream, dict), "upstream snapshot is missing")
    require(upstream.get("latest_durable_certification_step") == "P1.26",
            "upstream certification snapshot is not P1.26")
    require(upstream.get("certification_status") == "PASS",
            "upstream P1.26 snapshot is not PASS")
    require(upstream.get("blocking_phase") == "Phase 1",
            "native blocker phase changed without review")
    remaining = status.get("remaining_native_proofs")
    require(isinstance(remaining, list) and len(remaining) >= 5,
            "remaining native proof list is incomplete")

    print(json.dumps({
        "status": "PASS",
        "sdk_gaps_closed": True,
        "native_release_ready": False,
        "source_sha256": source_sha,
        "c48b_sha256": binary_sha,
        "cold_model_sha256": cold_sha,
        "final_iterations": [9102, 9103, 9104],
        "literal_context_iteration": 9101,
        "upstream_step": "P1.26",
    }, sort_keys=True))
    print("AILMZX48 SDK CONFORMANCE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''', encoding="utf-8")


def write_status() -> None:
    paths = [
        "usr/src/ailmzx48/ailmzx48.c",
        "usr/src/ailmzx48/aictx.h",
        "usr/src/ailmzx48/aievict.h",
        "usr/src/ailmzx48/ailit.h",
        "usr/src/ailmzx48/aimatch.h",
        "usr/src/ailmzx48/aimod.h",
        "usr/src/ailmzx48/model/cold-seed.bin",
        "usr/bin/ailmzx48/ailmzx48.c48b",
    ]
    status = {
        "schema": 1,
        "status": "SDK_GAPS_CLOSED_NATIVE_BLOCKED",
        "sdk_gaps_closed": True,
        "native_release_ready": False,
        "repair_commit": REPAIR_COMMIT,
        "runtime_files": {rel: sha(ROOT / rel) for rel in paths},
        "conformance_evidence": {
            "literal_context": {
                "iteration": 9101,
                "scenario": "sdk-design-literal-context-v1",
                "expected_literal_reference_losses": 1,
            },
            "final_regression": {
                "iterations": [9102, 9103, 9104],
                "scenarios": [
                    "final-regression-a-v1",
                    "final-regression-b-v1",
                    "final-regression-c-v1",
                ],
                "required_keyword_ratio": 1.0,
                "required_literal_reference_losses": 0,
            },
        },
        "upstream_snapshot": {
            "repository": (
                "tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project"
            ),
            "checked_main_commit": UPSTREAM_MAIN,
            "latest_durable_certification_step": "P1.26",
            "certification_source_commit": UPSTREAM_SOURCE,
            "certification_status": "PASS",
            "blocking_phase": "Phase 1",
            "blocking_reason": (
                "Upstream durable certification is still Phase 1 kernel "
                "work and does not yet provide the native C48/MEX1, "
                "allocator/tty integration, cassette packaging, Fuse, or "
                "physical-48K execution path required by the design."
            ),
        },
        "remaining_native_proofs": [
            "native C48 compile to canonical object form",
            "MEX1 link with measured stack/heap and arena placement",
            "native model RAW/PACKED object coexistence and decoder budget",
            "Fuse/cycle/tty multi-turn execution evidence",
            "cassette save/load/direct-exec workflow using canonical commands",
            "physical unexpanded ZX Spectrum 48K conversation and clean quit",
            "final source/runtime tape ordering and retained native hashes",
        ],
        "next_action": (
            "Do not claim native or physical release completion. Recheck "
            "upstream certification when the required userland C48/MEX1 and "
            "cassette execution phases exist."
        ),
    }
    (SDK / "status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def patch_verify_release() -> None:
    path = ROOT / "compiler" / "verify_release.py"
    replace_once(
        path,
        '        "usr/src/security/secforge.c",\n    ]\n',
        '        "usr/src/security/secforge.c",\n'
        '        "usr/src/ailmzx48/evaluation/check_sdk_conformance.py",\n'
        '        "usr/src/ailmzx48/evaluation/sdk-conformance/status.json",\n'
        '    ]\n',
    )
    anchor = '\n\ndef main() -> int:\n'
    addition = r'''


def check_ailmzx48_sdk() -> None:
    checker = SDK / "usr/src/ailmzx48/evaluation/check_sdk_conformance.py"
    cp = run([sys.executable, "-B", str(checker)], timeout=30)
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout + cp.stderr)
        fail("ailmzx48 SDK conformance evidence failed")
    if "AILMZX48 SDK CONFORMANCE PASS" not in cp.stdout:
        fail("ailmzx48 SDK conformance completion marker missing")
'''
    replace_once(path, anchor, addition + anchor)
    replace_once(
        path,
        '        ("manifest", check_manifest),\n'
        '        ("automated tests", check_tests),\n',
        '        ("manifest", check_manifest),\n'
        '        ("ailmzx48 SDK conformance", check_ailmzx48_sdk),\n'
        '        ("automated tests", check_tests),\n',
    )


def patch_design() -> None:
    path = AILM / "AILMZX48-DETAILED-DESIGN.md"
    replace_once(
        path,
        "Status: Design in progress — forensic review corrections incorporated; Candidate A remains a measurement baseline\nRevision: 0.25-draft\n",
        "Status: SDK implementation/convergence and design-gap closure complete; native ZX-UX/Fuse/physical certification blocked on upstream readiness\nRevision: 0.26-draft\n",
    )
    replace_once(
        path,
        "Canonical SDK executable path: `usr/bin/ailmzx48/ailmzx48.c48b`\n\n## 1. Purpose\n",
        "Canonical SDK executable path: `usr/bin/ailmzx48/ailmzx48.c48b`\n\n"
        "Revision 0.26 records the post-convergence SDK gap-closure checkpoint. "
        "Runtime repair commit `fbf963ccdbdff63d6cc2201ebf6bfff88e7ea6ee` "
        "adds transactional context preflight, retention-aware deterministic "
        "eviction, deterministic session-literal reuse/invalidation, and normal "
        "bounded-context participation for literal-name turns. The repaired "
        "binary is requalified by retained SDK evidence in "
        "`evaluation/sdk-conformance/`.\n\n"
        "This checkpoint does **not** claim native ZX-UX, Fuse, cassette, or "
        "physical-48K release completion. The upstream ZX-UX repository was "
        "rechecked read-only at main commit "
        "`8c8f918743897b352513b0545ff77487682c088f`; its latest durable "
        "certification is P1.26 PASS for Phase-1 wall-clock kernel work, with "
        "certified source commit "
        "`cb8e4ea0b68df693e5d4133fc906ed46234427b6`. The native userland "
        "C48/MEX1/cassette path required by Sections 18 and 19 therefore remains "
        "an external readiness blocker, not an SDK implementation defect.\n\n"
        "`evaluation/sdk-conformance/status.json` is the machine-readable "
        "boundary between completed SDK work and those remaining native proofs. "
        "`evaluation/check_sdk_conformance.py` is part of the full SDK release "
        "verifier and rejects stale repaired-source, binary, cold-model, or "
        "retained conformance identities.\n\n"
        "## 1. Purpose\n",
    )
    text = path.read_text(encoding="utf-8")
    start = text.index("## 23. Open design questions after Revision 0.12\n")
    end = text.index("## 24. Revision and durability discipline\n", start)
    section = '''## 23. Resolved SDK parameters and remaining native questions after Revision 0.26

The SDK-side questions below are no longer open. They are frozen by the accepted implementation and retained evidence at the Revision-0.26 gap-closure checkpoint:

- the resident canonical token vocabulary is 96 entries; alias retrieval uses collision-free salted trigger IDs in 224..4095 with accepted salt 23;
- the cold A48M v2 object is 8,432 logical bytes with 69 records, a 192-byte maximum record, a 64-byte maximum read request, and SHA-256 `e2df4c13bc0b98999cec1e155bf0c7100d6ffd01965e6d2a4d05071c4da888db`;
- the fixed conversation memory bounds are L0=896 bytes/32 descriptors, L1=48 sixteen-byte capsules, L2=24 sixteen-byte capsules, eight generation-checked literal slots in 272 bytes, and a 96-token decoded LM window;
- the host reference stress test exercises 500 dialogue pairs, 444 L1-to-L2 compactions and 376 L2 evictions without relaxing those bounds;
- context commit now performs a no-mutation capacity/invariant preflight before age/eviction/write mutation;
- L1/L2 victim selection orders retention protection first, then importance, then age; pinned/corrective semantic state is not treated as ordinary low-value history;
- session-literal storage reuses an exact live spelling, prefers an unreferenced slot, and otherwise evicts the least-protected/least-important/oldest referenced slot with explicit stale-reference invalidation;
- literal-name responses are built in the normal bounded output buffer and their user/assistant pair is committed through the same L0/L1/L2 path before the new semantic reference is published;
- post-repair literal/context evidence is retained as iteration 9101: 70/70 keyword hits, 15 compactions, L2 occupancy 2, 61 semantic retrieval uses, exactly one expected stale-reference invalidation, and successful newest-name recall;
- post-repair final regression A/B/C is retained as iterations 9102/9103/9104 against one repaired source identity, one repaired C48B1 binary identity and one unchanged cold-model identity; every suite is 12/12 with clean exit and zero unexpected literal-reference loss;
- the repaired `ailmzx48.c` remains below the compiler's unchanged 32,768-byte source-object ceiling by moving bounded helper logic into normal shipped C48 headers rather than weakening the compiler gate;
- `python -B compiler/verify_release.py` now includes a permanent ailmzx48 SDK conformance evidence check, so runtime/binary/model drift cannot silently leave this checkpoint looking current.

The remaining questions are specifically **native-release** questions and must stay visibly separate from completed SDK qualification:

1. exact native OBJ1/MEX1 text, BSS, stack, heap and arena-placement measurements;
2. actual RAW/PACKED model physical bytes and decoder-state coexistence under the native allocator;
3. Fuse/cycle and real-tty latency for repeated full A48M scans and long context use;
4. canonical target object names, shell operations, process-replacement behavior and cassette M48O ordering;
5. native build/save/reclaim/load/direct-exec commands proven from the implemented upstream system rather than inferred from architecture prose;
6. physical unexpanded 48K boot, multi-turn conversation, compaction/model-scan exercise and clean `q` termination;
7. final source/development and runtime/distribution tape hashes plus operator transcript.

As of the Revision-0.26 checkpoint, upstream `main` is `8c8f918743897b352513b0545ff77487682c088f` and its latest durable evidence is P1.26 PASS from certified source `cb8e4ea0b68df693e5d4133fc906ed46234427b6`. P1.26 is still Phase-1 kernel wall-clock work. It does not supply the later native userland C48/MEX1/cassette execution path needed to answer the seven questions above. No exact native command sequence is invented to make this document look complete early.

The machine-readable current boundary is `evaluation/sdk-conformance/status.json`. When upstream reaches the required native phases, that snapshot must be refreshed before native qualification begins; until then `native_release_ready` remains false.

'''
    path.write_text(text[:start] + section + text[end:], encoding="utf-8")


def main() -> int:
    write_checker()
    write_status()
    patch_verify_release()
    patch_design()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
