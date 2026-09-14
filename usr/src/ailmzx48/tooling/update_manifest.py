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
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
BASE_COMMIT = "871948f884e00b9ec16d0afee9421712c3dabc9e"
SELF = Path("usr/src/ailmzx48/tooling/update_manifest.py")
WORKFLOW = Path(".github/workflows/ailmzx48-maintenance.yml")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"quota optimization: expected one match in {path}, found {count}"
        )
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace(old, new, 1))
    print(f"quota optimization: patched {path}", flush=True)


def patch_runtime() -> None:
    path = "compiler/c48run.py"
    replace_once(
        path,
        '''import argparse\nimport math\nfrom pathlib import Path\nimport sys\nimport time\n''',
        '''import argparse\nimport math\nfrom pathlib import Path\nimport sys\nimport threading\n''',
    )
    replace_once(
        path,
        '''class _QuotaRomMathVM(RomMathVM):\n    """RomMathVM with an optional wall-clock execution quota."""\n\n    def __init__(self, *args, time_quota: float = 0.0, **kwargs):\n        # VM construction evaluates global initializers, which can call _tick().\n        # Establish quota state before the base constructor starts that work.\n        self._time_quota = float(time_quota)\n        self._time_deadline = (\n            time.monotonic() + self._time_quota\n            if self._time_quota > 0.0\n            else None\n        )\n        super().__init__(*args, **kwargs)\n\n    def _tick(self) -> None:\n        super()._tick()\n        if self._time_deadline is not None and time.monotonic() >= self._time_deadline:\n            raise RuntimeC48Error(\n                f"C48 execution time quota exceeded ({self._time_quota:g}s)"\n            )\n\n\n''',
        '''class _QuotaRomMathVM(RomMathVM):\n    """RomMathVM with a low-overhead wall-clock execution quota."""\n\n    def __init__(self, *args, time_quota: float, **kwargs):\n        self._time_quota = float(time_quota)\n        self._time_quota_expired = False\n        self._quota_timer: threading.Timer | None = None\n        # Global initializers can call _tick(); the false flag above keeps those\n        # construction-time ticks safe without charging them to program runtime.\n        super().__init__(*args, **kwargs)\n        timer = threading.Timer(self._time_quota, self._expire_time_quota)\n        timer.daemon = True\n        self._quota_timer = timer\n        timer.start()\n\n    def _expire_time_quota(self) -> None:\n        self._time_quota_expired = True\n\n    def _tick(self) -> None:\n        super()._tick()\n        if self._time_quota_expired:\n            raise RuntimeC48Error(\n                f"C48 execution time quota exceeded ({self._time_quota:g}s)"\n            )\n\n    def run(self) -> int:\n        try:\n            return super().run()\n        finally:\n            if self._quota_timer is not None:\n                self._quota_timer.cancel()\n\n\ndef _new_vm(program, screen, *, time_quota: float, **kwargs) -> RomMathVM:\n    """Use the historical zero-overhead VM unless a quota is requested."""\n    if time_quota > 0.0:\n        return _QuotaRomMathVM(\n            program, screen, time_quota=time_quota, **kwargs\n        )\n    return RomMathVM(program, screen, **kwargs)\n\n\n''',
    )
    replace_once(
        path,
        '''        if ns.headless:\n            vm = _QuotaRomMathVM(\n                program, screen, argv=pargv,\n                approximate_rom_math=ns.allow_approx_rom_math,\n                heap_size=ns.heap, max_steps=max_steps,\n                time_quota=ns.time_quota,\n            )\n            status = vm.run()\n''',
        '''        if ns.headless:\n            vm = _new_vm(\n                program, screen, argv=pargv,\n                approximate_rom_math=ns.allow_approx_rom_math,\n                heap_size=ns.heap, max_steps=max_steps,\n                time_quota=ns.time_quota,\n            )\n            status = vm.run()\n''',
    )
    replace_once(
        path,
        '''            vm = _QuotaRomMathVM(\n                program, screen, argv=pargv,\n                approximate_rom_math=ns.allow_approx_rom_math,\n                heap_size=ns.heap, max_steps=max_steps,\n                time_quota=ns.time_quota,\n                input_provider=display.input_char,\n                display_update=display.update,\n                display_present=display.present,\n            )\n''',
        '''            vm = _new_vm(\n                program, screen, argv=pargv,\n                approximate_rom_math=ns.allow_approx_rom_math,\n                heap_size=ns.heap, max_steps=max_steps,\n                time_quota=ns.time_quota,\n                input_provider=display.input_char,\n                display_update=display.update,\n                display_present=display.present,\n            )\n''',
    )


def patch_graphics_diagnostics() -> None:
    path = "compiler/verify_graphics_demos.py"
    replace_once(
        path,
        '''            fail(\n                f"{name}: host timeout after {host_timeout:g}s "\n                f"(VM quota {time_quota:g}s)"\n            )\n''',
        '''            fail(\n                f"{name}: {frames} frame(s): host timeout after "\n                f"{host_timeout:g}s (VM quota {time_quota:g}s)"\n            )\n''',
    )
    replace_once(
        path,
        '''            fail(f"{name}: runtime status {cp.returncode}: {detail}")\n''',
        '''            fail(\n                f"{name}: {frames} frame(s): runtime status "\n                f"{cp.returncode}: {detail}"\n            )\n''',
    )


def restore_scaffolding() -> None:
    subprocess.run(
        ["git", "checkout", BASE_COMMIT, "--", str(SELF), str(WORKFLOW)],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    print("quota optimization: restored maintenance scaffolding", flush=True)


def regenerate_manifest() -> None:
    lines = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if ".git" in rel.parts or rel.as_posix() == "MANIFEST.sha256":
            continue
        data = path.read_bytes()
        if path.suffix.lower() == ".bat":
            data = data.replace(b"\r\n", b"\n")
        digest = hashlib.sha256(data).hexdigest()
        lines.append(f"{digest}  {rel.as_posix()}\n")
    (ROOT / "MANIFEST.sha256").write_text(
        "".join(lines), encoding="ascii", newline="\n"
    )


patch_runtime()
patch_graphics_diagnostics()
restore_scaffolding()
regenerate_manifest()
