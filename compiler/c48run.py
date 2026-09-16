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

import argparse
import math
from pathlib import Path
import sys
import threading

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SDK_VERSION = "1.0.0"

from c48.errors import C48Error, RuntimeC48Error
from c48.format import read
from c48.gui import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    TkDisplay,
    render_snapshot_frame_rgb,
)
from c48.screen import Font4x8, ZXScreen
from c48.romvm import RomMathVM


class _QuotaRomMathVM(RomMathVM):
    """RomMathVM with a low-overhead wall-clock execution quota."""

    def __init__(self, *args, time_quota: float, **kwargs):
        self._time_quota = float(time_quota)
        self._time_quota_expired = False
        self._quota_timer: threading.Timer | None = None
        # Global initializers can call _tick(); the false flag above keeps those
        # construction-time ticks safe without charging them to program runtime.
        super().__init__(*args, **kwargs)
        timer = threading.Timer(self._time_quota, self._expire_time_quota)
        timer.daemon = True
        self._quota_timer = timer
        timer.start()

    def _expire_time_quota(self) -> None:
        self._time_quota_expired = True

    def _tick(self) -> None:
        super()._tick()
        if self._time_quota_expired:
            raise RuntimeC48Error(
                f"C48 execution time quota exceeded ({self._time_quota:g}s)"
            )

    def run(self) -> int:
        try:
            return super().run()
        finally:
            if self._quota_timer is not None:
                self._quota_timer.cancel()


def _new_vm(program, screen, *, time_quota: float, **kwargs) -> RomMathVM:
    """Use the historical zero-overhead VM unless a quota is requested."""
    if time_quota > 0.0:
        return _QuotaRomMathVM(
            program, screen, time_quota=time_quota, **kwargs
        )
    return RomMathVM(program, screen, **kwargs)


def _sdk_icon(tk):
    """Build the SDK-owned application icon without third-party asset bytes."""
    icon = tk.PhotoImage(width=32, height=32)
    icon.put("#101010", to=(0, 0, 32, 32))
    icon.put("#d0d0d0", to=(2, 2, 30, 4))
    icon.put("#d0d0d0", to=(2, 28, 30, 30))
    icon.put("#d0d0d0", to=(2, 4, 4, 28))
    icon.put("#d0d0d0", to=(28, 4, 30, 28))
    for x, color in enumerate(("#00c000", "#00c0c0", "#c0c000", "#c00000")):
        left = 7 + x * 5
        icon.put(color, to=(left, 8, left + 3, 24))
    return icon


def _run_display_with_sdk_icon(display: TkDisplay, target) -> int:
    """Run TkDisplay with the generated ZX-UX C48 SDK icon."""
    try:
        import tkinter as tk
    except ImportError as exc:  # pragma: no cover - host-specific
        raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc

    original_init = tk.Tk.__init__

    def init_with_icon(root, *args, **kwargs):
        original_init(root, *args, **kwargs)
        try:
            icon = _sdk_icon(tk)
            root.iconphoto(True, icon)
            root._zx_ux_app_icon = icon
        except tk.TclError:
            # Keep the VM usable on old/minimal Tk builds with limited icon APIs.
            root._zx_ux_app_icon = None

    tk.Tk.__init__ = init_with_icon
    try:
        return display.run_vm(target)
    finally:
        tk.Tk.__init__ = original_init


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="c48run", description="Portable ZX-UX C48 host runtime")
    ap.add_argument("--version", action="version", version=f"%(prog)s {SDK_VERSION}")
    ap.add_argument(
        "--about",
        action="version",
        version=(
            f"%(prog)s {SDK_VERSION}\n"
            "ZX-UX C48 SDK\n"
            "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n"
            "SANYALnet Labs Non-Commercial License; see the root LICENSE file."
        ),
        help="show copyright and license information and exit",
    )
    ap.add_argument("program", help="C48B1 program path")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--headless", action="store_true", help="run without opening a display window")
    ap.add_argument("--dump-screen", type=Path, help="write exact 6912-byte ZX screen after execution")
    ap.add_argument("--ppm", type=Path,
                    help="write a 256x192 paper-only PPM after execution")
    ap.add_argument(
        "--frame-ppm",
        type=Path,
        help="write a 320x240 PPM including the Spectrum border",
    )
    ap.add_argument("--scale", type=int, default=3, choices=(1,2,3,4,5))
    ap.add_argument(
        "--font",
        type=Path,
        default=ROOT / "assets" / "SANYALnet-Labs-4x8-font-FINAL.bin",
        metavar="PATH",
        help=(
            "F4X8 font resource to use for the ZX display "
            "(default: compiler/assets/SANYALnet-Labs-4x8-font-FINAL.bin)"
        ),
    )
    ap.add_argument("--allow-approx-rom-math", action="store_true",
                    help="use explicitly non-certified host approximations instead of ROM-derived transcendental math")
    ap.add_argument("--heap", type=int, default=1024, metavar="BYTES",
                    help="host C48 heap reserve: even 0..8192 bytes (default: 1024)")
    ap.add_argument(
        "--max-steps", type=int, default=0, metavar="STEPS",
        help=(
            "deterministic VM safety budget; 0 means unlimited "
            "(default: 0)"
        ),
    )
    ap.add_argument(
        "--time-quota", type=float, default=0.0, metavar="SECONDS",
        help="wall-clock VM execution quota in seconds; 0 means unlimited",
    )
    ns = ap.parse_args(argv)
    try:
        if ns.heap < 0 or ns.heap > 8192 or (ns.heap & 1):
            raise RuntimeC48Error("--heap must be an even value from 0..8192")
        if ns.max_steps < 0:
            raise RuntimeC48Error("--max-steps must be zero or positive")
        if not math.isfinite(ns.time_quota) or ns.time_quota < 0.0:
            raise RuntimeC48Error("--time-quota must be zero or a finite positive number")
        max_steps = None if ns.max_steps == 0 else ns.max_steps
        program_path = Path(ns.program)
        program = read(program_path)
        font = Font4x8.load(ns.font)
        screen = ZXScreen(font)
        # Preserve argv[0] as the exact host command token supplied for the program.
        pargv = [ns.program, *ns.args]
        if ns.headless:
            vm = _new_vm(
                program, screen, argv=pargv,
                approximate_rom_math=ns.allow_approx_rom_math,
                heap_size=ns.heap, max_steps=max_steps,
                time_quota=ns.time_quota,
            )
            status = vm.run()
        else:
            display = TkDisplay(screen, scale=ns.scale, title=f"ZX-UX C48 - {program_path.name}")
            vm = _new_vm(
                program, screen, argv=pargv,
                approximate_rom_math=ns.allow_approx_rom_math,
                heap_size=ns.heap, max_steps=max_steps,
                time_quota=ns.time_quota,
                input_provider=display.input_char,
                display_update=display.update,
                display_present=display.present,
            )
            status = _run_display_with_sdk_icon(display, vm.run)
        if ns.dump_screen:
            ns.dump_screen.parent.mkdir(parents=True, exist_ok=True)
            ns.dump_screen.write_bytes(screen.bytes())
        if ns.ppm:
            ns.ppm.parent.mkdir(parents=True, exist_ok=True)
            screen.save_ppm(ns.ppm)
        if ns.frame_ppm:
            ns.frame_ppm.parent.mkdir(parents=True, exist_ok=True)
            rgb = render_snapshot_frame_rgb(
                screen.bytes(),
                screen.border_color,
            )
            header = f"P6\n{FRAME_WIDTH} {FRAME_HEIGHT}\n255\n"
            ns.frame_ppm.write_bytes(header.encode("ascii") + rgb)
        return int(status) & 0xFF
    except MemoryError:
        print(
            "c48run: runtime error: host memory safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except RecursionError:
        print(
            "c48run: runtime error: host recursion safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except (C48Error, RuntimeError, OSError, ValueError) as exc:
        print(f"c48run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
