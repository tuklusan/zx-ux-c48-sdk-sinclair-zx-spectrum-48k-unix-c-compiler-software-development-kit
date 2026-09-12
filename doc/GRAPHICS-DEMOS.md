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

The suite contains 21 independent clean-room C48 graphics and animation
programs. The former `showcase` finale was removed because the complete reel
now serves that purpose directly. Perspective-based demos use a wider camera
scale so their primary graphics occupy substantially more of the 256x192
Spectrum canvas instead of sitting in a small central patch.

Canonical screenshots are rendered from the exact 6912-byte Spectrum screen
state produced by the C48 VM. The final workflow assigns one demo to each of
21 independent GitHub-hosted jobs. Ubuntu and Windows jobs are x64; the
`macos-latest` jobs are arm64. Each job recompiles its demo, proves the binary
and canonical screen/PNG hashes, checks the actual runner architecture, runs
an extended animation pass, and uploads the freshly rebuilt C48B1 plus SCR,
PNG and JSON evidence. After all 21 jobs pass, an aggregation job downloads
every runner artifact and publishes one commit-addressed release-evidence
bundle with `SHA256SUMS` and workflow/run metadata, retained for 90 days.
The general SDK verifier separately covers both macOS arm64 (`macos-latest`)
and macOS Intel (`macos-15-intel`) at Python 3.10 and 3.13.

## Suite

1. **Crystal Goblet** (`goblet.c`) - canonical frame 2, stress 4.
2. **Infinity Tunnel** (`tunnel.c`) - canonical frame 2, stress 8.
3. **Vector Metropolis** (`city.c`) - canonical frame 2, stress 4.
4. **Mountain Flight** (`terrain.c`) - canonical frame 2, stress 4.
5. **Ocean Grid** (`ocean.c`) - canonical frame 2, stress 4.
6. **Torus Reactor** (`torus.c`) - canonical frame 2, stress 4.
7. **Mobius Flight** (`mobius.c`) - canonical frame 2, stress 4.
8. **Polyhedron Morph** (`morph3d.c`) - canonical frame 2, stress 4.
9. **Warp Drive** (`warp.c`) - canonical frame 2, stress 8.
10. **Spiral Galaxy** (`galaxy.c`) - canonical frame 2, stress 6.
11. **Clockwork Orrery** (`orrery.c`) - canonical frame 2, stress 4.
12. **Firework Night** (`firework.c`) - canonical frame 2, stress 8.
13. **Sprite Storm** (`sprites.c`) - canonical frame 2, stress 6.
14. **UDG Walker** (`spriteanim.c`) - canonical frame 12, stress 36.
15. **Spectrum Plasma** (`plasma.c`) - canonical frame 2, stress 4.
16. **Kaleidoscope** (`kaleido.c`) - canonical frame 2, stress 4.
17. **Moire Engine** (`moire.c`) - canonical frame 2, stress 4.
18. **Mandelbrot Dive** (`mandel.c`) - canonical frame 2, stress 3.
19. **Julia Ballet** (`julia.c`) - canonical frame 2, stress 3.
20. **Fractal Forest** (`forest.c`) - canonical frame 2, stress 4.
21. **Raycast Labyrinth** (`raymaze.c`) - canonical frame 2, stress 4.
