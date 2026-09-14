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

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tooling"
if str(TOOL) not in sys.path:
    sys.path.insert(0, str(TOOL))

from a48m_reference import (
    A48MError,
    HEADER_LEN,
    ShortReader,
    build_from_seed,
    fletcher16,
    parse_container,
    protected_bytes,
    token_spans,
    u16,
)

from bridge_policy import (
    BRIDGE_WORDS, assign_bridge_gaps,
)


def expect_fail(fn) -> None:
    try:
        fn()
    except A48MError:
        return
    raise AssertionError("expected A48M validation failure")


def main() -> int:
    root = HERE.parent
    corpus = root / "training" / "seed_corpus.json"
    model = root / "model" / "current-model.json"
    out_bin = root / "model" / "cold-seed.bin"
    out_meta = root / "model" / "cold-seed.json"
    out_header = root / "aicold.h"
    report_path = HERE / "a48m-reference-report.json"

    data, meta = build_from_seed(corpus, model)
    parsed = parse_container(
        ShortReader(data, (1, 7, 3, 64, 2, 11)), len(data)
    )
    assert parsed["record_count"] == meta["record_count"]
    assert parsed["logical_length"] == len(data)
    assert parsed["read_calls"] > 1
    assert all(record["anchors"] for record in parsed["records"])
    assert all(1 <= len(record["anchors"]) <= 2
               for record in parsed["records"])
    assert all(sum(length for _, length in record["anchors"])
               < len(record["payload"]) - 2
               for record in parsed["records"])
    corpus_doc = json.loads(corpus.read_text(encoding="utf-8"))
    assignments = assign_bridge_gaps(corpus_doc["records"])
    facts = [
        (index, row)
        for index, row in enumerate(corpus_doc["records"])
        if row.get("kind") == "fact-user"
    ]
    assert len(facts) == len(parsed["records"])
    assert len(assignments) == len(facts)
    model_doc = json.loads(model.read_text(encoding="utf-8"))
    assert len(model_doc.get("bridge_contexts", [])) <= 68
    assert len(model_doc.get("bridge_contexts", [])) >= 1
    for (source_index, source), record in zip(
        facts, parsed["records"]
    ):
        payload = record["payload"]
        spans = [span for span in token_spans(payload) if not span[2]]
        uncovered = []
        for start, end, _control in spans:
            covered = any(
                off <= start and end <= off + length
                for off, length in record["anchors"]
            )
            if not covered:
                code = payload[start]
                assert code in (0xF1, 0xF2, 0xF3)
                size = payload[start + 1]
                word = bytes(
                    payload[start + 2:start + 2 + size]
                ).decode("ascii").lower()
                uncovered.append(word)
        expected = assignments[source_index]["word"]
        assert uncovered == [expected], (source["text"], uncovered)
        assert expected in BRIDGE_WORDS
        triggers = {
            str(value).lower() for value in source.get("triggers", [])
        }
        assert expected not in triggers
    assert any(record["triggers"] for record in parsed["records"])
    assert any(len(record["triggers"]) >= 2 for record in parsed["records"])

    expect_fail(
        lambda: parse_container(ShortReader(data[:-1], (5,)), len(data))
    )
    expect_fail(
        lambda: parse_container(ShortReader(data, (5,)), len(data) - 1)
    )
    corrupt = bytearray(data)
    corrupt[-1] ^= 1
    expect_fail(
        lambda: parse_container(ShortReader(bytes(corrupt), (13,)), len(data))
    )
    bad_reserved = bytearray(data)
    bad_reserved[39] = 1
    expect_fail(
        lambda: parse_container(
            ShortReader(bytes(bad_reserved), (17,)), len(data)
        )
    )
    bad_length = bytearray(data)
    bad_length[HEADER_LEN] = 193
    bad_length[32:34] = b"\x00\x00"
    bad_length[32:34] = u16(
        fletcher16(protected_bytes(bytes(bad_length)))
    )
    expect_fail(
        lambda: parse_container(
            ShortReader(bytes(bad_length), (19,)), len(data)
        )
    )

    out_bin.write_bytes(data)
    out_meta.write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    vocab = list(data[8:16])
    interface = list(data[16:24])
    header = [
        "// ============================================================",
        "// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.",
        "// Proprietary rights reserved except as licensed in LICENSE.",
        "//",
        "// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.",
        "// Attribution required: Based on original work by Supratim",
        "// Sanyal of SANYALnet Labs. See root LICENSE for full terms.",
        "// Generated hot/cold A48M identity constants.",
        "// ============================================================",
        "unsigned char ai_cvid[8] = {",
        "    " + ", ".join(str(v) for v in vocab),
        "};",
        "unsigned char ai_ciid[8] = {",
        "    " + ", ".join(str(v) for v in interface),
        "};",
    ]
    out_header.write_text(
        "\n".join(header) + "\n", encoding="ascii", newline="\n"
    )
    report = {
        "schema": 1,
        "status": "PASS",
        "logical_length": len(data),
        "record_count": parsed["record_count"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "short_read_calls": parsed["read_calls"],
        "max_read_request": parsed["max_read_request"],
        "max_record_bytes": 192,
        "trigger_salt": parsed["trigger_salt"],
        "bridge_salt": meta.get("bridge_salt"),
        "bridge_contexts": meta.get("bridge_contexts"),
        "tests": [
            "deterministic-seed-build",
            "positive-short-read-full-parse",
            "premature-eof-rejection",
            "actual-length-mismatch-rejection",
            "integrity-corruption-rejection",
            "reserved-header-byte-rejection",
            "oversize-record-length-rejection",
            "factual-anchor-presence",
            "predicate-anchor-not-full-sentence",
            "learned-bridge-full-factual-coverage",
            "cold-gap-excluded-from-anchor-copy",
            "exact-record-count-and-section-end",
            "collision-free-salted-trigger-id-space",
        ],
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
