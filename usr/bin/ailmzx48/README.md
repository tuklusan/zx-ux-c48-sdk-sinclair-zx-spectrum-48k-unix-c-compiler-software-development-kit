<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
-->

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
