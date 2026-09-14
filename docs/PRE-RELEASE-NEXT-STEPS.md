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
# 1.0.0 Release Certification Record

Status: 1.0.0 RELEASE CERTIFICATION RECORD

This file records the certification gates and release evidence that must survive
ephemeral development filesystems and runner workspaces. It is intentionally
separate from the frozen language/architecture authorities.

## Evidence now required for each release candidate

1. Run `compiler/verify_release.py` on Ubuntu x64, Windows x64, macOS arm64 and
   macOS Intel with Python 3.10 and 3.13.
2. Run the ROM-derived BEEP numerical proof on the same four host families and
   both Python versions.
3. Run all 21 graphics stress jobs on their assigned runners. Preserve, from the
   runner that performed each rebuild, the `.c48b`, `.scr`, `.png` and `.json`
   evidence files.
4. Preserve the combined graphics evidence artifact containing all 21 runner
   sets, `RELEASE-EVIDENCE.json`, and `SHA256SUMS`. Before the 90-day Actions
   retention expires, attach the evidence archive to the formal GitHub release
   or another durable project-controlled release record.
5. Keep the exact candidate commit SHA with every evidence record. Do not treat
   evidence from a different commit as certification of the candidate.

## Documentation freeze for 1.0.0

Audit every non-authoritative README/Markdown/DOCX for stale host-platform claims.
In particular, replace obsolete Windows/Linux-only wording where the statement is
intended to describe the portable host SDK. Current CI verification covers Ubuntu
x64, Windows x64, macOS arm64 (`macos-latest`) and macOS Intel
(`macos-15-intel`). Do not rewrite historical or architecture-frozen statements
merely to make them sound current; distinguish normative target architecture from
host-SDK implementation documentation.

Review at least:

- `README.md` and `docs/RELEASE-NOTES.md`;
- `docs/GRAPHICS-DEMOS.md`, `docs/HOST-DIVERGENCES.md` and `docs/CONFORMANCE.md`;
- the C48 Compiler User Manual and C48 SDK User Manual DOCX files;
- installation/launcher examples, especially where POSIX shell commands are
  described as Linux-only even though they are also used on macOS;
- BEEP documentation, keeping the distinction between numerical/headless proof
  and physical audible-output testing;
- any pre-1.0 counts, hashes, screenshots, demo inventories or platform matrices
  that became stale during final hardening.


The final documentation audit distinguishes the portable host SDK from the frozen
target-native architecture. The Compiler User Manual remains intentionally
unchanged where Windows/native wording is part of that frozen portability
contract; the SDK User Manual carries the current Windows, Linux and macOS host
support and installation wording. Current release-facing counts and platform
matrices are checked against `compiler/release_expectations.json` and the
workflow files rather than copied from older review baselines.

## Final packaging gates

The release notes currently require three independent fresh-filesystem executions
of `compiler/verify_release.py` against identical frozen bytes, followed by ZIP
creation and one more verification from a virgin extraction. Preserve that gate.
After documentation is frozen, regenerate `MANIFEST.sha256`, rerun all candidate
evidence workflows, create the release archive, verify the archive extraction,
then create the formal tag/release only from the exact certified commit.

Before final tagging, require all eight rows of `.github/workflows/gui-desktop.yml`
and its aggregate evidence job to pass on the intended release commit. The gate opens
Tk windows, checks compositor pixels, host key delivery, completed close behavior, and
active BREAK status. Linux uses a fresh Xvfb X11 server because GitHub Linux runners
are headless; Windows and macOS run their native Tk windowing paths directly. Preserve
the combined screenshot/probe artifact and manifest as release evidence keyed to the
exact candidate commit. Any runtime/GUI change after that gate requires the matrix again.
