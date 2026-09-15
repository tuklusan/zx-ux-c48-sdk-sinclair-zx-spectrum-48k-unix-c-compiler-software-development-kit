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

# Fuse 48x48 application icon, data/icons/48x48/fuse.png, from the read-only
# Fuse emulator repository.  Kept inline so every SDK copy has the same icon
# without adding a packaging-only binary dependency.
# Source: https://github.com/trufanov-nok/fuse-emulator/blob/master/data/icons/48x48/fuse.png
_FUSE_ICON_PNG_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAAXNSR0IArs4c
6QAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sIBRYHN1zUEbUAAAz3
SURBVGje7VhZbxxXdv7OqarurqpuNsmmaFGkqIWydlKi5NiWZzQZzUw0QGbg
GTsLMsm85ickz3nMW4A85CFIECABHCQ25PG+S+MZ2zKtjRZF0tzErZvdXHpn
r1V1Th7Y1FDKJHYcO86DPuACt4HbwPed75y651zgIR7iIR7imwT9P+V0AMAQ
gEEAg6ZpHgJQAPDnvu/P7TxsfsNkuwCcbJHdXscBuDsPqSqICKr6RwD++psQ
EAZwYkdUh1q/e3by3LGXHW5oSwC1/ouvUwABOLgjmtvRPQSAHyBLDxDm/2ov
ImBmJaKhr1JA1wMRHQJw7AH7dxLdSUy/ZP0dBhAC0PyfCNhp/xARDanqCQC7
HcfZCjuR+r6PRqOxTU53OCKfs/+i5whAiJkPi8id3ybgQfsHW+tRwzAoHA5D
VeG6rtIWBABXKhVUKhX171Lgc/Zf6JyqSovjEIDfCDhz+vH+SmXzb6ZmJn7I
zK5lWdhezWYTpmmqaZqoVqtgZniep0EQkO/78DwPQRB8rdVv2zZCoQgMw0AQ
+KjX60ONRv25ewIiYfuvLMN6FoAmEglpqSXf97VSqQAAWZYlnuc9aPcXtf0L
pZBlWWLbLgyDSRVCRCACNRoNqVTKUFUCoET3f4lMAG1sGAiHwuo4DkciEfT1
9Ylt2+z7ATyvKSMjI7xDwLat8mXShpnhOK6YpsVbJAlEJJ7X5Fqtgp6eHrlw
4QKPjo5ibGxMmJlbd4AwM4vqyQcFpIkIjuNCRFAulzE5OYmVlZWvwH4HoVAY
zNwiCgSBoFarol6v/YaEaaItHodhGjAsCyvrGzBsF7F4HJVy+b5PmgH0W0Bb
HShtC5gHEDi2y8vLy1+KqGVZaNkPgLZvTTQaDVQqZahBQJcFzXvgpiIeb4cZ
DqO9owNzU5P40U+fxXJmFZv5HDKpJJy2dngCdHR13ycAAIZFUTUxOObjw20B
KQBl143GPy9fW/aTaVqy/SUiInhek2qNukjYBTbzBCI5dswFsUfptCvlUh2n
9z9GkeO2zE5PoSuRoMTuPdLb3Y3U8jJWVlept3+feIlOzEyOk7VZls5yEZOF
HKmIKBEAkIjKtwzh2af41Nj7ck9ABkDOdaLxnflq2w6Hw2EQsRARb9kfoF6r
iVdvsq++aE+EDR8wK4FE2jo50b8fUanL/MwM9+z9DupBIAOH2/iVF1+A294u
hmnyI317kVqYlxNHj3NuYx3hcBjJyQlJjt7klVIJiBjy+i8vswQBOnt2ybH9
ZzkMxtjtUfF9n586pbh+WAfx/nYNiKwrUca2nQMdHQlstRxb9lcrZbQzI+sH
AAE94d3YF98PxBkLazM4OXAWPb29mL97F4tzsxga2IeI7yGbzSKVXsHx4bPg
eg1WKAQU8wjVa5ifX0CpkMdbL/wrSoHCTsThOw7CkQjMeg1/8LOfY3bmLvKp
JNQ0MHDwUXTt2oWFpUV0rq8jfg740GgbbJUATCUqGIaR9DwPpXJBVPaBuUZE
JTHZwMDgIA11dcvduVnYjoNEbx/tSSRk5tIUkWVJqVrD3t09NHbrhlgArEaD
TCJJzU5D56ZpsVYX3zHxyfhtIoFY4RCGL5ynWLkhozPTOHToGDq7H6GowfKL
X1xCsVSlc9/+ttz4+Combn9K1fSKvHfjGsrFAv1YRK6eAwUjz5xA7DVCeUNN
IqoEqgvMRGErTCfP7IEdjUl7W5xfffEFdB86IpFahVNuFNmNdRw9fVYKm2V2
YzHJJ5c5Ypn4YGlJfN/ndy49jyaRRDrjHO/tgZphaU5P8cUf/BheNif1WoVv
T0+jJ9ErRo/FexoNlEsl7OntleT6OhuGifHLb8sHLz7PZRaEOCS/GrnKTjSG
/gMDstzeztdLN0CfxdppM9cnwLIZBFo3DFlQoqYdsUPFcgkdu/cg7DiwTAuN
jXWsNX1Uy2VsZNK49fxzWG40QU4ITa+JjBVCudHAxWd+go1MFtnkEsKui32H
j6I70Yl0KgU2LAw89hgWF+ZRu3UTmYU5JFMpZNdWoUGAxc8mwG0u2rt3oUEG
GpUKLly8iM1CGatLi/AkwNknnkSj4eHaZAI0OwJAhwAsm6qBB5hpqBZsx91V
zKxqsVqlT1dWpOk1cfn9K8SGIZYdwZEzpxCqB7SxOC9Pfee7VK/VJRYJ4/U3
XiNWU06eOoVURweNXhuRx1WQm56iQAK58vIl1H2fNMRiRyKYGB8ntgw5cvo0
DBiYn/6Mzn3rvGw2PHREo/T6S5fEcWLo33eQLNOQybHbiM3OUf+zaXkl/xPw
4husTIMI9DUjlV7WvX37OwD8wPe97lQ6Sal8XqtBwM/+/E8p7rZrLBbjcqlM
F77/Q+re06P5QpErtZoeOHSYA4NpfnpaHb/JmdFb9MnoTa1WKzw1M01Lxby2
Jzr5kc5dlMtl9Zk//hlH3Bh1xWJaKJV46MxjNHD4MBUKeS2Xynysfy+5taqO
z99lf32Vxj/6QKfmZrnRbNBwaU0Xjguv/TKgevKuArSmqpfMVu+zASDt2O7x
e80JEVaW0zg6fBrFQgETk+PYXFzAwto61jJp1EtFZO/cxroJuNEo5jeyqG6W
cO73L8LbKGEltYy2zgSGB0+BJUAyk0a+WMa58+exMDONT8fHIKtpjNy6joVk
EtpsIj15B3U2EO/ohEZsFFDAwaPHcfrMGcT6+uBt5NFTHUFx67Ic3NlOFwEs
h8MRZWYNgoBUVVKT48jcvEbzpbKwaeCVy+/BskP0yMF9Eue9NDM9LxcvfA9a
qVDIMOS1995FmG3ad+qg2J2dGB+9Reubm5LL5QAojV55R+bffRMZ8YmiEfnw
zhjKhQKe/P53qZgtSa1cRjGfpd87dEg8w0KxVqNQJCK79+5DuVGmDdeRrbuJ
CMARAKFtAVVVzDEzhcMRqlYrwsycWl+HiMj3nv4RG+sFrBbySGfX5dTRYe6I
hKRQqnFyJY0jJ0+KSsAGMzJ35+T29RHOra0hEJHLr77EwoRde3slQhaXclkc
OfSo7N7Tx/VqFVffv4yOWEIOHjzKlfIm3n7pkpT6+rlYKMAyDVmYneHozBia
/16XV1/4CzY/+Ri61QGEiOjRVgqhwYykKip2xHar1cq9NCICGptNDJw6g856
FZ899y8oFHKYz+VQLOSxsnAXE7euAwYh3BlDJruGYjaHoccfQwAGewHujN7C
M0//ITayG5iamEB2fQNDv/MkWAWjNz5BemYKzblpzKeSqNdreOOFfwMRoAqQ
AufPB/jLei8wtnxvEFUVmKZ50gQAz2v44XAkA2jBsaNOFhskIrJdDYuT43Ln
5jWUCgUwEV298p40m03af/KodHQ9Aq1uUhOQM088iWa5QjdHb4jfFOwdGKDe
PT1y+9YNFFZSZJSKUsznkE4t00f/9PeSaTZRFcVoPk8KCO3ovVQBBeiEqqwO
RGjl6mHaX13UthPDiEZjZJoWcrmN3nuD9bnHv3MGwD8Uivnh6dkJAdFW7+5G
xXZcrpZL6Dt0ELG2DmElvnH113Lx6Z9yOGKjUi7JB1cu89N/8mcIi8jlK++y
NhrY67oymUpyqV6HBYivytrq7YmId7z7CBHYNE04TkxdN0qxWBui0TZ1o21k
GJYwtKLQAqBZEc00GrVrzab3tztn4hyAlGM7wwBwfPgsjhw5iu6uLszencfU
xB3UyhUMnXkciUQC05NjKCSTiNgRzC4vo16t4Ff//I+oiaAoWzN9qvUgBQDN
HXsihuO4cN0otojGKBqNw7Yjqoq6qhYBzQNYE9EU1F8kg9NMRhrAqmli3TTN
rGUFuZ0CSgAWLSukpmmSG4tJe6ILhUqFlCCRSATJpXkk33ubXkklpR4IjeRy
EqiCWranPf8/teLhcFhdN4atqMY1Go3BdWNExB4gJVUUAN1QxYrvB0vMnDIM
TgOUIaK1lpAyEdVFAu/NN18Ofuu7kKrWiGieiMSOODw99il/+vFHaDYaQgCj
Fb2rlaVt+0UB5q3uVUzTYseJwnWjGovFORqNIRZrU9O0VFUrqlv2qyIjIkki
XTIMI81MGQCrRMiqogRQlUibjUY9uHz5Tf28YWqHADSZKaWqZdt24mvrmXtR
VECgum0/ua6rjhOlWKxNo9EYotE4bdlPdVUpAppXxZqqpnzfX2TmtGEYaQAZ
ImxsRR0VImoEgee//far8mXH1nsCRq7/Onjqid/NAMjZthMHwJGIDdeNquvG
uFVUiEajCrAPSFkVeUDXVZHesp9SzEaaiDIA1gC07EddRLy33nr5K3+DMe9/
BcY6Ea329x84uP/Ao7AsSx60PwhkmUiXW/anW0SzRCipogqg2WjUgitX3lL8
H+A+AaZl5ayQ9YlpmvVAZCUI/CXD4BVmI3O//VQh0obve/4777wm+AZxn4Cw
HdkwTf47gEOGaRQAbBJRPQiCr8X+h3iIh3iIh3iI/y3+A0UD+L0NzmN3AAAA
AElFTkSuQmCC
"""


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


def _run_display_with_fuse_icon(display: TkDisplay, target) -> int:
    """Run TkDisplay with the Fuse Spectrum icon on its root window."""
    try:
        import tkinter as tk
    except ImportError as exc:  # pragma: no cover - host-specific
        raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc

    original_init = tk.Tk.__init__

    def init_with_icon(root, *args, **kwargs):
        original_init(root, *args, **kwargs)
        try:
            icon = tk.PhotoImage(data=_FUSE_ICON_PNG_BASE64)
            root.iconphoto(True, icon)
            root._zx_ux_app_icon = icon
        except tk.TclError:
            # Keep the VM usable on old/minimal Tk builds that cannot decode PNG.
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
            status = _run_display_with_fuse_icon(display, vm.run)
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