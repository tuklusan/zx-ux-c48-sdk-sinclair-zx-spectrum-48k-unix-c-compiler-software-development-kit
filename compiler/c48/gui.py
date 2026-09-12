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
import threading
import time
from dataclasses import dataclass

from .screen import (
    HEIGHT,
    PALETTE_BRIGHT,
    PALETTE_NORMAL,
    SCREEN_SIZE,
    WIDTH,
    ZXScreen,
)

COPYRIGHT_TEXT = (
    "ZX-UX | 48K ZX Spectrum Unix | © 2026 Supratim Sanyal | "
    "SANYALnet Labs"
)

BORDER_X = 32
BORDER_Y = 24
FRAME_WIDTH = WIDTH + BORDER_X * 2
FRAME_HEIGHT = HEIGHT + BORDER_Y * 2

# Rendering the Spectrum bitmap pixel-by-pixel costs enough Python time to
# starve Tk on animation-heavy programs.  Pre-expand the 128 possible
# BRIGHT/PAPER/INK combinations for every bitmap byte once, then render a
# frame 8 pixels at a time.  FLASH is handled by swapping ink/paper when the
# row is emitted, so no second table is required.
_PIXEL_RUNS = []
for _bright in range(2):
    _palette = PALETTE_BRIGHT if _bright else PALETTE_NORMAL
    for _paper in range(8):
        for _ink in range(8):
            _ink_rgb = bytes(_palette[_ink])
            _paper_rgb = bytes(_palette[_paper])
            _runs = []
            for _bits in range(256):
                _run = bytearray()
                for _bit in range(8):
                    _run.extend(
                        _ink_rgb
                        if _bits & (0x80 >> _bit)
                        else _paper_rgb
                    )
                _runs.append(bytes(_run))
            _PIXEL_RUNS.append(tuple(_runs))
_PIXEL_RUNS = tuple(_PIXEL_RUNS)
_BITMAP_ROW_BASES = tuple(
    ((y & 0xC0) << 5) | ((y & 0x07) << 8) | ((y & 0x38) << 2)
    for y in range(HEIGHT)
)
_ATTR_ROW_BASES = tuple(6144 + (y >> 3) * 32 for y in range(HEIGHT))


def is_break_key(keysym: str, state: int) -> bool:
    """Return True for the host equivalent of Spectrum BREAK."""
    return keysym == "space" and bool(state & 0x0001)


def footer_text(done: bool) -> str:
    """Return host-chrome guidance without changing screen RAM."""
    if done:
        return "Program ended - Shift+Space to close"
    return "Shift+Space = BREAK"


def footer_config(done: bool) -> dict[str, str]:
    """Return Tk label options for the normal or completed-program footer."""
    if done:
        return {
            "text": footer_text(True),
            "background": "yellow",
            "foreground": "red",
        }
    return {"text": footer_text(False)}


def key_event_bytes(keysym: str, text: str) -> tuple[int, ...]:
    """Map one Tk key event to canonical C48 console bytes."""
    if keysym in {"Return", "KP_Enter"}:
        return (10,)
    if keysym == "BackSpace":
        return (8,)
    if keysym == "Escape":
        return (27,)
    if len(keysym) == 4 and keysym.startswith("KP_"):
        digit = keysym[3]
        if "0" <= digit <= "9":
            return (ord(digit),)
    if not text:
        return ()
    try:
        return tuple(text.encode("ascii"))
    except UnicodeEncodeError:
        return ()


def fit_footer_font_size(
    text: str,
    max_width: int,
    measure,
    *,
    max_size: int = 9,
) -> int:
    """Return the largest measured integer font size that fits."""
    if max_width <= 0:
        raise ValueError("footer width must be positive")
    for size in range(max_size, 0, -1):
        if measure(size, text) <= max_width:
            return size
    return 1


def rectangle_fits_bounds(
    x: int,
    y: int,
    width: int,
    height: int,
    bounds: tuple[int, int, int, int],
) -> bool:
    """Return whether a positive rectangle is completely inside bounds."""
    left, top, right, bottom = (int(value) for value in bounds)
    x = int(x)
    y = int(y)
    width = int(width)
    height = int(height)
    return (
        width > 0
        and height > 0
        and right > left
        and bottom > top
        and x >= left
        and y >= top
        and x + width <= right
        and y + height <= bottom
    )


def _host_work_area(root) -> tuple[int, int, int, int]:
    """Return the usable desktop rectangle for the Tk toplevel's host."""
    screen = (0, 0, int(root.winfo_screenwidth()), int(root.winfo_screenheight()))
    if os.name != "nt":
        return screen
    # Tk's winfo_screenheight includes the Windows taskbar.  A toplevel can
    # therefore report its requested client geometry while its lower rows are
    # actually obscured.  SPI_GETWORKAREA returns the primary desktop area
    # available to ordinary application windows, excluding app bars/taskbar.
    try:
        import ctypes
        from ctypes import wintypes

        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(
            0x0030,  # SPI_GETWORKAREA
            0,
            ctypes.byref(rect),
            0,
        ):
            work = (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
            if work[2] > work[0] and work[3] > work[1]:
                return work
    except (AttributeError, OSError):
        pass
    return screen


def largest_fully_mapped_scale(requested_scale: int, map_scale) -> int:
    """Map the largest integer display scale the host can show completely.

    Desktop window managers are allowed to constrain oversized toplevels.
    Aqua does this on small hosted desktops, which can silently shrink the Tk
    canvas even after an explicit geometry request.  Probe each integer scale
    from the caller's preference downward and accept only an exact full-canvas
    mapping.
    """
    if requested_scale < 1:
        raise ValueError("display scale must be positive")
    for scale in range(requested_scale, 0, -1):
        mapped_width, mapped_height = map_scale(scale)
        required = (FRAME_WIDTH * scale, FRAME_HEIGHT * scale)
        if (int(mapped_width), int(mapped_height)) == required:
            return scale
    raise RuntimeError("host desktop cannot fully map even a 1x C48 canvas")


def render_snapshot_rgb(mem: bytes, flash_phase: bool = False) -> bytes:
    """Render one immutable 6912-byte Spectrum framebuffer snapshot."""
    if len(mem) != SCREEN_SIZE:
        raise ValueError("invalid Spectrum framebuffer snapshot size")
    out = bytearray(WIDTH * HEIGHT * 3)
    p = 0
    for y in range(HEIGHT):
        bitmap = _BITMAP_ROW_BASES[y]
        attrs = _ATTR_ROW_BASES[y]
        for xbyte in range(32):
            a = mem[attrs + xbyte]
            ink = a & 7
            paper = (a >> 3) & 7
            if flash_phase and (a & 0x80):
                ink, paper = paper, ink
            run = _PIXEL_RUNS[((a >> 6) & 1) * 64 + paper * 8 + ink][
                mem[bitmap + xbyte]
            ]
            out[p:p + 24] = run
            p += 24
    return bytes(out)


def render_snapshot_frame_rgb(
    mem: bytes,
    border_color: int,
    flash_phase: bool = False,
) -> bytes:
    """Render the paper inside a visible ZX Spectrum border."""
    if not 0 <= border_color <= 7:
        raise ValueError("border color out of range")
    paper = render_snapshot_rgb(mem, flash_phase=flash_phase)
    border = bytes(PALETTE_NORMAL[border_color])
    out = bytearray(border * (FRAME_WIDTH * FRAME_HEIGHT))
    src_stride = WIDTH * 3
    dst_stride = FRAME_WIDTH * 3
    xoff = BORDER_X * 3
    for y in range(HEIGHT):
        src = y * src_stride
        dst = (y + BORDER_Y) * dst_stride + xoff
        out[dst:dst + src_stride] = paper[src:src + src_stride]
    return bytes(out)


@dataclass
class TkDisplay:
    """Small dependency-free Tk display for the Spectrum framebuffer."""

    screen: ZXScreen
    scale: int = 3
    title: str = "ZX-UX C48"

    def __post_init__(self) -> None:
        # Keyboard input is a rendezvous, not a typeahead FIFO. A normal key
        # event is accepted only while the VM is blocked in getchar().
        self._key_cond = threading.Condition()
        self._key_waiting = False
        self._key_byte: int | None = None
        self._frame_lock = threading.Lock()
        self._frame_cond = threading.Condition(self._frame_lock)
        self._frame_generation = 0
        self._frame_snapshot = self.screen.bytes()
        self._frame_border = int(self.screen.border_color) & 7
        self._rendered_generation = -1
        self._stop = False
        self._root = None
        self._photo = None
        self._copy_font = None
        self._probe_path = os.environ.get("C48_GUI_PROBE")
        self._probe_lock = threading.Lock()
        self._probe_seq = 0

    def _probe(self, event: str, **fields) -> None:
        """Append one fail-closed GUI acceptance record when probing is enabled."""
        if not self._probe_path:
            return
        with self._probe_lock:
            self._probe_seq += 1
            record = {
                "event": event,
                "monotonic_ns": time.monotonic_ns(),
                "pid": os.getpid(),
                "seq": self._probe_seq,
            }
            record.update(fields)
            path = Path(self._probe_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def input_char(self) -> int:
        with self._key_cond:
            self._key_waiting = True
            self._key_byte = None
            self._probe("input_waiting")
            while self._key_byte is None and not self._stop:
                self._key_cond.wait()
            value = -1 if self._key_byte is None else self._key_byte
            self._key_waiting = False
            self._key_byte = None
            self._probe("input_return", value=value)
            return value

    def _offer_key(self, value: int) -> bool:
        """Offer one key to a currently waiting getchar()."""
        with self._key_cond:
            if not self._key_waiting or self._key_byte is not None:
                return False
            self._key_byte = int(value) & 0xFF
            self._probe("key_accepted", value=self._key_byte)
            self._key_cond.notify()
            return True

    def _waiting_for_key(self) -> bool:
        with self._key_cond:
            return self._key_waiting and self._key_byte is None

    def update(self) -> int:
        snapshot = self.screen.bytes()
        border = int(self.screen.border_color) & 7
        with self._frame_cond:
            self._frame_generation += 1
            self._frame_snapshot = snapshot
            self._frame_border = border
            return self._frame_generation

    def present(self) -> None:
        """Wait until Tk has painted the latest intentionally published frame."""
        with self._frame_cond:
            target = self._frame_generation
            while self._rendered_generation < target and not self._stop:
                self._frame_cond.wait()

    def _frame_after(
        self,
        rendered_generation: int,
    ) -> tuple[int, bytes, int] | None:
        with self._frame_lock:
            if self._frame_generation == rendered_generation:
                return None
            return (
                self._frame_generation,
                self._frame_snapshot,
                self._frame_border,
            )

    def _mark_rendered(self, generation: int) -> None:
        with self._frame_cond:
            if generation > self._rendered_generation:
                self._rendered_generation = generation
            self._frame_cond.notify_all()

    def close(self) -> None:
        if not self._stop:
            self._probe("display_close")
        self._stop = True
        with self._key_cond:
            self._key_cond.notify_all()
        with self._frame_cond:
            self._frame_cond.notify_all()

    def run_vm(self, target) -> int:
        try:
            import tkinter as tk
            import tkinter.font as tkfont
        except Exception as exc:  # pragma: no cover - host-specific
            raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc
        root = tk.Tk()
        self._root = root
        root.title(self.title)
        canvas_width = FRAME_WIDTH * self.scale
        canvas = tk.Canvas(
            root,
            width=canvas_width,
            height=FRAME_HEIGHT * self.scale,
            highlightthickness=0,
        )
        # Aqua can composite a one-pixel NSWindow edge over an otherwise
        # fully mapped canvas.  Keep the Spectrum border inside the client
        # area so compositor evidence and the visible frame remain intact.
        canvas.pack(padx=1)
        footer = tk.Label(root, anchor="w", **footer_config(False))
        footer.pack(fill="x")

        base = tkfont.nametofont("TkDefaultFont")
        family = base.actual("family")

        def measure(size: int, text: str) -> int:
            font = tkfont.Font(root=root, family=family, size=size)
            return int(font.measure(text))

        copy_size = fit_footer_font_size(
            COPYRIGHT_TEXT,
            max(1, canvas_width - 12),
            measure,
        )
        self._copy_font = tkfont.Font(
            root=root,
            family=family,
            size=copy_size,
        )
        copyright_footer = tk.Label(
            root,
            text=COPYRIGHT_TEXT,
            anchor="center",
            font=self._copy_font,
            foreground="#707070",
        )
        copyright_footer.pack(fill="x")

        # Let the host map the requested client area before locking the window.
        # Aqua can constrain an oversized toplevel to the usable desktop area;
        # when that happens Tk silently shrinks the packed canvas.  Detect that
        # real mapped geometry and step down to the largest integer scale whose
        # complete Spectrum frame is actually visible.
        def map_scale(scale: int) -> tuple[int, int]:
            nonlocal canvas_width
            self.scale = scale
            canvas_width = FRAME_WIDTH * scale
            canvas.configure(
                width=canvas_width,
                height=FRAME_HEIGHT * scale,
            )
            copy_size = fit_footer_font_size(
                COPYRIGHT_TEXT,
                max(1, canvas_width - 12),
                measure,
            )
            self._copy_font.configure(size=copy_size)
            root.update_idletasks()
            requested_width = max(canvas_width, int(root.winfo_reqwidth()))
            requested_height = max(1, int(root.winfo_reqheight()))
            root.geometry(f"{requested_width}x{requested_height}")
            # A full event-loop turn is required here: update_idletasks() alone
            # can report the requested geometry rather than the host-constrained
            # mapped geometry on Aqua.
            root.update()
            mapped_width = int(canvas.winfo_width())
            mapped_height = int(canvas.winfo_height())
            work_area = _host_work_area(root)
            if not rectangle_fits_bounds(
                int(root.winfo_rootx()),
                int(root.winfo_rooty()),
                int(root.winfo_width()),
                int(root.winfo_height()),
                work_area,
            ):
                # A mapped client that extends beneath a taskbar/app bar is not
                # fully visible.  Reject this scale even if Tk reports the
                # requested canvas dimensions verbatim.
                return 0, 0
            return mapped_width, mapped_height

        self.scale = largest_fully_mapped_scale(self.scale, map_scale)
        root.resizable(False, False)
        if self._probe_path:
            root.lift()
            root.focus_force()
            canvas.focus_force()
            root.update()
            self._probe(
                "window_ready",
                title=self.title,
                windowing_system=str(root.tk.call("tk", "windowingsystem")),
                tk_patchlevel=str(root.tk.call("info", "patchlevel")),
                screen_width=int(root.winfo_screenwidth()),
                screen_height=int(root.winfo_screenheight()),
                root_x=int(root.winfo_rootx()),
                root_y=int(root.winfo_rooty()),
                root_width=int(root.winfo_width()),
                root_height=int(root.winfo_height()),
                canvas_x=int(canvas.winfo_rootx()),
                canvas_y=int(canvas.winfo_rooty()),
                canvas_width=int(canvas.winfo_width()),
                canvas_height=int(canvas.winfo_height()),
                scale=int(self.scale),
            )

        result = {
            "status": 1,
            "error": None,
            "done": False,
            "break_running": False,
            "footer_reported": False,
        }

        def key(event):
            if is_break_key(event.keysym, int(event.state)):
                result["break_running"] = not bool(result["done"])
                self._probe(
                    "break_key",
                    done=bool(result["done"]),
                    break_running=bool(result["break_running"]),
                )
                self.close()
                root.after_idle(root.destroy)
                return "break"
            for b in key_event_bytes(event.keysym, event.char):
                self._offer_key(b)
            return None

        root.bind("<Key>", key)
        canvas.focus_set()

        def worker():
            try:
                result["status"] = int(target()) & 0xFF
            except BaseException as exc:
                result["error"] = exc
            finally:
                result["done"] = True
                self._probe(
                    "program_done",
                    status=int(result["status"]),
                    error_type=(
                        None
                        if result["error"] is None
                        else type(result["error"]).__name__
                    ),
                )
                self.update()

        threading.Thread(target=worker, daemon=True).start()

        def redraw():
            if self._stop:
                root.destroy()
                return
            frame = self._frame_after(self._rendered_generation)
            if frame is not None:
                generation, snapshot, border_color = frame
                rgb = render_snapshot_frame_rgb(
                    snapshot,
                    border_color,
                    flash_phase=bool(int(time.monotonic() * 2) & 1),
                )
                header = f"P6\n{FRAME_WIDTH} {FRAME_HEIGHT}\n255\n"
                ppm = header.encode("ascii") + rgb
                photo = tk.PhotoImage(data=ppm, format="PPM")
                if self.scale != 1:
                    photo = photo.zoom(self.scale, self.scale)
                self._photo = photo
                canvas.delete("all")
                canvas.create_image(0, 0, image=photo, anchor="nw")
                if self._probe_path:
                    root.update_idletasks()
                    probe_path = Path(self._probe_path)
                    frame_path = probe_path.with_name(
                        f"{probe_path.stem}-frame.ppm"
                    )
                    frame_tmp = frame_path.with_suffix(frame_path.suffix + ".tmp")
                    frame_tmp.write_bytes(ppm)
                    os.replace(frame_tmp, frame_path)
                    self._probe(
                        "frame_rendered",
                        generation=int(generation),
                        border_color=int(border_color),
                        frame_sha256=hashlib.sha256(rgb).hexdigest(),
                        frame_ppm=frame_path.name,
                        canvas_x=int(canvas.winfo_rootx()),
                        canvas_y=int(canvas.winfo_rooty()),
                        canvas_width=int(canvas.winfo_width()),
                        canvas_height=int(canvas.winfo_height()),
                    )
                self._mark_rendered(generation)
            if result["done"]:
                root.title(f"{self.title} - exited {result['status']}")
                footer.configure(**footer_config(True))
                if self._probe_path and not result["footer_reported"]:
                    root.update_idletasks()
                    self._probe(
                        "footer_done",
                        text=str(footer.cget("text")),
                        background=str(footer.cget("background")),
                        foreground=str(footer.cget("foreground")),
                        title=str(root.title()),
                    )
                    result["footer_reported"] = True
            root.after(20, redraw)

        root.after(0, redraw)
        root.mainloop()
        self._probe(
            "mainloop_exit",
            status=int(result["status"]),
            break_running=bool(result["break_running"]),
            error_type=(
                None
                if result["error"] is None
                else type(result["error"]).__name__
            ),
        )
        self.close()
        if result["break_running"]:
            return 130
        if result["error"] is not None:
            raise result["error"]
        return int(result["status"])
