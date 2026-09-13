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
certificate for the current Revision-0.26 SDK implementation profile.  It does
not erase that historical evidence; it makes the current scope explicit.

## Reviewed identities

- detailed-design revision: `0.26-draft`
- detailed-design Git blob: `f826c56c7507e3ce6207c00c4461af6738f140fd`
- detailed-design SHA-256: `0d804bc183c81f801d2a99f93e18ce6c71238430ee339aed78f25fcc965ad4c3`
- repaired C48 source SHA-256: `0a99c9287119760bad0a17f3128ed9cfccd8a7cd6a94472c9b53cc867abf8b7c`
- SDK C48B1 artifact SHA-256: `6c3dd416e482bd8d7d8698bd30d06dce93326c67417700cecb9d721fddbeb518`
- cold A48M SHA-256: `e2df4c13bc0b98999cec1e155bf0c7100d6ffd01965e6d2a4d05071c4da888db`
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
