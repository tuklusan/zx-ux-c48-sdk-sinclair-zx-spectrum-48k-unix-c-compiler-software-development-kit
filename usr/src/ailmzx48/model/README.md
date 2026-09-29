<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
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
