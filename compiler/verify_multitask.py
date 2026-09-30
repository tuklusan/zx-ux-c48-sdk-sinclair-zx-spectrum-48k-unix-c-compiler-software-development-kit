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
from c48.screen import Font4x8, ZXScreen, attr_offset, bitmap_offset

FONT = Font4x8.load(ROOT / "assets" / "SANYALnet-Labs-4x8-font-FINAL.bin")
EXPECTED_BINARY = {
    "hanoi": "0592065adba7cf2b651f0015a85b785850d8444230e0a98d5164bfec911015bf",
    "queens8": "07c1c3a17e5692b56dbb7921e796bb770d3568dc1f7535872e27307ea39e5520",
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


def run_pair(programs: list[dict]) -> tuple[int, bytes, tuple[tuple[object, ...], ...], list[int | None], int]:
    ticks = TickSource()
    screen = ZXScreen(FONT)
    session = CooperativeSession(
        programs,
        ["usr/bin/demos/hanoi.c48b", "usr/bin/demos/queens8.c48b"],
        screen,
        tick_provider=ticks.now,
        idle_wait=ticks.advance_to,
        # Aggregate guard for two complete recursive workloads in one session.
        max_steps=16000000,
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
    return status, screen.bytes(), tuple(session.trace), statuses, session.budget.steps


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
    first = run_pair(programs)
    if first[0] != 0:
        fail("cooperative pair returned nonzero")
    if first[3] != [0, 0]:
        fail("one or more direct processes did not terminate normally")
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

    blank = ZXScreen(FONT).bytes()
    changed = [0, 0]
    for y in range(192):
        for half, columns in enumerate((range(0, 128, 8), range(128, 256, 8))):
            for x in columns:
                pos = bitmap_offset(x, y)
                if first[1][pos] != blank[pos]:
                    changed[half] += 1
    for y in range(0, 192, 8):
        for half, columns in enumerate((range(0, 128, 8), range(128, 256, 8))):
            for x in columns:
                pos = attr_offset(x, y)
                if first[1][pos] != blank[pos]:
                    changed[half] += 1
    if min(changed) < 40:
        fail("one recursive final screen half did not retain substantial output")

    print(
        "MULTITASK VERIFY PASS: recursive pair"
        + " screen="
        + digest(first[1])
        + " events="
        + str(len(first[2]))
        + " steps="
        + str(first[4])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
