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
    attr_offset,
    bitmap_offset,
)

COPYRIGHT_TEXT = (
    "ZX-UX | 48K ZX Spectrum Unix | © 2026 Supratim Sanyal | "
    "SANYALnet Labs"
)


def is_break_key(keysym: str, state: int) -> bool:
    """Return True for the host equivalent of Spectrum BREAK."""
    return keysym == "space" and bool(state & 0x0001)


def footer_text(done: bool) -> str:
    """Return host-chrome guidance without changing screen RAM."""
    if done:
        return "Program ended - Shift+Space to close"
    return "Shift+Space = BREAK"


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


def render_snapshot_rgb(mem: bytes, flash_phase: bool = False) -> bytes:
    """Render one immutable 6912-byte Spectrum framebuffer snapshot."""
    if len(mem) != SCREEN_SIZE:
        raise ValueError("invalid Spectrum framebuffer snapshot size")
    out = bytearray(WIDTH * HEIGHT * 3)
    p = 0
    for y in range(HEIGHT):
        for x in range(WIDTH):
            a = mem[attr_offset(x, y)]
            ink = a & 7
            paper = (a >> 3) & 7
            br = (a >> 6) & 1
            fl = (a >> 7) & 1
            if fl and flash_phase:
                ink, paper = paper, ink
            bit = bool(mem[bitmap_offset(x, y)] & (0x80 >> (x & 7)))
            c = (PALETTE_BRIGHT if br else PALETTE_NORMAL)[
                ink if bit else paper
            ]
            out[p:p + 3] = bytes(c)
            p += 3
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
        self._frame_generation = 0
        self._frame_snapshot = self.screen.bytes()
        self._rendered_generation = -1
        self._stop = False
        self._root = None
        self._photo = None
        self._copy_font = None

    def input_char(self) -> int:
        with self._key_cond:
            self._key_waiting = True
            self._key_byte = None
            while self._key_byte is None and not self._stop:
                self._key_cond.wait()
            value = -1 if self._key_byte is None else self._key_byte
            self._key_waiting = False
            self._key_byte = None
            return value

    def _offer_key(self, value: int) -> bool:
        """Offer one key to a currently waiting getchar()."""
        with self._key_cond:
            if not self._key_waiting or self._key_byte is not None:
                return False
            self._key_byte = int(value) & 0xFF
            self._key_cond.notify()
            return True

    def _waiting_for_key(self) -> bool:
        with self._key_cond:
            return self._key_waiting and self._key_byte is None

    def update(self) -> None:
        snapshot = self.screen.bytes()
        with self._frame_lock:
            self._frame_generation += 1
            self._frame_snapshot = snapshot

    def _frame_after(self, rendered_generation: int) -> tuple[int, bytes] | None:
        with self._frame_lock:
            if self._frame_generation == rendered_generation:
                return None
            return self._frame_generation, self._frame_snapshot

    def close(self) -> None:
        self._stop = True
        with self._key_cond:
            self._key_cond.notify_all()

    def run_vm(self, target) -> int:
        try:
            import tkinter as tk
            import tkinter.font as tkfont
        except Exception as exc:  # pragma: no cover - host-specific
            raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc
        root = tk.Tk()
        self._root = root
        root.title(self.title)
        root.resizable(False, False)
        canvas_width = WIDTH * self.scale
        canvas = tk.Canvas(
            root,
            width=canvas_width,
            height=HEIGHT * self.scale,
            highlightthickness=0,
        )
        canvas.pack()
        footer = tk.Label(root, text=footer_text(False), anchor="w")
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

        result = {
            "status": 1,
            "error": None,
            "done": False,
            "break_running": False,
        }

        def key(event):
            if is_break_key(event.keysym, int(event.state)):
                result["break_running"] = not bool(result["done"])
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
                self.update()

        threading.Thread(target=worker, daemon=True).start()

        def redraw():
            if self._stop:
                root.destroy()
                return
            frame = self._frame_after(self._rendered_generation)
            if frame is not None:
                generation, snapshot = frame
                rgb = render_snapshot_rgb(
                    snapshot,
                    flash_phase=bool(int(time.monotonic() * 2) & 1),
                )
                ppm = b"P6\n256 192\n255\n" + rgb
                photo = tk.PhotoImage(data=ppm, format="PPM")
                if self.scale != 1:
                    photo = photo.zoom(self.scale, self.scale)
                self._photo = photo
                canvas.delete("all")
                canvas.create_image(0, 0, image=photo, anchor="nw")
                self._rendered_generation = generation
            if result["done"]:
                root.title(f"{self.title} - exited {result['status']}")
                footer.configure(text=footer_text(True))
            root.after(40, redraw)

        root.after(0, redraw)
        root.mainloop()
        self.close()
        if result["break_running"]:
            return 130
        if result["error"] is not None:
            raise result["error"]
        return int(result["status"])
