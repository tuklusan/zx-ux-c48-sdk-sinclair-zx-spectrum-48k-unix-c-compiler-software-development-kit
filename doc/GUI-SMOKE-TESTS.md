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
# 1.0.0 Host-Native Tk GUI Acceptance Gate

Status: **AUTOMATED HOST-NATIVE RELEASE GATE**

The original manual-only physical-desktop matrix was retained until the GUI
behaviors it protected could be measured objectively. The release gate is now
implemented by `compiler/verify_gui_desktop.py` and
`.github/workflows/gui-desktop.yml`. This is not a relaxation of the gate: each
row must still open a real Tk top-level window, paint through the host windowing
system, accept keys delivered through the host input system, distinguish
completed close from an active BREAK, and return the required process status.
In addition, compositor screenshots are checked against the exact RGB frame Tk
reported as rendered. Linux and Windows require byte-exact RGB equality. Aqua
accepts a one-to-one color bijection, or tightly bounded spatial dithering only
when every captured pixel remains uniquely classified as the exact Spectrum
palette color expected at that same position. Both paths preserve every pixel
position while accounting for host compositor color management.

Linux executes the native Tk/X11 path under a fresh Xvfb server because GitHub's
Linux runners are headless. Windows and macOS execute their native Tk windowing
paths directly on the hosted runner desktop. A subjective manual desktop check
remains useful as an optional spot-check, but it is no longer the formal release
blocker once all eight automated rows and the aggregate evidence job pass.

## Required matrix

| Host runner | Python | Required result |
| --- | --- | --- |
| Ubuntu x64 (`ubuntu-latest`) | 3.10 | PASS |
| Ubuntu x64 (`ubuntu-latest`) | 3.13 | PASS |
| Windows x64 (`windows-latest`) | 3.10 | PASS |
| Windows x64 (`windows-latest`) | 3.13 | PASS |
| macOS arm64 (`macos-latest`) | 3.10 | PASS |
| macOS arm64 (`macos-latest`) | 3.13 | PASS |
| macOS Intel (`macos-15-intel`) | 3.10 | PASS |
| macOS Intel (`macos-15-intel`) | 3.13 | PASS |

## Objective checks for every row

1. Run `compiler/verify_release.py` first and require PASS on the exact checked-out
   candidate commit.
2. Run the platform `c48run --version` launcher and require `c48run 1.0.0`.
3. Launch `usr/bin/demos/forest.c48b` without `--headless`; require the Tk window,
   a fully mapped Spectrum canvas at the largest host-safe integer scale
   (normally 3x/960x720; constrained desktops may use 2x/640x480), never
   Tk's clipped pre-map/default geometry,
   successful program completion, the exact footer text
   `Program ended - Shift+Space to close`, a compositor screenshot whose canvas
   pixels equal the Tk-rendered framebuffer, and Shift+Space close preserving
   process status 0.
4. Launch `usr/bin/games/fortune.c48b` without `--headless`; require its prompt
   framebuffer to be rendered before `getchar()` begins waiting, inject an
   ordinary key through the host window system and observe the VM accepting it,
   then inject `q`, require normal completion, and close the completed window.
5. Launch `usr/bin/games/snake.c48b`; wait until the VM is accepting input, inject
   Shift+Space through the host window system, require the GUI to classify it as
   an active BREAK and return host status 130 with no traceback.
6. Require `GUI-EVIDENCE.json`, the three probe logs, three exact Tk-rendered
   frame PPMs, six compositor PNG captures, and `SHA256SUMS` for that row. The
   aggregate job must find exactly eight reports
   and publish one combined evidence manifest keyed to the candidate commit.

## Screenshot and evidence layout

Each job writes a bounded, replace-in-place row directory:

```text
screenshots/gui-desktop/<runner>/python-<version>/
```

The path is stable for a runner/Python pair; it does not include timestamps or
run numbers, so local evidence file count does not grow on repeated execution.
GitHub artifacts include the candidate commit in the artifact name and expire
after 90 days. See `screenshots/gui-desktop/README.md`.

## Release rule

An immutable release tag (including a release-candidate tag) may be created only
after all eight jobs and
the aggregate GUI-evidence job pass on the intended release commit, with the
ordinary release verifier also green. Any runtime or GUI change after that gate
requires the matrix to run again. Evidence-only artifact retention does not
change the certified source tree.
