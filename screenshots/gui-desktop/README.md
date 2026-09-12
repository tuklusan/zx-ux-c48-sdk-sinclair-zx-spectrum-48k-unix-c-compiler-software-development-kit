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
# Host-native GUI screenshot evidence

`compiler/verify_gui_desktop.py` writes compositor screenshots and machine-readable
probe evidence under a stable row path:

```text
screenshots/gui-desktop/<runner>/python-<version>/
```

Each row contains a fixed set of `forest`, `fortune`, and `snake` desktop/canvas
PNGs, the exact Tk-rendered frame PPMs, probe logs, `GUI-EVIDENCE.json`, and
`SHA256SUMS`. The verifier clears
the target row before writing, so reruns replace that row instead of accumulating
files. GitHub Actions uploads each row and a combined release-evidence artifact
with 90-day retention. Generated row directories are intentionally ignored by
Git; the workflow and reports carry the candidate commit SHA.

The full-desktop PNGs are actual host screenshot captures. Their canvas regions
are cropped using Tk-reported screen geometry and compared, after nearest-neighbor
normalization, with the RGB framebuffer that Tk reported as painted. Linux and
Windows require byte-for-byte RGB identity. Aqua additionally permits only a
strict one-to-one color bijection that preserves every pixel position, accounting
for compositor color management without masking clipping or spatial differences.
This makes the screenshots executable release evidence rather than decorative
images.
