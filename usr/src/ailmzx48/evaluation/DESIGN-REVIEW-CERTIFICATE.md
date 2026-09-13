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
- detailed-design Git blob: `fb090795488eb9cd168f4c5a3e6df89667f4bf34`
- detailed-design SHA-256: `50effb12fb2c37a391821849f18bf4fceac2212ebb203ff06926836b8b073660`
- repaired C48 source SHA-256: `d8def7e22c53657bab1fa66b85bdd1f3be4a04ada54579d488301e7014227693`
- SDK C48B1 artifact SHA-256: `d6a1b234877e8592c53db17018e59e64c4bf7055d5b682f35b7b24302bfe73da`
- cold A48M SHA-256: `e2df4c13bc0b98999cec1e155bf0c7100d6ffd01965e6d2a4d05071c4da888db`
- upstream ZX-UX main inspected read-only: `cb8e4ea0b68df693e5d4133fc906ed46234427b6`
- latest inspected upstream durable certification item: `P1.25`

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
