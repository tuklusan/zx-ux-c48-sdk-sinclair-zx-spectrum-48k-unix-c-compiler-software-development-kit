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
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
sys.path.insert(0, str(COMPILER))

from c48.gui import TkDisplay, render_snapshot_rgb
from c48.screen import Font4x8, ZXScreen, bitmap_offset

FONT_PATH = COMPILER / "assets" / "font4x8-tasword.bin"


def new_screen() -> ZXScreen:
    return ZXScreen(Font4x8.load(FONT_PATH))


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


if __name__ == "__main__":
    unittest.main()
