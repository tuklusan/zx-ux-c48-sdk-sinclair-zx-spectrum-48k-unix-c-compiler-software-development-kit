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
import subprocess
import threading
import time
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
sys.path.insert(0, str(COMPILER))

from c48.gui import (
    COPYRIGHT_TEXT,
    BORDER_X,
    BORDER_Y,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    TkDisplay,
    VISUAL_FRAME_DWELL_MS,
    key_event_bytes,
    fit_footer_font_size,
    largest_fully_mapped_scale,
    render_snapshot_frame_rgb,
    render_snapshot_rgb,
    rectangle_fits_bounds,
)
from c48.screen import Font4x8, ZXScreen, bitmap_offset
from verify_gui_desktop import (
    AQUA_MAX_CHANNEL_DRIFT,
    _aqua_palette_spatial_match,
    _terminate_process_tree,
)

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
        generation, snapshot, border_color = frame
        self.assertEqual(generation, 1)
        self.assertEqual(border_color, 0)
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
        first_generation, _, first_border = first
        self.assertEqual(first_border, 0)
        screen.mem[bitmap_offset(0, 0)] = 0x40
        display.update()
        second = display._frame_after(first_generation)
        self.assertIsNotNone(second)
        second_generation, second_snapshot, second_border = second
        self.assertEqual(second_border, 0)
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
        framed = render_snapshot_frame_rgb(snapshot, 2)
        self.assertEqual(len(framed), FRAME_WIDTH * FRAME_HEIGHT * 3)
        self.assertEqual(framed[:3], bytes((205, 0, 0)))
        paper = (BORDER_Y * FRAME_WIDTH + BORDER_X) * 3
        self.assertEqual(framed[paper:paper + 3], expected[:3])

    def test_fast_renderer_matches_reference_for_flash_phases(self):
        screen = new_screen()
        for index in range(len(screen.mem)):
            screen.mem[index] = (index * 73 + 19) & 0xFF
        snapshot = screen.bytes()
        self.assertEqual(
            render_snapshot_rgb(snapshot, flash_phase=False),
            screen.render_rgb(flash_phase=False),
        )
        self.assertEqual(
            render_snapshot_rgb(snapshot, flash_phase=True),
            screen.render_rgb(flash_phase=True),
        )

    def test_present_waits_for_visual_release_not_tk_commit(self):
        display = TkDisplay(new_screen())
        generation = display.update()
        finished = []
        thread = threading.Thread(
            target=lambda: (display.present("yield"), finished.append(True))
        )
        thread.start()
        time.sleep(0.02)
        self.assertTrue(thread.is_alive())
        display._mark_committed(generation)
        time.sleep(0.02)
        self.assertTrue(thread.is_alive())
        self.assertEqual(display._take_present_request(), (generation, "yield"))
        display._mark_presented(generation, "yield", VISUAL_FRAME_DWELL_MS)
        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(finished, [True])

        prompt = TkDisplay(new_screen())
        prompt_generation = prompt.update()
        prompt_done = []
        prompt_thread = threading.Thread(
            target=lambda: (prompt.present("input"), prompt_done.append(True))
        )
        prompt_thread.start()
        time.sleep(0.02)
        prompt._mark_committed(prompt_generation)
        self.assertEqual(
            prompt._take_present_request(), (prompt_generation, "input")
        )
        prompt._mark_presented(prompt_generation, "input", 0)
        prompt_thread.join(1.0)
        self.assertEqual(prompt_done, [True])

        closing = TkDisplay(new_screen())
        closing.update()
        released = []
        waiter = threading.Thread(
            target=lambda: (closing.present("sleep"), released.append(True))
        )
        waiter.start()
        time.sleep(0.02)
        self.assertTrue(waiter.is_alive())
        closing.close()
        waiter.join(1.0)
        self.assertFalse(waiter.is_alive())
        self.assertEqual(released, [True])

    def test_typeahead_fifo_preserves_rapid_text(self):
        self.assertEqual(key_event_bytes("Escape", ""), (7,))
        display = TkDisplay(new_screen())
        expected = b"rapid text\n"
        for value in expected:
            self.assertTrue(display._offer_key(value))
        actual = bytes(display.input_char() for _ in expected)
        self.assertEqual(actual, expected)

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

    def test_display_scale_keeps_largest_fully_mapped_canvas(self):
        attempts = []

        def map_scale(scale):
            attempts.append(scale)
            if scale == 3:
                return 960, 642
            return FRAME_WIDTH * scale, FRAME_HEIGHT * scale

        self.assertEqual(largest_fully_mapped_scale(3, map_scale), 2)
        self.assertEqual(attempts, [3, 2])

    def test_display_scale_keeps_requested_scale_when_fully_mapped(self):
        attempts = []

        def map_scale(scale):
            attempts.append(scale)
            return FRAME_WIDTH * scale, FRAME_HEIGHT * scale

        self.assertEqual(largest_fully_mapped_scale(3, map_scale), 3)
        self.assertEqual(attempts, [3])

    def test_display_scale_fails_if_even_1x_is_clipped(self):
        with self.assertRaisesRegex(RuntimeError, "cannot fully map"):
            largest_fully_mapped_scale(1, lambda scale: (319, 239))
        with self.assertRaisesRegex(ValueError, "scale must be positive"):
            largest_fully_mapped_scale(0, lambda scale: (320, 240))

    def test_client_rectangle_must_fit_usable_desktop_bounds(self):
        work = (0, 0, 1024, 720)
        self.assertTrue(rectangle_fits_bounds(55, 31, 642, 522, work))
        self.assertFalse(rectangle_fits_bounds(54, 31, 962, 762, work))
        self.assertFalse(rectangle_fits_bounds(55, 31, 960, 720, work))
        self.assertFalse(rectangle_fits_bounds(-1, 0, 320, 240, work))
        self.assertFalse(rectangle_fits_bounds(0, 0, 0, 240, work))

    def test_failed_gui_cleanup_is_bounded(self):
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        started = time.monotonic()
        stdout, stderr = _terminate_process_tree(process)
        self.assertLess(time.monotonic() - started, 5.0)
        self.assertIsNotNone(process.poll())
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")

        match = _aqua_palette_spatial_match(
            [(0, 0, 0), (0, 255, 255), (205, 0, 0), (255, 0, 255)],
            [(1, 0, 0), (16, 255, 254), (204, 2, 0), (254, 3, 254)],
        )
        self.assertIsNotNone(match)
        self.assertEqual(match["max_channel_delta"], 16)
        self.assertEqual(AQUA_MAX_CHANNEL_DRIFT, 24)
        self.assertIsNone(
            _aqua_palette_spatial_match([(0, 255, 255)], [(0, 255, 0)])
        )
        self.assertIsNone(
            _aqua_palette_spatial_match([(0, 205, 0)], [(25, 205, 0)])
        )


if __name__ == "__main__":
    unittest.main()
