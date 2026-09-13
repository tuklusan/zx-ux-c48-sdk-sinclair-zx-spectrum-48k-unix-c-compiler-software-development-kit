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
import re

MAGIC = b"A48M"
VERSION = 2
TRIGGER_BASE = 224
TRIGGER_SLOTS = 4096 - TRIGGER_BASE
HEADER_LEN = 40
CHECKSUM_ALG = 1
MAX_RECORD = 192
MAX_OBJECT = 65535
MAX_READ = 64
FACT_TYPES = frozenset((1, 2, 3, 4, 5, 6))
RECORD_TYPES = {
    "fact": 1,
    "biography": 2,
    "game_software": 3,
    "hardware_arch": 4,
    "chronology": 5,
    "comparison": 6,
    "conversation": 7,
}
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class A48MError(ValueError):
    pass


def u16(value: int) -> bytes:
    if value < 0 or value > 65535:
        raise A48MError("u16 out of range")
    return bytes((value & 255, (value >> 8) & 255))


def get_u16(data: bytes, off: int) -> int:
    if off < 0 or off + 2 > len(data):
        raise A48MError("u16 outside buffer")
    return data[off] | (data[off + 1] << 8)


def fletcher_update(
    s1: int, s2: int, data: bytes
) -> tuple[int, int]:
    for value in data:
        s1 = (s1 + value) % 255
        s2 = (s2 + s1) % 255
    return s1, s2


def fletcher16(data: bytes) -> int:
    s1, s2 = fletcher_update(0, 0, data)
    return (s2 << 8) | s1


def protected_bytes(data: bytes) -> bytes:
    if len(data) < HEADER_LEN:
        raise A48MError("container shorter than header")
    work = bytearray(data)
    work[32] = 0
    work[33] = 0
    return bytes(work)


def identity(value: object) -> bytes:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(raw).digest()[:8]


def trigger_id(word: str, salt: int) -> int:
    h = (216 + salt) & 0xFFFF
    for value in word.encode("ascii"):
        h = ((h * 33) ^ value) & 0xFFFF
    return TRIGGER_BASE + (h % TRIGGER_SLOTS)


def choose_trigger_salt(words: list[str]) -> int:
    clean = []
    for raw in words:
        word = str(raw).lower()
        if TOKEN_RE.findall(word) != [word]:
            raise A48MError("trigger must be one normalized token: " + repr(raw))
        if word not in clean:
            clean.append(word)
    for salt in range(65536):
        seen = {}
        ok = True
        for word in clean:
            tid = trigger_id(word, salt)
            if tid in seen and seen[tid] != word:
                ok = False
                break
            seen[tid] = word
        if ok:
            return salt
    raise A48MError("no collision-free trigger hash salt")


def encode_literal_payload(
    text: str, anchor_words: tuple[str, ...] = ()
) -> tuple[bytes, list[tuple[int, int]]]:
    words = TOKEN_RE.findall(text)
    if not words:
        raise A48MError("empty cold-record payload")
    payload = bytearray((0x01,))
    starts: list[int] = []
    ends: list[int] = []
    for word in words:
        starts.append(len(payload))
        raw = word.encode("ascii")
        if word.isdigit():
            if len(raw) > 15:
                raise A48MError("numeric literal exceeds F2 bound")
            payload.extend((0xF2, len(raw)))
        else:
            if len(raw) > 31:
                raise A48MError("word literal exceeds F1 bound")
            payload.extend((0xF1, len(raw)))
        payload.extend(raw)
        ends.append(len(payload))
    first = 2 if len(words) > 3 else max(0, len(words) - 2)
    anchors: list[tuple[int, int]] = []
    if words[0].lower() in set(anchor_words) and first > 0:
        anchors.append((starts[0], ends[0] - starts[0]))
    anchors.append((starts[first], ends[-1] - starts[first]))
    payload.append(0x02)
    if any(length < 1 or length > 255 for _, length in anchors):
        raise A48MError("predicate anchor outside u8 length")
    return bytes(payload), anchors

def token_spans(payload: bytes) -> list[tuple[int, int, bool]]:
    spans: list[tuple[int, int, bool]] = []
    pos = 0
    while pos < len(payload):
        start = pos
        code = payload[pos]
        pos += 1
        control = False
        if code in (0x01, 0x02, 0x06):
            control = True
        elif 0x10 <= code <= 0xEF:
            pass
        elif code == 0xF0:
            if pos + 2 > len(payload):
                raise A48MError("truncated F0 token")
            token_id = get_u16(payload, pos)
            pos += 2
            if token_id < 224 or token_id > 4095:
                raise A48MError("noncanonical F0 token id")
        elif code in (0xF1, 0xF2, 0xF3):
            if pos >= len(payload):
                raise A48MError("truncated literal length")
            length = payload[pos]
            pos += 1
            max_len = 15 if code == 0xF2 else 31
            if length < 1 or length > max_len:
                raise A48MError("literal length outside bound")
            if pos + length > len(payload):
                raise A48MError("truncated literal payload")
            raw = payload[pos:pos + length]
            if any(value < 32 or value > 126 for value in raw):
                raise A48MError("literal contains nonprintable byte")
            pos += length
        else:
            raise A48MError("forbidden/reserved payload token")
        spans.append((start, pos, control))
    return spans


def validate_anchors(
    payload: bytes, anchors: list[tuple[int, int]]
) -> None:
    spans = token_spans(payload)
    boundaries = {0, len(payload)}
    controls: list[tuple[int, int]] = []
    for start, end, is_control in spans:
        boundaries.add(start)
        boundaries.add(end)
        if is_control:
            controls.append((start, end))
    last_end = -1
    for offset, length in anchors:
        if length < 1:
            raise A48MError("zero-length anchor")
        end = offset + length
        if offset not in boundaries or end not in boundaries:
            raise A48MError("anchor not on token boundaries")
        if end > len(payload):
            raise A48MError("anchor outside payload")
        if offset < last_end:
            raise A48MError("overlapping anchors")
        for cstart, cend in controls:
            if offset < cend and end > cstart:
                raise A48MError("control token inside anchor")
        last_end = end


def encode_record(
    record_type: int,
    topic_id: int,
    text: str,
    importance: int,
    triggers: tuple[int, ...] = (),
    entity_a: int = 0,
    entity_b: int = 0,
    anchor_words: tuple[str, ...] = (),
) -> bytes:
    if record_type not in RECORD_TYPES.values():
        raise A48MError("unknown record type")
    if topic_id < 0 or topic_id > 65535:
        raise A48MError("topic id outside u16")
    for entity in (entity_a, entity_b):
        if entity < 0 or entity > 0x7FFF:
            raise A48MError("cold entity must be persistent or zero")
    if importance < 0 or importance > 255:
        raise A48MError("importance outside u8")
    if len(triggers) > 4:
        raise A48MError("too many triggers")
    for trigger in triggers:
        if trigger < 0 or trigger > 4095:
            raise A48MError("trigger outside lexical id space")
    payload, fact_anchors = encode_literal_payload(
        text, anchor_words
    )
    anchors = fact_anchors if record_type in FACT_TYPES else []
    validate_anchors(payload, anchors)
    raw = bytearray((0, record_type))
    raw.extend(u16(topic_id))
    raw.extend(u16(entity_a))
    raw.extend(u16(entity_b))
    raw.append(importance)
    raw.append(len(triggers))
    for trigger in triggers:
        raw.extend(u16(trigger))
    raw.append(len(anchors))
    for offset, length in anchors:
        raw.extend((offset, length))
    raw.extend(payload)
    if len(raw) > MAX_RECORD:
        raise A48MError("record exceeds Candidate-A maximum: " + str(len(raw)) + " bytes")
    raw[0] = len(raw)
    return bytes(raw)


def parse_record(raw: bytes) -> dict:
    if not raw or raw[0] != len(raw):
        raise A48MError("record length mismatch")
    if len(raw) > MAX_RECORD or len(raw) < 11:
        raise A48MError("record size outside bounds")
    record_type = raw[1]
    if record_type not in RECORD_TYPES.values():
        raise A48MError("unknown record type")
    topic_id = get_u16(raw, 2)
    entity_a = get_u16(raw, 4)
    entity_b = get_u16(raw, 6)
    if entity_a > 0x7FFF or entity_b > 0x7FFF:
        raise A48MError("session entity in cold record")
    importance = raw[8]
    trigger_count = raw[9]
    if trigger_count > 4:
        raise A48MError("trigger count exceeds bound")
    pos = 10
    triggers: list[int] = []
    for _ in range(trigger_count):
        trigger = get_u16(raw, pos)
        pos += 2
        if trigger > 4095:
            raise A48MError("trigger outside lexical id space")
        triggers.append(trigger)
    if pos >= len(raw):
        raise A48MError("missing anchor count")
    anchor_count = raw[pos]
    pos += 1
    if anchor_count > 2:
        raise A48MError("anchor count exceeds bound")
    anchors: list[tuple[int, int]] = []
    for _ in range(anchor_count):
        if pos + 2 > len(raw):
            raise A48MError("truncated anchor pair")
        anchors.append((raw[pos], raw[pos + 1]))
        pos += 2
    payload = raw[pos:]
    if not payload:
        raise A48MError("empty record payload")
    token_spans(payload)
    validate_anchors(payload, anchors)
    if record_type in FACT_TYPES and not anchors:
        raise A48MError("factual record lacks anchor")
    return {
        "record_type": record_type,
        "topic_id": topic_id,
        "entity_a": entity_a,
        "entity_b": entity_b,
        "importance": importance,
        "triggers": triggers,
        "anchors": anchors,
        "payload": payload,
    }


class ShortReader:
    def __init__(
        self, data: bytes, pattern: tuple[int, ...] = (64,)
    ) -> None:
        if not pattern or any(n < 1 or n > MAX_READ for n in pattern):
            raise A48MError("invalid short-read pattern")
        self.data = data
        self.pattern = pattern
        self.pos = 0
        self.calls = 0
        self.max_requested = 0

    def read(self, count: int) -> bytes:
        if count < 0 or count > MAX_READ:
            raise A48MError("read request outside 0..64")
        if count > self.max_requested:
            self.max_requested = count
        if count == 0 or self.pos >= len(self.data):
            return b""
        cap = self.pattern[self.calls % len(self.pattern)]
        self.calls += 1
        take = min(count, cap, len(self.data) - self.pos)
        out = self.data[self.pos:self.pos + take]
        self.pos += take
        return out

    def read_full(self, count: int) -> bytes:
        out = bytearray()
        while len(out) < count:
            ask = min(MAX_READ, count - len(out))
            chunk = self.read(ask)
            if not chunk:
                raise A48MError("premature EOF")
            out.extend(chunk)
        return bytes(out)


def build_container(
    records: list[bytes], vocab_id: bytes, interface_id: bytes,
    trigger_salt: int,
) -> bytes:
    if len(vocab_id) != 8 or len(interface_id) != 8:
        raise A48MError("identity width must be eight bytes")
    for record in records:
        parse_record(record)
    records_blob = b"".join(records)
    logical_length = HEADER_LEN + len(records_blob)
    if logical_length > MAX_OBJECT:
        raise A48MError("container exceeds u16 object length")
    header = bytearray()
    header.extend(MAGIC)
    header.extend((VERSION, 0, HEADER_LEN, CHECKSUM_ALG))
    header.extend(vocab_id)
    header.extend(interface_id)
    header.extend(u16(len(records)))
    header.extend(u16(HEADER_LEN))
    header.extend(u16(len(records_blob)))
    header.extend(u16(logical_length))
    header.extend(b"\x00\x00")
    header.extend(u16(trigger_salt))
    header.extend(b"\x00" * 4)
    if len(header) != HEADER_LEN:
        raise AssertionError("header size construction error")
    data = bytes(header) + records_blob
    checksum = fletcher16(protected_bytes(data))
    header[32:34] = u16(checksum)
    return bytes(header) + records_blob


def parse_container(
    reader: ShortReader, actual_length: int
) -> dict:
    if actual_length < HEADER_LEN or actual_length > MAX_OBJECT:
        raise A48MError("actual object length outside bounds")
    header = reader.read_full(HEADER_LEN)
    if header[:4] != MAGIC:
        raise A48MError("bad A48M magic")
    if header[4] != VERSION:
        raise A48MError("unsupported A48M version")
    if header[5] != 0 or header[6] != HEADER_LEN:
        raise A48MError("unsupported flags/header length")
    if header[7] != CHECKSUM_ALG:
        raise A48MError("unsupported integrity algorithm")
    if any(header[36:40]):
        raise A48MError("nonzero reserved header bytes")
    trigger_salt = get_u16(header, 34)
    record_count = get_u16(header, 24)
    records_offset = get_u16(header, 26)
    records_length = get_u16(header, 28)
    logical_length = get_u16(header, 30)
    checksum = get_u16(header, 32)
    if logical_length != actual_length:
        raise A48MError("declared/actual logical length mismatch")
    if records_offset != HEADER_LEN:
        raise A48MError("unexpected records offset")
    if records_length != logical_length - records_offset:
        raise A48MError("records section length mismatch")

    protected_header = bytearray(header)
    protected_header[32] = 0
    protected_header[33] = 0
    s1, s2 = fletcher_update(0, 0, bytes(protected_header))
    records: list[dict] = []
    section_used = 0
    for _ in range(record_count):
        if section_used >= records_length:
            raise A48MError("record count exceeds section")
        first = reader.read_full(1)
        length = first[0]
        if length < 11 or length > MAX_RECORD:
            raise A48MError("invalid record length")
        remaining = records_length - section_used
        if length > remaining:
            raise A48MError("record crosses section end")
        raw = first + reader.read_full(length - 1)
        records.append(parse_record(raw))
        s1, s2 = fletcher_update(s1, s2, raw)
        section_used += length
    if section_used != records_length:
        raise A48MError("records do not consume declared section")
    if reader.read(1):
        raise A48MError("bytes beyond declared logical length")
    if ((s2 << 8) | s1) != checksum:
        raise A48MError("integrity check mismatch")
    return {
        "version": header[4],
        "vocab_id": header[8:16],
        "interface_id": header[16:24],
        "record_count": record_count,
        "logical_length": logical_length,
        "checksum": checksum,
        "trigger_salt": trigger_salt,
        "read_calls": reader.calls,
        "max_read_request": reader.max_requested,
        "records": records,
    }


def build_from_seed(
    corpus_path: Path, model_path: Path
) -> tuple[bytes, dict]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    model = json.loads(model_path.read_text(encoding="utf-8"))
    topics = list(model["topics"])
    topic_map = {name: index for index, name in enumerate(topics)}
    vocab_id = identity(model["vocab"])
    all_trigger_words = []
    for item in corpus["records"]:
        if item.get("kind") == "fact-user":
            for word in item.get("triggers", []):
                if word not in all_trigger_words:
                    all_trigger_words.append(word)
    trigger_salt = choose_trigger_salt(all_trigger_words)
    if model.get("trigger_salt") != trigger_salt:
        raise A48MError("hot/cold trigger salt mismatch")
    if sorted(model.get("trigger_words", [])) != sorted(all_trigger_words):
        raise A48MError("hot/cold trigger lexicon mismatch")
    interface_desc = {
        "wire": "candidate-a-v1",
        "vocab": model["vocab"],
        "topics": topic_map,
        "semantic_symbols": {},
        "record_types": RECORD_TYPES,
        "record_schema": "a48m-record-v1",
        "scoring": "topic-match-plus-importance-v1",
        "trigger_scheme": "salted-wordhash16-exact-v2",
        "trigger_lexicon": sorted(all_trigger_words),
        "lm_schema": model.get("schema"),
    }
    interface_id = identity(interface_desc)
    records: list[bytes] = []
    for item in corpus["records"]:
        if item.get("kind") != "fact-user":
            continue
        topic = item["topic"]
        if topic not in topic_map:
            raise A48MError("cold fact uses unknown topic")
        record_type = (
            RECORD_TYPES["chronology"]
            if topic == "history"
            else RECORD_TYPES["fact"]
        )
        trigger_words = item.get("triggers", [])
        if len(trigger_words) > 4:
            raise A48MError("seed fact has too many triggers")
        trigger_ids = []
        for raw in trigger_words:
            word = str(raw).lower()
            if TOKEN_RE.findall(word) != [word]:
                raise A48MError("invalid seed trigger: " + repr(raw))
            trigger_ids.append(trigger_id(word, trigger_salt))
        records.append(
            encode_record(
                record_type,
                topic_map[topic],
                item["text"],
                200,
                tuple(trigger_ids),
                anchor_words=tuple(
                    str(word).lower() for word in trigger_words
                ),
            )
        )
    if not records:
        raise A48MError("seed corpus produced no factual records")
    data = build_container(records, vocab_id, interface_id, trigger_salt)
    meta = {
        "schema": 1,
        "format": "A48M Candidate-A prototype v2",
        "record_count": len(records),
        "logical_length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "fletcher16": get_u16(data, 32),
        "vocab_id_hex": vocab_id.hex(),
        "interface_id_hex": interface_id.hex(),
        "trigger_salt": trigger_salt,
        "interface_sha256": hashlib.sha256(
            json.dumps(
                interface_desc,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
        ).hexdigest(),
    }
    return data, meta
