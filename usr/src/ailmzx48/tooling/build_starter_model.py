\
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
TOPICS = (
    "identity",
    "spectrum",
    "history",
    "memory",
    "local",
    "games",
)
SEED_WORD = {
    "identity": "i",
    "spectrum": "spectrum",
    "history": "history",
    "memory": "memory",
    "local": "local",
    "games": "games",
}


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


def ranked_edges(
    seqs: list[list[str]],
    ids: dict[str, int],
) -> tuple[list[int], list[int]]:
    edges: dict[int, collections.Counter[int]] = {}
    for seq in seqs:
        clean = [w for w in seq if w in ids]
        if not clean:
            continue
        for a, b in zip(clean, clean[1:]):
            edges.setdefault(
                ids[a], collections.Counter()
            )[ids[b]] += 1
        edges.setdefault(
            ids[clean[-1]], collections.Counter()
        )[0] += 1
    n1 = [0] * len(ids)
    n2 = [0] * len(ids)
    for src, ctr in edges.items():
        ranked = sorted(
            (
                (dst, count)
                for dst, count in ctr.items()
                if dst != 0
            ),
            key=lambda kv: (-kv[1], kv[0]),
        )
        if ranked:
            n1[src] = ranked[0][0]
        if len(ranked) > 1:
            n2[src] = ranked[1][0]
    return n1, n2


def build(
    corpus: Path,
    out_json: Path,
    out_h: Path,
    iteration: int,
) -> dict:
    doc = json.loads(corpus.read_text(encoding="utf-8"))
    records = doc["records"]
    by_topic: dict[str, list[list[str]]] = {
        topic: [] for topic in TOPICS
    }
    all_seqs = []
    for record in records:
        topic = record.get("topic")
        if topic not in by_topic:
            raise ValueError(
                "missing/invalid corpus topic: "
                + repr(topic)
            )
        seq = toks(record["text"])
        if not seq:
            raise ValueError("empty token sequence in corpus")
        by_topic[topic].append(seq)
        all_seqs.append(seq)
    for topic in TOPICS:
        if not by_topic[topic]:
            raise ValueError("topic has no records: " + topic)

    freq = collections.Counter()
    for seq in all_seqs:
        freq.update(seq)
    required = tuple(SEED_WORD[t] for t in TOPICS)
    ordered = sorted(
        freq,
        key=lambda w: (-freq[w], w),
    )
    selected = []
    for word in required:
        if word not in freq:
            raise ValueError("missing seed word: " + word)
        if word not in selected:
            selected.append(word)
    for word in ordered:
        if word not in selected:
            selected.append(word)
        if len(selected) >= MAX_VOCAB - 1:
            break

    vocab = ["<eos>"] + selected
    ids = {w: i for i, w in enumerate(vocab)}
    flat_n1 = []
    flat_n2 = []
    for topic in TOPICS:
        n1, n2 = ranked_edges(by_topic[topic], ids)
        flat_n1.extend(n1)
        flat_n2.extend(n2)

    blob = bytearray()
    offs = []
    lens = []
    for word in vocab:
        data = (
            b""
            if word == "<eos>"
            else word.encode("ascii")
        )
        offs.append(len(blob))
        lens.append(len(data))
        blob.extend(data)
        blob.append(0)

    seeds = {
        topic: ids[SEED_WORD[topic]]
        for topic in TOPICS
    }
    body = {
        "schema": 2,
        "iteration": iteration,
        "corpus_sha256": sha256(corpus),
        "topics": list(TOPICS),
        "topic_seeds": seeds,
        "vocab": vocab,
        "next_primary": flat_n1,
        "next_secondary": flat_n2,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    hdr = [
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
        f"unsigned int ai_tcnt = {len(TOPICS)};",
        "unsigned int ai_t_id = 0;",
        "unsigned int ai_t_spec = 1;",
        "unsigned int ai_t_hist = 2;",
        "unsigned int ai_t_mem = 3;",
        "unsigned int ai_t_local = 4;",
        "unsigned int ai_t_games = 5;",
    ]
    hdr.append(
        wrap_nums(
            "ai_tseed",
            "unsigned char",
            [seeds[t] for t in TOPICS],
        )
    )
    hdr.append(
        wrap_nums("ai_voff", "unsigned int", offs)
    )
    hdr.append(
        wrap_nums("ai_vlen", "unsigned char", lens)
    )
    hdr.append(
        wrap_nums("ai_n1", "unsigned char", flat_n1)
    )
    hdr.append(
        wrap_nums("ai_n2", "unsigned char", flat_n2)
    )
    hdr.append(
        wrap_nums(
            "ai_vblob",
            "unsigned char",
            list(blob),
        )
    )
    out_h.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    out_h.write_text(
        "\n".join(hdr) + "\n",
        encoding="ascii",
    )
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--corpus",
        type=Path,
        required=True,
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        required=True,
    )
    ap.add_argument(
        "--out-h",
        type=Path,
        required=True,
    )
    ap.add_argument(
        "--iteration",
        type=int,
        required=True,
    )
    ns = ap.parse_args()
    build(
        ns.corpus,
        ns.out_json,
        ns.out_h,
        ns.iteration,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
