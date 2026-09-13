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

p = Path(__file__).with_name("upgrade_session_refs.py")
t = p.read_text(encoding="utf-8")
needle = "    text = once(\n        text,\n        '        \"semantic_retrieval_uses\": semuse_total,\\n'\n"
start = t.find(needle)
if start < 0:
    raise RuntimeError("runner field-patch start not found")
end = t.find('    RUN.write_text(text, encoding="utf-8")\n', start)
if end < 0:
    raise RuntimeError("runner field-patch end not found")
new = '''    field_old = (\n        '        "semantic_retrieval_uses": semuse_total,\\n'\n        '        "max_l0bytes": max_l0bytes,\\n'\n    )\n    field_new = (\n        '        "semantic_retrieval_uses": semuse_total,\\n'\n        '        "literal_reference_losses": litloss_total,\\n'\n        '        "max_l0bytes": max_l0bytes,\\n'\n    )\n    if text.count(field_old) != 2:\n        raise RuntimeError("runner literal-loss fields changed")\n    text = text.replace(field_old, field_new, 2)\n'''
t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
