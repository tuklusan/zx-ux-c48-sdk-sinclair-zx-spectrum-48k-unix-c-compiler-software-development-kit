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
# ZX-UX C48 SDK — Portable C compiler and runtime for Sinclair ZX Spectrum 48K development

| ![Torus Reactor wireframe torus demo screen](docs/images/demos/torus.png)<br>**Torus Reactor** | ![Sprite Storm animated sprite demo screen](docs/images/demos/sprites.png)<br>**Sprite Storm** | ![Spectrum Plasma color plasma demo screen](docs/images/demos/plasma.png)<br>**Spectrum Plasma** |
|---|---|---|
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/torus.c">torus.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/sprites.c">sprites.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/plasma.c">plasma.c</a></sub> |

[![ZX-UX C48 SDK verification status](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml/badge.svg)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml)

**ZX-UX C48 SDK** is a portable, host-side **C compiler, virtual machine and software development kit** for writing and testing C48 programs for [**ZX-UX Unix on the Sinclair ZX Spectrum 48K**](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project). It runs on Windows, Linux and macOS, on Intel and Arm hosts, providing the desktop toolchain and Spectrum-facing services needed away from the original machine. It remains separate from native ZX-UX: this SDK is not the operating system, native Z80 compiler, linker, runtime or final ABI.

## Download and install

Get the [Latest ZX-UX C48 SDK release](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/releases/latest) for the certified download package and installation instructions.

## ZX Spectrum 48K graphics showcase — 21 C48 demos

The three hero images above and 18 demos below are rendered from the C48 VM's exact ZX Spectrum 48K bitmap/attribute screen state. Automated graphics verification renders every demo independently on GitHub-hosted Windows, Linux and macOS runners.

| ![UDG Walker](docs/images/demos/spriteanim.png)<br>**UDG Walker** | ![Raycast Labyrinth](docs/images/demos/raymaze.png)<br>**Raycast Labyrinth** | ![Crystal Goblet](docs/images/demos/goblet.png)<br>**Crystal Goblet** |
|---|---|---|
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/spriteanim.c">spriteanim.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/raymaze.c">raymaze.c</a></sub> | <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/goblet.c">goblet.c</a></sub> |
| ![Infinity Tunnel](docs/images/demos/tunnel.png)<br>**Infinity Tunnel** | ![Vector Metropolis](docs/images/demos/city.png)<br>**Vector Metropolis** | ![Mountain Flight](docs/images/demos/terrain.png)<br>**Mountain Flight** |
| <sub>Windows Server 2025/x64 · <a href="usr/src/demos/tunnel.c">tunnel.c</a></sub> | <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/city.c">city.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/terrain.c">terrain.c</a></sub> |
| ![Ocean Grid](docs/images/demos/ocean.png)<br>**Ocean Grid** | ![Mobius Flight](docs/images/demos/mobius.png)<br>**Mobius Flight** | ![Polyhedron Morph](docs/images/demos/morph3d.png)<br>**Polyhedron Morph** |
| <sub>macOS 26/Arm64 · <a href="usr/src/demos/ocean.c">ocean.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/mobius.c">mobius.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/morph3d.c">morph3d.c</a></sub> |
| ![Warp Drive](docs/images/demos/warp.png)<br>**Warp Drive** | ![Spiral Galaxy](docs/images/demos/galaxy.png)<br>**Spiral Galaxy** | ![Clockwork Orrery](docs/images/demos/orrery.png)<br>**Clockwork Orrery** |
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/warp.c">warp.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/galaxy.c">galaxy.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/orrery.c">orrery.c</a></sub> |
| ![Firework Night](docs/images/demos/firework.png)<br>**Firework Night** | ![Kaleidoscope](docs/images/demos/kaleido.png)<br>**Kaleidoscope** | ![Moire Engine](docs/images/demos/moire.png)<br>**Moire Engine** |
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/firework.c">firework.c</a></sub> | <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/kaleido.c">kaleido.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/moire.c">moire.c</a></sub> |
| ![Mandelbrot Dive](docs/images/demos/mandel.png)<br>**Mandelbrot Dive** | ![Julia Ballet](docs/images/demos/julia.png)<br>**Julia Ballet** | ![Fractal Forest](docs/images/demos/forest.png)<br>**Fractal Forest** |
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/mandel.c">mandel.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/julia.c">julia.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/forest.c">forest.c</a></sub> |

A [combined contact sheet of all 21 ZX Spectrum graphics demos](docs/images/demos/contact-sheet.png) is covered by the same automated verification.

## Document Library

These documents cover portable compiler/runtime usage, technical architecture and security; the authoritative C48 language definition remains upstream in the native ZX-UX project.

<table>
  <tr>
    <td width="84" valign="top"><a href="https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx"><img src="docs/images/doc-thumbs/c48-language-specification.png" width="72" alt="C48 Language Specification cover"></a></td>
    <td valign="middle"><a href="https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx"><strong>C48 Language Specification for native ZX-UX</strong></a><br>Authoritative definition of the C language implemented by this portable SDK.</td>
  </tr>
  <tr>
    <td width="84" valign="top"><a href="docs/ZX-UX%20C48%20SDK%20User%20Manual.docx"><img src="docs/images/doc-thumbs/user-manual.png" width="72" alt="ZX-UX C48 SDK User Manual cover"></a></td>
    <td valign="middle"><a href="docs/ZX-UX%20C48%20SDK%20User%20Manual.docx"><strong>ZX-UX C48 SDK User Manual</strong></a><br>Command-line workflow and day-to-day SDK usage.</td>
  </tr>
  <tr>
    <td width="84" valign="top"><a href="docs/ZX-UX%20C48%20SDK%20Technical%20Reference.docx"><img src="docs/images/doc-thumbs/technical-reference.png" width="72" alt="ZX-UX C48 SDK Technical Reference cover"></a></td>
    <td valign="middle"><a href="docs/ZX-UX%20C48%20SDK%20Technical%20Reference.docx"><strong>ZX-UX C48 SDK Technical Reference</strong></a><br>Implementation architecture, runtime behavior, graphics, Float5, verification and host/native boundaries.</td>
  </tr>
  <tr>
    <td width="84" valign="top"><a href="docs/ZX-UX%20C48%20SDK%20Adversarial%20Security%20Review.docx"><img src="docs/images/doc-thumbs/adversarial-security-review.png" width="72" alt="ZX-UX C48 SDK Adversarial Security Review cover"></a></td>
    <td valign="middle"><a href="docs/ZX-UX%20C48%20SDK%20Adversarial%20Security%20Review.docx"><strong>ZX-UX C48 SDK Adversarial Security Review</strong></a><br>Hostile-input and memory-boundary assessment.</td>
  </tr>
</table>

The repository also keeps a stable [`C48 specification pointer`](docs/ZX-UX%20C48%20Language%20Specification.md) to the authoritative upstream document.

## C48 compiler and runtime features

The host toolchain provides the compiler, VM, Spectrum-facing runtime services and deterministic tooling summarized below.

- `c48` / `c48.bat`: command-line C48 compiler.
- `c48run` / `c48run.bat`: C48B1 host runtime and 16-bit VM.
- C48 preprocessing, lexing, parsing, semantic/type checks, diagnostics, and deterministic output.
- C48 data model with 16-bit `int`, 16-bit pointers, unsigned plain `char`, a 64 KiB logical address space, and five-byte Spectrum-style `float` storage.
- Exact 6912-byte Spectrum screen state: 6144 bitmap bytes plus 768 attribute bytes.
- 256x192 graphics, Spectrum attributes, UDGs, and a 64x24 software text display using packed 4x8 fonts.
- Interactive Tk display plus headless execution, exact `.scr` dumps, and deterministic image/test output.
- Examples, games, applications, sound demos, graphics demos, adversarial security fixtures, and the `ailmzx48` agentic language-model source/design under `usr/src/`, with frozen C48B1 counterparts under `usr/bin/` where compilation is expected.

Programs run through an SDK-specific host executable format:

```text
C48 source -> portable C48 compiler -> C48B1 -> c48run -> C48 VM
```

`C48B1` is an SDK-only host executable representation. It is not Z80 machine code, ZX-UX `OBJ1`, or ZX-UX `MEX1`.

## Games gallery — 14 C48 games

These games form a small cultural time capsule of what “computer games” meant around 1982—not replicas of any one historical library, but a compact cross-section of ideas and stories moving through mainframes, school labs, clubs and homes.

By then **Adventure** had turned caves, maps and magic words into mainframe folklore; **Hunt the Wumpus** had made pits, superbats and a monster lurking in a graph of rooms a shared BASIC-era legend; **Star Trek** had travelled through time-sharing systems, schools, magazines and books in endlessly rewritten listings; **Rogue** was carrying that tradition into Unix terminals with a different dungeon every run; and **Chess** remained computing’s classic public test of whether a machine could appear to think.

| ![C48 Adventure](docs/images/games/advent.png)<br>**Adventure** | ![C48 Arithmetic](docs/images/games/arith.png)<br>**Arithmetic** | ![C48 Backgammon](docs/images/games/bgammon.png)<br>**Backgammon** |
|---|---|---|
| <sub><a href="usr/src/games/advent.c">advent.c</a></sub> | <sub><a href="usr/src/games/arith.c">arith.c</a></sub> | <sub><a href="usr/src/games/bgammon.c">bgammon.c</a></sub> |
| ![C48 Chess](docs/images/games/chess.png)<br>**Chess** | ![C48 Cribbage](docs/images/games/cribbage.png)<br>**Cribbage** | ![C48 Go Fish](docs/images/games/fish.png)<br>**Go Fish** |
| <sub><a href="usr/src/games/chess.c">chess.c</a></sub> | <sub><a href="usr/src/games/cribbage.c">cribbage.c</a></sub> | <sub><a href="usr/src/games/fish.c">fish.c</a></sub> |
| ![C48 Fortune](docs/images/games/fortune.png)<br>**Fortune** | ![C48 Hangman](docs/images/games/hangman.png)<br>**Hangman** | ![C48 Maze](docs/images/games/maze.png)<br>**Maze** |
| <sub><a href="usr/src/games/fortune.c">fortune.c</a></sub> | <sub><a href="usr/src/games/hangman.c">hangman.c</a></sub> | <sub><a href="usr/src/games/maze.c">maze.c</a></sub> |
| ![C48 Quiz](docs/images/games/quiz.png)<br>**Quiz** | ![C48 Rogue](docs/images/games/rogue.png)<br>**Rogue** | ![C48 Snake](docs/images/games/snake.png)<br>**Snake** |
| <sub><a href="usr/src/games/quiz.c">quiz.c</a></sub> | <sub><a href="usr/src/games/rogue.c">rogue.c</a></sub> | <sub><a href="usr/src/games/snake.c">snake.c</a></sub> |
| ![C48 Star Trek](docs/images/games/trek.png)<br>**Star Trek** | ![C48 Hunt the Wumpus](docs/images/games/wump.png)<br>**Hunt the Wumpus** | |
| <sub><a href="usr/src/games/trek.c">trek.c</a></sub> | <sub><a href="usr/src/games/wump.c">wump.c</a></sub> | |

The [14-game contact sheet](docs/images/games/contact-sheet.png) assembles those certified captures in one image.

The quieter side of that culture mattered just as much. **Backgammon**, **Cribbage**, **Go Fish**, **Hangman**, **Maze**, **Quiz**, **Arithmetic**, **Fortune** and **Snake** evoke the compact programs people typed in, copied, traded, ported, altered and understood by reading the code—part game, part programming lesson, part social currency in a school lab or terminal room.

Together, the selection connects the SDK to the cultural memory and nostalgia of early personal computing, and to the imagination that greeted machines like the ZX Spectrum when it arrived in 1982.

## Relationship to native ZX-UX

[ZX-UX](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project) is the actual Unix-like operating and development environment for the original unexpanded 48K Sinclair ZX Spectrum. Its native compiler, linker, ABI, ROM bridge, persistence and process facilities are separate from this host SDK, whose role is C48 development and testing on modern computers.

The authoritative [C48 language specification](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx) lives upstream and defines the language baseline implemented here. `usr/src/c48host.h` is explicitly a **development-only Host Game API profile** and is not the final native ZX-UX `<c48.h>` ABI.

## Applications gallery — 3 C48 applications

The games above capture the exploratory, playful side of early computing; these applications tell the other half of the story—the point at which personal computers were expected to be useful. Word processing and spreadsheets symbolized the shift from hobby machine to everyday work tool, while interactive graphics turned the screen into a place to design and manipulate rather than merely print results. By the early 1990s, writing, personal finance and visual experimentation were established parts of serious home computing.

| ![WRITE48](docs/images/apps/write48.png)<br>**WRITE48 — Resume Editor** | ![SHEET48](docs/images/apps/sheet48.png)<br>**SHEET48 — Home Brokerage** | ![WIRE3D](docs/images/apps/wire3d.png)<br>**WIRE3D — Imperial Cruiser** |
|---|---|---|
| <sub><a href="usr/src/apps/write48.c">write48.c</a></sub> | <sub><a href="usr/src/apps/sheet48.c">sheet48.c</a></sub> | <sub><a href="usr/src/apps/wire3d.c">wire3d.c</a></sub> |

A [three-application contact sheet](docs/images/apps/contact-sheet.png) presents the verified screenshots together.

**WRITE48** evokes the word processors that turned a keyboard-and-screen micro into a practical writing desk; **SHEET48** recalls the spreadsheet tradition that helped establish personal computers as tools for planning, modelling and finance; and **WIRE3D** nods to the much older lineage of interactive computer graphics and CAD, compressed here into a tiny wireframe modeler. They are not replicas of particular historical products. Like the games, they are deliberately legible C48 programs: compact enough to read, but substantial enough to exercise editing, formulas, screen handling, geometry and interaction under severe constraints.

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

### Screen, input, heap and execution controls

- Tk visualizes the VM's bitmap/attribute screen state rather than maintaining a separate display model.
- **Shift+Space** is the host BREAK chord while a graphical program is running.
- The runtime heap defaults to **1024 bytes**; `--heap` accepts even values from `0` through `8192`.
- `--max-steps` and `--time-quota` bound execution when testing hostile or runaway programs.
- `--allow-approx-rom-math` selects an explicitly non-certified approximation fallback; normal execution uses the checked-in 48K-ROM-derived math path.

For BEEP details and error conventions beyond this summary, see the [ZX-UX C48 SDK Technical Reference](docs/ZX-UX%20C48%20SDK%20Technical%20Reference.docx).

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

[Supratim Sanyal / SANYALnet Labs development notes](https://supratim-sanyal.blogspot.com/)
