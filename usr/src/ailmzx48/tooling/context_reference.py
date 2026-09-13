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
"""Host reference for Candidate-A compressed conversation context.

This is an executable correctness oracle, not target storage.  Extra Python
metadata attached to L0 descriptors exists only to make promotion and
differential tests explicit.  Target L0 descriptors remain exactly 4 bytes.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace

L0_BYTES = 896
L0_DESCS = 32
L0_DESC_BYTES = 4
L1_CAP = 48
L2_CAP = 24
CAPSULE_BYTES = 16
LIT_SLOTS = 8
LIT_LEN = 31
SESSION_LITERAL_BYTES = LIT_SLOTS * 2 + LIT_SLOTS + LIT_SLOTS * LIT_LEN

FLAG_SPEAKER = 0x01
FLAG_QUESTION = 0x02
FLAG_CORRECTION = 0x04
FLAG_NEGATIVE = 0x08
FLAG_UNRESOLVED = 0x10
FLAG_SUPERSEDED = 0x20
SOURCE_SHIFT = 6


def source_class(flags: int) -> int:
    return (flags >> SOURCE_SHIFT) & 3


@dataclass
class Capsule:
    flags: int = 0
    relation: int = 0
    topic: int = 0
    ent_a: int = 0
    ent_b: int = 0
    hi_a: int = 0
    hi_b: int = 0
    value: int = 0
    importance: int = 0
    age: int = 0
    value_is_ref: bool = False

    def key(self) -> tuple[int, ...]:
        return (
            source_class(self.flags),
            self.relation,
            self.topic,
            self.ent_a,
            self.ent_b,
        )

    def refs(self) -> list[int]:
        refs = [self.ent_a, self.ent_b, self.hi_a, self.hi_b]
        if self.value_is_ref:
            refs.append(self.value)
        return refs

    def clear_ref(self, ref: int) -> "Capsule":
        out = replace(self)
        for field in ("ent_a", "ent_b", "hi_a", "hi_b"):
            if getattr(out, field) == ref:
                setattr(out, field, 0)
        if out.value_is_ref and out.value == ref:
            out.value = 0
        return out

    def pack(self) -> bytes:
        out = bytearray(CAPSULE_BYTES)
        out[0] = self.flags & 0xFF
        out[1] = self.relation & 0xFF
        vals = (
            self.topic,
            self.ent_a,
            self.ent_b,
            self.hi_a,
            self.hi_b,
            self.value,
        )
        off = 2
        for value in vals:
            out[off] = value & 0xFF
            out[off + 1] = (value >> 8) & 0xFF
            off += 2
        out[14] = self.importance & 0xFF
        out[15] = self.age & 0xFF
        return bytes(out)


@dataclass
class Descriptor:
    start: int
    length: int
    speaker: int
    dialogue: int
    capsules: tuple[Capsule, ...]


def protection(capsule: Capsule) -> int:
    if capsule.flags & (FLAG_CORRECTION | FLAG_UNRESOLVED):
        return 3
    src = source_class(capsule.flags)
    if src == 0:
        return 2
    if src == 1:
        return 1
    return 0


def retention_key(capsule: Capsule, index: int) -> tuple[int, ...]:
    return (
        protection(capsule),
        capsule.importance,
        -capsule.age,
        index,
    )


class SessionLiterals:
    def __init__(self) -> None:
        self.generations = [0] * LIT_SLOTS
        self.values: list[bytes | None] = [None] * LIT_SLOTS

    @staticmethod
    def make_ref(slot: int, generation: int) -> int:
        if not 0 <= slot < LIT_SLOTS:
            raise ValueError("session literal slot out of range")
        if not 1 <= generation <= 4095:
            raise ValueError("session literal generation out of range")
        return 0x8000 | (generation << 3) | slot

    @staticmethod
    def decode_ref(ref: int) -> tuple[int, int] | None:
        if (ref & 0x8000) == 0:
            return None
        return ref & 7, (ref >> 3) & 0x0FFF

    def live_ref(self, slot: int) -> int:
        generation = self.generations[slot]
        if generation == 0:
            return 0
        return self.make_ref(slot, generation)

    def resolve(self, ref: int) -> bytes | None:
        decoded = self.decode_ref(ref)
        if decoded is None:
            return None
        slot, generation = decoded
        if generation == 0:
            return None
        if self.generations[slot] != generation:
            return None
        return self.values[slot]

    def _slot_records(
        self,
        context: "ContextReference",
        slot: int,
    ) -> list[tuple[int, Capsule]]:
        out = []
        for index, capsule in context.record_items():
            for ref in capsule.refs():
                decoded = self.decode_ref(ref)
                if decoded is None:
                    continue
                if decoded[0] == slot and self.resolve(ref) is not None:
                    out.append((index, capsule))
                    break
        return out

    def allocate(
        self,
        data: bytes,
        context: "ContextReference",
    ) -> tuple[int, bool]:
        if not 1 <= len(data) <= LIT_LEN:
            raise ValueError("session literal length out of range")
        if any(byte < 32 or byte > 126 for byte in data):
            raise ValueError("session literal must be printable ASCII")
        folded = data.lower()
        for slot, value in enumerate(self.values):
            if value is not None and value.lower() == folded:
                return self.live_ref(slot), False

        free_by_reference = []
        for slot in range(LIT_SLOTS):
            if not self._slot_records(context, slot):
                free_by_reference.append(slot)
        if free_by_reference:
            victim = free_by_reference[0]
        else:
            candidates = []
            for slot in range(LIT_SLOTS):
                records = self._slot_records(context, slot)
                strongest = max(
                    retention_key(capsule, index)
                    for index, capsule in records
                )
                victim_key = (
                    strongest[0],
                    strongest[1],
                    strongest[2],
                    slot,
                )
                candidates.append((victim_key, slot))
            victim = min(candidates)[1]

        old_ref = self.live_ref(victim)
        if old_ref:
            context.invalidate_ref(old_ref)
        generation = self.generations[victim] + 1
        if generation == 0 or generation > 4095:
            generation = 1
        self.generations[victim] = generation
        self.values[victim] = bytes(data)
        return self.live_ref(victim), True


class ContextReference:
    def __init__(self) -> None:
        self.ring = bytearray(L0_BYTES)
        self.head = 0
        self.descriptors: list[Descriptor] = []
        self.l1: list[Capsule | None] = [None] * L1_CAP
        self.l2: list[Capsule | None] = [None] * L2_CAP
        self.literals = SessionLiterals()
        self.ai_compact = 0
        self.ai_l2evict = 0
        self.ai_litloss = 0
        self.next_dialogue = 1

    @property
    def l0bytes(self) -> int:
        return sum(desc.length for desc in self.descriptors)

    @property
    def l1count(self) -> int:
        return sum(capsule is not None for capsule in self.l1)

    @property
    def l2count(self) -> int:
        return sum(capsule is not None for capsule in self.l2)

    def record_items(self) -> list[tuple[int, Capsule]]:
        out = []
        for index, capsule in enumerate(self.l1):
            if capsule is not None:
                out.append((index, capsule))
        for index, capsule in enumerate(self.l2):
            if capsule is not None:
                out.append((L1_CAP + index, capsule))
        return out

    def invalidate_ref(self, ref: int) -> int:
        cleared = 0
        for records in (self.l1, self.l2):
            for index, capsule in enumerate(records):
                if capsule is None:
                    continue
                if ref in capsule.refs():
                    records[index] = capsule.clear_ref(ref)
                    cleared += 1
        self.ai_litloss += cleared
        return cleared

    def validate(self) -> None:
        if not 0 <= self.head < L0_BYTES:
            raise AssertionError("L0 head outside ring")
        if len(self.descriptors) > L0_DESCS:
            raise AssertionError("L0 descriptor overflow")
        if self.l0bytes > L0_BYTES:
            raise AssertionError("L0 byte overflow")
        for desc in self.descriptors:
            if not 0 <= desc.start < L0_BYTES:
                raise AssertionError("bad L0 descriptor start")
            if not 1 <= desc.length <= L0_BYTES:
                raise AssertionError("bad L0 descriptor length")
            if desc.speaker not in (0, 1):
                raise AssertionError("bad L0 speaker")
            if len(desc.capsules) > 2:
                raise AssertionError("too many capsules from one speaker turn")
        for records, expected in ((self.l1, L1_CAP), (self.l2, L2_CAP)):
            if len(records) != expected:
                raise AssertionError("semantic record capacity changed")
            for capsule in records:
                if capsule is not None and len(capsule.pack()) != CAPSULE_BYTES:
                    raise AssertionError("capsule wire size changed")
        if SESSION_LITERAL_BYTES != 272:
            raise AssertionError("session literal ledger changed")

    def _age_records(self) -> None:
        for records in (self.l1, self.l2):
            for index, capsule in enumerate(records):
                if capsule is not None and capsule.age < 255:
                    records[index] = replace(
                        capsule,
                        age=capsule.age + 1,
                    )

    def _merge_l2(self, capsule: Capsule) -> int:
        key = capsule.key()
        for index, current in enumerate(self.l2):
            if current is not None and current.key() == key:
                if capsule.age <= current.age:
                    self.l2[index] = replace(
                        capsule,
                        importance=max(
                            capsule.importance,
                            current.importance,
                        ),
                    )
                else:
                    self.l2[index] = replace(
                        current,
                        importance=max(
                            capsule.importance,
                            current.importance,
                        ),
                    )
                return index
        for index, current in enumerate(self.l2):
            if current is None:
                self.l2[index] = capsule
                return index
        victim = min(
            range(L2_CAP),
            key=lambda index: retention_key(self.l2[index], index),
        )
        self.l2[victim] = capsule
        self.ai_l2evict += 1
        return victim

    def _add_l1(self, capsule: Capsule) -> int:
        for index, current in enumerate(self.l1):
            if current is None:
                self.l1[index] = capsule
                return index
        victim = min(
            range(L1_CAP),
            key=lambda index: retention_key(self.l1[index], index),
        )
        self._merge_l2(self.l1[victim])
        self.ai_compact += 1
        self.l1[victim] = capsule
        return victim

    def _read_descriptor(self, desc: Descriptor) -> bytes:
        return bytes(
            self.ring[(desc.start + offset) % L0_BYTES]
            for offset in range(desc.length)
        )

    def _newer_user_turns(self, dialogue: int) -> int:
        return len({
            desc.dialogue
            for desc in self.descriptors
            if desc.dialogue > dialogue and desc.speaker == 0
        })

    def _evict_oldest_dialogue(self) -> None:
        if not self.descriptors:
            raise ValueError("cannot evict empty L0")
        dialogue = self.descriptors[0].dialogue
        newer = self._newer_user_turns(dialogue)
        initial_age = min(255, 1 + newer)
        while (
            self.descriptors
            and self.descriptors[0].dialogue == dialogue
        ):
            desc = self.descriptors.pop(0)
            self._read_descriptor(desc)
            for capsule in desc.capsules:
                self._add_l1(
                    replace(capsule, age=initial_age),
                )

    def _write_descriptor(
        self,
        data: bytes,
        speaker: int,
        dialogue: int,
        capsules: tuple[Capsule, ...],
    ) -> None:
        if not data or len(data) > L0_BYTES:
            raise ValueError("bad L0 speaker-turn length")
        if len(capsules) > 2:
            raise ValueError("too many capsules")
        start = self.head
        for offset, byte in enumerate(data):
            self.ring[(start + offset) % L0_BYTES] = byte
        self.head = (start + len(data)) % L0_BYTES
        self.descriptors.append(
            Descriptor(
                start,
                len(data),
                speaker,
                dialogue,
                capsules,
            ),
        )

    def _apply_pair(
        self,
        user: bytes,
        assistant: bytes,
        user_capsules: tuple[Capsule, ...],
        assistant_capsules: tuple[Capsule, ...],
    ) -> None:
        if not user or not assistant:
            raise ValueError("speaker turns must be nonempty")
        if len(user) + len(assistant) > L0_BYTES:
            raise ValueError("dialogue pair cannot fit L0")
        self._age_records()
        needed = len(user) + len(assistant)
        while (
            self.l0bytes + needed > L0_BYTES
            or len(self.descriptors) + 2 > L0_DESCS
        ):
            self._evict_oldest_dialogue()
        dialogue = self.next_dialogue
        self.next_dialogue += 1
        self._write_descriptor(
            user,
            0,
            dialogue,
            user_capsules,
        )
        self._write_descriptor(
            assistant,
            1,
            dialogue,
            assistant_capsules,
        )
        self.validate()

    def preflight_pair(
        self,
        user: bytes,
        assistant: bytes,
        user_capsules: tuple[Capsule, ...] = (),
        assistant_capsules: tuple[Capsule, ...] = (),
    ) -> "ContextReference":
        trial = deepcopy(self)
        trial._apply_pair(
            bytes(user),
            bytes(assistant),
            tuple(user_capsules),
            tuple(assistant_capsules),
        )
        return trial

    def commit_pair(
        self,
        user: bytes,
        assistant: bytes,
        user_capsules: tuple[Capsule, ...] = (),
        assistant_capsules: tuple[Capsule, ...] = (),
    ) -> None:
        trial = self.preflight_pair(
            user,
            assistant,
            user_capsules,
            assistant_capsules,
        )
        self.__dict__ = trial.__dict__

    def retrieve(
        self,
        topic: int,
        entity_refs: tuple[int, ...] = (),
        limit: int = 4,
    ) -> list[tuple[int, int, Capsule]]:
        if not 1 <= limit <= 4:
            raise ValueError("retrieval limit must be 1..4")
        requested = set(entity_refs)
        ranked = []
        for index, capsule in self.record_items():
            score = 0
            if capsule.topic == topic:
                score += 100
            refs = set(capsule.refs())
            score += 40 * len(requested & refs)
            if capsule.flags & FLAG_UNRESOLVED:
                score += 20
            if capsule.flags & FLAG_CORRECTION:
                score += 16
            score += capsule.importance
            score += max(0, 15 - min(capsule.age, 15))
            ranked.append((score, index, capsule))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[:limit]

    def snapshot(self) -> tuple:
        return (
            self.head,
            self.l0bytes,
            tuple(
                (
                    desc.start,
                    desc.length,
                    desc.speaker,
                    desc.dialogue,
                )
                for desc in self.descriptors
            ),
            tuple(
                capsule.pack() if capsule is not None else None
                for capsule in self.l1
            ),
            tuple(
                capsule.pack() if capsule is not None else None
                for capsule in self.l2
            ),
            tuple(self.literals.generations),
            tuple(self.literals.values),
            self.ai_compact,
            self.ai_l2evict,
            self.ai_litloss,
            self.next_dialogue,
        )
