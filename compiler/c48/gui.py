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

import queue
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


def is_break_key(keysym: str, state: int) -> bool:
    """Return True for the host equivalent of Spectrum BREAK (Shift+Space)."""
    return keysym == "space" and bool(state & 0x0001)


def footer_text(done: bool) -> str:
    """Return host-chrome guidance without altering Spectrum screen memory."""
    if done:
        return "Program ended - Shift+Space to close"
    return "Shift+Space = BREAK"


def key_event_bytes(keysym: str, text: str) -> tuple[int, ...]:
    """Map one Tk key event to canonical C48 console bytes.

    Control keys are selected by keysym before event.char because Tk commonly
    reports Return as ``\r``.  ZX-UX text input uses LF (0x0A), not CR.
    Numeric-keypad digits are selected by keysym so they work even when Tk
    supplies an empty event.char.  Non-ASCII host text is ignored rather than
    leaking Unicode into C48.
    """
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


def render_snapshot_rgb(mem: bytes, flash_phase: bool = False) -> bytes:
    """Render one immutable 6912-byte Spectrum framebuffer snapshot.

    The VM owns and mutates ``ZXScreen.mem`` on its worker thread. Tk must not
    walk that live bytearray because a glyph or graphics primitive can be only
    partly written while the GUI is reading it. This renderer consumes only a
    frozen bytes snapshot published after a VM screen operation completes.
    """
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
    """Small dependency-free Tk display for the 256x192 Spectrum framebuffer.

    Tk calls remain on the main thread. The VM executes on a worker thread and
    publishes immutable framebuffer snapshots. Keyboard bytes are delivered
    through a thread-safe queue.
    """
    screen: ZXScreen
    scale: int = 3
    title: str = "ZX-UX C48"

    def __post_init__(self) -> None:
        self.keys: queue.Queue[int] = queue.Queue()
        self._frame_lock = threading.Lock()
        self._frame_generation = 0
        self._frame_snapshot = self.screen.bytes()
        self._rendered_generation = -1
        self._stop = False
        self._root = None
        self._photo = None

    def input_char(self) -> int:
        return self.keys.get()

    def update(self) -> None:
        # Called by the VM worker after a complete screen operation. Snapshot
        # before taking the mailbox lock so Tk never blocks the VM while it
        # converts a previous snapshot to RGB.
        snapshot = self.screen.bytes()
        with self._frame_lock:
            self._frame_generation += 1
            self._frame_snapshot = snapshot

    def _frame_after(self, rendered_generation: int) -> tuple[int, bytes] | None:
        """Return the newest published frame if it is newer than the caller."""
        with self._frame_lock:
            if self._frame_generation == rendered_generation:
                return None
            return self._frame_generation, self._frame_snapshot

    def close(self) -> None:
        self._stop = True

    def run_vm(self, target) -> int:
        try:
            import tkinter as tk
        except Exception as exc:  # pragma: no cover - host-specific
            raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc
        root = tk.Tk()
        self._root = root
        root.title(self.title)
        root.resizable(False, False)
        canvas = tk.Canvas(root, width=WIDTH*self.scale, height=HEIGHT*self.scale,
                           highlightthickness=0)
        canvas.pack()
        footer = tk.Label(root, text=footer_text(False), anchor="w")
        footer.pack(fill="x")
        result = {"status": 1, "error": None, "done": False, "break_running": False}

        def key(event):
            if is_break_key(event.keysym, int(event.state)):
                # CAPS SHIFT+SPACE is BREAK on the Spectrum. A host Shift+Space
                # therefore closes a completed final frame, or aborts a still-running
                # VM session. The VM worker is a daemon so blocked getchar() calls do
                # not keep the host process alive after the display exits.
                result["break_running"] = not bool(result["done"])
                self._stop = True
                root.after_idle(root.destroy)
                return "break"
            for b in key_event_bytes(event.keysym, event.char):
                self.keys.put(b)
            return None

        root.bind("<Key>", key)
        canvas.focus_set()

        def worker():
            try:
                result["status"] = int(target()) & 0xFF
            except BaseException as exc:  # handed back to main thread
                result["error"] = exc
            finally:
                result["done"] = True
                # Publish the exact final framebuffer. This also makes a final
                # update impossible to lose if Tk is rendering an older frame.
                self.update()

        threading.Thread(target=worker, daemon=True).start()

        def redraw():
            if self._stop:
                root.destroy(); return
            frame = self._frame_after(self._rendered_generation)
            if frame is not None:
                generation, snapshot = frame
                rgb = render_snapshot_rgb(
                    snapshot,
                    flash_phase=bool(int(time.monotonic()*2)&1),
                )
                # PPM is accepted natively by Tk PhotoImage and avoids Pillow.
                ppm = b"P6\n256 192\n255\n" + rgb
                photo = tk.PhotoImage(data=ppm, format="PPM")
                if self.scale != 1:
                    photo = photo.zoom(self.scale, self.scale)
                self._photo = photo
                canvas.delete("all")
                canvas.create_image(0, 0, image=photo, anchor="nw")
                # A newer publish that happened during RGB conversion has a
                # higher generation and therefore remains pending next tick.
                self._rendered_generation = generation
            if result["done"]:
                # Keep the final frame visible until the user closes the window.
                # Completion guidance lives in host chrome, never in the 6912-byte
                # Spectrum framebuffer, so deterministic program screen output stays exact.
                root.title(f"{self.title} - exited {result['status']}")
                footer.configure(text=footer_text(True))
            root.after(40, redraw)
        root.after(0, redraw)
        root.mainloop()
        if result["break_running"]:
            return 130
        if result["error"] is not None:
            raise result["error"]
        return int(result["status"])
