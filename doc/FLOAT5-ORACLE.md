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
# Float5 Oracle Boundary - Pre-1.0 SDK

## Normative requirement

C48 uses the Sinclair ZX Spectrum five-byte numeric representation. The
language specification's Section 94 requires a golden corpus to be compared
against the canonical Spectrum ROM conversion path, the native
compiler/runtime, and the Windows host implementation. A host implementation
may not certify itself solely against IEEE floating point.

## What the pre-1.0 SDK implements and tests

`compiler/c48/float5.py` stores every C48 float as exactly five bytes. Parsing
from decimal text uses `Decimal`/`Fraction` only as exact host-side construction
tools; stored C48 state is always quantized to the five-byte representation.
Core `+`, `-`, `*`, and `/` use exact rational intermediates and quantize after
each C48 operation.

`compiler/c48/rommath.py` imports the native 48K ROM calculator algorithms at
source level from the checked-in `Spectrum48.asm` disassembly. It implements
`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sqrt`, `exp`, `log`, and `pow`
using the ROM's compressed constants, argument reduction, calculator operation
order, zero-power rules, and Chebyshev series. Every arithmetic operation in
that path is quantized through `Float5`.

The normal `c48run` host runtime now selects that ROM-derived path for the
transcendental runtime family. `c48run --allow-approx-rom-math` remains available only as an
explicit development fallback; it selects Python host math followed by Float5
requantization and is not an oracle path.

The SDK tests exact five-byte reference points for the ROM-derived functions,
including zero/one cases, pi-derived inverse-trig values, square root,
zero-power behavior, and domain/range failures. `fabs` remains exact
sign/magnitude handling and does not require transcendental math.

## Certification boundary that remains open

This change removes the old host-runtime blocker that disabled transcendental
functions by default. It does **not** claim that all Float5 arithmetic and
conversion boundaries have now been exhaustively compared byte-for-byte
against an independently executing 48K ROM.

It also does not close the language specification's full Section-94 three-way
ROM/native/host certification, because the future native compiler/runtime side
is still outside this pre-1.0 SDK's certified envelope. See `CONFORMANCE.md`.

## ROM reference source

The source-level import is tied to
`doc/reference/rom-disassemblies/spectrum-48k/Spectrum48.asm`. In particular,
the implementation follows the ROM calculator's `series-xx`, `exp`, `ln`,
`get-argt`, `sin`, `cos`, `tan`, `atn`, `asn`, `acs`, `sqr`, and `to-power`
routines rather than substituting host libm formulas.

## Release claim

The pre-1.0 SDK may therefore claim a default ROM-derived host implementation
for the C48 transcendental runtime family. It may not claim complete
Section-94 three-way ROM/native/host differential certification until that
separate native and independent-oracle work is complete.
