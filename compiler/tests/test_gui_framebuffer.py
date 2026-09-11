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

from pathlib import Path
import sys
import threading
import time
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
sys.path.insert(0, str(COMPILER))

from c48.gui import (
    COPYRIGHT_TEXT,
    TkDisplay,
    fit_footer_font_size,
    render_snapshot_rgb,
)
from c48.screen import Font4x8, ZXScreen, bitmap_offset

FONT_PATH = COMPILER / "assets" / "font4x8-tasword.bin"


def new_screen() -> ZXScreen:
    return ZXScreen(Font4x8.load(FONT_PATH))


def wait_for(predicate) -> None:
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("timed out waiting for test condition")


class GuiFramebufferRegressions(unittest.TestCase):
    def test_published_frame_is_immutable(self):
        screen = new_screen()
        display = TkDisplay(screen)
        screen.mem[bitmap_offset(0, 0)] = 0x80
        display.update()
        frame = display._frame_after(-1)
        self.assertIsNotNone(frame)
        generation, snapshot = frame
        self.assertEqual(generation, 1)
        self.assertEqual(snapshot[bitmap_offset(0, 0)], 0x80)
        screen.mem[bitmap_offset(0, 0)] = 0
        self.assertEqual(snapshot[bitmap_offset(0, 0)], 0x80)

    def test_newer_generation_is_not_lost(self):
        screen = new_screen()
        display = TkDisplay(screen)
        screen.mem[bitmap_offset(0, 0)] = 0x80
        display.update()
        first = display._frame_after(-1)
        self.assertIsNotNone(first)
        first_generation, _ = first
        screen.mem[bitmap_offset(0, 0)] = 0x40
        display.update()
        second = display._frame_after(first_generation)
        self.assertIsNotNone(second)
        second_generation, second_snapshot = second
        self.assertGreater(second_generation, first_generation)
        self.assertEqual(second_snapshot[bitmap_offset(0, 0)], 0x40)
        self.assertIsNone(display._frame_after(second_generation))

    def test_snapshot_renderer_does_not_read_live_screen(self):
        screen = new_screen()
        screen.mem[bitmap_offset(0, 0)] = 0x80
        snapshot = screen.bytes()
        expected = screen.render_rgb()
        screen.mem[bitmap_offset(0, 0)] = 0
        self.assertEqual(render_snapshot_rgb(snapshot), expected)
        self.assertNotEqual(render_snapshot_rgb(screen.bytes()), expected)

    def test_nonwaiting_key_is_discarded(self):
        display = TkDisplay(new_screen())
        self.assertFalse(display._offer_key(ord("x")))
        got = []
        thread = threading.Thread(
            target=lambda: got.append(display.input_char())
        )
        thread.start()
        wait_for(display._waiting_for_key)
        self.assertTrue(display._offer_key(ord("a")))
        self.assertFalse(display._offer_key(ord("b")))
        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(got, [ord("a")])
        self.assertFalse(display._offer_key(ord("c")))

    def test_close_releases_waiting_getchar(self):
        display = TkDisplay(new_screen())
        got = []
        thread = threading.Thread(
            target=lambda: got.append(display.input_char())
        )
        thread.start()
        wait_for(display._waiting_for_key)
        display.close()
        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(got, [-1])

    def test_footer_font_uses_largest_measured_fit(self):
        def measure(size, text):
            return len(text) * size

        width = len(COPYRIGHT_TEXT) * 6
        size = fit_footer_font_size(
            COPYRIGHT_TEXT,
            width,
            measure,
            max_size=9,
        )
        self.assertEqual(size, 6)
        self.assertLessEqual(measure(size, COPYRIGHT_TEXT), width)
        self.assertGreater(measure(size + 1, COPYRIGHT_TEXT), width)


if __name__ == "__main__":
    unittest.main()
