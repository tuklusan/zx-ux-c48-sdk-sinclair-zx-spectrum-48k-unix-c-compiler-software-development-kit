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
# ZX-UX C48 SDK for Windows, Linux and macOS: a portable compiler + runtime for desktop development of C programs for ZX-UX Unix for Sinclair ZX Spectrum 48K

[![C48 SDK verification](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml/badge.svg)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml)

**ZX-UX C48 SDK** is not the full [**ZX-UX Unix for the Sinclair ZX Spectrum 48K**](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project). It is a portable C compiler and just enough ZX-UX runtime to let you write and test C48 programs away from the actual ZX-UX environment on a real 48K Spectrum. The SDK runs on Windows, Linux and macOS, on Intel and Arm hosts.

| ![Torus Reactor](docs/images/demos/torus.png)<br>**Torus Reactor** | ![Sprite Storm](docs/images/demos/sprites.png)<br>**Sprite Storm** | ![Spectrum Plasma](docs/images/demos/plasma.png)<br>**Spectrum Plasma** |
|---|---|---|
| <sub>Ubuntu 24.04 · x64<br>torus.c</sub> | <sub>Windows Server 2025 · x64<br>sprites.c</sub> | <sub>macOS 26 · Arm64<br>plasma.c</sub> |

## Graphics showcase — 18 more C48 demos

These and the three hero images above are rendered from the exact 6912-byte ZX Spectrum screen state produced by the C48 VM. The automated graphics gate runs all 21 demos independently across GitHub-hosted Windows, Linux and macOS runners.

| ![UDG Walker](docs/images/demos/spriteanim.png)<br>**UDG Walker** | ![Raycast Labyrinth](docs/images/demos/raymaze.png)<br>**Raycast Labyrinth** | ![Crystal Goblet](docs/images/demos/goblet.png)<br>**Crystal Goblet** |
|---|---|---|
| <sub>Ubuntu 24.04 · x64<br>spriteanim.c</sub> | <sub>macOS 26 · Arm64<br>raymaze.c</sub> | <sub>Ubuntu 24.04 · x64<br>goblet.c</sub> |
| ![Infinity Tunnel](docs/images/demos/tunnel.png)<br>**Infinity Tunnel** | ![Vector Metropolis](docs/images/demos/city.png)<br>**Vector Metropolis** | ![Mountain Flight](docs/images/demos/terrain.png)<br>**Mountain Flight** |
| <sub>Windows Server 2025 · x64<br>tunnel.c</sub> | <sub>Ubuntu 24.04 · x64<br>city.c</sub> | <sub>Windows Server 2025 · x64<br>terrain.c</sub> |
| ![Ocean Grid](docs/images/demos/ocean.png)<br>**Ocean Grid** | ![Mobius Flight](docs/images/demos/mobius.png)<br>**Mobius Flight** | ![Polyhedron Morph](docs/images/demos/morph3d.png)<br>**Polyhedron Morph** |
| <sub>macOS 26 · Arm64<br>ocean.c</sub> | <sub>Windows Server 2025 · x64<br>mobius.c</sub> | <sub>macOS 26 · Arm64<br>morph3d.c</sub> |
| ![Warp Drive](docs/images/demos/warp.png)<br>**Warp Drive** | ![Spiral Galaxy](docs/images/demos/galaxy.png)<br>**Spiral Galaxy** | ![Clockwork Orrery](docs/images/demos/orrery.png)<br>**Clockwork Orrery** |
| <sub>Ubuntu 24.04 · x64<br>warp.c</sub> | <sub>Windows Server 2025 · x64<br>galaxy.c</sub> | <sub>macOS 26 · Arm64<br>orrery.c</sub> |
| ![Firework Night](docs/images/demos/firework.png)<br>**Firework Night** | ![Kaleidoscope](docs/images/demos/kaleido.png)<br>**Kaleidoscope** | ![Moire Engine](docs/images/demos/moire.png)<br>**Moire Engine** |
| <sub>Ubuntu 24.04 · x64<br>firework.c</sub> | <sub>Ubuntu 24.04 · x64<br>kaleido.c</sub> | <sub>Windows Server 2025 · x64<br>moire.c</sub> |
| ![Mandelbrot Dive](docs/images/demos/mandel.png)<br>**Mandelbrot Dive** | ![Julia Ballet](docs/images/demos/julia.png)<br>**Julia Ballet** | ![Fractal Forest](docs/images/demos/forest.png)<br>**Fractal Forest** |
| <sub>Ubuntu 24.04 · x64<br>mandel.c</sub> | <sub>Windows Server 2025 · x64<br>julia.c</sub> | <sub>macOS 26 · Arm64<br>forest.c</sub> |

The combined [21-demo contact sheet](docs/images/demos/contact-sheet.png) and the individual demo outputs are covered by automated verification.

## Documentation

The language authority is upstream: the [**C48 Language Specification for native ZX-UX**](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx) defines the C language implemented by this portable SDK. The SDK documentation describes the host compiler/runtime implementation and its deliberate boundaries from native ZX-UX.

- [`ZX-UX C48 SDK User Manual`](docs/ZX-UX%20C48%20SDK%20User%20Manual.docx) — command-line workflow and day-to-day SDK usage.
- [`ZX-UX C48 SDK Technical Reference`](docs/ZX-UX%20C48%20SDK%20Technical%20Reference.docx) — implementation architecture, runtime behavior, graphics, Float5, verification and host/native boundaries.
- [`ZX-UX C48 SDK Adversarial Security Review`](docs/ZX-UX%20C48%20SDK%20Adversarial%20Security%20Review.docx) — hostile-input and memory-boundary assessment.

The repository also keeps a stable [`C48 specification pointer`](docs/ZX-UX%20C48%20Language%20Specification.md) to the authoritative upstream document.

## What the SDK provides

The SDK is a portable host-side development environment for C48 programs intended for ZX-UX. It does **not** claim that its Python compiler/VM is the native ZX-UX Z80 compiler or runtime.

- `c48` / `c48.bat`: command-line C48 compiler.
- `c48run` / `c48run.bat`: C48B1 host runtime and 16-bit VM.
- C48 preprocessing, lexing, parsing, semantic/type checks, diagnostics, and deterministic output.
- C48 data model with 16-bit `int`, 16-bit pointers, unsigned plain `char`, a 64 KiB logical address space, and five-byte Spectrum-style `float` storage.
- Exact 6912-byte Spectrum screen state: 6144 bitmap bytes plus 768 attribute bytes.
- 256x192 graphics, Spectrum attributes, UDGs, and a 64x24 software text display using packed 4x8 fonts.
- Interactive Tk display plus headless execution, exact `.scr` dumps, and deterministic image/test output.
- Examples, games, applications, sound demos, graphics demos, adversarial security fixtures, and the `ailmzx48` agentic language-model source/design under `usr/src/`, with frozen C48B1 counterparts under `usr/bin/` where compilation is expected.

The portable pipeline is deliberately separate from native ZX-UX formats:

```text
C48 source -> portable C48 compiler -> C48B1 -> c48run -> C48 VM
```

`C48B1` is an SDK-only host executable representation. It is not Z80 machine code, ZX-UX `OBJ1`, or ZX-UX `MEX1`.

## Relationship to native ZX-UX

[ZX-UX](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project) is the actual Unix-like operating and development environment for the original unexpanded 48K Sinclair ZX Spectrum. This SDK exists so C48 software can be developed and tested on modern computers while native ZX-UX compiler, linker, ABI, ROM-bridge, persistence, and process facilities remain separately implemented and verified.

The authoritative C48 language specification lives upstream and is the language baseline implemented by the SDK. `usr/src/c48host.h` is explicitly a **development-only Host Game API profile** and is not the final native ZX-UX `<c48.h>` ABI.

## Runtime notes

### Fonts

The runtime defaults to the SANYALnet Labs final 4x8 font:

```text
compiler/assets/SANYALnet-Labs-4x8-font-FINAL.bin
```

Select another supplied F4X8 font with `--font`, including the ZX-UX font slot shipped with the SDK:

```bat
c48run --font compiler\assets\font4x8-zxux.bin usr\bin\examples\hello.c48b
```

```sh
./c48run --font compiler/assets/font4x8-zxux.bin usr/bin/examples/hello.c48b
```

Font selection stays explicit through the same `--font PATH` command-line contract.

### Screen, input, heap and execution controls

- The Spectrum screen is always represented by the underlying 6912-byte bitmap/attribute state; Tk is a host visualizer over that state.
- **Shift+Space** is the host BREAK chord while a graphical program is running.
- The host heap defaults to **1024 bytes**; `--heap` accepts even values from `0` through `8192`.
- `--max-steps` and `--time-quota` provide bounded host execution for testing hostile or runaway programs.
- `--allow-approx-rom-math` selects an explicitly non-certified host approximation fallback; the normal runtime uses the checked-in 48K-ROM-derived math path.

For the exact host/native boundaries, Float5 status, BEEP behavior, and error conventions, use the Technical Reference rather than treating host behavior as a promise about the future native ABI.

## Source tree

```text
c48 / c48.bat                 compiler launchers
c48run / c48run.bat           runtime launchers
compiler/                     compiler, VM, assets and verification
usr/src/ailmzx48/             agentic language-model source and design
usr/src/examples/             basic examples
usr/src/sound/                BEEP demonstration
usr/src/demos/                21 graphics demos
usr/src/games/                games
usr/src/apps/                 larger applications
usr/src/security/             adversarial fixtures
usr/bin/                      matching frozen C48B1 programs
docs/                         manuals, technical reference and images
```

Sources under `usr/src/` compile by default to the matching relative path under `usr/bin/`. Other sources compile beside the input as `.c48b` unless `-o` is supplied.

## License and author

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

This repository is distributed under the **SANYALnet Labs Non-Commercial License** in [`LICENSE`](LICENSE). Non-commercial personal, educational and hobbyist use is permitted subject to the license terms; commercial use and use for AI/ML model training are prohibited unless separately authorized.

Required attribution:

> Based on original work by Supratim Sanyal of SANYALnet Labs.

Supratim Sanyal / SANYALnet Labs development notes: <https://supratim-sanyal.blogspot.com/>
