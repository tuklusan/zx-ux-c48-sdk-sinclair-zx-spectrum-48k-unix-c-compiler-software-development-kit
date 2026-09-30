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

## Runtime provenance and supported-symbol policy

The host linker never reads a moving native checkout. Runtime members are
constructed deterministically inside the SDK. The startup, exit, puts, ink,
plot, and udg_clear members are byte-exact copies of the corresponding frozen
OBJ1 members in the pinned native tree. Release verification checks their
complete serialized OBJ1 digests.

Other accepted runtime helpers are deterministic target-equivalent
translations of the pinned libc48 assembly contract. They are used only where
the backend has an explicit lowering and tests for the same observable C48
semantics. An external symbol with neither an exact pinned member nor a proved
translation is unresolved and the output transaction fails.

The supported boundary is intentionally narrower than the host interpreter.
Five-byte floating arithmetic, casts, comparisons, truth testing, hidden
Float5 returns, and the admitted public math calls are emitted through the
pinned ZX-UX floating syscall ABI and its exact five-byte storage convention.
Block-scope static storage is rejected by the current target lowering.
Host-only display conveniences are not silently translated into target calls.

Exact prebuilt-member provenance comes from `v1/src/libc48/crt0.asm` and
the P10/P11 object members in `v1/src/libc48/runtime_archive.asm`. Translated
integer, string, memory, graphics, process, Float5, and math helpers are tied
to the corresponding pinned libc48 sources and `v1/include/zx48ux.inc`.
`compiler/native_runtime_provenance.json` records the authority commit,
source set, exact serialized-member digests, archive order, and complete
exported-symbol map checked by release verification.
