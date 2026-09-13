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


one("Revision: 0.8-draft", "Revision: 0.9-draft")
one("Revision 0.8 retains it as a corrected benchmark baseline",
    "Revision 0.9 retains it as a corrected benchmark baseline")
one("Revision 0.8 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:",
    "Revision 0.9 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:")
one("## 23. Open design questions after Revision 0.8",
    "## 23. Open design questions after Revision 0.9")

one(
"""The baseline cold plane is scanned forward exactly once per user turn. With one persistent handle, the scanner seeks to logical offset zero at the start of the next turn; on a PACKED object REV12 therefore resets the decoder and the subsequent scan decodes forward again. The scanner issues bounded logical reads no larger than 64 bytes and places `yield()`/kernel boundaries at measured chunk or record intervals rather than asking one syscall to decompress the entire model.""",
"""The baseline cold plane is scanned forward exactly once per user turn. At model-open time the program obtains the object's actual logical length through the canonical object metadata/stat path and requires it to equal the A48M declared logical length before any record can be accepted. With one persistent handle, the scanner seeks to logical offset zero at the start of the next turn; on a PACKED object REV12 therefore resets the decoder and the subsequent scan decodes forward again.

The scanner requests logical chunks no larger than 64 bytes but never assumes one `read` returns the whole request. It uses `read_full` where the exact remaining byte count is known, or an equivalent bounded loop that accepts legal positive short reads and treats zero/premature EOF before the declared end as model corruption. It never reads past the declared/actual equal logical length. `yield()`/kernel boundaries occur at measured chunk or record intervals rather than asking one syscall to decompress the entire model.""")

one(
"""An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical/control/literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries.""",
"""An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical or literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries. BOS, EOS, newline and every other control byte are forbidden **inside anchor spans**: anchors represent factual content, not sentence/turn framing.""")

one(
"""Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, forbidden/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, overlapping anchors, or payload parsing that does not consume exactly the declared record.""",
"""Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, forbidden/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, control bytes inside anchors, overlapping anchors, or payload parsing that does not consume exactly the declared record.""")

one(
"""Before record scoring, the target validates the A48M header/version/declared lengths plus resident-vocabulary and hot/cold-interface identities. Every complete cold scan then validates structural bounds and accumulates the integrity check while bytes are already streaming.""",
"""Before record scoring, the target validates the A48M header/version/declared lengths, requires actual object logical length == declared logical length, and checks resident-vocabulary plus hot/cold-interface identities. Every complete cold scan then validates section boundaries, exact declared record count, structural bounds and the requirement that the last declared section/record ends exactly at logical length while accumulating the integrity check over the canonical protected bytes.""")

one(
"""It must fail with target-like bounds/errors and must not become a hidden alternate inference path. A RAW fixture adapter can validate parser/retriever logic; claims about ZXP1 decoder state, packed seek cost, allocator placement or cassette behavior still require their native/architecture-specific tests.""",
"""It must fail with target-like bounds/errors, support deterministic positive short-read injection and premature-EOF/error cases, expose the fixture's actual logical length to the C48 path, and must not become a hidden alternate inference path. A RAW fixture adapter can validate parser/retriever logic; claims about ZXP1 decoder state, packed seek cost, allocator placement or cassette behavior still require their native/architecture-specific tests.""")

one(
"""12. cold model reader/sequential scorer using bounded reads/yields and at most two winners;""",
"""12. cold model reader/sequential scorer using bounded short-read-safe reads/yields, exact object-vs-header length/count validation and at most two winners;""")

one(
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do mismatched hot/cold interface identities fail before record use?""",
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do object/header length mismatches, short/premature reads and mismatched hot/cold interface identities fail before record use?""")

if "Revision 0.8" in t:
    raise SystemExit("stale Revision 0.8 reference remains")

P.write_text(t, encoding="utf-8", newline="\n")
