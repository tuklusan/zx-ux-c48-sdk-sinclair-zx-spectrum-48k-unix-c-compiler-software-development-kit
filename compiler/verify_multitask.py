#!/usr/bin/env python3
# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Independent cooperative runtime proof using the frozen recursive demo pair."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
sys.path.insert(0, str(ROOT))

from c48.format import read
from c48.multitask import CooperativeSession
from c48.romvm import RomMathVM
from c48.screen import Font4x8, ZXScreen, attr_offset, bitmap_offset

FONT = Font4x8.load(ROOT / "assets" / "SANYALnet-Labs-4x8-font-FINAL.bin")
EXPECTED_BINARY = {
    "hanoi": "0592065adba7cf2b651f0015a85b785850d8444230e0a98d5164bfec911015bf",
    "queens8": "07c1c3a17e5692b56dbb7921e796bb770d3568dc1f7535872e27307ea39e5520",
}
EXPECTED_SINGLE_SCREEN = {
    "hanoi": "db087d44c1d01984de46ebaf83452b27d8a03f7fabd2f8612baf62ac89be69ac",
    "queens8": "568f45c848f82a318c4942f28227015fd9625c3a9cfbe56bfe254ab1b7fa3efe",
}


def fail(message: str) -> None:
    raise SystemExit("MULTITASK VERIFY FAIL: " + message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TickSource:
    def __init__(self) -> None:
        self.value = 100

    def now(self) -> int:
        return self.value

    def advance_to(self, deadline: int | None) -> None:
        if deadline is None:
            self.value += 1
        elif deadline > self.value:
            self.value = deadline
        else:
            self.value += 1


def run_single(name: str, program: dict) -> bytes:
    screen = ZXScreen(FONT)
    status = RomMathVM(
        program,
        screen,
        argv=[name + ".c48b", "--verify"],
    ).run()
    if status != 0:
        fail(name + ": established single-process path returned nonzero")
    data = screen.bytes()
    if digest(data) != EXPECTED_SINGLE_SCREEN[name]:
        fail(name + ": established single-process final screen changed")
    return data


def merge_expected(left: bytes, right: bytes) -> bytes:
    merged = bytearray(ZXScreen(FONT).bytes())
    for y in range(192):
        for x in range(0, 128, 8):
            pos = bitmap_offset(x, y)
            merged[pos] = left[pos]
        for x in range(128, 256, 8):
            pos = bitmap_offset(x, y)
            merged[pos] = right[pos]
    for y in range(0, 192, 8):
        for x in range(0, 128, 8):
            pos = attr_offset(x, y)
            merged[pos] = left[pos]
        for x in range(128, 256, 8):
            pos = attr_offset(x, y)
            merged[pos] = right[pos]
    return bytes(merged)


def run_pair(programs: list[dict]) -> tuple[int, bytes, tuple[tuple[object, ...], ...], list[int | None]]:
    ticks = TickSource()
    screen = ZXScreen(FONT)
    session = CooperativeSession(
        programs,
        ["usr/bin/demos/hanoi.c48b", "usr/bin/demos/queens8.c48b"],
        screen,
        tick_provider=ticks.now,
        idle_wait=ticks.advance_to,
        max_steps=4000000,
    )
    status = session.run()
    statuses = [session.descriptors[pid].exit_status for pid in (2, 3)]
    if status != 0:
        details = [
            (
                pid,
                session.descriptors[pid].state,
                session.descriptors[pid].exit_status,
                session.descriptors[pid].cancelled,
                session.descriptors[pid].error,
            )
            for pid in (2, 3)
        ]
        fail(
            "cooperative pair stopped before proof completion: "
            + f"status={status} steps={session.budget.steps} "
            + f"details={details!r}"
        )
    return status, screen.bytes(), tuple(session.trace), statuses


def main() -> int:
    paths = {
        name: SDK / "usr" / "bin" / "demos" / (name + ".c48b")
        for name in ("hanoi", "queens8")
    }
    for name, path in paths.items():
        if not path.is_file():
            fail(name + ": frozen binary is missing")
        if digest(path.read_bytes()) != EXPECTED_BINARY[name]:
            fail(name + ": frozen binary hash changed")

    programs = [read(paths["hanoi"]), read(paths["queens8"])]
    expected = merge_expected(
        run_single("hanoi", programs[0]),
        run_single("queens8", programs[1]),
    )

    first = run_pair(programs)
    if first[0] != 0:
        fail("cooperative pair returned nonzero")
    if first[3] != [0, 0]:
        fail("one or more direct processes did not terminate normally")
    if first[1] != expected:
        fail("shared final screen differs from independent half-screen merge")

    yields = [event[1] for event in first[2] if event[0] == "yield"]
    if 2 not in yields or 3 not in yields:
        fail("both recursive processes must reach cooperative yield boundaries")
    sleepers = [event[1] for event in first[2] if event[0] == "sleep"]
    if 2 not in sleepers or 3 not in sleepers:
        fail("both recursive processes must reach positive-sleep boundaries")
    wakes = [event[1] for event in first[2] if event[0] == "wake"]
    if 2 not in wakes or 3 not in wakes:
        fail("both recursive processes must resume after positive sleep")
    dispatches = [event[1] for event in first[2] if event[0] == "dispatch"]
    if 2 not in dispatches or 3 not in dispatches:
        fail("both recursive processes must be dispatched")

    print(
        "MULTITASK VERIFY PASS: recursive pair"
        + " screen="
        + digest(first[1])
        + " events="
        + str(len(first[2]))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
