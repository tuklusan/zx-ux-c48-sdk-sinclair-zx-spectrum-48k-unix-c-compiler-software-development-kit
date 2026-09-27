<!-- Copyright (c) 2026 SANYALnet Labs. -->
<!-- ZX-UX C48 SDK -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the root LICENSE file. -->
<!-- Attribution required: SANYALnet Labs. -->

# ailmzx48 SDK artifacts

This directory contains SDK-side runtime artifacts for `ailmzx48`.

## Native ZX-UX build limit

The current `ailmzx48` source is too large as-is to compile on a real ZX-UX
system with the current native C48 compiler.

Accordingly, `ailmzx48.c48b` is an SDK artifact. It is not evidence of a
native ZX-UX compile to OBJ1 or a native link to MEX1. A native build would
require the source to be refactored into smaller translation units first.

`ailm.dat` is the associated runtime data object used by the SDK artifact.

SANYALnet Labs
