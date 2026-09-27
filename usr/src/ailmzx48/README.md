# ailmzx48 source

This directory contains the SDK-side C48 source for `ailmzx48`.

## Native ZX-UX build limit

`ailmzx48` is too large in its current form to compile on a real ZX-UX
system with the current native C48 compiler. The source plus its included
headers exceed native compiler resource limits when treated as one native
translation unit.

A native build would require the program to be refactored into smaller
translation units first. The current source remains the authoritative SDK-side
source and is retained for SDK compilation, execution, and verification.

SANYALnet Labs
