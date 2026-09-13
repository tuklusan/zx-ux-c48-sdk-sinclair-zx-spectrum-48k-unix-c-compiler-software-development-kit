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
from pathlib import Path

P = Path("usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md")
t = P.read_text(encoding="utf-8")


def one(old, new):
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"expected one match, got {n}: {old[:100]!r}")
    t = t.replace(old, new, 1)


one("Revision: 0.7-draft", "Revision: 0.8-draft")
one("Revision 0.7 retains it as a corrected benchmark baseline",
    "Revision 0.8 retains it as a corrected benchmark baseline")
one("Revision 0.7 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:",
    "Revision 0.8 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:")
one("## 23. Open design questions after Revision 0.7",
    "## 23. Open design questions after Revision 0.8")

one(
"""Candidate A uses a 16-byte L1 capsule:

```text""",
"""Candidate A uses a 16-byte L1 capsule. Before target implementation, each intent/relation-class ID also freezes a small host/target schema saying which semantic-reference fields are meaningful and whether bytes +12..13 hold a raw numeric/date/token payload or a semantic reference. The same schema drives validation, correction keys, session-literal invalidation and host/target differential tests; a field is never guessed to be a reference from its bit pattern alone.

```text""")

one(
"""Every session-literal reference is validated against its slot and generation before use. A stale reference is treated as absent and counted; it is never allowed to resolve to newly reused bytes.""",
"""Every semantic-reference-bearing field identified by the frozen relation schema—including +12..13 when that relation declares it a semantic ref—is validated before use. A session-literal ref must match its slot and generation; a stale ref is cleared/treated as absent and counted, never resolved to newly reused bytes. Slot invalidation scans exactly the same schema-declared fields, so no hidden semantic-ref position can escape generation checking.""")

one(
"""- resident-vocabulary identity, record count, logical length and section lengths.""",
"""- resident-vocabulary identity, hot/cold interface identity, record count, logical length and section lengths.""") if "- resident-vocabulary identity, record count, logical length and section lengths." in t else None

# The current prose is a sentence, not a bullet.
one(
"""The container shall declare at least format version, feature flags, resident-vocabulary identity, record count, logical length and section lengths.""",
"""The container shall declare at least format version, feature flags, resident-vocabulary identity, a fixed-size hot/cold **interface identity**, record count, logical length and section lengths. The interface identity is generated from the canonical lexical-ID map, semantic-symbol map, relation/record schemas and scoring-feature schema; target code compares the fixed bytes before accepting records. This prevents a cold object from a different build from being interpreted under merely similar vocabulary. Host provenance additionally records SHA-256 of the full interface description; the exact compact target identity width is frozen with A48M.""")

one(
"""An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical/control/literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries. Candidate A permits at most two spans; factual record types admitted for factual-answer use must carry at least one. The controller copies required anchor sequences byte-for-byte into its anchor plan and never asks the LM to regenerate their content from memory.""",
"""An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical/control/literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries. Candidate A permits at most two spans; factual record types admitted for factual-answer use must carry at least one. The anchor plan does **not** copy those bytes: it stores only bounded `(winner_slot, payload_offset, encoded_length, progress)` descriptors inside generation/scoring state. The two complete winner slots remain live until response generation finishes, and required anchor bytes are copied directly from the referenced winner into the response buffer. This preserves anchors without inventing an unbudgeted duplicate buffer.""")

one(
"""Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, illegal/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, overlapping anchors, or payload parsing that does not consume exactly the declared record. Payload-only wording need not consume resident dictionary bytes.""",
"""Cold payloads use the same canonical lexical/literal encodings as conversation text. Candidate-A payload controls are limited to BOS, EOS and newline; user-turn, assistant-turn, turn-end, `0x00`, reserved wire controls and unknown escapes are forbidden inside a knowledge-record payload.

Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, forbidden/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, overlapping anchors, or payload parsing that does not consume exactly the declared record. Payload-only wording need not consume resident dictionary bytes.""")

one(
"""The target model includes an incremental integrity check suitable for the Z80/C48 implementation. Every complete cold scan validates structural bounds and accumulates that integrity check while bytes are already streaming.""",
"""The target model includes an incremental integrity check suitable for the Z80/C48 implementation. Before record scoring, the target validates the A48M header/version/declared lengths plus resident-vocabulary and hot/cold-interface identities. Every complete cold scan then validates structural bounds and accumulates the integrity check while bytes are already streaming.""")

one(
"""- the reviewed read-only model-object adapter required above before external-model runs are called end-to-end SDK tests;
- optional VM-global inspection helpers""",
"""- the reviewed read-only model-object adapter required above before external-model runs are called end-to-end SDK tests;
- an explicit VM heap setting equal to the candidate configuration (`heap_size=0` for the initial zero-heap target), never the host VM's convenient default; this catches accidental `malloc` dependence even though it does not certify native BSS placement;
- optional VM-global inspection helpers""")

one(
"""C48 compiler/runtime version and relevant hashes
ailmzx48 source hash
model build id and model SHA-256
scenario id/hash""",
"""C48 compiler/runtime version and relevant hashes
ailmzx48 source hash and compiled C48B1 artifact hash
model build-manifest hash plus SHA-256 of every generated hot/cold model artifact
compact hot/cold interface identity embedded in the tested artifacts
configured SDK heap value and target heap/link settings
scenario id/hash""")

one(
"""5. cold knowledge-record builder and sequential two-winner retrieval benchmark;
6. pruned bounded-fanout order-1/2/3 hot language-model trainer and quantizer;
7. frozen experimental A48M container plus host packer/verifier with u16 target-limit tests;""",
"""5. cold knowledge-record builder, frozen relation/semantic-reference schemas, anchor-span validation and sequential two-winner retrieval benchmark;
6. pruned bounded-fanout order-1/2/3 hot language-model trainer, quantizer and widened score-bound proof;
7. frozen experimental A48M container plus host packer/verifier with u16 target-limit and hot/cold-interface-identity mismatch tests;""")

one(
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit?""",
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do mismatched hot/cold interface identities fail before record use?""")

one("- final A48M numeric field IDs, section order and integrity algorithm;",
    "- final A48M numeric field IDs, section order, compact hot/cold interface-identity width and integrity algorithm;")

if "Revision 0.7" in t:
    raise SystemExit("stale Revision 0.7 reference remains")

P.write_text(t, encoding="utf-8", newline="\n")
