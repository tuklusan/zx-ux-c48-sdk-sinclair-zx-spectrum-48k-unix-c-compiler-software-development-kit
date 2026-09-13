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


one("Revision: 0.9-draft", "Revision: 0.10-draft")
one("Revision 0.9 retains it as a corrected benchmark baseline",
    "Revision 0.10 retains it as a corrected benchmark baseline")
one("Revision 0.9 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:",
    "Revision 0.10 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:")
one("## 23. Open design questions after Revision 0.9",
    "## 23. Open design questions after Revision 0.10")

one(
"""The 16-bit **semantic-reference** namespace used by L1/L2 and cold-record entity fields is deliberately separate from the 0..4095 lexical token-ID namespace. Semantic reference 0 means absent; persistent semantic symbols use 1..0x7FFF; bit-15-set values are session literals. Host tooling owns the mapping from recognized lexical tokens/phrases to persistent semantic symbols and charges that mapping to resident hot-table bytes. A lexical token ID is never copied blindly into a semantic-reference field.""",
"""The 16-bit **semantic-reference** namespace used by L1/L2 and cold-record entity fields is deliberately separate from the 0..4095 lexical token-ID namespace. Semantic reference 0 means absent; persistent semantic symbols use 1..0x7FFF; bit-15-set values are session literals. Host tooling owns the mapping from recognized lexical tokens/phrases to persistent semantic symbols and charges that mapping to resident hot-table bytes. A lexical token ID is never copied blindly into a semantic-reference field.

Topic IDs are a third namespace. Candidate A reserves topic ID 0 for generic/unknown and assigns 1..65535 only through the generated model's frozen topic-ID map. L1/L2 topic fields, classifier outputs and cold-record `topic_id` values all use that same map. The map is a hot/cold compatibility input, not an incidental trainer ordering.""")

one(
"""The interface identity is generated from the canonical lexical-ID map, semantic-symbol map, relation/record schemas and scoring-feature schema; target code compares the fixed bytes before accepting records.""",
"""The interface identity is generated from the canonical lexical-ID map, topic-ID map, semantic-symbol map, relation/record schemas and scoring-feature schema; target code compares the fixed bytes before accepting records.""")

one(
"""7. frozen experimental A48M container plus host packer/verifier with u16 target-limit and hot/cold-interface-identity mismatch tests;""",
"""7. frozen experimental A48M container plus host packer/verifier with u16 target-limit and hot/cold-interface-identity mismatch tests, including changed topic-ID assignments;""")

one(
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do object/header length mismatches, short/premature reads and mismatched hot/cold interface identities fail before record use?""",
"""9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do object/header length mismatches, short/premature reads and mismatched hot/cold interface identities—including changed topic-ID maps—fail before record use?""")

if "Revision 0.9" in t:
    raise SystemExit("stale Revision 0.9 reference remains")

P.write_text(t, encoding="utf-8", newline="\n")
