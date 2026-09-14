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
# Host-native GUI screenshots

`compiler/verify_gui_desktop.py` writes compositor screenshots and generated
probe/checksum evidence under a stable working path:

```text
screenshots/gui-desktop/<runner>/python-<version>/
```

The checked-in PNG files are retained as human-facing screenshots. They are not
the release gate's machine evidence and do not need to match the most recent CI
run. Generated `GUI-EVIDENCE.json`, `SHA256SUMS`, probe `*.jsonl` files and Tk
frame `*.ppm` files are deliberately not retained in the source repository.

The host-native GUI workflow creates fresh evidence for all eight runner/Python
rows, uploads each row as a GitHub Actions artifact, then uploads a combined
release-evidence artifact with the aggregate manifest. Those artifacts are
bounded by the workflow retention period rather than committed back to `main`.

Release packaging requires a successful host-native GUI workflow for the exact
candidate commit. This prevents stale checked-in evidence from being reused and
keeps generated execution material out of the source tree.

The full-desktop PNGs produced by the verifier are actual host screenshot
captures. Their canvas regions are cropped using Tk-reported screen geometry and
compared, after nearest-neighbor normalization, with the RGB framebuffer that Tk
reported as painted. Linux and Windows require byte-for-byte RGB identity. Aqua
first accepts the same strict one-to-one color bijection. If the host compositor
spatially dithers color-managed pixels, every captured pixel must instead remain
uniquely classified as the exact Spectrum palette color expected at that same
position and stay inside half the minimum palette separation. This preserves
spatial identity while rejecting clipping, shifts, normal/bright swaps, or
cross-palette corruption.
