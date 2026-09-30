# ZX-UX C48 SDK — Portable C compiler and runtime for Sinclair ZX Spectrum 48K development

| ![Torus Reactor wireframe torus demo screen](docs/images/demos/torus.png)<br>**Torus Reactor** | ![Sprite Storm animated sprite demo screen](docs/images/demos/sprites.png)<br>**Sprite Storm** | ![Spectrum Plasma color plasma demo screen](docs/images/demos/plasma.png)<br>**Spectrum Plasma** |
|---|---|---|
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/torus.c">torus.c</a></sub> | <sub>Windows Server 2025/x64 · <a href="usr/src/demos/sprites.c">sprites.c</a></sub> | <sub>macOS 26/Arm64 · <a href="usr/src/demos/plasma.c">plasma.c</a></sub> |

[![ZX-UX C48 SDK verification status](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml/badge.svg)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml)

**ZX-UX C48 SDK** is a portable, host-side **C compiler, virtual machine and software development kit** for writing and testing C48 programs for [**ZX-UX Unix on the Sinclair ZX Spectrum 48K**](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project). It runs on Windows, Linux and macOS, on Intel and Arm hosts, providing the desktop toolchain and Spectrum-facing services needed away from the original machine. This saves the 48K Spectrum from having to impersonate a modern workstation (a role for which it was never interviewed). The SDK remains separate from native ZX-UX: it is not the operating system, native Z80 compiler, linker, runtime or final ABI.

## Download and install

Get the [Latest ZX-UX C48 SDK release](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/releases/latest) for the certified download package and installation instructions.

## ZX Spectrum 48K graphics showcase — 24 C48 demos

The three hero images above and 21 demos below are rendered from the C48 VM's exact ZX Spectrum 48K bitmap/attribute screen state—a remarkably small place in which to keep this much visual ambition. The 22 frame-driven graphics demos are certified across Windows, Linux and macOS runners; Towers of Hanoi and 8-Queens use the separate recursive-demo gate on Linux and Windows because they run to a proved final state rather than a fixed frame count.

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
| ![Dizzy 4K C48 port hero phase](docs/images/demos/dizzy4k.png)<br>**Dizzy 4K (C48 Port)** | ![Towers of Hanoi](docs/images/demos/hanoi.png)<br>**Towers of Hanoi** | ![8-Queens Recursive Search](docs/images/demos/queens8.png)<br>**8-Queens Recursive Search** |
| <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/dizzy4k.c">dizzy4k.c</a></sub> | <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/hanoi.c">hanoi.c</a></sub> | <sub>Ubuntu 24.04/x64 · <a href="usr/src/demos/queens8.c">queens8.c</a></sub> |

A [combined contact sheet of the 22 frame-driven ZX Spectrum graphics demos](docs/images/demos/contact-sheet.png) is covered by the graphics reel. Towers of Hanoi and 8-Queens are shown separately in the matrix above and are covered by recursive-demo verification.

## Document Library

These documents cover portable compiler/runtime usage, technical architecture and security, because even a 48K universe eventually develops paperwork.

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

`C48B1` is an SDK-only host executable representation. It is not Z80 machine code, ZX-UX `OBJ1`, or ZX-UX `MEX1`—a distinction of the sort that seems pedantic right up until the moment it saves an afternoon.

## Games gallery — 14 C48 games

These games form a small cultural time capsule of what “computer games” meant around 1982—not replicas of any one historical library, but a compact cross-section of ideas and stories moving through mainframes, school labs, clubs and homes. It is nostalgia with source code attached, which is generally the more useful kind.

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

[ZX-UX](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project) is the actual Unix-like operating and development environment for the original unexpanded 48K Sinclair ZX Spectrum. Its native compiler, linker, ABI, ROM bridge, persistence and process facilities are separate from this host SDK, whose role is C48 development and testing on modern computers. The distinction is deliberate; the machine is already constrained enough without making the terminology do two jobs as well.

The authoritative [C48 language specification](https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project/blob/main/docs/04-C48%20Language%20Specification%20Rev%200.11.docx) lives upstream and defines the language baseline implemented here. `usr/src/c48host.h` is explicitly a **development-only Host Game API profile** and is not the final native ZX-UX `<c48.h>` ABI.

## Native ZX-UX source tapes

The distribution includes **57 native ZX-UX source tapes** beside the
matching frozen programs under `usr/bin/`. Each `*.src.tap` image
carries the C48 program source plus the local header it needs, so the
same source corpus can be moved from a modern SDK host onto a real
ZX-UX system.

The tapes use ZX-UX **M48O version 1** RAW objects with the symbolic
**USERHOME** target. C files are stored as object type **C (5)**;
headers are stored as **TXT (1)**. Payload and header CRCs are
generated and verified by `c48srctap`. The tool accepts only
lowercase `.c`, `.h`, and `.txt` inputs and refuses a mixed or
unsupported command line before creating output.

A typical native workflow is:

```text
attach or position the .src.tap cassette at its start
load exapi.h
load hello.c
cc hello.c
link the emitted OBJ1 with ld
run the resulting MEX1 program
```

The tape order is deliberate: the required local header is first and
the C source follows it. `load` installs the objects into the current
user's home directory through USERHOME mapping. The native
compiler-resident `<c48.h>` remains part of ZX-UX itself and is not
duplicated on these tapes.

The complete locked mapping is recorded in
[`compiler/source_tape_manifest.json`](compiler/source_tape_manifest.json).
The generator is available as `c48srctap` / `c48srctap.bat`; run
`c48srctap --help` for syntax and examples.

## Native executable tape cross-development

`c48b2tap` converts one validated SDK `.c48b` program into target-native
ZX-UX artifacts without pretending that C48B1 itself is machine code. C48B1 is
the deterministic host representation used by the SDK. `c48b2tap` lowers that
representation to relocatable Z80 `OBJ1`, links `MEX1` through the pinned
ZX-UX startup/runtime contract, and can wrap the complete MEX1 as a native
M48O version-1 RAW `BIN` object in a standard Spectrum `.tap` stream.

Typical commands are:

```text
c48b2tap --obj program.c48b program.obj
c48b2tap --mex program.c48b program.mex
c48b2tap --name PROGRAM program.c48b program.tap
```

TAP object names are portable ZX-UX names of 1–10 bytes. `--stack BYTES`
sets the requested FAST stack within the native 64–4096 byte range. Generated
executables must satisfy both native ceilings independently: image plus BSS
must fit within 32,768 bytes, and the complete stored MEX1 including relocation
records must also fit within 32,768 bytes. The release proof includes a
deterministic generated source in the 29–31 KiB band whose final stored MEX1 is
also in that band, demonstrating useful host cross-development without changing
any native ZX-UX memory limit.

OBJ1, MEX1 and TAP output is deterministic for identical input, options and
tool version. Output is written transactionally and is published only after
generation and validation succeed; unsupported native operations, unresolved
symbols, format overflow, invalid paths or invalid object names fail without
leaving a partial replacement.

The native executable backend and `c48run --multitask` share C48 semantic
fixtures where their contracts overlap, but they solve different problems:
`c48run --multitask` is a cooperative host execution model, while
`c48b2tap` creates target-native single-process executable artifacts. This
release does not claim a native concurrent-execution proof.

## Applications gallery — 4 C48 applications

The applications corpus spans writing, spreadsheets, interactive
geometry, and data visualization. **GP82** brings the collection back to
the Spectrum's launch year with a compact dashboard built from real 1982
Grand Prix season figures.

| ![WRITE48](docs/images/apps/write48.png)<br>**WRITE48 — Resume Editor** | ![SHEET48](docs/images/apps/sheet48.png)<br>**SHEET48 — Home Brokerage** |
|---|---|
| <sub><a href="usr/src/apps/write48.c">write48.c</a></sub> | <sub><a href="usr/src/apps/sheet48.c">sheet48.c</a></sub> |
| ![WIRE3D](docs/images/apps/wire3d.png)<br>**WIRE3D — Imperial Cruiser** | ![GP82](docs/images/apps/gp82.png)<br>**GP82 — Grand Prix 1982** |
| <sub><a href="usr/src/apps/wire3d.c">wire3d.c</a></sub> | <sub><a href="usr/src/apps/gp82.c">gp82.c</a></sub> |

The [four-application contact sheet](docs/images/apps/contact-sheet.png)
assembles the verified startup screens.

**GP82** plots grouped wins, podiums, and poles for Ferrari, McLaren,
Renault, and Williams on the left, with the 16 race wins divided among
seven constructors in a pie chart on the right. Ferrari's 74-point
constructors' title is called out beneath the chart. The values are based
on the published 1982 season results and constructor statistics.

**WRITE48**, **SHEET48**, and **WIRE3D** retain the practical and visual
side of the corpus: text editing, formulas and tabular work, and compact
wireframe geometry. All four are deliberately readable C48 programs that
exercise substantial screen handling and interaction under tight limits.

## Runtime notes

### Cooperative multitasking

`c48run --multitask` runs one through six C48B1 programs in one host session:

```text
c48run --multitask PROGRAM1.c48b PROGRAM2.c48b [PROGRAM3.c48b ...]
```

The session mirrors the native eight-slot identity shape without pretending to be a booted ZX-UX kernel: PID0 is synthetic idle state, PID1 is a synthetic session supervisor, and directly listed programs receive PID2 through PID7 in command-line order. Every positional token in multitask mode is a program path, and each process receives only that exact token as `argv[0]`. Native `spawn`, `wait`, and `kill` remain deliberately unsupported in this host mode.

Scheduling is cooperative round-robin. A process hands control back only at `yield()`, positive `sleep()`, blocking `getchar()`, termination, cancellation, or a configured session safety ceiling. `sleep(0)` returns without yielding. A CPU-bound process that never reaches one of those boundaries can starve its peers until a safety ceiling intervenes; that is a property of cooperative scheduling, not a surprise bonus feature.

Each process has private C48 memory, globals, locals, call/continuation frames, heap, argument storage, and status. The Spectrum screen, border, sound service, tick source, and keyboard are session devices shared in scheduler order. A waiting GUI input owner blocks only that process; unrelated runnable processes continue. Headless multitask execution never performs a blocking stdin read: an unprovided `getchar()` fails that process explicitly.

`--heap` is applied separately to every process. `--max-steps` and `--time-quota` are session-wide ceilings. A process runtime failure ends that process with status 1 while peers continue; after all processes end, the command returns zero only if all direct processes returned zero, otherwise it returns the first nonzero status in PID order. Shift+Space during a graphical session is a global BREAK and returns 130; after final completion it only closes the retained display. The completed-program footer is shown only after every direct process has terminated.

The acceptance proof runs the frozen `usr/bin/demos/hanoi.c48b` and `usr/bin/demos/queens8.c48b` together to their verified final states on one shared screen. A separate repeated synthetic tick/input regression requires identical status, scheduler trace, and final screen bytes from identical sessions. This is host-side evidence aligned to the pinned native process semantics; it is not a claim that the host VM is the native ZX-UX scheduler.

### Fonts

The runtime defaults to the SANYALnet Labs final 4x8 font, where every pixel has a job and none has time for decorative flourishes:

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
- **Host `Esc` maps to ZX `CAPS+1` (console byte `7`).** In **WRITE48**, while editing text, press `Esc` to leave INSERT mode and return to CMD mode; from there `I` re-enters insert mode, `5`/`8` move, `7`/`6` page, `X` deletes, `F` finds, `G` jumps to top, and `Q` quits.
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
usr/src/demos/                24 demos (22 frame-driven + 2 recursive)
usr/src/games/                games
usr/src/apps/                 4 larger applications
usr/src/security/             adversarial fixtures
usr/bin/                      matching frozen C48B1 programs
docs/                         manuals, technical reference and images
```

Sources under `usr/src/` compile by default to the matching relative path under `usr/bin/`. Other sources compile beside the input as `.c48b` unless `-o` is supplied.

## License and author

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

This repository is distributed under the **SANYALnet Labs Non-Commercial License** in [`LICENSE`](LICENSE). Non-commercial personal, educational and hobbyist use is permitted subject to the license terms; commercial use and use for machine-learning model training are prohibited unless separately authorized.

Required attribution:

> Based on original work by Supratim Sanyal of SANYALnet Labs.

[Supratim Sanyal / SANYALnet Labs development notes](https://supratim-sanyal.blogspot.com/)
