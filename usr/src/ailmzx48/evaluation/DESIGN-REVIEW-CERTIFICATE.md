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
- detailed-design Git blob: `b99219d028a58e1996b80c02ab24fe3e1f750801`
- detailed-design SHA-256: `128bf43c1a3a7407c64d757eaaafa77772d34fad00af53960b4b685984f62b92`
- repaired C48 source SHA-256: `0a99c9287119760bad0a17f3128ed9cfccd8a7cd6a94472c9b53cc867abf8b7c`
- SDK C48B1 artifact SHA-256: `660ced3835b1f12e7be1e5cde947a94bd12b18f252bfac0f6c4e0dbe306d4ba6`
- cold A48M SHA-256: `5d0ad7ad82c5547f37714df1baa859510d199598e0b4a10e330393a288c70cd6`
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
