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

C48 / ZX-UX Tasword Two 4x8 Font Extraction

Source provenance:
  original archive contained TASWORD2.TAP
  TASWORD2.TAP SHA-256: e9c7159c2319ef1c31059879635f37d99e681567e3731b2d9042ca88df9dcec0

The complete Tasword Two program archive is intentionally NOT redistributed in this
repository.  It is unnecessary at runtime and is not required to verify the packed
font.  The retained raw 768-byte character-generator extraction plus the mechanical
packing check in compiler/verify_release.py are sufficient for reproducibility.

Tasword Two CODE block:
  load address : 54784 (0xD600)
  length       : 10751 bytes

Character generator:
  start address: 61184 (0xEF00)
  offset in CODE block: 6400 (0x1900)
  length       : 768 bytes
  glyphs       : 96
  codes        : 0x20..0x7F
  layout       : 8 bytes/glyph, one 4-bit scan row per byte in low nibble

Extracted raw font:
  file         : compiler/tasword2-font4x8-raw-768.bin
  size         : 768
  SHA-256      : 0ccd55f30450231b4219f15c945af53a3eb418082a28b5062589723d8fa1834d

Canonical packed F4X8 Tasword resource:
  file         : compiler/assets/font4x8-tasword.bin
  size         : 392
  SHA-256      : 90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339
  header       : "F4X8", version 1, first code 0x20, 96 glyphs, flags 0
  glyph data   : 384 bytes; 4 bytes/glyph
  packing      : high nibble = earlier scan row; low nibble = following scan row

Glyph 0x7F preview:
.##.
#...
#.##
#.#.
#.##
#...
#..#
.##.

Runtime-selectable F4X8 assets:
  compiler/assets/SANYALnet-Labs-4x8-font-FINAL.bin  default runtime font
    SHA-256: dceb0a9c2cac3fa15e66759f55b12633d9338df0a7961e4372406e21da9c7942
  compiler/assets/font4x8-tasword.bin                 selectable Tasword font
    SHA-256: 90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339
  compiler/assets/font4x8-zxux.bin                    alternate selectable font slot
    SHA-256: 90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339

Select a font explicitly with:
  c48run --font PATH program.c48b

All three supplied runtime assets are valid 392-byte F4X8 resources.  The Tasword and
ZX-UX selectable slots are byte-identical in this repository revision.  The default
FINAL font is a distinct resource and is frozen independently by the release gate.
The three names are retained independently so any slot can change later without
changing the c48run command-line contract.
