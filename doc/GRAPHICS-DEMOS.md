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
# C48 Graphics Demo Reel

The suite contains 22 clean-room C48 graphics and animation programs.
Canonical screenshots are rendered from the exact 6912-byte Spectrum
screen state produced by the C48 VM. The final workflow assigns exactly
one demo to each of 22 independent GitHub-hosted jobs: eight Ubuntu,
seven Windows, and seven macOS. Each job recompiles its demo, proves the
binary and canonical screen/PNG hashes, runs an extended animation pass,
and uploads SCR, PNG, and JSON evidence with measured stress duration.

## Suite

1. **Crystal Goblet** (`goblet.c`) - canonical frame 2, stress 4, `ubuntu-latest`.
2. **Infinity Tunnel** (`tunnel.c`) - canonical frame 2, stress 8, `windows-latest`.
3. **Vector Metropolis** (`city.c`) - canonical frame 2, stress 4, `ubuntu-latest`.
4. **Mountain Flight** (`terrain.c`) - canonical frame 2, stress 4, `windows-latest`.
5. **Ocean Grid** (`ocean.c`) - canonical frame 2, stress 4, `macos-latest`.
6. **Torus Reactor** (`torus.c`) - canonical frame 2, stress 4, `ubuntu-latest`.
7. **Mobius Flight** (`mobius.c`) - canonical frame 2, stress 4, `windows-latest`.
8. **Polyhedron Morph** (`morph3d.c`) - canonical frame 2, stress 4, `macos-latest`.
9. **Warp Drive** (`warp.c`) - canonical frame 2, stress 8, `ubuntu-latest`.
10. **Spiral Galaxy** (`galaxy.c`) - canonical frame 2, stress 6, `windows-latest`.
11. **Clockwork Orrery** (`orrery.c`) - canonical frame 2, stress 4, `macos-latest`.
12. **Firework Night** (`firework.c`) - canonical frame 2, stress 8, `ubuntu-latest`.
13. **Sprite Storm** (`sprites.c`) - canonical frame 2, stress 6, `windows-latest`.
14. **Spectrum Plasma** (`plasma.c`) - canonical frame 2, stress 4, `macos-latest`.
15. **Kaleidoscope** (`kaleido.c`) - canonical frame 2, stress 4, `ubuntu-latest`.
16. **Moire Engine** (`moire.c`) - canonical frame 2, stress 4, `windows-latest`.
17. **Mandelbrot Dive** (`mandel.c`) - canonical frame 2, stress 3, `ubuntu-latest`.
18. **Julia Ballet** (`julia.c`) - canonical frame 2, stress 3, `windows-latest`.
19. **Fractal Forest** (`forest.c`) - canonical frame 2, stress 4, `macos-latest`.
20. **Raycast Labyrinth** (`raymaze.c`) - canonical frame 2, stress 4, `macos-latest`.
21. **C48 Grand Finale** (`showcase.c`) - canonical frame 2, stress 8, `macos-latest`.

22. **UDG Walker** (`spriteanim.c`) - canonical frame 12, stress 36, `ubuntu-latest`.
