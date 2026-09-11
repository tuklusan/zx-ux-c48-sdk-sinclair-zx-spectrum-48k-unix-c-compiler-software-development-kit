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

from c48.screen import BITMAP_SIZE, Font4x8, ZXScreen, bitmap_offset

FONT_PATH = COMPILER / "assets" / "font4x8-tasword.bin"


def new_screen() -> ZXScreen:
    return ZXScreen(Font4x8.load(FONT_PATH))


class DeferredWrapRegressions(unittest.TestCase):
    def test_cls_initializes_and_clears_pending_wrap(self):
        s = new_screen()
        self.assertEqual((s.row, s.col, s.wrap_pending), (0, 0, False))
        s.row = 9
        s.col = 63
        s.wrap_pending = True
        s.mem[bitmap_offset(0, 0)] = 0xFF
        self.assertEqual(s.cls(), 0)
        self.assertEqual((s.row, s.col, s.wrap_pending), (0, 0, False))
        self.assertEqual(s.mem[:BITMAP_SIZE], b"\0" * BITMAP_SIZE)

    def test_final_column_printable_defers_wrap_until_next_printable(self):
        s = new_screen()
        s.row = 4
        s.col = 63
        s.putchar(ord("A"))
        self.assertEqual((s.row, s.col, s.wrap_pending), (4, 63, True))
        s.putchar(ord("B"))
        self.assertEqual((s.row, s.col, s.wrap_pending), (5, 1, False))

    def test_bottom_right_printable_does_not_scroll_until_next_printable(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0x11
        s.mem[bitmap_offset(0, 8)] = 0x22
        s.row = 23
        s.col = 63
        s.putchar(ord("X"))
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 63, True))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x11)
        s.putchar(ord("Y"))
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 1, False))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x22)

    def test_pending_cr_cancels_wrap_without_scroll(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0x31
        s.row = 23
        s.col = 63
        s.wrap_pending = True
        s.putchar(13)
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 0, False))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x31)

    def test_pending_lf_scrolls_exactly_once(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0x11
        s.mem[bitmap_offset(0, 8)] = 0x22
        s.mem[bitmap_offset(0, 16)] = 0x33
        s.row = 23
        s.col = 63
        s.wrap_pending = True
        s.putchar(10)
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 0, False))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x22)
        self.assertEqual(s.mem[bitmap_offset(0, 8)], 0x33)

    def test_pending_bs_moves_left_without_crossing_row(self):
        s = new_screen()
        s.row = 12
        s.col = 63
        s.wrap_pending = True
        s.putchar(8)
        self.assertEqual((s.row, s.col, s.wrap_pending), (12, 62, False))
        s.col = 0
        s.wrap_pending = True
        s.putchar(8)
        self.assertEqual((s.row, s.col, s.wrap_pending), (12, 0, False))

    def test_tab_uses_logical_multiple_of_eight_and_cancels_pending(self):
        s = new_screen()
        s.row = 3
        s.col = 1
        s.putchar(9)
        self.assertEqual((s.row, s.col, s.wrap_pending), (3, 8, False))
        s.col = 56
        s.wrap_pending = False
        s.putchar(9)
        self.assertEqual((s.row, s.col, s.wrap_pending), (4, 0, False))
        s.row = 7
        s.col = 63
        s.wrap_pending = True
        s.putchar(9)
        self.assertEqual((s.row, s.col, s.wrap_pending), (8, 0, False))

    def test_bottom_row_tab_scrolls_exactly_once(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0x41
        s.mem[bitmap_offset(0, 8)] = 0x52
        s.mem[bitmap_offset(0, 16)] = 0x63
        s.row = 23
        s.col = 63
        s.wrap_pending = True
        s.putchar(9)
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 0, False))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x52)
        self.assertEqual(s.mem[bitmap_offset(0, 8)], 0x63)

    def test_ff_clears_display_homes_and_cancels_pending(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0xFF
        s.row = 23
        s.col = 63
        s.wrap_pending = True
        s.putchar(12)
        self.assertEqual((s.row, s.col, s.wrap_pending), (0, 0, False))
        self.assertEqual(s.mem[:BITMAP_SIZE], b"\0" * BITMAP_SIZE)
        self.assertEqual(s.mem[BITMAP_SIZE:], bytes([s.attr()]) * 768)

    def test_ignored_control_preserves_pending_state_and_screen(self):
        s = new_screen()
        s.row = 10
        s.col = 63
        s.wrap_pending = True
        before = s.bytes()
        self.assertEqual(s.putchar(1), 1)
        self.assertEqual((s.row, s.col, s.wrap_pending), (10, 63, True))
        self.assertEqual(s.bytes(), before)

    def test_puts_at_bottom_right_causes_only_explicit_lf_scroll(self):
        s = new_screen()
        s.mem[bitmap_offset(0, 0)] = 0x12
        s.mem[bitmap_offset(0, 8)] = 0x34
        s.mem[bitmap_offset(0, 16)] = 0x56
        s.row = 23
        s.col = 63
        s.puts(b"A")
        self.assertEqual((s.row, s.col, s.wrap_pending), (23, 0, False))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x34)
        self.assertEqual(s.mem[bitmap_offset(0, 8)], 0x56)

    def test_exact_line_and_screenful_stream_boundaries(self):
        line = new_screen()
        for _ in range(64):
            line.putchar(ord("A"))
        self.assertEqual((line.row, line.col, line.wrap_pending), (0, 63, True))
        line.putchar(ord("B"))
        self.assertEqual((line.row, line.col, line.wrap_pending), (1, 1, False))

        screen = new_screen()
        for _ in range(64):
            screen.putchar(ord("A"))
        top_band = bytes(
            screen.mem[bitmap_offset(x * 8, y)]
            for y in range(8)
            for x in range(32)
        )
        for _ in range(64 * 23):
            screen.putchar(ord("B"))
        self.assertEqual((screen.row, screen.col, screen.wrap_pending), (23, 63, True))
        self.assertEqual(
            bytes(
                screen.mem[bitmap_offset(x * 8, y)]
                for y in range(8)
                for x in range(32)
            ),
            top_band,
        )
        screen.putchar(ord("C"))
        self.assertEqual((screen.row, screen.col, screen.wrap_pending), (23, 1, False))
        self.assertNotEqual(
            bytes(
                screen.mem[bitmap_offset(x * 8, y)]
                for y in range(8)
                for x in range(32)
            ),
            top_band,
        )

    def test_puts_matches_chunked_putchar_then_lf_at_right_margin(self):
        direct = new_screen()
        chunked = new_screen()
        data = b"A" * 64
        direct.puts(data)
        for b in data:
            chunked.putchar(b)
        chunked.putchar(10)
        self.assertEqual(direct.bytes(), chunked.bytes())
        self.assertEqual(
            (direct.row, direct.col, direct.wrap_pending),
            (chunked.row, chunked.col, chunked.wrap_pending),
        )

    def test_print_at_cross_boundary_matches_temporary_console_state(self):
        reference = new_screen()
        reference.row = 2
        reference.col = 63
        reference.putchar(ord("A"))
        reference.putchar(ord("B"))

        positioned = new_screen()
        positioned.row = 7
        positioned.col = 11
        positioned.wrap_pending = False
        self.assertEqual(positioned.print_at(2, 63, b"AB"), 0)
        self.assertEqual(positioned.bytes(), reference.bytes())
        self.assertEqual(
            (positioned.row, positioned.col, positioned.wrap_pending),
            (7, 11, False),
        )

    def test_print_at_preserves_sequential_cursor_and_pending_state(self):
        s = new_screen()
        s.row = 5
        s.col = 63
        s.wrap_pending = True
        s.mem[bitmap_offset(0, 0)] = 0x21
        s.mem[bitmap_offset(0, 8)] = 0x43
        self.assertEqual(s.print_at(23, 63, b"Z"), 0)
        self.assertEqual((s.row, s.col, s.wrap_pending), (5, 63, True))
        self.assertEqual(s.mem[bitmap_offset(0, 0)], 0x21)
        self.assertEqual(s.mem[bitmap_offset(0, 8)], 0x43)
        s.row = 2
        s.col = 10
        s.wrap_pending = False
        self.assertEqual(s.print_at(0, 63, b"Q"), 0)
        self.assertEqual((s.row, s.col, s.wrap_pending), (2, 10, False))
        s.putchar(ord("R"))
        self.assertEqual((s.row, s.col, s.wrap_pending), (2, 11, False))


if __name__ == "__main__":
    unittest.main()
