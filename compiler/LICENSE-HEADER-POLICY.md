<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
-->

# License Header Policy

`compiler/check_license_headers.py` is the fail-closed repository gate for
source-level license headings. It is part of `compiler/verify_release.py`.
The tracked license-header gate is separate from the project-wide ephemeral
content/path policy gate used during repository writes and full-tree review.

## Canonical header

Every governed file carries exactly these two logical lines:

```text
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
```

A file format may add only its required comment delimiters. POSIX launchers
keep the shebang as physical line 1 and place the canonical header immediately
after it. Windows batch launchers keep `@echo off` as physical line 1 and
place the canonical header immediately after it.

Governed C and header files use the repository's 64-column-safe physical
wrapping. The checker reconstructs the same two logical lines from that
wrapper; the words, order, and punctuation do not change. The UTF-8 copyright
glyph is permitted only by the proved leading-comment exception in governed
C48 C/H sources.

## Header-bearing artifacts

The gate requires the canonical header at the beginning of every
project-owned, header-safe tracked file, immediately after a required launcher
preamble when one exists. Header-safe classes currently include Python,
project-owned C/C48 source and headers, Markdown, ordinary text, tracked
runbooks, YAML (including GitHub Actions workflows), Windows batch files,
the POSIX launchers, `.gitignore`, and `.gitattributes`.

Unknown artifact classes fail closed. Adding a new suffix or special path
therefore requires an explicit classification rather than inheriting an
accidental exemption.

## Root-file exemptions

The root `README.md` and root `LICENSE` are intentionally exempt from
source-header enforcement only. The README stays headerless, and the LICENSE
is the license text itself. Both remain subject to all other repository
content, security, and release checks.

## Immutable pinned C/H corpus

The pre-existing C/H files under `usr/src/demos/`, `usr/src/examples/`,
and `usr/src/apps/` are externally pinned by the native ZX-UX project. Their
exact path set is enumerated in `check_license_headers.py` and is exempt from
header normalization. This exemption is deliberately path-specific: a newly
added unrelated C/H file in those directories is not silently exempted.

Those pinned files must remain byte-identical to
`BASELINE-BEFORE-MULTITASKING-AND-BIN-TAPE-TOOL`; their exemption does not
permit edits for formatting, line endings, comments, or any other reason.

## Microsoft Office exemptions

Microsoft Office and related container formats are exempt from in-band source
headers because prepending text would corrupt the container. The checker
classifies the following suffixes explicitly:

```text
.accdb .doc .docm .docx .dot .dotm .dotx .mdb .mpp .mpt .msg
.one .onetoc2 .ost .pot .potm .potx .pps .ppsm .ppsx .ppt .pptm
.pptx .pst .pub .vsd .vsdm .vsdx .vst .vstm .vstx .xlam .xls
.xlsb .xlsm .xlsx .xlt .xltm .xltx
```

This is a license-header exemption only. Office/container contents remain in
scope for the project-wide content/security and release reviews.

## Other format-preserving exemptions

The following machine, binary, or container classes are deliberately exempt
because an inserted source header would corrupt their syntax or bytes:

- `VERSION`, `MANIFEST.sha256`, and `C48-SPECIFICATION.json`;
- strict `*.json`;
- `*.bin`, `*.dat`, and `*.rom` binary payloads;
- `*.png` images;
- `*.c48b` canonical C48B1 executables;
- `*.tap` tape images;
- `*.zip` archives and release containers.

Two exemptions are path-scoped rather than suffix-wide:

- `docs/reference/` contains imported reference material preserved under its
  own provenance/licensing and is not modified merely to normalize headers;
- generated files under `screenshots/gui-desktop/` may include
  `SHA256SUMS`, `*.json`, `*.jsonl`, `*.png`, and `*.ppm`.
  These generated-evidence forms are retained exactly as generated.
  In particular, `.jsonl` and `.ppm` are not globally exempt elsewhere.

Imported-reference and generated-evidence header exemptions do not override
any higher project-wide content/security requirement. If such a requirement
rejects an imported artifact, the upstream bytes are not edited in place.

## C48 source-tape exception

`c48srctap` preserves its ASCII payload rule except for the exact canonical
UTF-8 leading header. For C/H sources, the exception is accepted only when a
syntax-aware scan proves the non-ASCII bytes are inside the canonical leading
comment header. Governed plain `.txt` may contain the same exact canonical
leading text header. Malformed UTF-8 and any other non-ASCII occurrence remain
rejected. The locked 57-tape corpus is independently round-tripped by the
source-tape tests.

## Attribution scope

The root `LICENSE` requires attribution in source-level documentation. It
does not require the attribution text to be printed in graphical, terminal,
or command-line user interfaces. `c48` and `c48run` retain `--about` as
compact copyright/license information commands, but the header gate does not
require the source/document attribution sentence in that output.

Run the gate directly with:

```sh
python3 -B compiler/check_license_headers.py --root .
```

or run the complete SDK release verifier:

```sh
python3 -B compiler/verify_release.py
```
