<!--
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
-->
# C48 Applications

The SDK ships three interactive C48 applications under `usr/bin/apps`, with
sources under `usr/src/apps`. Each program opens with editable sample content
so a first run is useful without setup.

## sheet48

`sheet48` is a compact 1982-style spreadsheet. The initial worksheet is a
fictional 1992 home brokerage allocation using period-appropriate ticker
symbols. Dollar values and percentages are sample data, not historical market
prices or investment advice. The worksheet demonstrates labels, numeric cells,
cell references, arithmetic formulas and a `SUM` range.

Keys: `5/8` left/right, `7/6` up/down, `E` edit, `Q` quit.

## write48

`write48` is a small word processor with insertion, deletion, word-aware screen
wrapping, movement, scrolling and find. It redraws only changed character cells,
so cursor motion does not clear and reconstruct the whole screen. It opens an original 1992-dated resume
for Sir Clive Sinclair. The prose is newly written from historical facts known
by 1992; it is not copied from a historical resume.

Command keys: `I` insert, `5/8` or `H/L` move, `7/6` page, `X` delete,
`F` find, `G` top, `Q` quit. In insert mode, `Esc` returns to command mode.

## wire3d

`wire3d` is an original cross-section wireframe model editor inspired by the
class of 1982 Spectrum 3D design tools. Its startup model, the Imperial
Battleship Aurelian, is original SDK geometry and is not copied from a film,
game, Psion example, or external model. Startup uses a large low-angle cruiser
above a perspective arena grid for an immediate 1982 wireframe presentation.

Keys: `N/P` select plane, `A/D` width, `W/S` height, `Z/X` depth, `5/8` yaw,
`7/6` pitch, `+/-` zoom, `R` reset, `Q` quit.
