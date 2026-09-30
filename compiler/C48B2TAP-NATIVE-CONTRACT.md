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

### Pinned-reference execution errata

The pinned revision is also frozen as evidence for four native-owned execution
fault sites that affect the BIN tape route but do not change the artifact
formats frozen below:

1. P509's match/public-type check loads the M48O type with
   `ld b,(p509_header+M48O_HDR_TYPE)`, which is not a target Z80 memory-load
   form and is encoded by the pinned assembler as an immediate byte.
2. P509 repeats the same invalid type-load form in its new-object commit path.
3. P504's successful RAW return leaves DE holding the expected payload CRC,
   while P509 consumes DE as the new object's logical length.
4. P514's streamed image loop calls the CRC updater without preserving the
   just-loaded image byte before `ld (hl),a`.

The SDK keeps generated OBJ1, MEX1, M48O and TAP bytes unchanged. Independent
format oracles and native linker consumption remain unmodified. The execution
verifier first proves each frozen native failure at the earliest reachable
site, then uses only independently bounded, fail-closed in-memory corrections
to reach and prove later sites and the final executable behavior. A correction
is removed only after a new native revision is pinned and the complete native
contract is requalified.

## Object and executable formats

OBJ1 is version 1 with a 24-byte header, CCITT-FALSE CRC16, 20-byte symbol
records, 6-byte ABS16 relocation records, exact stored length, and no trailing
bytes. Relocations are strictly increasing and non-overlapping. Text plus BSS
and the complete stored object are each bounded by 32768 bytes.

MEX1 is version 1 with a 24-byte header, image-relative entry point, minimum
FAST-stack request that is even and from 64 through 4096 bytes, image-relative relocation words,
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

## Frozen host/native semantic divergence matrix

The classifications below are part of the target contract. **Exact** means the
generated target operation has the same C48-observable result as the host VM.
**Translated** means the host convenience is deliberately mapped onto a
different native mechanism with the same admitted observable contract.
**Rejected** means native generation or linking fails before an output file is
published.

| C48B1 surface | Classification | Native rule |
|---|---|---|
| integer/character literals, `sizeof`, identifiers, arrays and indexing | Exact | 8/16-bit C48 widths, alignment and array stride are preserved |
| scalar assignment and integer casts | Exact | narrowing/widening follows the C48 unsigned-char and 16-bit integer model |
| integer unary `+`, `-`, `~`, `!`, prefix/postfix `++` and `--` | Exact | 16-bit wrap and 8-bit zero extension are preserved |
| integer `+`, `-`, `*`, `/`, `%`, shifts and bitwise operators | Exact | signed division/remainder and signed right shift use the pinned C48 rules |
| integer comparisons and `&&`/`||` | Exact | results are canonical 0/1 and logical operators retain short-circuit order |
| address-of, dereference, pointer indexing, pointer add/subtract/difference and relational comparison | Exact | scaling uses the pointed-to type size and 16-bit target addresses |
| function calls, recursion and scalar returns | Exact | C48_REGCALL, left-to-right argument evaluation and caller cleanup are preserved |
| Float5 literals, casts, arithmetic, comparisons, truth, prefix/postfix update and float returns | Translated | five-byte storage plus the pinned ZX-UX floating syscall ABI is used; host binary floating representation is never emitted |
| `if`, `while`, `do`, `for`, `break`, `continue`, compound and expression statements | Exact | generated branches preserve C48 evaluation order |
| scalar, array and string initializers plus zero initialization | Exact | target data bytes and BSS semantics match C48; consumed string initializers are not duplicated as anonymous data |
| block-scope `static` or `extern` declarations | Rejected | C48 Version 1 semantic analysis rejects them before native lowering |
| any C48B1 node/operator outside the admitted cases above | Rejected | lowering raises a target error rather than guessing a host behavior |

The host runtime/builtin surface is frozen separately because a matching name
alone is not evidence of matching semantics:

| Runtime/builtin surface | Classification | Native rule |
|---|---|---|
| `exit` | Translated | native process-exit syscall; successful exit is non-returning |
| `yield`, `sleep`, `getpid` | Translated | pinned cooperative process syscalls and request layouts |
| `getchar`, `putchar`, `puts` | Translated | native read/write syscalls; host presentation side effects are not target semantics |
| `strlen`, `strcmp`, `strcpy`, `strncpy` | Translated | deterministic target string helpers matching C48 return/copy rules |
| `memcpy`, `memmove`, `memchr`, `memset` | Translated | deterministic target memory helpers with the C48 byte-count contract |
| `cls`, `plot`, `ink`, `paper`, `bright`, `flash`, `inverse`, `over`, `border`, `udg_clear` | Translated | pinned graphics/UDG syscall contracts |
| `ticks` | Translated | low 16 bits of the pinned native tick service |
| `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sqrt`, `exp`, `log`, `fabs`, `pow` | Translated | pinned Float5 service operations and hidden-result convention |
| `beep`, `malloc`, `free`, `point`, `draw`, `circle`, `print_at`, `udg_define`, `udg_get`, `udg_draw`, `udg_draw_2x2` | Rejected | no admitted Phase 3 native member; unresolved use fails the link transaction |
| any other external function without a generated definition or admitted runtime member | Rejected | fixed-point runtime selection ends in an unresolved-symbol error |

## Runtime provenance and supported-symbol policy

The host linker never reads a moving native checkout. Runtime members are
constructed deterministically inside the SDK. The startup, ink, plot, and
udg_clear members are byte-exact copies of frozen OBJ1 members in the pinned
native tree. Release verification checks their complete serialized OBJ1
digests. Exit, text/string, memory, process and other admitted helpers are
target-equivalent translations of the pinned native source contracts rather
than falsely claimed byte copies.

Other accepted runtime helpers are deterministic target-equivalent
translations of the pinned libc48 assembly contract. They are used only where
the backend has an explicit lowering and tests for the same observable C48
semantics. An external symbol with neither an exact pinned member nor a proved
translation is unresolved and the output transaction fails.

The supported boundary is intentionally narrower than the host interpreter.
Five-byte floating arithmetic, casts, comparisons, truth testing, hidden
Float5 returns, and the admitted public math calls are emitted through the
pinned ZX-UX floating syscall ABI and its exact five-byte storage convention.
C48 Version 1 rejects block-scope static/extern declarations before target
lowering. Host-only display conveniences are not silently translated into
target calls.

Exact prebuilt-member provenance comes from `v1/src/libc48/crt0.asm` and
the P10/P11 object members in `v1/src/libc48/runtime_archive.asm`. Translated
integer, string, memory, graphics, process, Float5, and math helpers are tied
to the corresponding pinned libc48 sources and `v1/include/zx48ux.inc`.
`compiler/native_runtime_provenance.json` records the authority commit,
source set, exact serialized-member digests, archive order, and complete
exported-symbol map checked by release verification.
