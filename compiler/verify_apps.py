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
"""Verify the three shipped interactive C48 applications."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
SRC = SDK / "usr" / "src" / "apps"
BIN = SDK / "usr" / "bin" / "apps"
EXPECT_PATH = ROOT / "app_expectations.json"

sys.path.insert(0, str(ROOT))
from c48.compiler import compile_file
from c48.format import encode, read
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM

FONT = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")


class VerifyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerifyError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def compile_bytes(name: str) -> bytes:
    return encode(compile_file(SRC / f"{name}.c"))


def run_startup(name: str) -> ZXScreen:
    program = read(BIN / f"{name}.c48b")
    screen = ZXScreen(FONT)
    vm = C48VM(
        program,
        screen,
        argv=[name, "verify"],
        max_steps=10000000,
    )
    status = vm.run()
    if status != 0:
        fail(f"{name}: runtime status {status}")
    return screen


def main() -> int:
    expect = json.loads(EXPECT_PATH.read_text(encoding="ascii"))
    if expect.get("schema") != 1:
        fail("app expectation schema mismatch")
    names = set(expect.get("apps", {}))
    if names != {"sheet48", "write48", "wire3d"}:
        fail("app expectation member set mismatch")
    source_names = {p.stem for p in SRC.glob("*.c")}
    binary_names = {p.stem for p in BIN.glob("*.c48b")}
    if source_names != names:
        fail("app source member set mismatch")
    if binary_names != names:
        fail("app binary member set mismatch")
    if sha(SRC / "appapi.h") != expect["helper_sha256"]:
        fail("appapi.h hash mismatch")
    for name, item in expect["apps"].items():
        source = SRC / f"{name}.c"
        frozen = BIN / f"{name}.c48b"
        if sha(source) != item["source_sha256"]:
            fail(f"{name}: source hash mismatch")
        if sha(frozen) != item["binary_sha256"]:
            fail(f"{name}: binary hash mismatch")
        if compile_bytes(name) != frozen.read_bytes():
            fail(f"{name}: deterministic rebuild mismatch")
        screen = run_startup(name)
        if sha_bytes(screen.bytes()) != item["screen_sha256"]:
            fail(f"{name}: startup screen hash mismatch")
        print(f"APP VERIFY: {name} PASS", flush=True)
    print("APP VERIFY PASS: 3 apps", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerifyError as exc:
        print(f"APP VERIFY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
