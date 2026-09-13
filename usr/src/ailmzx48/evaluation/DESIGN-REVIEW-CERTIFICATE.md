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
certificate for the current Revision-0.27 SDK implementation profile.  It does
not erase that historical evidence; it makes the current scope explicit.

## Reviewed identities

- detailed-design revision: `0.27-draft`
- detailed-design Git blob: `93335d286b87a5538f27de2d043a71f0add04980`
- detailed-design SHA-256: `1412cde257bb5026eee313aadc6830fbf6a50195b89983fa6c791671100f6f04`
- repaired C48 source SHA-256: `660d517059644b04a3e6507d45d28aed7603cdfd5e0ab5adc136bd121cc3c3b7`
- SDK C48B1 artifact SHA-256: `560414b6a1e8dd2f388adbff6887508b855d6e91649c08bcc525447910fc9584`
- cold A48M SHA-256: `3dda3f6633cd8731e158970bf0658cd9126496e9d7c30ff14ab4cbcae25611ea`
- upstream ZX-UX main inspected read-only: `8c8f918743897b352513b0545ff77487682c088f`
- latest inspected upstream durable certification item: `P1.26`
- certified source named by P1.26: `cb8e4ea0b68df693e5d4133fc906ed46234427b6`

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

Every cold scan recomputes Fletcher-16 and rejects vocabulary/interface identity mismatch before record use.

The schema-3 hot plane is a bounded variable-order LM with a 12-token unigram fallback, topic-conditioned bigrams and 64 sorted sparse trigram contexts. Cold retrieval requires exact trigger spelling after salted-ID lookup, factual answers combine learned lead wording with immutable subject/predicate anchors, topic 0 is generic/unknown, and cold scans yield after each eight records. The blind candidate remains reserved and unscored; no blind-generalization result is claimed.

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
