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
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
TOOLING = HERE.parents[1] / "tooling"
if str(TOOLING) not in sys.path:
    sys.path.insert(0, str(TOOLING))

from context_reference import (
    Capsule,
    ContextReference,
    FLAG_CORRECTION,
    FLAG_UNRESOLVED,
    L0_BYTES,
    L0_DESC_BYTES,
    L0_DESCS,
    L1_CAP,
    L2_CAP,
    SESSION_LITERAL_BYTES,
)


def capsule(
    relation: int,
    topic: int = 1,
    importance: int = 1,
    flags: int = 0,
    ent_a: int = 0,
) -> Capsule:
    return Capsule(
        flags=flags,
        relation=relation,
        topic=topic,
        importance=importance,
        ent_a=ent_a,
    )


def test_descriptor_pressure() -> None:
    context = ContextReference()
    for index in range(16):
        context.commit_pair(
            b"u",
            b"a",
            (capsule(index + 1),),
            (capsule(index + 101, flags=1),),
        )
    assert len(context.descriptors) == L0_DESCS
    context.commit_pair(b"x", b"y")
    assert len(context.descriptors) == L0_DESCS
    promoted = [item for item in context.l1 if item is not None]
    assert len(promoted) == 2
    assert sorted(item.relation for item in promoted) == [1, 101]
    assert all(item.age == 16 for item in promoted)


def test_byte_pressure() -> None:
    context = ContextReference()
    for index in range(7):
        context.commit_pair(
            bytes([65 + index]) * 64,
            bytes([97 + index]) * 64,
            (capsule(index + 1),),
        )
    assert context.l0bytes == L0_BYTES
    context.commit_pair(b"u" * 20, b"a" * 20)
    assert context.l0bytes == 808
    assert len(context.descriptors) == 14
    assert context.l1count == 1


def test_transaction_rollback() -> None:
    context = ContextReference()
    context.commit_pair(b"u", b"a")
    before = context.snapshot()
    try:
        context.commit_pair(b"x" * 500, b"y" * 500)
    except ValueError:
        pass
    else:
        raise AssertionError("oversized pair unexpectedly committed")
    assert context.snapshot() == before


def test_l1_l2_compaction() -> None:
    context = ContextReference()
    for index in range(L1_CAP + 1):
        context._add_l1(
            capsule(
                index + 1,
                topic=index + 1,
                importance=index % 5,
            ),
        )
    assert context.l1count == L1_CAP
    assert context.l2count == 1
    assert context.ai_compact == 1

    context = ContextReference()
    for index in range(L2_CAP + 1):
        context._merge_l2(
            capsule(
                index + 1,
                topic=index + 1,
            ),
        )
    assert context.l2count == L2_CAP
    assert context.ai_l2evict == 1


def test_age_saturation() -> None:
    context = ContextReference()
    context.l1[0] = Capsule(relation=1, age=255)
    context.l2[0] = Capsule(relation=2, age=254)
    context.commit_pair(b"u", b"a")
    assert context.l1[0].age == 255
    assert context.l2[0].age == 255


def test_retrieval_bound() -> None:
    context = ContextReference()
    target_ref = 123
    context.l1[0] = capsule(
        1,
        topic=7,
        importance=9,
        flags=FLAG_CORRECTION,
        ent_a=target_ref,
    )
    context.l1[1] = capsule(2, topic=7, importance=2)
    context.l1[2] = capsule(
        3,
        topic=2,
        importance=10,
        flags=FLAG_UNRESOLVED,
        ent_a=target_ref,
    )
    context.l1[3] = capsule(4, topic=1, importance=1)
    context.l1[4] = capsule(5, topic=1, importance=1)
    result = context.retrieve(7, (target_ref,))
    assert len(result) == 4
    assert result[0][2].relation == 1


def test_session_literals() -> None:
    context = ContextReference()
    refs = []
    for index, name in enumerate(
        (b"A", b"B", b"C", b"D", b"E", b"F", b"G", b"H")
    ):
        ref, created = context.literals.allocate(name, context)
        assert created
        refs.append(ref)
        context.l1[index] = capsule(
            index + 1,
            ent_a=ref,
            importance=index + 1,
        )
    assert [
        context.literals.resolve(ref)
        for ref in refs
    ] == [
        bytes([65 + index])
        for index in range(8)
    ]

    replacement, created = context.literals.allocate(b"I", context)
    assert created
    assert replacement & 7 == 0
    assert context.ai_litloss == 1
    assert context.l1[0].ent_a == 0
    assert context.literals.resolve(refs[0]) is None
    assert context.literals.resolve(replacement) == b"I"

    context = ContextReference()
    context.literals.generations[0] = 4095
    context.literals.values[0] = b"Old"
    wrapped, created = context.literals.allocate(b"New", context)
    assert created
    assert context.literals.decode_ref(wrapped) == (0, 1)
    assert context.literals.resolve(wrapped) == b"New"

    reused, created = context.literals.allocate(b"new", context)
    assert not created
    assert reused == wrapped
    assert context.literals.resolve(reused) == b"New"


def test_long_stress() -> dict:
    context = ContextReference()
    raw_source_bytes = 0
    for index in range(500):
        flags = 0 if index % 2 == 0 else 1
        item = capsule(
            (index % 17) + 1,
            topic=(index % 6) + 1,
            importance=index % 9,
            flags=flags,
        )
        user = (
            f"user-{index:04d}-" + "x" * 40
        ).encode("ascii")
        assistant = (
            f"assist-{index:04d}-" + "y" * 40
        ).encode("ascii")
        raw_source_bytes += len(user) + len(assistant)
        context.commit_pair(
            user,
            assistant,
            (item,),
        )
    context.validate()
    assert raw_source_bytes > 32768
    assert context.l0bytes <= L0_BYTES
    assert len(context.descriptors) <= L0_DESCS
    assert context.l1count <= L1_CAP
    assert context.l2count <= L2_CAP
    return {
        "dialogue_pairs": 500,
        "raw_source_bytes": raw_source_bytes,
        "l0_bytes": context.l0bytes,
        "l0_descriptors": len(context.descriptors),
        "l1_records": context.l1count,
        "l2_records": context.l2count,
        "l1_to_l2_compactions": context.ai_compact,
        "l2_evictions": context.ai_l2evict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    assert L0_DESCS * L0_DESC_BYTES == 128
    assert SESSION_LITERAL_BYTES == 272
    test_descriptor_pressure()
    test_byte_pressure()
    test_transaction_rollback()
    test_l1_l2_compaction()
    test_age_saturation()
    test_retrieval_bound()
    test_session_literals()
    stress = test_long_stress()
    report = {
        "schema": 1,
        "status": "PASS",
        "l0_bytes": L0_BYTES,
        "l0_descriptors": L0_DESCS,
        "l0_directory_bytes": L0_DESCS * L0_DESC_BYTES,
        "l1_records": L1_CAP,
        "l2_records": L2_CAP,
        "capsule_bytes": 16,
        "session_literal_bytes": SESSION_LITERAL_BYTES,
        "tests": [
            "descriptor-pressure-complete-dialogue-eviction",
            "byte-pressure-complete-dialogue-eviction",
            "transactional-preflight-rollback",
            "l1-to-l2-deterministic-compaction",
            "l2-deterministic-eviction",
            "saturating-age",
            "bounded-four-record-retrieval",
            "session-literal-generation-and-invalidation",
            "source-history-over-32k-with-fixed-context-bounds",
        ],
        "stress": stress,
    }
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
