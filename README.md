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
# ZX-UX C48 SDK for Windows, Linux and macOS: Sinclair ZX Spectrum 48K C Compiler and Portable Unix-Like Development Runtime

[![C48 SDK verification](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml/badge.svg)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml)

## C48 Graphics Highlights

| Demo | Demo | Demo |
|---|---|---|
| ![UDG Walker](docs/images/demos/spriteanim.png)<br>**UDG Walker**<br>Ubuntu / x64 · `ubuntu-latest` · frame 12 | ![Torus Reactor](docs/images/demos/torus.png)<br>**Torus Reactor**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Raycast Labyrinth](docs/images/demos/raymaze.png)<br>**Raycast Labyrinth**<br>macOS / arm64 · `macos-latest` · frame 2 |

**ZX-UX C48 SDK** is a portable, Python-based **C compiler and development SDK for the original Sinclair ZX Spectrum 48K programming model**. The repository is the **1.0.0 release line**, frozen for formal release from the fully certified release commit. It provides a command-line C48 compiler, deterministic host executable format, 16-bit C48 virtual machine, authentic 256x192 ZX Spectrum bitmap/attribute display model, Tasword-style 64-column 4x8 text, graphics and UDG support, and Windows plus POSIX (Linux/macOS) launchers.

The SDK exists to make C48 programs practical to write, compile, test, and run on a modern **Windows, Linux, or macOS command line** while the native Z80 implementation of the wider **ZX-UX Unix-like operating environment for the 48K ZX Spectrum** continues to evolve.

> **Overarching ZX-UX project:** https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project
> **Supratim Sanyal / SANYALnet Labs blog:** https://supratim-sanyal.blogspot.com/

This repository is especially aimed at retrocomputing developers who want to experiment with **ZX Spectrum C programming**, **Z80-era Unix-style software**, compact 1980s games, graphics programs, utilities, and C code constrained by a deliberately tiny 48K-machine data model.

## What this repository is

This repository contains the **portable host-side C48 SDK**. It is designed for rapid development and forensic testing of C48 source on contemporary computers.

The SDK includes:

- `c48` / `c48.bat` - C48 command-line compiler front end;
- `c48run` / `c48run.bat` - portable C48 host runtime and virtual machine;
- a dedicated C48 lexer, preprocessor, recursive-descent parser, type system, semantic checker, and diagnostics layer;
- a deterministic `C48B1` host executable representation;
- a logical 64 KiB C48 address space with 16-bit pointers;
- C48 integer, pointer, array, function, storage, and evaluation semantics derived from the frozen language specification;
- Spectrum five-byte `float` storage and deterministic core arithmetic support;
- an exact 6912-byte ZX Spectrum screen model: 6144 bitmap bytes plus 768 attribute bytes;
- 256x192 ZX Spectrum graphics with native-style INK, PAPER, BRIGHT, FLASH, OVER, and INVERSE behavior;
- 64x24 text using a 4x8 packed `F4X8` font resource;
- UDG support for classic ZX Spectrum game and application graphics;
- headless execution for deterministic tests and CI-style verification;
- a Tk-based graphical display for interactive Windows, Linux, and macOS execution;
- a conformance/regression suite and deterministic demonstration programs.

This is **not** a claim that the native ZX-UX C compiler is already complete. The future target-native ZX-UX `cc` will execute as Z80 machine code and emit ZX-UX object modules. This SDK deliberately keeps its portable host executable format separate so the language and runtime semantics can be exercised now without pretending Python host execution is native Z80 execution.

## Relationship to ZX-UX

**ZX-UX** is a Unix-like operating and development environment designed specifically for the original, unexpanded **48K Sinclair ZX Spectrum**: one Z80A processor, 48 KiB RAM, Spectrum ROM services, cassette persistence, cooperative tasks, a compact Unix-style namespace, 64-column software text, an editor, assembler/linker, C48 compiler, graphics, UDGs, and small demonstration programs.

The main project lives here:

https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project

The canonical C48 language specification is maintained only in the overarching ZX-UX repository. The current upstream file is [`docs/04-C48 Language Specification Rev 0.11.docx`](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx). Its revisioned `04-C48 Language Specification Rev ...` filename may change as the specification advances. This SDK source tree deliberately does not keep a separate copy.

Release packages fetch the latest matching upstream `docs/04-C48 Language Specification Rev *.docx` at package-build time and include `C48-SPECIFICATION.json` recording the upstream commit, source path, package path, Git blob and SHA-256. The compiler architecture/user manual remains local:

- `docs/ZX-UX C48 Compiler User Manual Rev 0.11.docx`

The host SDK is intentionally useful before native Phase-11 `cc` is finished. Programs written against the frozen C48 language subset and conservative host API can therefore be developed early, while target-native compiler, linker, ROM bridge, and ABI work remain separately verifiable.

## Why a Python C48 compiler/runtime?

Python keeps the development environment simple and portable while allowing the C48 implementation to model the Spectrum rather than inherit host-C assumptions.

A normal modern C compiler would naturally prefer 32/64-bit integers and pointers, IEEE floating point, operating-system memory, and platform-specific evaluation/code-generation behavior. C48 instead models a tiny machine deliberately:

- `char` / `unsigned char`: 1 byte;
- `short` / `unsigned short`: 2 bytes;
- `int` / `unsigned int`: 2 bytes;
- pointer: 2 bytes;
- `float`: 5-byte Spectrum-style representation;
- plain `char`: unsigned;
- logical pointer space: 16-bit;
- explicit wrap, shift, division, conversion, and evaluation semantics.

That makes the Python VM a useful portability and correctness laboratory for code intended for the ZX-UX environment.

## Requirements

- **Python 3.10 or newer**;
- Windows: Command Prompt or PowerShell with `python` on `PATH`;
- Linux/macOS: a POSIX shell with `python3` on `PATH`;
- Tkinter only when using the graphical display window.

No third-party Python packages are required by the compiler or non-audio headless
runtime. Audible `beep()` playback uses the optional `playsound3==3.3.2` adapter.
The release package is one platform-neutral ZIP containing both the Windows batch
launchers and POSIX shell launchers; this SDK does not build separate native MSI,
PKG/DMG, DEB/RPM, or wheel installers.

## Continuous verification

The complete release verifier is exercised on **Ubuntu x64, Windows x64, macOS arm64,
and macOS Intel** with both the minimum supported Python 3.10 and a current Python 3.13
runtime. GitHub Actions runs the same `compiler/verify_release.py` gate used locally, plus
platform-native launcher smoke tests. The BEEP numerical proof uses the same four host
families. A separate host-native Tk acceptance matrix opens real Tk windows, verifies
compositor pixels against the rendered framebuffer, delivers keys through the host window
system, and proves completed-close versus active-BREAK exit semantics on all eight
OS/Python rows.

## Graphics Demo Reel - 21 programs, 21 runners

The three highlights above and every image below are rendered from the exact
6912-byte Spectrum screen state produced by the C48 VM. The dedicated GitHub
Actions workflow launches exactly **21 independent jobs**, one demo per
GitHub-hosted runner. Captions name the runner operating-system family and
CPU architecture as well as the workflow label and canonical frame.

| Demo | Demo | Demo |
|---|---|---|
| ![Crystal Goblet](docs/images/demos/goblet.png)<br>**Crystal Goblet**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Infinity Tunnel](docs/images/demos/tunnel.png)<br>**Infinity Tunnel**<br>Windows / x64 · `windows-latest` · frame 2 | ![Vector Metropolis](docs/images/demos/city.png)<br>**Vector Metropolis**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 |
| ![Mountain Flight](docs/images/demos/terrain.png)<br>**Mountain Flight**<br>Windows / x64 · `windows-latest` · frame 2 | ![Ocean Grid](docs/images/demos/ocean.png)<br>**Ocean Grid**<br>macOS / arm64 · `macos-latest` · frame 2 | ![Mobius Flight](docs/images/demos/mobius.png)<br>**Mobius Flight**<br>Windows / x64 · `windows-latest` · frame 2 |
| ![Polyhedron Morph](docs/images/demos/morph3d.png)<br>**Polyhedron Morph**<br>macOS / arm64 · `macos-latest` · frame 2 | ![Warp Drive](docs/images/demos/warp.png)<br>**Warp Drive**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Spiral Galaxy](docs/images/demos/galaxy.png)<br>**Spiral Galaxy**<br>Windows / x64 · `windows-latest` · frame 2 |
| ![Clockwork Orrery](docs/images/demos/orrery.png)<br>**Clockwork Orrery**<br>macOS / arm64 · `macos-latest` · frame 2 | ![Firework Night](docs/images/demos/firework.png)<br>**Firework Night**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Sprite Storm](docs/images/demos/sprites.png)<br>**Sprite Storm**<br>Windows / x64 · `windows-latest` · frame 2 |
| ![Spectrum Plasma](docs/images/demos/plasma.png)<br>**Spectrum Plasma**<br>macOS / arm64 · `macos-latest` · frame 2 | ![Kaleidoscope](docs/images/demos/kaleido.png)<br>**Kaleidoscope**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Moire Engine](docs/images/demos/moire.png)<br>**Moire Engine**<br>Windows / x64 · `windows-latest` · frame 2 |
| ![Mandelbrot Dive](docs/images/demos/mandel.png)<br>**Mandelbrot Dive**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Julia Ballet](docs/images/demos/julia.png)<br>**Julia Ballet**<br>Windows / x64 · `windows-latest` · frame 2 | ![Fractal Forest](docs/images/demos/forest.png)<br>**Fractal Forest**<br>macOS / arm64 · `macos-latest` · frame 2 |

The top three plus this gallery show all 21 current graphics demos exactly once.

The combined 21-demo contact sheet is preserved at [`docs/images/demos/contact-sheet.png`](docs/images/demos/contact-sheet.png) and is covered by `MANIFEST.sha256`.

Each graphics runner preserves its freshly rebuilt `.c48b`, canonical `.scr`, rendered
`.png`, and machine-readable `.json` evidence. A final aggregation job collects all 21
runner artifacts, writes `SHA256SUMS` plus release metadata, and retains the combined
pre-release evidence artifact for 90 days.

The human-facing graphics, conformance, host-divergence, application, game, and release material is consolidated in `docs/ZX-UX C48 SDK Technical Reference.docx`. The detailed host-native Tk release gate and its bounded screenshot/probe evidence contract live with the verification tooling in `compiler/GUI-SMOKE-TESTS.md`.

## Clone and quick start

```text
git clone https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit.git
cd zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit
```

### Windows Command Prompt

```bat
c48 --version
c48 --about
c48 usr\src\examples\hello.c
c48run --headless usr\bin\examples\hello.c48b --dump-screen usr\bin\examples\hello.scr
c48run usr\bin\examples\hello.c48b
```

### Linux / macOS (POSIX)

```sh
./c48 --version
./c48 --about
./c48 usr/src/examples/hello.c
./c48run --headless usr/bin/examples/hello.c48b --dump-screen usr/bin/examples/hello.scr
./c48run usr/bin/examples/hello.c48b
```

Sources under `usr/src/` compile by default to the corresponding relative path under `usr/bin/`. Sources elsewhere compile beside the source with the `.c48b` suffix unless `-o` is supplied.

## ZX Spectrum 4x8 fonts and `--font`

The runtime ships with two independent `F4X8` font asset names under `compiler/assets/`:

```text
compiler/assets/font4x8-tasword.bin   # default
compiler/assets/font4x8-zxux.bin      # alternate slot
```

`font4x8-tasword.bin` is the default runtime font. It is the packed 392-byte `F4X8` resource mechanically derived from the supplied Tasword Two 4x8 character generator.

Select another valid `F4X8` font at runtime with `--font PATH`:

```bat
c48run --font compiler\assets\font4x8-zxux.bin usr\bin\examples\hello.c48b
```

```sh
./c48run --font compiler/assets/font4x8-zxux.bin usr/bin/examples/hello.c48b
```

Any replacement font must satisfy the SDK's frozen `F4X8` format: 392 bytes total, `F4X8` magic, version 1, first character `0x20`, 96 glyphs, and four packed bytes per 4x8 glyph.

**Current repository note:** the two bundled font assets presently have identical bytes and the same SHA-256. They are intentionally retained under separate names so the ZX-UX font can diverge later without changing the CLI or runtime architecture.

The complete Tasword Two program archive is **not redistributed** by this repository. The retained raw character-generator extraction and its SHA-256/provenance record are sufficient to verify the mechanical packing of the default runtime font.

## C48 compiler pipeline

The portable compiler follows a small auditable pipeline:

```text
C48 source
   |
   v
preprocessor -> lexer -> recursive-descent parser -> semantic/type checks
   |
   v
deterministic C48B1 host executable
   |
   v
c48run -> 64K C48 VM -> ZX Spectrum screen/runtime services
```

The compiler does not transpile to ordinary host C. That avoids accidentally replacing C48 behavior with GCC, Clang, MSVC, CPython integer, or native pointer semantics.

## C48B1 host executable format

`C48B1` is a deterministic SDK-only host representation. It consists of canonical ASCII JSON protected by a SHA-256 integrity field and a strict schema validator.

It is deliberately **not**:

- ZX-UX `OBJ1`;
- ZX-UX `MEX1`;
- Z80 machine code;
- a replacement for the future native C48 backend.

Deterministic serialization allows the test suite to prove that the same C48 source produces byte-identical host binaries across clean rebuilds.

## ZX Spectrum screen and graphics model

The runtime keeps the real ZX Spectrum display organization rather than a generic terminal framebuffer.
