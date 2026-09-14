#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use permitted; Commercial Use and use
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

ROOT = Path.cwd()
A = ROOT / 'usr' / 'src' / 'ailmzx48'
E = A / 'evaluation'


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise RuntimeError(f'anchor mismatch {path}: {old[:80]!r} count={text.count(old)}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch() -> None:
    ref = A / 'tooling' / 'a48m_reference.py'
    replace_once(
        ref,
        'TOKEN_RE = re.compile(r"[A-Za-z0-9]+")\n',
        'TOKEN_RE = re.compile(r"[A-Za-z0-9]+")\n'
        'ANCHOR_GAP_WORDS = (\n'
        '    "a", "an", "the", "and", "in", "on", "at",\n'
        '    "for", "with", "by", "of", "from", "to", "style",\n'
        ')\n'
    )
    old = (
        '    first = 2 if len(words) > 3 else max(0, len(words) - 2)\n'
        '    anchors: list[tuple[int, int]] = []\n'
        '    if words[0].lower() in set(anchor_words) and first > 0:\n'
        '        anchors.append((starts[0], ends[0] - starts[0]))\n'
        '    anchors.append((starts[first], ends[-1] - starts[first]))\n'
        '    payload.append(0x02)\n'
        '    if any(length < 1 or length > 255 for _, length in anchors):\n'
        '        raise A48MError("predicate anchor outside u8 length")\n'
        '    return bytes(payload), anchors\n'
    )
    new = (
        '    gap = -1\n'
        '    trigger_set = {word.lower() for word in anchor_words}\n'
        '    for filler in ANCHOR_GAP_WORDS:\n'
        '        for index, word in enumerate(words):\n'
        '            if word.lower() != filler or word.lower() in trigger_set:\n'
        '                continue\n'
        '            if index == len(words) - 1:\n'
        '                continue\n'
        '            if index == 0 and filler not in ("a", "an", "the"):\n'
        '                continue\n'
        '            gap = index\n'
        '            break\n'
        '        if gap >= 0:\n'
        '            break\n'
        '    if gap < 0:\n'
        '        raise A48MError("fact has no safe learned-word anchor gap")\n'
        '    anchors: list[tuple[int, int]] = []\n'
        '    if gap > 0:\n'
        '        anchors.append((starts[0], ends[gap - 1] - starts[0]))\n'
        '    if gap + 1 < len(words):\n'
        '        anchors.append((starts[gap + 1], ends[-1] - starts[gap + 1]))\n'
        '    payload.append(0x02)\n'
        '    if not anchors or len(anchors) > 2:\n'
        '        raise A48MError("fact anchor count outside Candidate-A bound")\n'
        '    if any(length < 1 or length > 255 for _, length in anchors):\n'
        '        raise A48MError("fact anchor outside u8 length")\n'
        '    return bytes(payload), anchors\n'
    )
    replace_once(ref, old, new)

    test = E / 'test_a48m_reference.py'
    replace_once(
        test,
        'from a48m_reference import (\n    A48MError,\n',
        'from a48m_reference import (\n    A48MError,\n    ANCHOR_GAP_WORDS,\n'
    )
    replace_once(
        test,
        '    parse_container,\n    protected_bytes,\n    u16,\n)\n',
        '    parse_container,\n    protected_bytes,\n    token_spans,\n    u16,\n)\n'
    )
    needle = (
        '    assert all(sum(length for _, length in record["anchors"])\n'
        '               < len(record["payload"]) - 2\n'
        '               for record in parsed["records"])\n'
        '    assert any(record["triggers"] for record in parsed["records"])\n'
    )
    insertion = (
        '    assert all(sum(length for _, length in record["anchors"])\n'
        '               < len(record["payload"]) - 2\n'
        '               for record in parsed["records"])\n'
        '    fact_rows = [\n'
        '        row for row in json.loads(corpus.read_text(encoding="utf-8"))["records"]\n'
        '        if row.get("kind") == "fact-user"\n'
        '    ]\n'
        '    assert len(fact_rows) == len(parsed["records"])\n'
        '    for source, record in zip(fact_rows, parsed["records"]):\n'
        '        payload = record["payload"]\n'
        '        spans = [span for span in token_spans(payload) if not span[2]]\n'
        '        uncovered = []\n'
        '        for start, end, _ in spans:\n'
        '            covered = any(\n'
        '                off <= start and end <= off + length\n'
        '                for off, length in record["anchors"]\n'
        '            )\n'
        '            if not covered:\n'
        '                code = payload[start]\n'
        '                assert code in (0xF1, 0xF2, 0xF3)\n'
        '                size = payload[start + 1]\n'
        '                word = bytes(\n'
        '                    payload[start + 2:start + 2 + size]\n'
        '                ).decode("ascii").lower()\n'
        '                uncovered.append(word)\n'
        '        assert len(uncovered) == 1, (source["text"], uncovered)\n'
        '        assert uncovered[0] in ANCHOR_GAP_WORDS, (\n'
        '            source["text"], uncovered\n'
        '        )\n'
        '        triggers = {\n'
        '            str(value).lower() for value in source.get("triggers", [])\n'
        '        }\n'
        '        assert uncovered[0] not in triggers, (source["text"], uncovered)\n'
        '    assert any(record["triggers"] for record in parsed["records"])\n'
    )
    replace_once(test, needle, insertion)
    replace_once(
        test,
        '            "predicate-anchor-not-full-sentence",\n',
        '            "predicate-anchor-not-full-sentence",\n'
        '            "critical-anchor-coverage-one-safe-gap",\n'
    )

    design = A / 'AILMZX48-DETAILED-DESIGN.md'
    replace_once(design, 'Revision: 0.27-draft', 'Revision: 0.28-draft')
    marker = '### 6.1 No remote inference dependency\n'
    note = (
        'Implementation measurement note (Revision 0.28): a fresh SoP model scan found that the first predicate-anchor splitter could omit factual relation or multi-word subject tokens even though keyword regressions remained green.  The repaired A48M builder now anchors every factual lexical token except exactly one allowlisted low-information filler word (`a`, `an`, `the`, `and`, `in`, `on`, `at`, `for`, `with`, `by`, `of`, `from`, `to`, or `style`) that is not itself a retrieval trigger.  The host reference independently parses every emitted record and rejects any factual record with more than one uncovered lexical token, an uncovered token outside that allowlist, or an uncovered trigger.  This preserves names and relation verbs such as `amstrad acquired`, `the hobbit was`, `jet set willy followed`, `knight lore is known`, and `head over heels was` while still preventing a complete stored sentence from becoming one immutable anchor span.\n\n'
    )
    replace_once(design, marker, note + marker)
    replace_once(
        design,
        'Revision 0.27 closes the SDK-side design questions',
        'Revision 0.28 closes the SDK-side design questions'
    )
    replace_once(
        design,
        '- A48M v2 is 8,458 logical bytes with 69 records, a 192-byte maximum record,\n'
        '  a 64-byte maximum read request, and cold-model SHA-256\n'
        '  `3dda3f6633cd8731e158970bf0658cd9126496e9d7c30ff14ab4cbcae25611ea`;',
        '- A48M v2 is 8,538 logical bytes with 69 records, a 192-byte maximum record,\n'
        '  a 64-byte maximum read request, and cold-model SHA-256\n'
        '  `aad821b22b10482cd598f58888fb257149c7847d88ec6bb5b6fdae9ea6f1f1e1`;'
    )
    replace_once(
        design,
        '- factual A48M anchors cover selected predicate spans rather than complete\n'
        '  stored sentences; normal cold answers generate learned lead wording before\n'
        '  copying the selected factual span unchanged;',
        '- factual A48M anchors preserve every critical lexical fact token while\n'
        '  leaving exactly one allowlisted non-trigger filler token outside the\n'
        '  immutable spans; normal cold answers generate learned lead wording before\n'
        '  copying those selected factual spans unchanged;'
    )

    checker = E / 'check_design_compliance.py'
    text = checker.read_text(encoding='utf-8')
    replacements = {
        'Revision: 0.27-draft': 'Revision: 0.28-draft',
        'a48m.get("logical_length") == 8458': 'a48m.get("logical_length") == 8538',
        '{"final-a": 9118, "final-b": 9119,\n                      "final-c": 9120}': '{"final-a": 9123, "final-b": 9124,\n                      "final-c": 9125}',
        'run.get("iteration") == 9117': 'run.get("iteration") == 9122',
        'route_run.get("iteration") == 9121': 'route_run.get("iteration") == 9126',
        'for name in ("literal-context", "final-a", "final-b",\n                 "final-c"):': 'for name in ("literal-context", "final-a", "final-b",\n                 "final-c", "architecture-routing",\n                 "anchor-fidelity"):',
    }
    for old_text, new_text in replacements.items():
        if text.count(old_text) != 1:
            raise RuntimeError(f'checker replacement mismatch: {old_text!r}')
        text = text.replace(old_text, new_text, 1)
    old_test = (
        '    require("predicate-anchor-not-full-sentence" in\n'
        '            a48m.get("tests", []),\n'
        '            "predicate-anchor reference test missing")\n'
    )
    new_test = old_test + (
        '    require("critical-anchor-coverage-one-safe-gap" in\n'
        '            a48m.get("tests", []),\n'
        '            "critical factual-anchor coverage test missing")\n'
    )
    if text.count(old_test) != 1:
        raise RuntimeError('checker A48M test anchor mismatch')
    text = text.replace(old_test, new_test, 1)
    route_anchor = (
        '    require(second.get("ai_semuse") == 0 and\n'
        '            second.get("ai_mhits") == 0 and\n'
        '            second.get("ai_lasttop") == 0,\n'
        '            "hash-collision unknown route was not rejected")\n'
    )
    anchor_block = route_anchor + (
        '\n    anchor_score = load(base / "anchor-fidelity" / "score.json")\n'
        '    anchor_run = load(base / "anchor-fidelity" / "run.json")\n'
        '    require(anchor_score.get("keyword_ratio") == 1.0 and\n'
        '            anchor_score.get("turns") == 5,\n'
        '            "anchor-fidelity: score mismatch")\n'
        '    require(anchor_score.get("trigram_uses", 0) >= 5 and\n'
        '            anchor_score.get("cooperative_yields", 0) >= 45,\n'
        '            "anchor-fidelity: LM/yield evidence missing")\n'
        '    require(anchor_run.get("iteration") == 9127,\n'
        '            "anchor-fidelity: iteration mismatch")\n'
        '    require(anchor_run.get("source_sha256") == source_hash and\n'
        '            anchor_run.get("c48b_sha256") == binary_hash and\n'
        '            anchor_run.get("cold_model_sha256") == cold_hash,\n'
        '            "anchor-fidelity: identity mismatch")\n'
    )
    if text.count(route_anchor) != 1:
        raise RuntimeError('checker anchor-fidelity insertion mismatch')
    checker.write_text(text.replace(route_anchor, anchor_block, 1), encoding='utf-8', newline='\n')

    reqdir = E / 'sdk-conformance' / 'anchor-fidelity'
    reqdir.mkdir(parents=True, exist_ok=True)
    request = {
        'schema': 1,
        'iteration': 9127,
        'scenario': 'sdk-anchor-fidelity-v1',
        'purpose': 'SoP factual-anchor coverage proof for preserved subjects, multi-word names, and relation verbs.',
        'prompts': [
            'who acquired spectrum computer rights in april 1986',
            'tell me about the hobbit adventure and european sales',
            'what did jet set willy follow',
            'what is knight lore known for',
            'tell me about head over heels by ritman',
        ],
        'expected_keywords': [
            'amstrad acquired', 'the hobbit was',
            'jet set willy followed', 'knight lore is known',
            'head over heels was',
        ],
        'min_keyword_ratio': 1.0,
        'min_trigram_uses': 5,
        'min_cooperative_yields': 45,
        'max_seconds': 1200,
    }
    (reqdir / 'request.json').write_text(
        json.dumps(request, indent=2, sort_keys=True) + '\n',
        encoding='utf-8', newline='\n'
    )


def finalize() -> None:
    base = E / 'sdk-conformance'
    parts_path = A / 'training' / 'evaluation-partitions.json'
    parts = json.loads(parts_path.read_text(encoding='utf-8'))
    reg = parts['regression']['request_sha256']
    for name in (
        'literal-context', 'final-a', 'final-b', 'final-c',
        'architecture-routing', 'anchor-fidelity'
    ):
        reg[name] = sha(base / name / 'request.json')
    parts_path.write_text(
        json.dumps(parts, indent=2, sort_keys=True) + '\n',
        encoding='utf-8', newline='\n'
    )

    status_path = E / 'DESIGN-COMPLIANCE-STATUS.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    status['design_revision'] = '0.28-draft'
    status['source_sha256'] = sha(A / 'ailmzx48.c')
    status['sdk_c48b_sha256'] = sha(ROOT / 'usr/bin/ailmzx48/ailmzx48.c48b')
    status['cold_model_sha256'] = sha(A / 'model/cold-seed.bin')
    sdk = status['sdk_profile']
    sdk['model_architecture']['factual_anchor_policy'] = (
        'critical-content-spans-one-safe-nontrigger-filler-gap'
    )
    for name in ('final-a', 'final-b', 'final-c'):
        score = json.loads((base / name / 'score.json').read_text())
        sdk['post_repair_final_regressions'][name] = {
            key: score[key] for key in (
                'turns', 'keyword_ratio', 'clean_exit',
                'literal_reference_losses', 'trigram_uses',
                'cooperative_yields'
            )
        }
    score = json.loads((base / 'literal-context' / 'score.json').read_text())
    sdk['literal_context'] = {key: score[key] for key in (
        'turns', 'keyword_ratio', 'context_compactions', 'max_l2count',
        'max_lmcount', 'semantic_retrieval_uses', 'literal_reference_losses',
        'final_keyword_hit', 'trigram_uses', 'cooperative_yields'
    )}
    score = json.loads((base / 'architecture-routing' / 'score.json').read_text())
    sdk['architecture_routing'] = {key: score[key] for key in (
        'turns', 'keyword_ratio', 'semantic_retrieval_uses',
        'trigram_uses', 'cooperative_yields'
    )}
    score = json.loads((base / 'anchor-fidelity' / 'score.json').read_text())
    sdk['anchor_fidelity'] = {key: score[key] for key in (
        'turns', 'keyword_ratio', 'semantic_retrieval_uses',
        'trigram_uses', 'cooperative_yields'
    )}

    design = A / 'AILMZX48-DETAILED-DESIGN.md'
    data = design.read_bytes()
    dsha = hashlib.sha256(data).hexdigest()
    dblob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    status['design_sha256'] = dsha
    status['design_git_blob_sha1'] = dblob
    status_path.write_text(
        json.dumps(status, indent=2, sort_keys=True) + '\n',
        encoding='utf-8', newline='\n'
    )

    cert = E / 'DESIGN-REVIEW-CERTIFICATE.md'
    text = cert.read_text(encoding='utf-8')
    text = text.replace(
        'current Revision-0.27 SDK implementation profile',
        'current Revision-0.28 SDK implementation profile'
    ).replace(
        '- detailed-design revision: `0.27-draft`',
        '- detailed-design revision: `0.28-draft`'
    )
    lines = []
    for line in text.splitlines():
        if line.startswith('- detailed-design Git blob:'):
            line = f'- detailed-design Git blob: `{dblob}`'
        elif line.startswith('- detailed-design SHA-256:'):
            line = f'- detailed-design SHA-256: `{dsha}`'
        elif line.startswith('- repaired C48 source SHA-256:'):
            line = f'- repaired C48 source SHA-256: `{status["source_sha256"]}`'
        elif line.startswith('- SDK C48B1 artifact SHA-256:'):
            line = f'- SDK C48B1 artifact SHA-256: `{status["sdk_c48b_sha256"]}`'
        elif line.startswith('- cold A48M SHA-256:'):
            line = f'- cold A48M SHA-256: `{status["cold_model_sha256"]}`'
        lines.append(line)
    text = '\n'.join(lines) + '\n'
    old = (
        'Cold retrieval requires exact trigger spelling after salted-ID lookup, '
        'factual answers combine learned lead wording with immutable subject/predicate anchors, '
    )
    new = (
        'Cold retrieval requires exact trigger spelling after salted-ID lookup, '
        'factual answers combine learned lead wording with immutable critical-content anchors '
        'that leave exactly one allowlisted non-trigger filler word unanchored, '
    )
    if old not in text:
        raise RuntimeError('certificate anchor-policy text missing')
    cert.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('patch', 'finalize'))
    ns = ap.parse_args()
    if ns.mode == 'patch':
        patch()
    else:
        finalize()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
