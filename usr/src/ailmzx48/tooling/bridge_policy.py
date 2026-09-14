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

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
BRIDGE_WORDS = (
    "a", "an", "the", "and", "in", "on", "at",
    "for", "with", "by", "of", "from", "to", "style",
)


def words(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def word_hash(word: str) -> int:
    h = 216
    for value in word.encode("ascii"):
        h = ((h * 33) ^ value) & 0xFFFF
    return h


def bridge_context(record: dict, seq: list[str], at: int) -> tuple[str, int, int]:
    prev1 = word_hash(seq[at - 1]) if at > 0 else 0
    prev2 = word_hash(seq[at - 2]) if at > 1 else 0
    return str(record["topic"]), prev2, prev1


def candidate_gaps(record: dict) -> list[dict]:
    seq = words(str(record["text"]))
    triggers = {str(value).lower() for value in record.get("triggers", [])}
    out = []
    for at, word in enumerate(seq):
        if word not in BRIDGE_WORDS or word in triggers:
            continue
        if at == len(seq) - 1:
            continue
        if at == 0 and word not in ("a", "an", "the"):
            continue
        topic, prev2, prev1 = bridge_context(record, seq, at)
        out.append({
            "gap": at,
            "word": word,
            "topic": topic,
            "prev2_hash": prev2,
            "prev1_hash": prev1,
        })
    return out


def assign_bridge_gaps(records: list[dict]) -> dict[int, dict]:
    facts = []
    for index, record in enumerate(records):
        if record.get("kind") != "fact-user":
            continue
        candidates = candidate_gaps(record)
        if not candidates:
            raise ValueError(
                "fact has no safe bridge candidate: " + str(record.get("text"))
            )
        facts.append((index, record, candidates))
    order = sorted(facts, key=lambda row: (len(row[2]), row[0]))
    chosen: dict[int, dict] = {}
    predicted: dict[tuple[str, int, int], str] = {}

    def visit(pos: int) -> bool:
        if pos == len(order):
            return True
        index, _record, candidates = order[pos]
        ranked = sorted(
            candidates,
            key=lambda item: (
                item["gap"] == 0,
                item["gap"],
                BRIDGE_WORDS.index(item["word"]),
            ),
        )
        for item in ranked:
            ctx = (
                item["topic"], item["prev2_hash"], item["prev1_hash"]
            )
            old = predicted.get(ctx)
            if old is not None and old != item["word"]:
                continue
            inserted = old is None
            if inserted:
                predicted[ctx] = item["word"]
            chosen[index] = item
            if visit(pos + 1):
                return True
            chosen.pop(index, None)
            if inserted:
                predicted.pop(ctx, None)
        return False

    if not visit(0):
        raise ValueError("no globally consistent learned bridge assignment")
    if len(chosen) != len(facts):
        raise AssertionError("bridge assignment coverage mismatch")
    return chosen


def bridge_key(topic: int, prev2: int, prev1: int, salt: int) -> int:
    h = (216 + salt) & 0xFFFF
    for value in (topic, prev2, prev1):
        h = ((h * 33) ^ (value & 255)) & 0xFFFF
        h = ((h * 33) ^ ((value >> 8) & 255)) & 0xFFFF
    return h


def build_bridge_rows(
    assignments: dict[int, dict],
    topic_map: dict[str, int],
    vocab_ids: dict[str, int],
) -> tuple[int, list[dict]]:
    by_context: dict[tuple[int, int, int], str] = {}
    for item in assignments.values():
        topic = topic_map[item["topic"]]
        ctx = (topic, item["prev2_hash"], item["prev1_hash"])
        old = by_context.get(ctx)
        if old is not None and old != item["word"]:
            raise ValueError("bridge context predicts conflicting words")
        by_context[ctx] = item["word"]
    for salt in range(65536):
        seen: dict[int, tuple[int, int, int]] = {}
        ok = True
        for ctx in sorted(by_context):
            key = bridge_key(ctx[0], ctx[1], ctx[2], salt)
            if key in seen and seen[key] != ctx:
                ok = False
                break
            seen[key] = ctx
        if not ok:
            continue
        rows = []
        for ctx in sorted(by_context):
            word = by_context[ctx]
            if word not in vocab_ids:
                raise ValueError("bridge word absent from hot vocabulary: " + word)
            rows.append({
                "key": bridge_key(ctx[0], ctx[1], ctx[2], salt),
                "next": vocab_ids[word],
                "topic": ctx[0],
                "prev2_hash": ctx[1],
                "prev1_hash": ctx[2],
                "word": word,
            })
        rows.sort(key=lambda row: row["key"])
        return salt, rows
    raise ValueError("no collision-free learned bridge salt")
