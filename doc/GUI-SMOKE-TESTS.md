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
# 1.0.0 Interactive Tk GUI Smoke-Test Template

Status: **PENDING REAL-DESKTOP EXECUTION**

This record is intentionally separate from headless CI. A successful compiler,
BEEP-numerical, or graphics-rendering workflow does not prove that Tk can open,
paint, accept keyboard input, and close correctly on a physical desktop session.
The formal 1.0.0 release remains blocked until every row below is recorded PASS in
durable external evidence for the exact certified release ZIP bytes.

## Required matrix

| Host | Python | Result | Tester / date | Notes |
| --- | --- | --- | --- | --- |
| Ubuntu x64 | 3.10 | PENDING | - | - |
| Ubuntu x64 | 3.13 | PENDING | - | - |
| Windows x64 | 3.10 | PENDING | - | - |
| Windows x64 | 3.13 | PENDING | - | - |
| macOS arm64 | 3.10 | PENDING | - | - |
| macOS arm64 | 3.13 | PENDING | - | - |
| macOS Intel | 3.10 | PENDING | - | - |
| macOS Intel | 3.13 | PENDING | - | - |

## Test procedure for every row

Use a fresh extraction of the exact candidate release ZIP. Record the archive
SHA-256, candidate commit SHA, host OS/version, CPU architecture, Python
version, and Tk version with the row result.

1. Run `compiler/verify_release.py` from the extracted package and require PASS.
2. Run the platform launcher `--version` command and require `1.0.0`.
3. Launch `usr/bin/demos/forest.c48b` without `--headless`. Require a real Tk
   window showing the Spectrum frame with no clipping, blank canvas, traceback,
   or missing footer. After the program finishes, require the footer text
   `Program ended - Shift+Space to close`; press Shift+Space and require a clean
   close with the completed program status preserved.
4. Launch `usr/bin/games/fortune.c48b` without `--headless`. Require ordinary
   keyboard input to advance the program, then use `q` to exit normally. This
   proves that the desktop event loop is delivering VM input rather than merely
   rendering a static frame.
5. Launch `usr/bin/games/snake.c48b`, wait until it is accepting input, then use
   Shift+Space while the VM is still active. Require the GUI session to abort
   cleanly with host status 130 and no traceback.
6. Record PASS only if all five checks succeed in the same fresh extraction.

Windows uses `c48.bat` / `c48run.bat`; Ubuntu and macOS use `./c48` /
`./c48run`. POSIX launcher wording applies equally to Linux and macOS.

## Evidence rule

A screenshot may accompany a row, but a screenshot alone is not a PASS because
it cannot prove keyboard delivery, BREAK handling, exit status, or clean close.
Copy this matrix into the durable release evidence and complete that external copy.
Record the exact candidate SHA and release-ZIP SHA-256 with it. Do not edit this
tracked template after the physical tests: changing the repository would create a
different candidate from the bytes that were actually tested. Keep the completed
matrix (and any supporting screenshots/logs) with the formal release evidence.
