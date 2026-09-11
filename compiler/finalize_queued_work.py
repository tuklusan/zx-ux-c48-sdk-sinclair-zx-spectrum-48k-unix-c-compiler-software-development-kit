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
"""One-shot disk builder for the queued C48 SDK application work."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
sys.path.insert(0, str(ROOT))

from c48.compiler import compile_file
from c48.format import encode, read
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM
from verify_graphics_demos import png_bytes


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"missing patch anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def patch_permanent_files() -> None:
    replace(
        ROOT / "c48" / "gui.py",
        '# Attribution is required: "Based on original work by Supratim\n'
        '# Sanyal of SANYALnet Labs." See LICENSE for full terms, warranty disclaimer,\n',
        '# Attribution is required: "Based on original work by Supratim Sanyal of\n'
        '# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,\n',
    )

    p = ROOT / "verify_graphics_demos.py"
    text = p.read_text(encoding="utf-8")
    substitutions = (
        (
            '"""Verify the 21 deterministic C48 graphics demonstrations."""',
            '"""Verify the 22 deterministic C48 graphics demonstrations."""',
        ),
        ('if len(expect.get("demos", {})) != 21:',
         'if len(expect.get("demos", {})) != 22:'),
        ('graphics demo count is not exactly 21',
         'graphics demo count is not exactly 22'),
        ('GRAPHICS DEMO STATIC PASS: 21 demos',
         'GRAPHICS DEMO STATIC PASS: 22 demos'),
        ('GRAPHICS DEMO VERIFY PASS: 21 demos',
         'GRAPHICS DEMO VERIFY PASS: 22 demos'),
    )
    for old, new in substitutions:
        if old not in text:
            raise RuntimeError(f"missing graphics verifier anchor: {old!r}")
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8", newline="\n")

    release = ROOT / "verify_release.py"
    replace(
        release,
        '        "compiler/verify_graphics_demos.py",\n',
        '        "compiler/verify_graphics_demos.py",\n'
        '        "compiler/verify_apps.py",\n'
        '        "compiler/app_expectations.json",\n'
        '        "compiler/tests/test_gui_framebuffer.py",\n',
    )
    replace(
        release,
        '        "doc/GRAPHICS-DEMOS.md",\n',
        '        "doc/GRAPHICS-DEMOS.md", "doc/APPS.md",\n',
    )
    replace(
        release,
        '        "usr/src/demos/demoapi.h",\n',
        '        "usr/src/demos/demoapi.h",\n'
        '        "usr/src/apps/appapi.h",\n'
        '        "usr/src/apps/sheet48.c",\n'
        '        "usr/src/apps/write48.c",\n'
        '        "usr/src/apps/wire3d.c",\n',
    )
    replace(
        release,
        '    if "GRAPHICS DEMO STATIC PASS: 21 demos" not in cp.stdout:\n',
        '    if "GRAPHICS DEMO STATIC PASS: 22 demos" not in cp.stdout:\n',
    )
    text = release.read_text(encoding="utf-8")
    anchor = "\ndef check_security_programs() -> None:\n"
    if anchor not in text:
        raise RuntimeError("missing check_security_programs anchor")
    app_check = '''\ndef check_apps() -> None:\n    cp = run(\n        [sys.executable, "-B", str(ROOT / "verify_apps.py")],\n        timeout=120,\n    )\n    if cp.returncode != 0:\n        sys.stderr.write(cp.stdout + cp.stderr)\n        fail("application corpus verification failed")\n    if "APP VERIFY PASS: 3 apps" not in cp.stdout:\n        fail("application verifier completion marker missing")\n\n\n'''
    text = text.replace(anchor, "\n" + app_check + anchor.lstrip("\n"), 1)
    tuple_anchor = '        ("graphics demo corpus", check_graphics_demos),\n'
    if tuple_anchor not in text:
        raise RuntimeError("missing graphics tuple anchor")
    text = text.replace(
        tuple_anchor,
        tuple_anchor + '        ("application corpus", check_apps),\n',
        1,
    )
    release.write_text(text, encoding="utf-8", newline="\n")

    doc = SDK / "doc" / "GRAPHICS-DEMOS.md"
    text = doc.read_text(encoding="utf-8")
    doc_anchors = (
        (
            "The suite contains 21 clean-room C48 graphics and animation programs.",
            "The suite contains 22 clean-room C48 graphics and animation programs.",
        ),
        (
            "one demo to each of 21 independent GitHub-hosted jobs: seven Ubuntu,\n"
            "seven Windows, and seven macOS.",
            "one demo to each of 22 independent GitHub-hosted jobs: eight Ubuntu,\n"
            "seven Windows, and seven macOS.",
        ),
    )
    for old, new in doc_anchors:
        if old not in text:
            raise RuntimeError(f"missing graphics doc anchor: {old!r}")
        text = text.replace(old, new)
    text += (
        "\n22. **UDG Walker** (`spriteanim.c`) - canonical frame 12, "
        "stress 36, `ubuntu-latest`.\n"
    )
    doc.write_text(text, encoding="utf-8", newline="\n")


def build_apps(font: Font4x8) -> None:
    source_root = SDK / "usr" / "src" / "apps"
    binary_root = SDK / "usr" / "bin" / "apps"
    binary_root.mkdir(parents=True, exist_ok=True)
    expect = {
        "schema": 1,
        "helper_sha256": sha(source_root / "appapi.h"),
        "apps": {},
    }
    for name in ("sheet48", "write48", "wire3d"):
        source = source_root / f"{name}.c"
        binary = encode(compile_file(source))
        frozen = binary_root / f"{name}.c48b"
        frozen.write_bytes(binary)
        screen = ZXScreen(font)
        vm = C48VM(
            read(frozen),
            screen,
            argv=[name, "verify"],
            max_steps=10000000,
        )
        status = vm.run()
        if status != 0:
            raise RuntimeError(f"{name}: startup status {status}")
        expect["apps"][name] = {
            "source_sha256": sha(source),
            "binary_sha256": sha_bytes(binary),
            "screen_sha256": sha_bytes(screen.bytes()),
        }
    (ROOT / "app_expectations.json").write_text(
        json.dumps(expect, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )


def build_sprite_demo(font: Font4x8) -> None:
    name = "spriteanim"
    source = SDK / "usr" / "src" / "demos" / f"{name}.c"
    frozen = SDK / "usr" / "bin" / "demos" / f"{name}.c48b"
    binary = encode(compile_file(source))
    frozen.write_bytes(binary)

    def run_demo(frames: int) -> ZXScreen:
        screen = ZXScreen(font)
        vm = C48VM(
            read(frozen),
            screen,
            argv=[name, str(frames)],
            max_steps=10000000,
        )
        status = vm.run()
        if status != 0:
            raise RuntimeError(f"{name}: runtime status {status}")
        return screen

    first = run_demo(1)
    final = run_demo(12)
    png = png_bytes(final.render_rgb())
    image = SDK / "doc" / "images" / "demos" / f"{name}.png"
    image.write_bytes(png)
    lit = sum(value.bit_count() for value in final.mem[:6144])
    attrs = len(set(final.mem[6144:]))
    expect_path = ROOT / "graphics_demo_expectations.json"
    expect = json.loads(expect_path.read_text(encoding="ascii"))
    expect["demos"][name] = {
        "title": "UDG Walker",
        "runner": "ubuntu-latest",
        "frames": 12,
        "stress_frames": 36,
        "source_sha256": sha(source),
        "binary_sha256": sha_bytes(binary),
        "first_screen_sha256": sha_bytes(first.bytes()),
        "screen_sha256": sha_bytes(final.bytes()),
        "png_sha256": sha_bytes(png),
        "lit_pixels": lit,
        "attribute_values": attrs,
    }
    expect_path.write_text(
        json.dumps(expect, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )


def update_test_count() -> None:
    cp = subprocess.run(
        [sys.executable, "-B", str(ROOT / "run_tests.py")],
        cwd=SDK,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = cp.stdout + cp.stderr
    sys.stdout.write(output)
    if cp.returncode != 0:
        raise RuntimeError("unit tests failed during finalization")
    match = re.search(r"Ran (\d+) tests?", output)
    if not match:
        raise RuntimeError("unit test count was not reported")
    path = ROOT / "release_expectations.json"
    data = json.loads(path.read_text(encoding="ascii"))
    data["test_count"] = int(match.group(1))
    path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )


def main() -> int:
    patch_permanent_files()
    font = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")
    build_apps(font)
    build_sprite_demo(font)
    update_test_count()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
