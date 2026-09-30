<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
-->

# C48B1 to native ZX-UX contract

This file freezes the Phase 3 target contract for `c48b2tap`.

## Authority

The read-only native ZX-UX authority is commit
`69348ee366c48b436aa0d07237ae2e7473e55327`. The relevant frozen
sources are `v1/docs/obj1.md`, `v1/docs/mex1.md`,
`v1/docs/tape-object.md`, `v1/docs/c48.md`,
`v1/include/zx48ux.inc`, `v1/src/libc48/crt0.asm`, and the
`v1/src/libc48/` runtime sources. The native repository is reference-only.

## Object and executable formats

OBJ1 is version 1 with a 24-byte header, CCITT-FALSE CRC16, 20-byte symbol
records, 6-byte ABS16 relocation records, exact stored length, and no trailing
bytes. Relocations are strictly increasing and non-overlapping. Text plus BSS
and the complete stored object are each bounded by 32768 bytes.

MEX1 is version 1 with a 24-byte header, image-relative entry point, minimum
FAST-stack request from 64 through 4096 bytes, image-relative relocation words,
CCITT-FALSE CRC16, and no trailing bytes. Image plus BSS and complete stored
MEX1 are each bounded by 32768 bytes.

M48O version 1 BIN objects use type 2, target directory BIN (1), flags zero,
RAW codec zero, equal physical and logical lengths, a portable 1..10 byte base
name, payload CRC16, header CRC16 with the CRC field zeroed, and four zero
reserved bytes. The M48O payload is the exact MEX1 byte stream. TAP framing uses
ZX data blocks with flag FF, XOR checksums, one 32-byte M48O header block, and
payload blocks of at most 512 bytes.

`compiler/c48/native_format.py` is the SDK-owned independent encoder and
decoder for these contracts. Arithmetic used for offsets, counts, and total
sizes is widened before the 32768-byte limits are enforced.

## C48 target ABI

The target data model is char/unsigned char 1 byte, short/unsigned short/int/
unsigned int 2 bytes, pointer 2 bytes, and Spectrum Float5 5 bytes. Plain char
is unsigned.

C48_REGCALL places the first three scalar/pointer argument words in HL, DE, and
BC. Additional argument words are pushed right-to-left and removed by the
caller. Eight-bit arguments are zero-extended. Scalar returns use L for
eight-bit values and HL for 16-bit/pointer values. AF, BC, DE, and HL are
caller-clobbered. IX is callee-preserved when used. IY and the alternate
register bank remain reserved to ZX-UX.

Float arguments are pointers to caller-owned five-byte values. A float return
uses a hidden result pointer in HL, shifts user arguments right by one ABI slot,
writes exactly five bytes, and returns that pointer in HL.

The normal linked entry point is startup, not `main`. Startup calls
`main`, passes its result to `exit`, and is included before the user
object unless an explicitly tested no-start mode is added later.

## Translation boundary

C48B1 remains the deterministic host executable/IR. `c48b2tap` validates
it with the existing strict C48B1 decoder and then lowers supported typed nodes
to documented Z80 code, OBJ1 symbols/relocations, native runtime calls, and
startup. It never wraps C48B1 bytes in a tape object and never places a host
interpreter in the target payload.

Supported target lowering must preserve integer width/wrap, signedness,
pointer scaling, arrays, globals/statics, strings, function calls and
recursion, control flow, initializers, deterministic source evaluation order,
and the frozen Float5/runtime boundary. A dependency that has no proved native
implementation is rejected before any destination is replaced.

Host-only execution conveniences and target-only ZX-UX services are recorded
explicitly in the Phase 3 divergence table as the backend is completed.
