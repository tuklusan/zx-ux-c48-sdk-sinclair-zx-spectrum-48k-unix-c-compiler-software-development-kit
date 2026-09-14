#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
"""One-shot repair for quota state used during VM construction."""
from pathlib import Path

TARGET = Path("compiler/c48run.py")
SELF = Path(".github/c48-runtime-constructor-fix.py")

OLD = '''    def __init__(self, *args, time_quota: float = 0.0, **kwargs):\n        super().__init__(*args, **kwargs)\n        self._time_quota = float(time_quota)\n        self._time_deadline = (\n            time.monotonic() + self._time_quota\n            if self._time_quota > 0.0\n            else None\n        )\n'''
NEW = '''    def __init__(self, *args, time_quota: float = 0.0, **kwargs):\n        # VM construction evaluates global initializers, which can call _tick().\n        # Establish quota state before the base constructor starts that work.\n        self._time_quota = float(time_quota)\n        self._time_deadline = (\n            time.monotonic() + self._time_quota\n            if self._time_quota > 0.0\n            else None\n        )\n        super().__init__(*args, **kwargs)\n'''

text = TARGET.read_text(encoding="utf-8")
count = text.count(OLD)
if count != 1:
    raise SystemExit(
        f"runtime constructor repair: expected one match, found {count}"
    )
with TARGET.open("w", encoding="utf-8", newline="\n") as handle:
    handle.write(text.replace(OLD, NEW, 1))
SELF.unlink()
print("runtime constructor repair: quota state now precedes VM initialization", flush=True)
