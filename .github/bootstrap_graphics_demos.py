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
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

SDK = Path(__file__).resolve().parent.parent
ROOT = SDK / "compiler"
sys.path.insert(0, str(ROOT))

import verify_graphics_demos as vd

DEMOS = [('goblet', 'ubuntu-latest', 10, 40, 'Crystal Goblet'), ('tunnel', 'windows-latest', 16, 60, 'Infinity Tunnel'), ('city', 'ubuntu-latest', 10, 30, 'Vector Metropolis'), ('terrain', 'windows-latest', 10, 30, 'Mountain Flight'), ('ocean', 'macos-latest', 12, 30, 'Ocean Grid'), ('torus', 'ubuntu-latest', 10, 30, 'Torus Reactor'), ('mobius', 'windows-latest', 12, 30, 'Mobius Flight'), ('morph3d', 'macos-latest', 12, 30, 'Polyhedron Morph'), ('warp', 'ubuntu-latest', 20, 80, 'Warp Drive'), ('galaxy', 'windows-latest', 18, 40, 'Spiral Galaxy'), ('orrery', 'macos-latest', 16, 30, 'Clockwork Orrery'), ('firework', 'ubuntu-latest', 18, 60, 'Firework Night'), ('sprites', 'windows-latest', 14, 50, 'Sprite Storm'), ('plasma', 'macos-latest', 4, 8, 'Spectrum Plasma'), ('kaleido', 'ubuntu-latest', 12, 30, 'Kaleidoscope'), ('moire', 'windows-latest', 10, 30, 'Moire Engine'), ('mandel', 'ubuntu-latest', 3, 4, 'Mandelbrot Dive'), ('julia', 'windows-latest', 4, 6, 'Julia Ballet'), ('forest', 'macos-latest', 12, 20, 'Fractal Forest'), ('raymaze', 'macos-latest', 12, 30, 'Raycast Labyrinth'), ('showcase', 'macos-latest', 14, 50, 'C48 Grand Finale')]
WORKFLOW = '# ============================================================================\n# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n# Proprietary rights reserved except as expressly licensed herein.\n#\n# ZX-UX C48 SDK\n# This file is governed by the SANYALnet Labs Non-Commercial License in the\n# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use\n# for AI/ML model training are prohibited unless separately authorized.\n#\n# Attribution is required: "Based on original work by Supratim Sanyal of\n# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,\n# patent, trademark, and governing-law provisions.\n# ============================================================================\nname: C48 graphics demo reel\n\n"on":\n  push:\n    branches: [main, graphics-demos-21]\n  pull_request:\n  workflow_dispatch:\n\npermissions:\n  contents: read\n\njobs:\n  demo:\n    name: ${{ matrix.demo }} / ${{ matrix.os }}\n    strategy:\n      fail-fast: false\n      max-parallel: 21\n      matrix:\n        include:\n          - demo: goblet\n            os: ubuntu-latest\n          - demo: tunnel\n            os: windows-latest\n          - demo: city\n            os: ubuntu-latest\n          - demo: terrain\n            os: windows-latest\n          - demo: ocean\n            os: macos-latest\n          - demo: torus\n            os: ubuntu-latest\n          - demo: mobius\n            os: windows-latest\n          - demo: morph3d\n            os: macos-latest\n          - demo: warp\n            os: ubuntu-latest\n          - demo: galaxy\n            os: windows-latest\n          - demo: orrery\n            os: macos-latest\n          - demo: firework\n            os: ubuntu-latest\n          - demo: sprites\n            os: windows-latest\n          - demo: plasma\n            os: macos-latest\n          - demo: kaleido\n            os: ubuntu-latest\n          - demo: moire\n            os: windows-latest\n          - demo: mandel\n            os: ubuntu-latest\n          - demo: julia\n            os: windows-latest\n          - demo: forest\n            os: macos-latest\n          - demo: raymaze\n            os: macos-latest\n          - demo: showcase\n            os: macos-latest\n    runs-on: ${{ matrix.os }}\n    steps:\n      - name: Check out repository\n        uses: actions/checkout@v4\n\n      - name: Set up Python 3.10\n        uses: actions/setup-python@v5\n        with:\n          python-version: "3.10"\n\n      - name: Verify assigned graphics demo\n        run: >-\n          python -B compiler/verify_graphics_demos.py\n          --demo "${{ matrix.demo }}"\n          --runner "${{ matrix.os }}"\n          --evidence-dir runner-evidence\n\n      - name: Upload runner evidence\n        uses: actions/upload-artifact@v4\n        with:\n          name: graphics-${{ matrix.demo }}-${{ matrix.os }}\n          path: runner-evidence/\n          if-no-files-found: error\n'
DOCUMENT = '<!--\n============================================================================\nCopyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\nProprietary rights reserved except as expressly licensed herein.\n\nZX-UX C48 SDK\nThis file is governed by the SANYALnet Labs Non-Commercial License in the\nroot LICENSE file. Non-Commercial use is permitted; Commercial Use and use\nfor AI/ML model training are prohibited unless separately authorized.\n\nAttribution is required: "Based on original work by Supratim Sanyal of\nSANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,\npatent, trademark, and governing-law provisions.\n============================================================================\n-->\n# C48 Graphics Demo Reel\n\nThe demo reel is a clean-room suite of 21 C48 programs under `dev/src/demos/`.\nEach program compiles to a frozen deterministic C48B1 executable under\n`dev/bin/demos/`. Canonical screenshots under `doc/images/demos/` are rendered\nfrom the exact 6912-byte ZX Spectrum screen state, not from a mock UI.\n\nThe workflow `.github/workflows/graphics-demos.yml` launches exactly 21\nindependent GitHub-hosted runner jobs: seven Ubuntu, seven Windows, and seven\nmacOS jobs. Each job recompiles and runs one assigned demo, verifies exact\nscreen and PNG hashes, executes a longer stress animation, and uploads fresh\n`.scr`, `.png`, and JSON evidence.\n\n## Suite\n\n1. **Crystal Goblet** (`goblet.c`) — frame 10, stress 40, `ubuntu-latest`.\n2. **Infinity Tunnel** (`tunnel.c`) — frame 16, stress 60, `windows-latest`.\n3. **Vector Metropolis** (`city.c`) — frame 10, stress 30, `ubuntu-latest`.\n4. **Mountain Flight** (`terrain.c`) — frame 10, stress 30, `windows-latest`.\n5. **Ocean Grid** (`ocean.c`) — frame 12, stress 30, `macos-latest`.\n6. **Torus Reactor** (`torus.c`) — frame 10, stress 30, `ubuntu-latest`.\n7. **Mobius Flight** (`mobius.c`) — frame 12, stress 30, `windows-latest`.\n8. **Polyhedron Morph** (`morph3d.c`) — frame 12, stress 30, `macos-latest`.\n9. **Warp Drive** (`warp.c`) — frame 20, stress 80, `ubuntu-latest`.\n10. **Spiral Galaxy** (`galaxy.c`) — frame 18, stress 40, `windows-latest`.\n11. **Clockwork Orrery** (`orrery.c`) — frame 16, stress 30, `macos-latest`.\n12. **Firework Night** (`firework.c`) — frame 18, stress 60, `ubuntu-latest`.\n13. **Sprite Storm** (`sprites.c`) — frame 14, stress 50, `windows-latest`.\n14. **Spectrum Plasma** (`plasma.c`) — frame 4, stress 8, `macos-latest`.\n15. **Kaleidoscope** (`kaleido.c`) — frame 12, stress 30, `ubuntu-latest`.\n16. **Moire Engine** (`moire.c`) — frame 10, stress 30, `windows-latest`.\n17. **Mandelbrot Dive** (`mandel.c`) — frame 3, stress 4, `ubuntu-latest`.\n18. **Julia Ballet** (`julia.c`) — frame 4, stress 6, `windows-latest`.\n19. **Fractal Forest** (`forest.c`) — frame 12, stress 20, `macos-latest`.\n20. **Raycast Labyrinth** (`raymaze.c`) — frame 12, stress 30, `macos-latest`.\n21. **C48 Grand Finale** (`showcase.c`) — frame 14, stress 50, `macos-latest`.\n'
GALLERY = '## Graphics Demo Reel — 21 programs, 21 runners\n\nThese screenshots are rendered from the exact 6912-byte Spectrum screen state\nafter deterministic animation frames. The dedicated GitHub Actions workflow\nlaunches exactly **21 independent jobs**: seven on Ubuntu, seven on Windows,\nand seven on macOS. Each runner recompiles and runs one assigned C48 demo,\nchecks exact screen/PNG hashes, then runs a longer animation stress pass.\n\n| Demo | Demo | Demo |\n|---|---|---|\n| ![Crystal Goblet](doc/images/demos/goblet.png)<br>**Crystal Goblet**<br>`ubuntu-latest` · frame 10 | ![Infinity Tunnel](doc/images/demos/tunnel.png)<br>**Infinity Tunnel**<br>`windows-latest` · frame 16 | ![Vector Metropolis](doc/images/demos/city.png)<br>**Vector Metropolis**<br>`ubuntu-latest` · frame 10 |\n| ![Mountain Flight](doc/images/demos/terrain.png)<br>**Mountain Flight**<br>`windows-latest` · frame 10 | ![Ocean Grid](doc/images/demos/ocean.png)<br>**Ocean Grid**<br>`macos-latest` · frame 12 | ![Torus Reactor](doc/images/demos/torus.png)<br>**Torus Reactor**<br>`ubuntu-latest` · frame 10 |\n| ![Mobius Flight](doc/images/demos/mobius.png)<br>**Mobius Flight**<br>`windows-latest` · frame 12 | ![Polyhedron Morph](doc/images/demos/morph3d.png)<br>**Polyhedron Morph**<br>`macos-latest` · frame 12 | ![Warp Drive](doc/images/demos/warp.png)<br>**Warp Drive**<br>`ubuntu-latest` · frame 20 |\n| ![Spiral Galaxy](doc/images/demos/galaxy.png)<br>**Spiral Galaxy**<br>`windows-latest` · frame 18 | ![Clockwork Orrery](doc/images/demos/orrery.png)<br>**Clockwork Orrery**<br>`macos-latest` · frame 16 | ![Firework Night](doc/images/demos/firework.png)<br>**Firework Night**<br>`ubuntu-latest` · frame 18 |\n| ![Sprite Storm](doc/images/demos/sprites.png)<br>**Sprite Storm**<br>`windows-latest` · frame 14 | ![Spectrum Plasma](doc/images/demos/plasma.png)<br>**Spectrum Plasma**<br>`macos-latest` · frame 4 | ![Kaleidoscope](doc/images/demos/kaleido.png)<br>**Kaleidoscope**<br>`ubuntu-latest` · frame 12 |\n| ![Moire Engine](doc/images/demos/moire.png)<br>**Moire Engine**<br>`windows-latest` · frame 10 | ![Mandelbrot Dive](doc/images/demos/mandel.png)<br>**Mandelbrot Dive**<br>`ubuntu-latest` · frame 3 | ![Julia Ballet](doc/images/demos/julia.png)<br>**Julia Ballet**<br>`windows-latest` · frame 4 |\n| ![Fractal Forest](doc/images/demos/forest.png)<br>**Fractal Forest**<br>`macos-latest` · frame 12 | ![Raycast Labyrinth](doc/images/demos/raymaze.png)<br>**Raycast Labyrinth**<br>`macos-latest` · frame 12 | ![C48 Grand Finale](doc/images/demos/showcase.png)<br>**C48 Grand Finale**<br>`macos-latest` · frame 14 |\n\nSee [`doc/GRAPHICS-DEMOS.md`](doc/GRAPHICS-DEMOS.md) for the mechanical verification contract.\n\n'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"expected one patch anchor in {path}, got {count}"
        )
    write_text(path, text.replace(old, new, 1))


def build_demos() -> dict:
    names = [row[0] for row in DEMOS]
    actual = sorted(path.stem for path in vd.SRC.glob("*.c"))
    if actual != sorted(names):
        raise SystemExit(
            f"graphics source set mismatch: {actual!r}"
        )
    binary_dir = SDK / "dev" / "bin" / "demos"
    image_dir = SDK / "doc" / "images" / "demos"
    binary_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    for path in binary_dir.glob("*.c48b"):
        path.unlink()
    for path in image_dir.glob("*.png"):
        path.unlink()

    result = {}
    for name, runner, frames, stress, title in DEMOS:
        source = vd.SRC / f"{name}.c"
        binary = binary_dir / f"{name}.c48b"
        binary.write_bytes(vd.compile_bytes(name))

        first = vd.run_demo(name, 1)
        screen = vd.run_demo(name, frames)
        if first.bytes() == screen.bytes():
            raise SystemExit(f"{name} did not animate")
        lit, attrs = vd.screen_metrics(screen)
        if lit < 80 or attrs < 2:
            raise SystemExit(
                f"{name} visual floor failed: lit={lit} attrs={attrs}"
            )
        vd.run_demo(name, stress)
        png = vd.png_bytes(screen.render_rgb())
        image = image_dir / f"{name}.png"
        image.write_bytes(png)
        result[name] = {
            "title": title,
            "runner": runner,
            "frames": frames,
            "stress_frames": stress,
            "source_sha256": sha(source),
            "binary_sha256": sha(binary),
            "first_screen_sha256": vd.sha_bytes(first.bytes()),
            "screen_sha256": vd.sha_bytes(screen.bytes()),
            "png_sha256": vd.sha_bytes(png),
            "lit_pixels": lit,
            "attribute_values": attrs,
        }
        print(
            f"BUILD DEMO PASS: {name} | "
            f"lit={lit} attrs={attrs}",
            flush=True,
        )
    return result


def write_expectations(demos: dict) -> None:
    payload = {
        "schema": 1,
        "helper_sha256": sha(vd.SRC / "demoapi.h"),
        "demos": demos,
    }
    write_text(
        ROOT / "graphics_demo_expectations.json",
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
    )


def patch_license_gate() -> None:
    path = ROOT / "check_license_headers.py"
    old = (
        'EXEMPT_SUFFIXES = {".json", ".bin", ".c48b", '
        '".docx", ".zip"}\n'
    )
    new = (
        'EXEMPT_SUFFIXES = {".json", ".bin", ".png", ".c48b", '
        '".docx", ".zip"}\n'
    )
    replace_once(path, old, new)


def patch_release_gate() -> None:
    path = ROOT / "verify_release.py"
    text = path.read_text(encoding="utf-8")

    old = '        ".github/workflows/verify.yml",\n'
    new = (
        '        ".github/workflows/verify.yml",\n'
        '        ".github/workflows/graphics-demos.yml",\n'
    )
    if text.count(old) != 1:
        raise SystemExit("verify workflow anchor mismatch")
    text = text.replace(old, new, 1)

    old = (
        '        "compiler/tests/test_game_regressions.py", '
        '"compiler/verify_games.py",\n'
    )
    new = (
        '        "compiler/tests/test_game_regressions.py", '
        '"compiler/verify_games.py",\n'
        '        "compiler/verify_graphics_demos.py",\n'
        '        "compiler/graphics_demo_expectations.json",\n'
    )
    if text.count(old) != 1:
        raise SystemExit("verify compiler anchor mismatch")
    text = text.replace(old, new, 1)

    old = (
        '        "doc/RELEASE-NOTES.md", '
        '"doc/LICENSE-HEADER-POLICY.md", "doc/GAMES.md",\n'
    )
    new = (
        '        "doc/RELEASE-NOTES.md", '
        '"doc/LICENSE-HEADER-POLICY.md", "doc/GAMES.md",\n'
        '        "doc/GRAPHICS-DEMOS.md",\n'
    )
    if text.count(old) != 1:
        raise SystemExit("verify docs anchor mismatch")
    text = text.replace(old, new, 1)

    old = (
        '        "dev/src/c48host.h", '
        '"dev/src/games/gameapi.h",\n'
    )
    new = (
        '        "dev/src/c48host.h", '
        '"dev/src/games/gameapi.h",\n'
        '        "dev/src/demos/demoapi.h",\n'
    )
    if text.count(old) != 1:
        raise SystemExit("verify source anchor mismatch")
    text = text.replace(old, new, 1)

    old = "\ndef check_security_programs() -> None:\n"
    new = '''
def check_graphics_demos() -> None:
    cp = run(
        [
            sys.executable,
            "-B",
            str(ROOT / "verify_graphics_demos.py"),
            "--release",
        ],
        timeout=600,
    )
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout + cp.stderr)
        fail("graphics demo verification failed")
    if "GRAPHICS DEMO VERIFY PASS: 21 demos" not in cp.stdout:
        fail("graphics demo completion marker missing")


def check_security_programs() -> None:
'''
    if text.count(old) != 1:
        raise SystemExit("verify function anchor mismatch")
    text = text.replace(old, new, 1)

    old = (
        '        ("game corpus", check_games),\n'
        '        ("security fixture binaries", '
        'check_security_programs),\n'
    )
    new = (
        '        ("game corpus", check_games),\n'
        '        ("graphics demo corpus", check_graphics_demos),\n'
        '        ("security fixture binaries", '
        'check_security_programs),\n'
    )
    if text.count(old) != 1:
        raise SystemExit("verify check-list anchor mismatch")
    text = text.replace(old, new, 1)
    write_text(path, text)


def patch_readme() -> None:
    path = SDK / "README.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Clone and quick start\n"
    if text.count(marker) != 1:
        raise SystemExit("README insertion anchor mismatch")
    text = text.replace(marker, GALLERY + marker, 1)
    write_text(path, text)


def write_final_files() -> None:
    write_text(
        SDK / ".github" / "workflows" / "graphics-demos.yml",
        WORKFLOW,
    )
    write_text(SDK / "doc" / "GRAPHICS-DEMOS.md", DOCUMENT)


def remove_bootstrap() -> None:
    for rel in (
        ".github/bootstrap_graphics_demos.py",
        ".github/workflows/bootstrap-graphics-demos.yml",
    ):
        path = SDK / rel
        if path.exists():
            path.unlink()


def manifest_hash(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() == ".bat":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def write_manifest() -> None:
    lines = []
    for path in sorted(SDK.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SDK)
        if ".git" in rel.parts:
            continue
        if rel.as_posix() == "MANIFEST.sha256":
            continue
        lines.append(
            f"{manifest_hash(path)}  {rel.as_posix()}"
        )
    write_text(
        SDK / "MANIFEST.sha256",
        "\n".join(lines) + "\n",
    )


def run(cmd: list[str], timeout: int = 900) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cp = subprocess.run(
        cmd,
        cwd=SDK,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    sys.stdout.write(cp.stdout)
    sys.stderr.write(cp.stderr)
    if cp.returncode != 0:
        raise SystemExit(
            f"command failed ({cp.returncode}): "
            + " ".join(cmd)
        )


def main() -> int:
    demos = build_demos()
    write_expectations(demos)
    patch_license_gate()
    patch_release_gate()
    patch_readme()
    write_final_files()
    remove_bootstrap()
    write_manifest()

    run([
        sys.executable,
        "-B",
        "compiler/verify_graphics_demos.py",
        "--release",
    ])
    run([
        sys.executable,
        "-B",
        "compiler/verify_release.py",
    ], timeout=1200)
    run(["git", "diff", "--check"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
