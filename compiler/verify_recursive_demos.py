#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file.
#
# Attribution required: SANYALnet Labs.
# See root LICENSE file for full terms.
# ============================================================================
"""Deterministic proof for the recursive demo pair."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

# Release 1.0.2 certification touch.

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
FONT = ROOT / "assets" / "SANYALnet-Labs-4x8-font-FINAL.bin"

EXPECTED = {
    "hanoi": {
        "binary": "0592065adba7cf2b651f0015a85b785850d8444230e0a98d5164bfec911015bf",
        "screen": "db087d44c1d01984de46ebaf83452b27d8a03f7fabd2f8612baf62ac89be69ac",
    },
    "queens8": {
        "binary": "07c1c3a17e5692b56dbb7921e796bb770d3568dc1f7535872e27307ea39e5520",
        "screen": "568f45c848f82a318c4942f28227015fd9625c3a9cfbe56bfe254ab1b7fa3efe",
    },
}

from c48.screen import Font4x8, ZXScreen, attr_offset, bitmap_offset


def fail(message: str) -> None:
    raise SystemExit("RECURSIVE DEMO VERIFY FAIL: " + message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=360,
    )
    return cp


def compile_one(source: Path, output: Path) -> None:
    cp = run(
        [
            sys.executable,
            "-B",
            str(ROOT / "c48.py"),
            str(source),
            "-o",
            str(output),
        ]
    )
    if cp.returncode != 0:
        fail(source.name + ": compile failed: " + cp.stderr.strip())


def check_source(name: str, source: Path) -> None:
    text = source.read_text(encoding="ascii")
    lines = text.splitlines()
    wide = [
        str(index)
        for index, line in enumerate(lines, 1)
        if len(line) > 64
    ]
    if wide:
        fail(name + ": source exceeds 64 columns at " + ",".join(wide))
    if "cls(" in text or "border(" in text:
        fail(name + ": whole-screen operation is present")
    if name == "hanoi":
        required = (
            "#define H_LEFT_GCOL_MAX 15",
            "#define H_LEFT_TCOL_MAX 31",
            "h_guard_fail",
            "h_inv_fail",
            "h_move_count != 127",
            "h_maximum_depth != 7",
        )
    else:
        required = (
            "#define Q_GCOL_MIN 16",
            "#define Q_TCOL_MIN 32",
            "q_guard_fail",
            "q_inv_fail",
            "q_tests != 876",
            "q_backtracks != 105",
            "q_maximum_depth != 8",
        )
    for marker in required:
        if marker not in text:
            fail(name + ": required proof marker missing: " + marker)


def blank_screen() -> bytes:
    return ZXScreen(Font4x8.load(FONT)).bytes()


def check_half(name: str, screen: bytes) -> None:
    if len(screen) != 6912:
        fail(name + ": screen dump is not 6912 bytes")
    blank = blank_screen()
    if name == "hanoi":
        unowned = range(128, 256, 8)
        owned = range(0, 128, 8)
    else:
        unowned = range(0, 128, 8)
        owned = range(128, 256, 8)
    for y in range(192):
        for x in unowned:
            pos = bitmap_offset(x, y)
            if screen[pos] != blank[pos]:
                fail(name + ": bitmap write escaped owned half")
    for y in range(0, 192, 8):
        for x in unowned:
            pos = attr_offset(x, y)
            if screen[pos] != blank[pos]:
                fail(name + ": attribute write escaped owned half")
    changed = 0
    for y in range(192):
        for x in owned:
            pos = bitmap_offset(x, y)
            if screen[pos] != blank[pos]:
                changed += 1
    for y in range(0, 192, 8):
        for x in owned:
            pos = attr_offset(x, y)
            if screen[pos] != blank[pos]:
                changed += 1
    if changed < 40:
        fail(name + ": owned half did not render expected content")


def run_program(
    name: str,
    program: Path,
    screen: Path,
    *,
    fast: bool,
    frame: Path | None = None,
) -> None:
    command = [
        sys.executable,
        "-B",
        str(ROOT / "c48run.py"),
        "--headless",
        "--time-quota",
        "330",
        "--dump-screen",
        str(screen),
    ]
    if frame is not None:
        command.extend(["--frame-ppm", str(frame)])
    command.extend(["--", str(program)])
    if fast:
        command.append("--verify")
    cp = run(command)
    if cp.returncode != 0:
        fail(name + ": runtime failed: " + cp.stderr.strip())


def verify_case(
    name: str,
    root: Path,
    evidence: Path | None,
) -> tuple[str, str]:
    source = SDK / "usr" / "src" / "demos" / (name + ".c")
    frozen = SDK / "usr" / "bin" / "demos" / (name + ".c48b")
    if not source.is_file() or not frozen.is_file():
        fail(name + ": tracked source/binary pair is missing")
    check_source(name, source)

    first = root / (name + "-first.c48b")
    second = root / (name + "-second.c48b")
    compile_one(source, first)
    compile_one(source, second)
    if first.read_bytes() != second.read_bytes():
        fail(name + ": two clean rebuilds differ")
    if first.read_bytes() != frozen.read_bytes():
        fail(name + ": tracked binary differs from clean rebuild")

    fast_screen = root / (name + "-fast.scr")
    run_program(name, frozen, fast_screen, fast=True)
    fast_bytes = fast_screen.read_bytes()
    check_half(name, fast_bytes)
    binary_hash = sha(frozen)
    screen_hash = sha(fast_screen)
    if binary_hash != EXPECTED[name]["binary"]:
        fail(name + ": frozen binary hash changed")
    if screen_hash != EXPECTED[name]["screen"]:
        fail(name + ": frozen final screen changed")

    image = SDK / "docs" / "images" / "demos" / (name + ".png")
    if not image.is_file():
        fail(name + ": checked-in screenshot is missing")

    if evidence is not None:
        evidence.mkdir(parents=True, exist_ok=True)
        saved_fast = evidence / (name + "-fast.scr")
        shutil.copyfile(fast_screen, saved_fast)
        normal_screen = evidence / (name + "-normal.scr")
        frame = evidence / (name + "-normal.ppm")
        run_program(
            name,
            frozen,
            normal_screen,
            fast=False,
            frame=frame,
        )
        if normal_screen.read_bytes() != fast_bytes:
            fail(name + ": normal and fast final screens differ")
        check_half(name, normal_screen.read_bytes())

    return binary_hash, screen_hash


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--normal-evidence",
        type=Path,
        help="also run normal timing and retain final screen/frame files",
    )
    ns = ap.parse_args(argv)
    evidence = ns.normal_evidence
    if evidence is not None:
        evidence = evidence.resolve()
    with tempfile.TemporaryDirectory(prefix="c48-recursive-") as td:
        root = Path(td)
        results = {}
        for name in ("hanoi", "queens8"):
            results[name] = verify_case(name, root, evidence)
    for name in ("hanoi", "queens8"):
        binary_hash, screen_hash = results[name]
        print(
            "RECURSIVE DEMO VERIFY: "
            + name
            + " binary="
            + binary_hash
            + " screen="
            + screen_hash
        )
    print("RECURSIVE DEMO VERIFY PASS: 2 deterministic recursive demos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
