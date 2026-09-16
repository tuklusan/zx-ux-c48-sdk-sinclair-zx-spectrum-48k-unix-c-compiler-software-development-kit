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

## C48 Graphics Highlights

| Demo | Demo | Demo |
|---|---|---|
| ![UDG Walker](docs/images/demos/spriteanim.png)<br>**UDG Walker**<br>Ubuntu / x64 · `ubuntu-latest` · frame 12 | ![Torus Reactor](docs/images/demos/torus.png)<br>**Torus Reactor**<br>Ubuntu / x64 · `ubuntu-latest` · frame 2 | ![Raycast Labyrinth](docs/images/demos/raymaze.png)<br>**Raycast Labyrinth**<br>macOS / arm64 · `macos-latest` · frame 2 |

**ZX-UX C48 SDK** is not the full ZX-UX Unix Operating System for the ZX Spectrum 48K. It is a portable C Compiler and just enough ZX-UX runtime that lets you write and test C48 C language programs without working in the actual ZX-UX unix environment on a real ZX Spectrum 48K. The SDK runs on Windows, Linux and MacOS, intel and arm.

The SDK is a Python-based **C compiler and development SDK for the original Sinclair ZX Spectrum 48K programming model**. The repository is the **1.0.0 release line**, frozen for formal release from the fully certified release commit. It provides a command-line C48 compiler, deterministic host executable format, 16-bit C48 virtual machine, authentic 256x192 ZX Spectrum bitmap/attribute display model, Tasword-style 64-column 4x8 text, graphics and UDG support, and Windows plus POSIX (Linux/macOS) launchers. It defaults to a custom SANYALnet Labs 4x8 font, but a command-line parameter lets you choose the ZX-UX native font. See compiler/assets. 

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

The combined 21-demo contact sheet is preserved at [`docs/images/demos/contact-sheet.png`](docs/images/demos/contact-sheet.png) and is covered by the release package's generated `MANIFEST.sha256`.

Each graphics runner preserves its freshly rebuilt `.c48b`, canonical `.scr`, rendered
`.png`, and machine-readable `.json` evidence. A final aggregation job collects all 21
runner artifacts, writes `SHA256SUMS` plus release metadata, and retains the combined
pre-release evidence artifact for 90 days.

Human-facing graphics, conformance, host-divergence, application, game, Float5, and release material is consolidated in `docs/ZX-UX C48 SDK Technical Reference.docx`. The detailed host-native Tk release gate and its bounded screenshot/probe evidence contract live with the verification tooling in `compiler/GUI-SMOKE-TESTS.md`.

## Download, clone, and quick start

### Download the packaged SDK ZIP

If you want to use the SDK without Git, the packaged release ZIP is the simplest route. It is one platform-neutral archive containing both the Windows batch launchers and the POSIX shell launchers.

- **[Latest published release or release candidate](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/releases)** - this page is always current, with the newest published release at the top. Download the asset whose name starts with `zx-ux-c48-sdk-` and ends in `.zip`.
- **[Direct download: current certified 1.0.0-RC5 ZIP](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/releases/download/1.0.0-RC5/zx-ux-c48-sdk-1.0.0-RC5-41d130e489638dd07ba3305eea41517e0ec3b32f.zip)** - one-click download of the current certified package.

GitHub's `/releases/latest` shortcut deliberately excludes prereleases, so the Releases page above is the durable link to the newest available package while release candidates are active.

After downloading, extract the ZIP to a directory of your choice and run the commands below from the extracted SDK directory.

### Clone with Git

If you prefer to track the repository directly:

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

The runtime keeps the real ZX Spectrum display organization rather than a generic terminal framebuffer:

```text
6144 bytes  bitmap
 768 bytes  attributes
--------------------
6912 bytes  total ZX screen state
```

The graphical API models Spectrum coordinates and attribute constraints. The 4x8 text renderer provides a dense 64-column-by-24-row software console while still writing into the native Spectrum bitmap organization.

Headless mode can dump the exact 6912-byte screen for deterministic tests:

```sh
./c48run --headless --dump-screen output.scr usr/bin/examples/graphics.c48b
```

The Tk frontend is only a visualizer over that underlying ZX-compatible screen state; it is not the source of truth.

For Spectrum-style interactive control, **Shift+Space acts as BREAK**. While the program runs, the Tk footer shows `Shift+Space = BREAK`. After a program has returned and `c48run` is simply holding its final frame, the footer changes to `Program ended - Shift+Space to close`; pressing the chord closes the window while preserving the completed program status. If the VM is still running, Shift+Space aborts the host GUI session with status 130. The footer is host-window chrome and is never written into the emulated 6912-byte Spectrum screen.

## Host game API

`usr/src/c48host.h` is the **Host Game API profile** used for practical development before the final native `<c48.h>` prototype surface is frozen by ZX-UX Phase 11.

It exposes useful host-side calls for text, graphics, UDGs, memory/string operations, and related experiments. The file is intentionally labeled as a host profile and must not be mistaken for the final native ZX-UX ABI.

For this development-only host profile, integer-returning service calls use `0` for success and a nonzero status for failure. Screen, graphics, and UDG argument validation commonly returns `1`; `beep()` additionally uses host-side values `1` for invalid arguments, `5` for playback or I/O failure, and `14` when no audible host backend is available. These values describe the SDK host runtime only. They do not freeze or claim the final native ZX-UX P11.41 `<c48.h>` ABI or its error convention.

See `docs/ZX-UX C48 SDK Technical Reference.docx` for the host/native divergence and conformance boundaries.

### Sinclair-compatible BEEP

The host profile now exposes the architecture-frozen function:

```c
int beep(float duration, float pitch);
```

Its argument order follows Sinclair BASIC. The VM derives pitch and duration from
the frozen 48K ROM `BEEP`/`BEEPER` routines, generates the corresponding square-wave
WAV, and blocks C48 execution until playback returns. Literal tones are generated
when the C48B1 AST is loaded; dynamically computed tones are generated on first use
and cached.

On Windows, audible playback uses Python's standard-library `winsound` module
and needs no extra package. On Linux and macOS, install the optional playback
adapter for audible host playback:

```sh
python -m pip install playsound3==3.3.2
```

Then build and run the shipped fractional-pitch demonstration:

```sh
./c48 usr/src/sound/tune.c
./c48run usr/bin/sound/tune.c48b
```

Windows uses the corresponding `c48.bat` / `c48run.bat` launchers and needs no
third-party audio package. The compiler and non-audio programs do not require
`playsound3` on any host. If audible playback is unavailable, the runtime emits one
clear warning and `beep()` returns `ZX_E_NOTSUP` (14) rather than reporting fake
success. The shipped `tune` demo reports that condition on-screen, continues in
silent mode, and exits successfully.

The cross-platform BEEP matrix proves the generated waveform numerically: the logs
show the requested pitch, ROM frequency, `HL`, cycle count, physical BEEPER
frequency, measured WAV frequency, modeled duration, WAV duration and blocking wall
time. It deliberately does not claim that a headless CI runner's speaker was heard.

## Heap compatibility

The runtime defaults to the normal native-C48 `crt0` heap ceiling of **1024 bytes**.

For host development:

```sh
./c48run --heap 2048 usr/bin/examples/hello.c48b
```

`--heap` accepts even values from `0` through `8192`. The host allocator enforces the selected byte ceiling but does not claim byte-identical native allocator metadata or native process-stack placement.

For hostile-input testing and CI, `c48run` also provides a deterministic VM execution budget:

```sh
./c48run --max-steps 10000 usr/bin/program.c48b
```

`--max-steps 0` (the default) leaves normal interactive execution unlimited. A positive value terminates execution with a controlled runtime error when the VM reaches the requested evaluation/statement-step budget. The host VM separately caps C48 function-call depth so recursive programs cannot fall through to Python's recursion limit.

## Spectrum five-byte Float5 status

The SDK implements five-byte storage, parsing, integer conversion, comparison, and deterministic core arithmetic without allowing IEEE host values to become persistent C48 stored state.

The normal runtime uses the checked-in 48K-ROM-derived implementation for the transcendental family, with Float5 quantization at each C48 operation boundary. Full byte-for-byte differential certification of every ROM/native/host transcendental boundary is **not** claimed. An explicitly non-certified Python host-math approximation remains available only as a development fallback:

```sh
./c48run --allow-approx-rom-math usr/bin/program.c48b
```

See `docs/ZX-UX C48 SDK Technical Reference.docx` for the exact Float5 certification boundary.

## Included C48 examples

Shipped C48 programs are categorized beneath `usr/src/`, with matching frozen
`C48B1` files beneath the same relative category in `usr/bin/`:

- `usr/src/examples/` - `hello`, `colors`, `graphics`, `udg`, `maze`, and `argv`;
- `usr/src/sound/` - `tune`, the synchronous ROM-derived `beep()` demonstration;
- `usr/src/demos/` - the 21 animated graphics demonstrations;
- `usr/src/games/` - the shipped game corpus;
- `usr/src/apps/` - the larger application corpus;
- `usr/src/security/` - adversarial compiler/runtime fixtures.

Only the shared development header `usr/src/c48host.h` remains directly at the
source root; `usr/bin/` contains no uncategorized binaries. The release verifier
enforces that layout mechanically.

All shipped C48 `.c` and `.h` files under `usr/src/` obey a **64-character physical-line ceiling**, matching the ZX-UX tty64 presentation model rather than modern 80-column source formatting. The release verifier enforces this mechanically.

## Adversarial security fixtures

The 1.0.0 tree includes C48 programs written specifically to attack the host compiler/runtime safety envelope. Their source is under `usr/src/security/`, and runnable C48B1 forms are under `usr/bin/security/` where compilation is expected to succeed.

- `secguard.c` - successful dashboard for recoverable heap, screen-coordinate, UDG, and compiler-forgery protections;
- `secoob.c` - one-past pointer write;
- `secuaf.c` - use-after-free dereference;
- `secfree.c` - interior-pointer `free`;
- `secdbl.c` - double free;
- `secforge.c` - raw pointer-byte forgery without provenance;
- `secloop.c` - infinite loop stopped by `--max-steps`;
- `secrecur.c` - unbounded C48 recursion stopped by the VM call-depth guard;
- `seckern.c` - compile-negative attempt to manufacture a pointer to reserved address `0x5B00`; C48 must reject the arbitrary integer-to-pointer cast, so this fixture intentionally has no C48B1 binary.

The runnable fixtures place explicit `ATTEMPT:` and `MITIGATION:` text on the emulated 64-column Spectrum screen before the security boundary is exercised. Fatal tests are expected to terminate with controlled C48 runtime errors rather than continue after an invalid operation.

For example:

```bat
c48 usr\src\security\secguard.c
c48run usr\bin\security\secguard.c48b

c48run --max-steps 300 usr\bin\security\secloop.c48b
```

The hostile-input regression suite additionally attacks recursive parser structures, macro-expansion bombs, oversized source/C48B1 inputs, malformed-but-correctly-checksummed C48B1 schemas, stale-pointer address reuse, and raw pointer representation forgery. See `docs/ZX-UX C48 SDK Adversarial Security Review.docx` for the threat model and findings.

## Verification and zero-gap release discipline

Run the full automated test corpus:

```bat
python -B compiler\run_tests.py
```

```sh
python3 -B compiler/run_tests.py
```

Run the complete release verifier:

```bat
python -B compiler\verify_release.py
```

```sh
python3 -B compiler/verify_release.py
```

The release verifier checks, among other things:

- Python source parseability against the supported Python baseline;
- the repository-wide license-header policy;
- the legacy SDK tree-path invariant across repository text and DOCX OOXML;
- exact font resource structure and hashes;
- the 64-column physical-line contract for shipped C48 source;
- launcher behavior;
- version/about attribution output;
- source-tree/package manifest policy and packaged manifest integrity;
- the full compiler/runtime conformance, regression, and adversarial-security suite;
- deterministic reconstruction of every security-fixture binary;
- deterministic reconstruction of every frozen demo binary;
- exact 6912-byte Spectrum screen hashes for the demos;
- absence of transient cache/test debris.

The standalone header gate can also be run directly:

```sh
python3 -B compiler/check_license_headers.py
```

Artifacts that would be corrupted by an in-band text header are explicitly classified as exemptions by that gate: JSON, binary font resources, `C48B1`, DOCX, ZIP/TAP containers, the machine-readable version/hash files, and the root `LICENSE` itself.

## Repository layout

```text
zx-ux-c48-sdk/
|-- c48 / c48.bat
|-- c48run / c48run.bat
|-- compiler/
|   |-- c48.py
|   |-- c48run.py
|   |-- c48/                 compiler + VM implementation
|   |-- assets/              selectable F4X8 fonts
|   `-- tests/               conformance/regression corpus
|-- usr/
|   |-- src/                 editable C48 programs
|   `-- bin/                 deterministic C48B1 binaries
|-- docs/                     human manuals, technical reference, images, protected reference material
|-- LICENSE
`-- VERSION
```

## Project status and portability boundary

This SDK is intended to be conservative about what it claims.

Host execution proves the C48 language/VM behavior covered by the test and release-verification envelope. It does not by itself prove Z80 code-generation correctness, native `C48_REGCALL`, ZX-UX linker behavior, ROM-call register contracts, cassette persistence, native multiprocessing, or final `<c48.h>` prototypes. Those belong to the overarching ZX-UX target implementation and its own phase-by-phase verification process.

That separation is intentional: **portable C48 development now, native ZX Spectrum ZX-UX implementation without invented equivalence later.**

## Retrocomputing goals

The practical goal is simple: make it pleasant to write small programs that feel at home on a 1982 Sinclair machine while retaining enough Unix-like structure to build interesting software.

Good candidates include:

- classic terminal and maze games;
- compact adventure/game engines;
- Conway-style cellular automata;
- text utilities and filters;
- tiny editors and data tools;
- 256x192 graphics demonstrations;
- UDG sprite experiments;
- ports or reinterpretations of early Unix-era recreational programs within the C48 subset.

The constraints are part of the fun: 16-bit pointers, tiny heap, 4x8 text, attribute color, 48K-era screen memory, and a deliberately modest C language.

## Documentation

Start with:

- [`docs/04-C48 Language Specification Rev 0.11.docx`](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx) in the upstream ZX-UX repository - normative language baseline; the revisioned filename may change, and release packages carry the latest matching upstream version;
- `docs/ZX-UX C48 Compiler User Manual Rev 0.11.docx` - frozen/native compiler architecture and user manual;
- `docs/ZX-UX C48 SDK User Manual.docx` - portable Windows, Linux and macOS host-SDK installation and workflow manual;
- `docs/ZX-UX C48 SDK Technical Reference.docx` - applications, games, graphics, host divergences, Float5 boundary, conformance scope, and release notes;
- `compiler/GUI-SMOKE-TESTS.md` - host-native Tk acceptance gate for maintainers;
- `compiler/LICENSE-HEADER-POLICY.md` - source/header policy and gate behavior;
- `docs/ZX-UX C48 SDK Adversarial Security Review.docx` - hostile-input and memory-boundary security assessment.

## License

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

This repository is distributed under the **SANYALnet Labs Non-Commercial License** in [`LICENSE`](LICENSE). Non-commercial personal, educational, and hobbyist use is permitted subject to the license terms; commercial use and use for AI/ML model training are prohibited unless separately authorized.

Required attribution:

> Based on original work by Supratim Sanyal of SANYALnet Labs.

## Author, ZX-UX project, and development notes

**Supratim Sanyal / SANYALnet Labs**
Blog and software-development notes: https://supratim-sanyal.blogspot.com/

Main ZX-UX repository:
https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project

C48 portable SDK repository:
https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit

### Search/project taxonomy

Sinclair ZX Spectrum 48K, ZX Spectrum C compiler, ZX Spectrum C programming, Z80 C compiler, Z80 development SDK, retrocomputing, 1982 home computer programming, ZX-UX, Unix-like ZX Spectrum operating system, C48 language, Python C compiler, Windows ZX Spectrum development, Linux ZX Spectrum development, macOS ZX Spectrum development, 256x192 Spectrum graphics, UDG graphics, Tasword 64-column font, 4x8 Spectrum font, five-byte Spectrum floating point, classic Unix games, retro C development.
