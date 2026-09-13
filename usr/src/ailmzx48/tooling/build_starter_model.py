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

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_VOCAB = 96
REQ = ("i", "spectrum", "memory")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def toks(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def wrap_nums(name: str, ctype: str, vals: list[int]) -> str:
    out = [f"{ctype} {name}[{len(vals)}] = {{"]
    line = "    "
    for v in vals:
        item = f"{v},"
        if len(line) + len(item) + 1 > 60:
            out.append(line.rstrip())
            line = "    "
        line += item + " "
    if line.strip():
        out.append(line.rstrip())
    out.append("};")
    return "\n".join(out)


def build(corpus: Path, out_json: Path, out_h: Path,
          iteration: int) -> dict:
    doc = json.loads(corpus.read_text(encoding="utf-8"))
    records = doc["records"]
    seqs = [toks(r["text"]) for r in records]
    freq = collections.Counter()
    for seq in seqs:
        freq.update(seq)
    ordered = sorted(freq, key=lambda w: (-freq[w], w))
    selected = []
    for word in REQ:
        if word in freq and word not in selected:
            selected.append(word)
    for word in ordered:
        if word not in selected:
            selected.append(word)
        if len(selected) >= MAX_VOCAB - 1:
            break
    vocab = ["<eos>"] + selected
    ids = {w: i for i, w in enumerate(vocab)}
    edges: dict[int, collections.Counter[int]] = {}
    for seq in seqs:
        clean = [w for w in seq if w in ids]
        if not clean:
            continue
        for a, b in zip(clean, clean[1:]):
            edges.setdefault(ids[a], collections.Counter())[ids[b]] += 1
        edges.setdefault(ids[clean[-1]], collections.Counter())[0] += 1
    n1 = [0] * len(vocab)
    n2 = [0] * len(vocab)
    for src, ctr in edges.items():
        ranked = sorted(
            ((dst, count) for dst, count in ctr.items() if dst != 0),
            key=lambda kv: (-kv[1], kv[0]),
        )
        if ranked:
            n1[src] = ranked[0][0]
        if len(ranked) > 1:
            n2[src] = ranked[1][0]
    blob = bytearray()
    offs = []
    lens = []
    for word in vocab:
        data = b"" if word == "<eos>" else word.encode("ascii")
        offs.append(len(blob))
        lens.append(len(data))
        blob.extend(data)
        blob.append(0)
    body = {
        "schema": 1,
        "iteration": iteration,
        "corpus_sha256": sha256(corpus),
        "vocab": vocab,
        "next_primary": n1,
        "next_secondary": n2,
        "seeds": {"chat": ids["i"],
                  "spectrum": ids["spectrum"],
                  "memory": ids["memory"]},
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    hdr = []
    hdr.extend([
        "// ============================================================",
        "// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.",
        "// Proprietary rights reserved except as licensed in LICENSE.",
        "//",
        "// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.",
        "// Non-commercial use permitted; Commercial Use and AI/ML",
        "// model training prohibited unless separately authorized.",
        "//",
        "// Attribution required: Based on original work by Supratim",
        "// Sanyal of SANYALnet Labs. See root LICENSE for full terms.",
        "// ============================================================",
        f"unsigned int ai_vcnt = {len(vocab)};",
        f"unsigned int ai_s_chat = {ids['i']};",
        f"unsigned int ai_s_spec = {ids['spectrum']};",
        f"unsigned int ai_s_mem = {ids['memory']};",
    ])
    hdr.append(wrap_nums("ai_voff", "unsigned int", offs))
    hdr.append(wrap_nums("ai_vlen", "unsigned char", lens))
    hdr.append(wrap_nums("ai_n1", "unsigned char", n1))
    hdr.append(wrap_nums("ai_n2", "unsigned char", n2))
    hdr.append(wrap_nums("ai_vblob", "unsigned char", list(blob)))
    out_h.parent.mkdir(parents=True, exist_ok=True)
    out_h.write_text("\n".join(hdr) + "\n", encoding="ascii")
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-h", type=Path, required=True)
    ap.add_argument("--iteration", type=int, required=True)
    ns = ap.parse_args()
    build(ns.corpus, ns.out_json, ns.out_h, ns.iteration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
