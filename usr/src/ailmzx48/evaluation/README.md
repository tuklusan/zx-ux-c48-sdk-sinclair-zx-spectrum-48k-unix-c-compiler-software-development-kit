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
# ailmzx48 evaluation

This directory contains the executable reference tests, retained score gates,
training exit criteria, SDK conformance evidence and design-compliance status.
`test_context_reference.py` validates the bounded L0/L1/L2/session-literal
oracle.  `test_a48m_reference.py` validates the cold A48M stream.  The
`sdk-conformance/` subtree retains post-runtime-repair literal/context and final
A/B/C requalification runs.

`check_design_compliance.py` is the durable three-pass SDK-profile compliance
gate.  It intentionally reports the full native-release profile as
`BLOCKED_EXTERNAL` until native ZX-UX C48/OBJ1/MEX1, allocator/stack/Fuse and
physical-cassette evidence exists.  `DESIGN-REVIEW-CERTIFICATE.md` records that
scope distinction; an SDK PASS is never a native certification.
