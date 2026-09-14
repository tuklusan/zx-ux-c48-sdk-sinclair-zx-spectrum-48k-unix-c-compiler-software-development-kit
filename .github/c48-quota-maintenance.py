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
"""One-shot, self-cleaning C48 15-second quota maintenance helper."""
from __future__ import annotations

from pathlib import Path
import subprocess

BASE_COMMIT = "0bee81194e60fc5d7466e4d562c0cb9722d708ba"
WORKFLOW = Path(".github/workflows/ailmzx48-maintenance.yml")
SELF = Path(".github/c48-quota-maintenance.py")


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"quota maintenance: expected one match in {path}, found {count}"
        )
    text = text.replace(old, new, 1)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(f"quota maintenance: patched {path}", flush=True)


def patch_release_verifier() -> None:
    replace_once(
        "compiler/verify_release.py",
        '''            cmd = [sys.executable, "-B", str(ROOT / "c48run.py"), "--headless",\n                   "--dump-screen", screen.name, rebuilt.name, *exp["args"]]\n''',
        '''            cmd = [\n                sys.executable, "-B", str(ROOT / "c48run.py"), "--headless",\n                "--time-quota", "15",\n                "--dump-screen", screen.name, rebuilt.name, *exp["args"],\n            ]\n''',
    )


def patch_graphics_verifier() -> None:
    path = "compiler/verify_graphics_demos.py"
    replace_once(
        path,
        '''import argparse\nimport hashlib\nimport json\nfrom pathlib import Path\nimport platform\nimport struct\nimport sys\nimport time\nimport zlib\n''',
        '''import argparse\nimport hashlib\nimport json\nimport math\nfrom pathlib import Path\nimport platform\nimport struct\nimport subprocess\nimport sys\nimport tempfile\nimport time\nimport zlib\n''',
    )
    replace_once(
        path,
        '''from c48.compiler import compile_file\nfrom c48.format import encode, read\nfrom c48.screen import Font4x8, ZXScreen\nfrom c48.vm import C48VM\n''',
        '''from c48.compiler import compile_file\nfrom c48.format import encode\nfrom c48.screen import Font4x8, SCREEN_SIZE, ZXScreen\n''',
    )
    replace_once(
        path,
        '''def run_demo(name: str, frames: int) -> ZXScreen:\n    program = read(BIN / f"{name}.c48b")\n    screen = ZXScreen(FONT)\n    vm = C48VM(\n        program,\n        screen,\n        argv=[name, str(frames)],\n        max_steps=10000000,\n    )\n    status = vm.run()\n    if status != 0:\n        fail(f"{name}: runtime status {status}")\n    return screen\n''',
        '''def run_demo(name: str, frames: int, time_quota: float) -> ZXScreen:\n    with tempfile.TemporaryDirectory(prefix=f"c48-graphics-{name}-") as td:\n        temp = Path(td)\n        program_token = name\n        (temp / program_token).write_bytes(\n            (BIN / f"{name}.c48b").read_bytes()\n        )\n        screen_path = temp / f"{name}.scr"\n        cmd = [\n            sys.executable,\n            "-B",\n            str(ROOT / "c48run.py"),\n            "--headless",\n            "--time-quota",\n            f"{time_quota:g}",\n            "--dump-screen",\n            screen_path.name,\n            program_token,\n            str(frames),\n        ]\n        host_timeout = time_quota + 5.0\n        try:\n            cp = subprocess.run(\n                cmd,\n                cwd=temp,\n                text=True,\n                stdout=subprocess.PIPE,\n                stderr=subprocess.PIPE,\n                check=False,\n                timeout=host_timeout,\n            )\n        except subprocess.TimeoutExpired as exc:\n            fail(\n                f"{name}: host timeout after {host_timeout:g}s "\n                f"(VM quota {time_quota:g}s)"\n            )\n            raise AssertionError("unreachable") from exc\n        if cp.returncode != 0:\n            detail = (cp.stderr or cp.stdout).strip()\n            fail(f"{name}: runtime status {cp.returncode}: {detail}")\n        if not screen_path.is_file():\n            fail(f"{name}: runtime did not emit a screen dump")\n        screen_data = screen_path.read_bytes()\n        if len(screen_data) != SCREEN_SIZE:\n            fail(\n                f"{name}: screen dump size {len(screen_data)} "\n                f"!= {SCREEN_SIZE}"\n            )\n    screen = ZXScreen(FONT)\n    screen.mem[:] = screen_data\n    return screen\n''',
    )
    replace_once(
        path,
        '''def check_one(\n    name: str,\n    exp: dict,\n    *,\n    stress: bool,\n    evidence_dir: Path | None,\n) -> dict:\n''',
        '''def check_one(\n    name: str,\n    exp: dict,\n    *,\n    stress: bool,\n    evidence_dir: Path | None,\n    time_quota: float,\n) -> dict:\n''',
    )
    replace_once(path, "    first = run_demo(name, 1)\n", "    first = run_demo(name, 1, time_quota)\n")
    replace_once(
        path,
        '''    screen = run_demo(name, int(exp["frames"]))\n''',
        '''    screen = run_demo(name, int(exp["frames"]), time_quota)\n''',
    )
    replace_once(
        path,
        '''        run_demo(name, int(exp["stress_frames"]))\n''',
        '''        run_demo(name, int(exp["stress_frames"]), time_quota)\n''',
    )
    replace_once(
        path,
        '''        "stress_seconds": round(stress_seconds, 3),\n''',
        '''        "stress_seconds": round(stress_seconds, 3),\n        "time_quota_seconds": time_quota,\n''',
    )
    replace_once(
        path,
        '''    ap.add_argument("--evidence-dir", type=Path)\n    ns = ap.parse_args(argv)\n\n    expect = load_expect()\n''',
        '''    ap.add_argument("--evidence-dir", type=Path)\n    ap.add_argument(\n        "--time-quota",\n        type=float,\n        default=15.0,\n        metavar="SECONDS",\n        help="per-C48B wall-clock runtime quota (default: 15)",\n    )\n    ns = ap.parse_args(argv)\n    if not math.isfinite(ns.time_quota) or ns.time_quota <= 0.0:\n        ap.error("--time-quota must be a finite positive number")\n\n    expect = load_expect()\n''',
    )
    replace_once(
        path,
        '''        check_one(\n            ns.demo,\n            exp,\n            stress=True,\n            evidence_dir=ns.evidence_dir,\n        )\n''',
        '''        check_one(\n            ns.demo,\n            exp,\n            stress=True,\n            evidence_dir=ns.evidence_dir,\n            time_quota=ns.time_quota,\n        )\n''',
    )
    replace_once(
        path,
        '''        check_one(name, exp, stress=False, evidence_dir=None)\n''',
        '''        check_one(\n            name,\n            exp,\n            stress=False,\n            evidence_dir=None,\n            time_quota=ns.time_quota,\n        )\n''',
    )


def patch_graphics_workflow() -> None:
    replace_once(
        ".github/workflows/graphics-demos.yml",
        '''          --runner "${{ matrix.os }}"\n          --evidence-dir runner-evidence\n''',
        '''          --runner "${{ matrix.os }}"\n          --time-quota 15\n          --evidence-dir runner-evidence\n''',
    )


def cleanup_maintenance_scaffolding() -> None:
    subprocess.run(
        ["git", "checkout", BASE_COMMIT, "--", str(WORKFLOW)],
        check=True,
    )
    SELF.unlink()
    subprocess.run(["git", "diff", "--check"], check=True)
    print("quota maintenance: restored maintenance workflow and removed helper", flush=True)


def main() -> int:
    patch_release_verifier()
    patch_graphics_verifier()
    patch_graphics_workflow()
    cleanup_maintenance_scaffolding()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
