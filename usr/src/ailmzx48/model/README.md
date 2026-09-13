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
# ailmzx48 model

The retained SDK model is an A48M Candidate-A prototype v2 cold stream plus
generated resident C48 tables.  The canonical cold seed is `cold-seed.bin`;
`cold-seed.json` records its logical length, record count, interface identity,
trigger salt and SHA-256.  `current-model.json` and `iterations/` retain model
construction identities used by qualified conversations.

A48M reference validation is mandatory.  The current qualified cold stream is
bounded to 65535 logical bytes, requests at most 64 bytes per read, permits
records no larger than 192 bytes and retains at most two winners during a scan.
The SDK artifact is C48B1/VM code, not native OBJ1, MEX1 or Z80 machine code.
Native model-object packaging remains blocked on the upstream ZX-UX native
release phases and is not inferred from SDK evidence.
