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
"""Assemble the verified 21-runner graphics artifacts without workflow writes."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
SDK = Path(__file__).resolve().parents[1]
CONFIG = [
    ("goblet", "ubuntu-latest", 2, 4, "Crystal Goblet"),
    ("tunnel", "windows-latest", 2, 8, "Infinity Tunnel"),
    ("city", "ubuntu-latest", 2, 4, "Vector Metropolis"),
    ("terrain", "windows-latest", 2, 4, "Mountain Flight"),
    ("ocean", "macos-latest", 2, 4, "Ocean Grid"),
    ("torus", "ubuntu-latest", 2, 4, "Torus Reactor"),
    ("mobius", "windows-latest", 2, 4, "Mobius Flight"),
    ("morph3d", "macos-latest", 2, 4, "Polyhedron Morph"),
    ("warp", "ubuntu-latest", 2, 8, "Warp Drive"),
    ("galaxy", "windows-latest", 2, 6, "Spiral Galaxy"),
    ("orrery", "macos-latest", 2, 4, "Clockwork Orrery"),
    ("firework", "ubuntu-latest", 2, 8, "Firework Night"),
    ("sprites", "windows-latest", 2, 6, "Sprite Storm"),
    ("plasma", "macos-latest", 2, 4, "Spectrum Plasma"),
    ("kaleido", "ubuntu-latest", 2, 4, "Kaleidoscope"),
    ("moire", "windows-latest", 2, 4, "Moire Engine"),
    ("mandel", "ubuntu-latest", 2, 3, "Mandelbrot Dive"),
    ("julia", "windows-latest", 2, 3, "Julia Ballet"),
    ("forest", "macos-latest", 2, 4, "Fractal Forest"),
    ("raymaze", "macos-latest", 2, 4, "Raycast Labyrinth"),
    ("showcase", "macos-latest", 2, 8, "C48 Grand Finale"),
]


def load_bootstrap():
    path = SDK / ".github" / "bootstrap_graphics_demos.py"
    spec = importlib.util.spec_from_file_location("graphics_bootstrap", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load bootstrap helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def artifact_fragments(root: Path, names: set[str]) -> dict:
    found = {}
    for path in root.rglob("*.json"):
        if path.stem not in names:
            continue
        if path.stem in found:
            raise SystemExit(f"duplicate fragment: {path.stem}")
        found[path.stem] = (
            path,
            json.loads(path.read_text(encoding="ascii")),
        )
    if set(found) != names:
        raise SystemExit(
            f"fragment set mismatch: missing={sorted(names - set(found))}"
        )
    return found


def assemble_artifacts(bg, found: dict) -> dict:
    bindir = SDK / "dev" / "bin" / "demos"
    imgdir = SDK / "doc" / "images" / "demos"
    bindir.mkdir(parents=True, exist_ok=True)
    imgdir.mkdir(parents=True, exist_ok=True)
    for path in bindir.glob("*.c48b"):
        path.unlink()
    for path in imgdir.glob("*.png"):
        path.unlink()

    demos = {}
    for name, runner, frames, stress, title in CONFIG:
        frag_path, frag = found[name]
        for actual, expected, label in (
            (frag["runner"], runner, "runner"),
            (int(frag["frames"]), frames, "frames"),
            (int(frag["stress_frames"]), stress, "stress"),
            (frag["title"], title, "title"),
        ):
            if actual != expected:
                raise SystemExit(f"{name}: {label} mismatch")
        parent = frag_path.parent
        binary = parent / f"{name}.c48b"
        screen = parent / f"{name}.scr"
        png = parent / f"{name}.png"
        for item in (binary, screen, png):
            if not item.is_file():
                raise SystemExit(f"{name}: missing {item.name}")
        if bg.sha(binary) != frag["binary_sha256"]:
            raise SystemExit(f"{name}: binary hash mismatch")
        if bg.sha(screen) != frag["screen_sha256"]:
            raise SystemExit(f"{name}: screen hash mismatch")
        if bg.sha(png) != frag["png_sha256"]:
            raise SystemExit(f"{name}: PNG hash mismatch")
        shutil.copyfile(binary, bindir / binary.name)
        shutil.copyfile(png, imgdir / png.name)
        demos[name] = {
            key: frag[key]
            for key in (
                "title",
                "runner",
                "frames",
                "stress_frames",
                "source_sha256",
                "binary_sha256",
                "first_screen_sha256",
                "screen_sha256",
                "png_sha256",
                "lit_pixels",
                "attribute_values",
            )
        }
    return demos


def patch_graphics_verifier(bg) -> None:
    path = SDK / "compiler" / "verify_graphics_demos.py"
    text = path.read_text(encoding="utf-8")
    if "import time\n" not in text:
        text = text.replace("import sys\n", "import sys\nimport time\n", 1)
    old = "if lit < 80 or attrs < 2:"
    if text.count(old) != 1:
        raise SystemExit("visual-floor anchor mismatch")
    text = text.replace(old, "if lit < 80 or attrs < 1:", 1)

    anchor = "\ndef check_one(\n"
    static_fn = (
        "\ndef check_static_one(name: str, exp: dict) -> None:\n"
        "    source = SRC / f\"{name}.c\"\n"
        "    frozen = BIN / f\"{name}.c48b\"\n"
        "    image = IMG / f\"{name}.png\"\n"
        "    if sha(source) != exp[\"source_sha256\"]:\n"
        "        fail(f\"{name}: source hash mismatch\")\n"
        "    if sha(frozen) != exp[\"binary_sha256\"]:\n"
        "        fail(f\"{name}: binary hash mismatch\")\n"
        "    if compile_bytes(name) != frozen.read_bytes():\n"
        "        fail(f\"{name}: deterministic rebuild mismatch\")\n"
        "    if sha(image) != exp[\"png_sha256\"]:\n"
        "        fail(f\"{name}: checked-in PNG hash mismatch\")\n\n\n"
    )
    if text.count(anchor) != 1:
        raise SystemExit("static verifier anchor mismatch")
    text = text.replace(anchor, static_fn + "def check_one(\n", 1)

    old = (
        "    source = SRC / f\"{name}.c\"\n"
        "    frozen = BIN / f\"{name}.c48b\"\n"
        "    image = IMG / f\"{name}.png\"\n"
        "    if sha(source) != exp[\"source_sha256\"]:\n"
        "        fail(f\"{name}: source hash mismatch\")\n"
        "    if sha(frozen) != exp[\"binary_sha256\"]:\n"
        "        fail(f\"{name}: binary hash mismatch\")\n"
        "    rebuilt = compile_bytes(name)\n"
        "    if rebuilt != frozen.read_bytes():\n"
        "        fail(f\"{name}: deterministic rebuild mismatch\")\n\n"
    )
    new = (
        "    check_static_one(name, exp)\n"
        "    image = IMG / f\"{name}.png\"\n\n"
    )
    if text.count(old) != 1:
        raise SystemExit("check-one static anchor mismatch")
    text = text.replace(old, new, 1)

    old = (
        "    if stress:\n"
        "        run_demo(name, int(exp[\"stress_frames\"]))\n\n"
        "    evidence = {\n"
    )
    new = (
        "    stress_seconds = 0.0\n"
        "    if stress:\n"
        "        started = time.monotonic()\n"
        "        run_demo(name, int(exp[\"stress_frames\"]))\n"
        "        stress_seconds = time.monotonic() - started\n\n"
        "    evidence = {\n"
    )
    if text.count(old) != 1:
        raise SystemExit("stress timing anchor mismatch")
    text = text.replace(old, new, 1)

    old = '        "stress_frames": exp["stress_frames"],\n'
    new = (
        '        "stress_frames": exp["stress_frames"],\n'
        '        "stress_seconds": round(stress_seconds, 3),\n'
    )
    if text.count(old) != 1:
        raise SystemExit("evidence timing anchor mismatch")
    text = text.replace(old, new, 1)

    old = '    ap.add_argument("--release", action="store_true")\n'
    new = (
        '    ap.add_argument("--release", action="store_true")\n'
        '    ap.add_argument("--static", action="store_true")\n'
    )
    if text.count(old) != 1:
        raise SystemExit("static option anchor mismatch")
    text = text.replace(old, new, 1)

    old = "    check_members(expect)\n\n    if ns.demo:\n"
    new = (
        "    check_members(expect)\n\n"
        "    if ns.static:\n"
        "        for name, exp in expect[\"demos\"].items():\n"
        "            check_static_one(name, exp)\n"
        "        print(\"GRAPHICS DEMO STATIC PASS: 21 demos\", flush=True)\n"
        "        return 0\n\n"
        "    if ns.demo:\n"
    )
    if text.count(old) != 1:
        raise SystemExit("static dispatch anchor mismatch")
    text = text.replace(old, new, 1)

    old = '        ap.error("choose --demo NAME or --release")\n'
    new = '        ap.error("choose --demo NAME, --static, or --release")\n'
    if text.count(old) != 1:
        raise SystemExit("static usage anchor mismatch")
    bg.write_text(path, text.replace(old, new, 1))


def patch_release_gate(bg) -> None:
    bg.patch_release_gate()
    path = SDK / "compiler" / "verify_release.py"
    text = path.read_text(encoding="utf-8")
    old = '            "--release",\n'
    if text.count(old) != 1:
        raise SystemExit("release graphics mode anchor mismatch")
    text = text.replace(old, '            "--static",\n', 1)
    old = "GRAPHICS DEMO VERIFY PASS: 21 demos"
    if text.count(old) != 1:
        raise SystemExit("release graphics marker anchor mismatch")
    bg.write_text(
        path,
        text.replace(old, "GRAPHICS DEMO STATIC PASS: 21 demos", 1),
    )


def patch_docs(bg) -> None:
    cells = [
        f"![{title}](doc/images/demos/{name}.png)<br>**{title}**<br>"
        f"`{runner}` - frame {frames}"
        for name, runner, frames, _stress, title in CONFIG
    ]
    rows = "".join(
        "| " + " | ".join(cells[i:i + 3]) + " |\n"
        for i in range(0, 21, 3)
    )
    bg.GALLERY = (
        "## Graphics Demo Reel - 21 programs, 21 runners\n\n"
        "Every image below is rendered from the exact 6912-byte Spectrum screen "
        "state produced by the C48 VM. The dedicated GitHub Actions workflow "
        "launches exactly **21 independent jobs** - seven Ubuntu, seven Windows, "
        "and seven macOS - with one demo assigned to each runner. Each job "
        "recompiles, verifies the canonical screen and PNG, then runs a longer "
        "animation stress pass and uploads evidence.\n\n"
        "| Demo | Demo | Demo |\n|---|---|---|\n"
        + rows
        + "\nSee [`doc/GRAPHICS-DEMOS.md`](doc/GRAPHICS-DEMOS.md) for the "
        "verification contract.\n\n"
    )
    bg.patch_readme()

    md = [
        "<!--",
        "============================================================================",
        "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.",
        "Proprietary rights reserved except as expressly licensed herein.",
        "",
        "ZX-UX C48 SDK",
        "This file is governed by the SANYALnet Labs Non-Commercial License in the",
        "root LICENSE file. Non-Commercial use is permitted; Commercial Use and use",
        "for AI/ML model training are prohibited unless separately authorized.",
        "",
        'Attribution is required: "Based on original work by Supratim Sanyal of',
        'SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,',
        "patent, trademark, and governing-law provisions.",
        "============================================================================",
        "-->",
        "# C48 Graphics Demo Reel",
        "",
        "The suite contains 21 clean-room C48 graphics and animation programs.",
        "Canonical screenshots are rendered from the exact 6912-byte Spectrum",
        "screen state produced by the C48 VM. The final workflow assigns exactly",
        "one demo to each of 21 independent GitHub-hosted jobs: seven Ubuntu,",
        "seven Windows, and seven macOS. Each job recompiles its demo, proves the",
        "binary and canonical screen/PNG hashes, runs an extended animation pass,",
        "and uploads SCR, PNG, and JSON evidence with measured stress duration.",
        "",
        "## Suite",
        "",
    ]
    for index, (name, runner, frames, stress, title) in enumerate(CONFIG, 1):
        md.append(
            f"{index}. **{title}** (`{name}.c`) - canonical frame "
            f"{frames}, stress {stress}, `{runner}`."
        )
    bg.write_text(
        SDK / "doc" / "GRAPHICS-DEMOS.md",
        "\n".join(md) + "\n",
    )


def main() -> int:
    bg = load_bootstrap()
    root = Path(os.environ["RUNNER_TEMP"]) / "graphics-generated"
    names = {row[0] for row in CONFIG}
    found = artifact_fragments(root, names)
    demos = assemble_artifacts(bg, found)
    patch_graphics_verifier(bg)
    bg.DEMOS = CONFIG
    bg.write_expectations(demos)
    bg.patch_license_gate()
    patch_release_gate(bg)
    patch_docs(bg)

    for rel in (
        ".github/bootstrap_graphics_demos.py",
        ".github/stage_graphics_demos.py",
    ):
        path = SDK / rel
        if path.exists():
            path.unlink()
    bg.write_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
