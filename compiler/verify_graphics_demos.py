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
"""Verify the 21 deterministic C48 graphics demonstrations."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import time
import zlib

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
SRC = SDK / "usr" / "src" / "demos"
BIN = SDK / "usr" / "bin" / "demos"
IMG = SDK / "docs" / "images" / "demos"
EXPECT_PATH = ROOT / "graphics_demo_expectations.json"

sys.path.insert(0, str(ROOT))
from c48.compiler import compile_file
from c48.format import encode
from c48.screen import Font4x8, SCREEN_SIZE, ZXScreen

FONT = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")


def host_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


class VerifyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerifyError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_expect() -> dict:
    return json.loads(EXPECT_PATH.read_text(encoding="ascii"))


def png_bytes(rgb: bytes, scale: int = 3) -> bytes:
    width = 256
    height = 192
    if len(rgb) != width * height * 3:
        fail("RGB screen length mismatch")
    raw = bytearray()
    for y in range(height):
        row = bytearray()
        off = y * width * 3
        for x in range(width):
            p = rgb[off + x * 3:off + x * 3 + 3]
            row.extend(p * scale)
        scan = b"\0" + bytes(row)
        for _ in range(scale):
            raw.extend(scan)

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)

    head = struct.pack(
        ">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", head)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def compile_bytes(name: str) -> bytes:
    return encode(compile_file(SRC / f"{name}.c"))


def run_demo(name: str, frames: int, time_quota: float) -> ZXScreen:
    with tempfile.TemporaryDirectory(prefix=f"c48-graphics-{name}-") as td:
        temp = Path(td)
        program_token = name
        (temp / program_token).write_bytes(
            (BIN / f"{name}.c48b").read_bytes()
        )
        screen_path = temp / f"{name}.scr"
        cmd = [
            sys.executable,
            "-B",
            str(ROOT / "c48run.py"),
            "--headless",
            "--time-quota",
            f"{time_quota:g}",
            "--dump-screen",
            screen_path.name,
            program_token,
            str(frames),
        ]
        host_timeout = time_quota + 5.0
        try:
            cp = subprocess.run(
                cmd,
                cwd=temp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=host_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            fail(
                f"{name}: {frames} frame(s): host timeout after "
                f"{host_timeout:g}s (VM quota {time_quota:g}s)"
            )
            raise AssertionError("unreachable") from exc
        if cp.returncode != 0:
            detail = (cp.stderr or cp.stdout).strip()
            fail(
                f"{name}: {frames} frame(s): runtime status "
                f"{cp.returncode}: {detail}"
            )
        if not screen_path.is_file():
            fail(f"{name}: runtime did not emit a screen dump")
        screen_data = screen_path.read_bytes()
        if len(screen_data) != SCREEN_SIZE:
            fail(
                f"{name}: screen dump size {len(screen_data)} "
                f"!= {SCREEN_SIZE}"
            )
    screen = ZXScreen(FONT)
    screen.mem[:] = screen_data
    return screen


def screen_metrics(screen: ZXScreen) -> tuple[int, int]:
    lit = sum(value.bit_count() for value in screen.mem[:6144])
    attrs = len(set(screen.mem[6144:]))
    return lit, attrs


def check_members(expect: dict) -> None:
    names = set(expect["demos"])
    src_names = {p.stem for p in SRC.glob("*.c")}
    bin_names = {p.stem for p in BIN.glob("*.c48b")}
    img_files = {p.name for p in IMG.glob("*.png")}
    expected_img_files = {f"{name}.png" for name in names} | {"contact-sheet.png"}
    if src_names != names:
        fail("graphics demo source member set mismatch")
    if bin_names != names:
        fail("graphics demo binary member set mismatch")
    if img_files != expected_img_files:
        fail("graphics demo image member set mismatch")
    if sha(SRC / "demoapi.h") != expect["helper_sha256"]:
        fail("demoapi.h hash mismatch")


def check_static_one(name: str, exp: dict) -> bytes:
    source = SRC / f"{name}.c"
    frozen = BIN / f"{name}.c48b"
    image = IMG / f"{name}.png"
    if sha(source) != exp["source_sha256"]:
        fail(f"{name}: source hash mismatch")
    if sha(frozen) != exp["binary_sha256"]:
        fail(f"{name}: binary hash mismatch")
    rebuilt = compile_bytes(name)
    if rebuilt != frozen.read_bytes():
        fail(f"{name}: deterministic rebuild mismatch")
    if sha(image) != exp["png_sha256"]:
        fail(f"{name}: checked-in PNG hash mismatch")
    return rebuilt


def check_one(
    name: str,
    exp: dict,
    *,
    stress: bool,
    evidence_dir: Path | None,
    time_quota: float,
) -> dict:
    rebuilt = check_static_one(name, exp)
    image = IMG / f"{name}.png"

    first = run_demo(name, 1, time_quota)
    first_hash = sha_bytes(first.bytes())
    if first_hash != exp["first_screen_sha256"]:
        fail(f"{name}: first-frame screen hash mismatch")

    screen = run_demo(name, int(exp["frames"]), time_quota)
    screen_data = screen.bytes()
    screen_hash = sha_bytes(screen_data)
    if screen_hash != exp["screen_sha256"]:
        fail(f"{name}: canonical screen hash mismatch")
    if screen_hash == first_hash:
        fail(f"{name}: animation did not change the screen")

    png = png_bytes(screen.render_rgb())
    if sha_bytes(png) != exp["png_sha256"]:
        fail(f"{name}: rendered PNG mismatch")
    if png != image.read_bytes():
        fail(f"{name}: checked-in screenshot mismatch")

    lit, attrs = screen_metrics(screen)
    if lit != int(exp["lit_pixels"]):
        fail(f"{name}: lit-pixel metric mismatch")
    if attrs != int(exp["attribute_values"]):
        fail(f"{name}: attribute metric mismatch")
    if lit < 80 or attrs < 1:
        fail(f"{name}: visual complexity floor not met")

    stress_seconds = 0.0
    if stress:
        started = time.monotonic()
        run_demo(name, int(exp["stress_frames"]), time_quota)
        stress_seconds = time.monotonic() - started

    evidence = {
        "demo": name,
        "runner": exp["runner"],
        "architecture": host_arch(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_sha256": exp["source_sha256"],
        "binary_sha256": exp["binary_sha256"],
        "build_sha256": sha_bytes(rebuilt),
        "screen_sha256": screen_hash,
        "png_sha256": exp["png_sha256"],
        "frames": exp["frames"],
        "stress_frames": exp["stress_frames"],
        "stress_seconds": round(stress_seconds, 3),
        "time_quota_seconds": time_quota,
        "lit_pixels": lit,
        "attribute_values": attrs,
        "status": "PASS",
    }
    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{name}.c48b").write_bytes(rebuilt)
        (evidence_dir / f"{name}.scr").write_bytes(screen_data)
        (evidence_dir / f"{name}.png").write_bytes(png)
        (evidence_dir / f"{name}.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
    return evidence


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify C48 graphics demo corpus"
    )
    ap.add_argument("--demo")
    ap.add_argument("--runner")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--evidence-dir", type=Path)
    ap.add_argument(
        "--time-quota",
        type=float,
        default=45.0,
        metavar="SECONDS",
        help=(
            "per-C48B wall-clock runtime quota (default: 45; "
            "the graphics CI matrix uses the same 45-second quota)"
        ),
    )
    ns = ap.parse_args(argv)
    if not math.isfinite(ns.time_quota) or ns.time_quota <= 0.0:
        ap.error("--time-quota must be a finite positive number")

    expect = load_expect()
    if expect.get("schema") != 1:
        fail("graphics demo expectation schema mismatch")
    if len(expect.get("demos", {})) != 21:
        fail("graphics demo count is not exactly 21")
    check_members(expect)

    if ns.static:
        for name, exp in expect["demos"].items():
            check_static_one(name, exp)
        print("GRAPHICS DEMO STATIC PASS: 21 demos", flush=True)
        return 0

    if ns.demo:
        if ns.demo not in expect["demos"]:
            fail(f"unknown graphics demo: {ns.demo}")
        exp = expect["demos"][ns.demo]
        if ns.runner and ns.runner != exp["runner"]:
            fail(
                f"{ns.demo}: runner mismatch: "
                f"{ns.runner!r} != {exp['runner']!r}"
            )
        if ns.runner and host_arch() != exp["architecture"]:
            fail(
                f"{ns.demo}: architecture mismatch: "
                f"{host_arch()!r} != {exp['architecture']!r}"
            )
        check_one(
            ns.demo,
            exp,
            stress=True,
            evidence_dir=ns.evidence_dir,
            time_quota=ns.time_quota,
        )
        print(f"GRAPHICS DEMO PASS: {ns.demo}")
        return 0

    if not ns.release:
        ap.error("choose --demo NAME, --static, or --release")

    for name, exp in expect["demos"].items():
        check_one(
            name,
            exp,
            stress=False,
            evidence_dir=None,
            time_quota=ns.time_quota,
        )
        print(f"GRAPHICS DEMO: {name} PASS", flush=True)
    print("GRAPHICS DEMO VERIFY PASS: 21 demos", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerifyError as exc:
        print(f"GRAPHICS DEMO VERIFY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
