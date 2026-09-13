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
from pathlib import Path

p = Path(__file__).with_name("upgrade_context_wire.py")
t = p.read_text(encoding="utf-8")
old = "                if (ai_lower(s[start + j]) != ai_vblob[off + j]) {\n"
new = (
    "                if (ai_lower(s[start + j]) !=\n"
    "                    ai_vblob[off + j]) {\n"
)
if t.count(old) != 1:
    raise RuntimeError("wire long-line repair anchor mismatch")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
