<!--
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
certificate and the Revision-0.27 SDK certificate for the current
Revision-0.29 SDK implementation profile. Historical evidence remains retained;
this certificate states the current qualified SDK scope.

## Reviewed identities

- detailed-design revision: `0.29-draft`
- detailed-design Git blob: `f8120b66ade6029665cbd11910bdea593f9d64d9`
- detailed-design SHA-256: `796b2f9c6f6b1c630b2e7ef709f1969f264ce1bacf4edd3ae570f27c51778ad9`
- repaired C48 source SHA-256: `b660cf6c9122b900e07ebe37a08534b37ddd92af89e4db4888e2beb640fa06d3`
- SDK C48B1 artifact SHA-256: `73e07177c16a07fee979a0ba37d174c5d95a13559aebacfdc8060de10649f209`
- cold A48M SHA-256: `a0b87573f6e380bf33ba4f4803e9abd917f64c958793717da6d6130dc5fa1096`
- cold A48M logical length: `8566` bytes
- factual records: `69`
- learned bridge contexts: `68`
- bridge hash salt: `0`
- upstream ZX-UX main inspected read-only: `8c8f918743897b352513b0545ff77487682c088f`
- latest inspected upstream durable certification item: `P1.26`
- certified source named by P1.26: `cb8e4ea0b68df693e5d4133fc906ed46234427b6`

## Three-pass zero-gap result

**SDK_PROFILE: PASS (3/3 zero-gap passes)**

Pass 1 maps frozen SDK-scope design requirements to target implementation and
fixed bounds. Pass 2 maps the repaired implementation identity to fresh retained
SDK evidence and complete seed-record lineage. Pass 3 checks durability,
release-gate integration, current design/status identities, removal of repair
scaffolding, and the prohibition on turning SDK evidence into a native claim.

Fresh retained VM evidence uses iterations 9131 through 9136. Learned-bridge
iteration 9131 passed 2/2 factual prompts with 2 bridge uses and 2 real trigram
uses. Architecture-routing iteration 9132 passed its two-turn collision and
unknown-route proof. Literal/context iteration 9133 passed 70 turns while
retaining bounded compaction, literal invalidation and model-ring behavior.
Final A/B/C iterations 9134/9135/9136 each passed all 12 prompts with clean exit
and no literal-reference losses.

Every cold scan recomputes Fletcher-16 and rejects vocabulary/interface identity mismatch before record use.

The schema-3 hot plane is a bounded variable-order LM with a 12-token unigram
fallback, topic-conditioned bigrams and 64 sorted sparse trigram contexts. Cold
retrieval requires exact trigger spelling after salted-ID lookup. Factual answers
retain immutable admitted-fact anchors while exactly one safe non-trigger gap is
supplied through a 68-row learned factual bridge. The runtime validates the hot
vocabulary spelling against the cold gap but does not copy those cold gap bytes
into the answer. The bounded resident bridge scan needs no inner cooperative
yield; measured outer cold/model scans retain their deterministic yield cadence.
`ai_bruse` counts learned bridge emissions and `ai_triuse` remains exclusively a
real trigram-table-use counter. The blind candidate remains reserved and unscored;
no blind-generalization result is claimed.

## Native release boundary

**FULL_NATIVE_RELEASE: BLOCKED_EXTERNAL**

The current upstream ZX-UX implementation is still at Phase-1 durable evidence;
it does not yet expose the native C48/OBJ1/MEX1, allocator/stack/Fuse and
physical-cassette path required for the design's native proof. Those obligations
remain in the design and machine-readable status as blockers. They are not
waived, simulated by the host SDK, or counted among the three SDK zero-gap
passes. Other GitHub projects remain read-only.

A full native-release PASS requires a new certificate after the upstream native
facilities exist and the Section-18.4 proof has been executed and retained.
