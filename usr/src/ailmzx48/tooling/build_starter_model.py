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

from bridge_policy import (
    assign_bridge_gaps, build_bridge_rows,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_VOCAB = 96
MAX_UNIGRAM = 12
MAX_TRIGRAM = 64
BASE_TOPICS = (
    "identity",
    "spectrum",
    "history",
    "memory",
    "local",
    "games",
)
TOPICS = ("unknown",) + BASE_TOPICS
SEED_WORD = {
    "unknown": "small",
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
    for value in vals:
        item = f"{value},"
        if len(line) + len(item) + 1 > 60:
            out.append(line.rstrip())
            line = "    "
        line += item + " "
    if line.strip():
        out.append(line.rstrip())
    out.append("};")
    return "\n".join(out)


def ranked_edges(
    seqs: list[list[str]], ids: dict[str, int]
) -> tuple[list[int], list[int]]:
    edges: dict[int, collections.Counter[int]] = {}
    for seq in seqs:
        clean = [word for word in seq if word in ids]
        if not clean:
            continue
        for first, second in zip(clean, clean[1:]):
            src = ids[first]
            dst = ids[second]
            edges.setdefault(src, collections.Counter())[dst] += 1
    firsts = [0] * len(ids)
    seconds = [0] * len(ids)
    for src, ctr in edges.items():
        ranked = sorted(
            ctr.items(), key=lambda item: (-item[1], item[0])
        )
        if ranked:
            firsts[src] = ranked[0][0]
        if len(ranked) > 1:
            seconds[src] = ranked[1][0]
    return firsts, seconds


def trigram_rows(
    seqs: list[list[str]], ids: dict[str, int],
    required: set[tuple[int, int]],
) -> list[tuple[int, int, int, int, int]]:
    edges: dict[tuple[int, int], collections.Counter[int]] = {}
    for seq in seqs:
        clean = [ids[word] for word in seq if word in ids]
        for first, second, third in zip(
            clean, clean[1:], clean[2:]
        ):
            key = (first, second)
            edges.setdefault(key, collections.Counter())[third] += 1
    ranked_keys = sorted(
        edges,
        key=lambda key: (
            -sum(edges[key].values()), key[0], key[1]
        ),
    )
    selected: list[tuple[int, int]] = []
    for key in sorted(required):
        if key in edges and key not in selected:
            selected.append(key)
    for key in ranked_keys:
        if key not in selected:
            selected.append(key)
        if len(selected) >= MAX_TRIGRAM:
            break
    rows = []
    for first, second in sorted(selected):
        ctr = edges[(first, second)]
        ranked = sorted(
            ctr.items(), key=lambda item: (-item[1], item[0])
        )
        next1 = ranked[0][0]
        next2 = ranked[1][0] if len(ranked) > 1 else 0
        rows.append((first, second, next1, next2, sum(ctr.values())))
    return rows



def trigger_id(word: str, salt: int) -> int:
    h = (216 + salt) & 0xFFFF
    for value in word.encode("ascii"):
        h = ((h * 33) ^ value) & 0xFFFF
    return 224 + (h % 3872)


def choose_trigger_salt(words: list[str]) -> int:
    for salt in range(65536):
        seen: dict[int, str] = {}
        ok = True
        for word in words:
            ident = trigger_id(word, salt)
            if ident in seen and seen[ident] != word:
                ok = False
                break
            seen[ident] = word
        if ok:
            return salt
    raise ValueError("no collision-free trigger salt")

def trigger_tables(
    words: list[str], salt: int
) -> tuple[list[int], list[int], list[int], list[int]]:
    rows = sorted((trigger_id(word, salt), word) for word in words)
    ids: list[int] = []
    offs: list[int] = []
    lens: list[int] = []
    blob: list[int] = []
    for trigger, word in rows:
        raw = word.encode("ascii")
        ids.append(trigger)
        offs.append(len(blob))
        lens.append(len(raw))
        blob.extend(raw)
        blob.append(0)
    return ids, offs, lens, blob


def build(
    corpus: Path, out_json: Path, out_h: Path, iteration: int
) -> dict:
    doc = json.loads(corpus.read_text(encoding="utf-8"))
    records = doc["records"]
    bridge_assign = assign_bridge_gaps(records)
    by_topic: dict[str, list[list[str]]] = {
        topic: [] for topic in TOPICS
    }
    all_seqs: list[list[str]] = []
    trigger_words: list[str] = []
    for record in records:
        topic = record.get("topic")
        if topic not in BASE_TOPICS:
            raise ValueError("missing/invalid corpus topic: " + repr(topic))
        seq = toks(record["text"])
        if not seq:
            raise ValueError("empty token sequence in corpus")
        by_topic[topic].append(seq)
        all_seqs.append(seq)
        if record.get("kind") == "style-synthetic":
            by_topic["unknown"].append(seq)
        for raw_trigger in record.get("triggers", []):
            word = str(raw_trigger).lower()
            if toks(word) != [word]:
                raise ValueError(
                    "trigger must be one normalized token: "
                    + repr(raw_trigger)
                )
            if word not in trigger_words:
                trigger_words.append(word)
    for topic in TOPICS:
        if not by_topic[topic]:
            raise ValueError("topic has no training sequences: " + topic)

    freq = collections.Counter()
    for seq in all_seqs:
        freq.update(seq)
    seed_words = tuple(SEED_WORD[topic] for topic in TOPICS)
    ordered = sorted(freq, key=lambda word: (-freq[word], word))
    selected: list[str] = []
    for word in seed_words:
        if word not in freq:
            raise ValueError("missing seed word: " + word)
        if word not in selected:
            selected.append(word)
    bridge_words = sorted({
        item["word"] for item in bridge_assign.values()
    })
    for word in bridge_words:
        if word not in selected:
            selected.append(word)
    for word in ordered:
        if word not in selected:
            selected.append(word)
        if len(selected) >= MAX_VOCAB - 1:
            break

    vocab = ["<eos>"] + selected
    ids = {word: index for index, word in enumerate(vocab)}
    seeds = {topic: ids[SEED_WORD[topic]] for topic in TOPICS}
    topic_map = {name: index for index, name in enumerate(TOPICS)}
    bridge_salt, bridge_rows = build_bridge_rows(
        bridge_assign, topic_map, ids
    )

    flat_n1: list[int] = []
    flat_n2: list[int] = []
    required_tri: set[tuple[int, int]] = set()
    for topic in TOPICS:
        firsts, seconds = ranked_edges(by_topic[topic], ids)
        flat_n1.extend(firsts)
        flat_n2.extend(seconds)
        seed = seeds[topic]
        next1 = firsts[seed]
        if next1:
            required_tri.add((seed, next1))

    tri = trigram_rows(all_seqs, ids, required_tri)
    unigram = [
        ids[word] for word in ordered
        if word in ids and ids[word] != 0
    ][:MAX_UNIGRAM]
    while len(unigram) < MAX_UNIGRAM:
        unigram.append(0)

    blob = bytearray()
    offs: list[int] = []
    lens: list[int] = []
    for word in vocab:
        raw = b"" if word == "<eos>" else word.encode("ascii")
        offs.append(len(blob))
        lens.append(len(raw))
        blob.extend(raw)
        blob.append(0)

    trigger_salt = choose_trigger_salt(trigger_words)
    hids, hoffs, hlens, hblob = trigger_tables(
        trigger_words, trigger_salt
    )

    body = {
        "schema": 3,
        "iteration": iteration,
        "corpus_sha256": sha256(corpus),
        "topics": list(TOPICS),
        "topic_seeds": seeds,
        "vocab": vocab,
        "unigram_fallback": unigram,
        "next_primary": flat_n1,
        "next_secondary": flat_n2,
        "trigram_contexts": [
            {
                "first": first,
                "second": second,
                "next_primary": next1,
                "next_secondary": next2,
                "evidence": count,
            }
            for first, second, next1, next2, count in tri
        ],
        "trigger_words": sorted(trigger_words),
        "trigger_salt": trigger_salt,
        "bridge_salt": bridge_salt,
        "bridge_contexts": bridge_rows,
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
        "unsigned int ai_t_unknown = 0;",
        "unsigned int ai_t_id = 1;",
        "unsigned int ai_t_spec = 2;",
        "unsigned int ai_t_hist = 3;",
        "unsigned int ai_t_mem = 4;",
        "unsigned int ai_t_local = 5;",
        "unsigned int ai_t_games = 6;",
        f"unsigned int ai_tricnt = {len(tri)};",
        f"unsigned int ai_hcnt = {len(hids)};",
        f"unsigned int ai_brcnt = {len(bridge_rows)};",
        f"unsigned int ai_bsalt = {bridge_salt};",
    ]
    hdr.append(wrap_nums(
        "ai_tseed", "unsigned char",
        [seeds[topic] for topic in TOPICS]
    ))
    hdr.append(wrap_nums("ai_voff", "unsigned int", offs))
    hdr.append(wrap_nums("ai_vlen", "unsigned char", lens))
    hdr.append(wrap_nums("ai_n1", "unsigned char", flat_n1))
    hdr.append(wrap_nums("ai_n2", "unsigned char", flat_n2))
    hdr.append(wrap_nums("ai_uni", "unsigned char", unigram))
    hdr.append(wrap_nums(
        "ai_tri1", "unsigned char", [row[0] for row in tri]
    ))
    hdr.append(wrap_nums(
        "ai_tri2", "unsigned char", [row[1] for row in tri]
    ))
    hdr.append(wrap_nums(
        "ai_trin1", "unsigned char", [row[2] for row in tri]
    ))
    hdr.append(wrap_nums(
        "ai_trin2", "unsigned char", [row[3] for row in tri]
    ))
    hdr.append(wrap_nums(
        "ai_brkey", "unsigned int",
        [row["key"] for row in bridge_rows]
    ))
    hdr.append(wrap_nums(
        "ai_brnext", "unsigned char",
        [row["next"] for row in bridge_rows]
    ))
    hdr.append(wrap_nums("ai_hid", "unsigned int", hids))
    hdr.append(wrap_nums("ai_hoff", "unsigned int", hoffs))
    hdr.append(wrap_nums("ai_hlen", "unsigned char", hlens))
    hdr.append(wrap_nums(
        "ai_hblob", "unsigned char", hblob
    ))
    hdr.append(wrap_nums(
        "ai_vblob", "unsigned char", list(blob)
    ))
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
