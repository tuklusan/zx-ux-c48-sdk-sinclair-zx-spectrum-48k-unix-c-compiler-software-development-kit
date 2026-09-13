#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
A = ROOT / "usr" / "src" / "ailmzx48"
REF = A / "tooling" / "a48m_reference.py"
SRC = A / "ailmzx48.c"
MATCH = A / "aimatch.h"
CORPUS = A / "training" / "seed_corpus.json"
TEST = A / "evaluation" / "test_a48m_reference.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


def patch_reference() -> None:
    text = REF.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    topic_map = {name: index for index, name in enumerate(topics)}\n'
        '    vocab_id = identity(model["vocab"])\n',
        '    topic_map = {name: index for index, name in enumerate(topics)}\n'
        '    vocab_map = {\n'
        '        word: index for index, word in enumerate(model["vocab"])\n'
        '    }\n'
        '    vocab_id = identity(model["vocab"])\n',
        "reference vocab map",
    )
    text = replace_once(
        text,
        '        records.append(\n'
        '            encode_record(\n'
        '                record_type,\n'
        '                topic_map[topic],\n'
        '                item["text"],\n'
        '                200,\n'
        '            )\n'
        '        )\n',
        '        trigger_words = item.get("triggers", [])\n'
        '        if len(trigger_words) > 4:\n'
        '            raise A48MError("seed fact has too many triggers")\n'
        '        trigger_ids = []\n'
        '        for word in trigger_words:\n'
        '            if word not in vocab_map or vocab_map[word] == 0:\n'
        '                raise A48MError("seed trigger missing from vocab: " + word)\n'
        '            trigger_ids.append(vocab_map[word])\n'
        '        records.append(\n'
        '            encode_record(\n'
        '                record_type,\n'
        '                topic_map[topic],\n'
        '                item["text"],\n'
        '                200,\n'
        '                tuple(trigger_ids),\n'
        '            )\n'
        '        )\n',
        "reference trigger encoding",
    )
    REF.write_text(text, encoding="utf-8")


def patch_match_header() -> None:
    text = '''// ============================================================\n// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n// Proprietary rights reserved except as licensed in LICENSE.\n//\n// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.\n// Non-commercial use permitted; Commercial Use and AI/ML\n// model training prohibited unless separately authorized.\n//\n// Attribution required: Based on original work by Supratim\n// Sanyal of SANYALnet Labs. See root LICENSE for full terms.\n// ============================================================\nint ai_readfull(unsigned char *p, unsigned int n)\n{
    unsigned int done;\n    unsigned int ask;\n    int got;\n    done = 0;\n    while (done < n) {\n        ask = n - done;\n        if (ask > 64) ask = 64;\n        got = ai_mread(&p[done], ask);\n        ai_mreads = ai_mreads + 1;\n        if (got <= 0) return -1;\n        if ((unsigned int)got > ask) return -1;\n        done = done + (unsigned int)got;\n        ai_mbytes = ai_mbytes + (unsigned int)got;\n    }\n    return 0;\n}\n\nint ai_wordchar(int c)\n{
    c = ai_lower(c);\n    if (c >= 'a' && c <= 'z') return 1;\n    if (c >= '0' && c <= '9') return 1;\n    return 0;\n}\n\nint ai_vhas(unsigned int id)\n{
    unsigned int i;\n    unsigned int j;\n    unsigned int off;\n    unsigned int len;\n    int ok;\n    if (id == 0 || id >= ai_vcnt) return 0;\n    off = ai_voff[id];\n    len = ai_vlen[id];\n    if (len == 0) return 0;\n    i = 0;\n    while (ai_in[i] != 0) {\n        if (i != 0 && ai_wordchar(ai_in[i - 1])) {\n            i = i + 1;\n            continue;\n        }\n        j = 0;\n        ok = 1;\n        while (j < len) {\n            if (ai_in[i + j] == 0) {\n                ok = 0;\n                break;\n            }\n            if (ai_lower(ai_in[i + j]) != ai_vblob[off + j]) {\n                ok = 0;\n                break;\n            }\n            j = j + 1;\n        }\n        if (ok && !ai_wordchar(ai_in[i + len])) return 1;\n        i = i + 1;\n    }\n    return 0;\n}\n'''
    bad = [
        (n, len(line), line)
        for n, line in enumerate(text.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise RuntimeError("aimatch.h exceeds 64 columns: " + repr(bad))
    MATCH.write_text(text, encoding="utf-8")


def patch_source() -> None:
    text = SRC.read_text(encoding="utf-8")
    old_read = '''int ai_readfull(unsigned char *p, unsigned int n)\n{
    unsigned int done;\n    unsigned int ask;\n    int got;\n    done = 0;\n    while (done < n) {\n        ask = n - done;\n        if (ask > 64) ask = 64;\n        got = ai_mread(&p[done], ask);\n        ai_mreads = ai_mreads + 1;\n        if (got <= 0) return -1;\n        if ((unsigned int)got > ask) return -1;\n        done = done + (unsigned int)got;\n        ai_mbytes = ai_mbytes + (unsigned int)got;\n    }\n    return 0;\n}\n\n'''
    text = replace_once(
        text,
        old_read + "int ai_modelscan(unsigned int topic)\n{\n",
        '#include "aimatch.h"\n\nint ai_modelscan(unsigned int topic)\n{\n',
        "target trigger helper include",
    )
    text = replace_once(
        text,
        "    unsigned int tid;\n    unsigned int calc;\n",
        "    unsigned int tid;\n    unsigned int thits;\n"
        "    unsigned int calc;\n",
        "target trigger counter declaration",
    )
    old = '''        i = 0;\n        while (i < tcnt) {\n            tid = ai_getu16(ai_mstage, 10 + (i * 2));\n            if (tid > 4095) return -1;\n            i = i + 1;\n        }\n'''
    new = '''        thits = 0;\n        i = 0;\n        while (i < tcnt) {\n            tid = ai_getu16(ai_mstage, 10 + (i * 2));\n            if (tid > 4095) return -1;\n            if (ai_vhas(tid)) thits = thits + 1;\n            i = i + 1;\n        }\n'''
    text = replace_once(text, old, new, "target trigger matching")
    text = replace_once(
        text,
        "        score = -1;\n"
        "        if (rtopic == topic) score = ai_mstage[8];\n",
        "        score = -1;\n"
        "        if (rtopic == topic) {\n"
        "            score = (int)ai_mstage[8];\n"
        "            score = score + (int)(thits * 16);\n"
        "        }\n",
        "target trigger scoring",
    )
    bad = [
        (n, len(line), line)
        for n, line in enumerate(text.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise RuntimeError("C48 source exceeds 64 columns: " + repr(bad[:4]))
    if len(text.encode("utf-8")) > 32768:
        raise RuntimeError("C48 source object still exceeds 32768 bytes")
    SRC.write_text(text, encoding="utf-8")


def patch_corpus() -> None:
    doc = json.loads(CORPUS.read_text(encoding="utf-8"))
    trigger_map = {
        "display is 256 by 192": ["display", "256", "192", "colour"],
        "rubber keyboard and cassette": ["rubber", "keyboard"],
        "sinclair basic is stored": ["rom", "16k"],
        "followed the zx81": ["zx81"],
        "screen area occupies 6912": ["6912", "bytes", "display"],
        "display bitmap uses 6144": ["bitmap", "6144", "bytes"],
        "manic miner is a platform": ["manic", "miner"],
        "jet set willy followed": ["jet", "willy"],
        "knight lore is known": ["knight", "lore"],
        "offline chat avoids": ["network", "service"],
    }
    found = set()
    for item in doc["records"]:
        if item.get("kind") != "fact-user":
            continue
        value = item["text"]
        for needle, triggers in trigger_map.items():
            if needle in value:
                item["triggers"] = triggers
                found.add(needle)
                break
    missing = set(trigger_map) - found
    if missing:
        raise RuntimeError("missing trigger facts: " + repr(sorted(missing)))
    CORPUS.write_text(
        json.dumps(doc, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    assert all(record["anchors"] for record in parsed["records"])\n',
        '    assert all(record["anchors"] for record in parsed["records"])\n'
        '    assert any(record["triggers"] for record in parsed["records"])\n'
        '    assert any(len(record["triggers"]) >= 2 for record in parsed["records"])\n',
        "A48M trigger test",
    )
    TEST.write_text(text, encoding="utf-8")


def main() -> int:
    patch_reference()
    patch_match_header()
    patch_source()
    patch_corpus()
    patch_test()
    print("trigger-aware A48M migration applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
