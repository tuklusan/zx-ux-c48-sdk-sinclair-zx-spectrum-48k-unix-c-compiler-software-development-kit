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
"""Permanent regression probes for graphics review Batch-5A."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
SRC = SDK / "usr" / "src" / "demos"
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_file
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")


class GraphicsReviewBatch5ATests(unittest.TestCase):
    def test_mobius_seam_keeps_full_turn_endpoint(self):
        src = (SRC / "mobius.c").read_text(encoding="ascii")
        self.assertIn("u2 = (i + 1) * 256 / 20;", src)
        self.assertNotIn("if (i == 19) u2 = 0;", src)

    def test_firework_preserves_top_label_band(self):
        src = (SRC / "firework.c").read_text(encoding="ascii")
        self.assertIn("y1 >= 16 && y1 < 184", src)
        self.assertIn("y2 >= 16 && y2 < 184", src)
        self.assertIn("draw(x, 16, x, 18 +", src)
        self.assertNotIn("draw(x, 0, x, 18 +", src)

    def test_projection_muldiv_handles_large_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copy2(SRC / "demoapi.h", root / "demoapi.h")
            source = root / "probe.c"
            source.write_text(
                '#include "demoapi.h"\n'
                'int main(void)\n'
                '{\n'
                '    if (d_px(154, 84) != 258) return 1;\n'
                '    if (d_px(-154, 84) != -2) return 2;\n'
                '    if (d_py(154, 84) != 226) return 3;\n'
                '    if (d_py(-154, 84) != -34) return 4;\n'
                '    return 0;\n'
                '}\n',
                encoding="ascii",
                newline="\n",
            )
            program = compile_file(source)
            vm = C48VM(program, ZXScreen(FONT), argv=["probe"])
            self.assertEqual(vm.run(), 0)


class GraphicsReviewBatch5BTests(unittest.TestCase):
    def test_sprites_preserves_top_label_band(self):
        src = (SRC / "sprites.c").read_text(encoding="ascii")
        self.assertIn("y = 16 + (i * 29 + f * 2) % 160;", src)
        self.assertNotIn("y = (i * 29 + f * 2) % 176;", src)

    def test_warp_preserves_top_label_band(self):
        src = (SRC / "warp.c").read_text(encoding="ascii")
        self.assertIn("y1 >= 16 && y1 < 184", src)
        self.assertIn("y2 >= 16 && y2 < 184", src)

    def test_muldiv_large_divisor_and_small_divisor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copy2(SRC / "demoapi.h", root / "demoapi.h")
            source = root / "probe.c"
            source.write_text(
                '#include "demoapi.h"\n'
                'int main(void)\n'
                '{\n'
                '    if (d_muldiv(160, 220, 32767) != 1) return 1;\n'
                '    if (d_muldiv(-160, 220, 32767) != -1) return 2;\n'
                '    if (d_muldiv(100, 220, 1) != 22000) return 3;\n'
                '    return 0;\n'
                '}\n',
                encoding="ascii",
                newline="\n",
            )
            program = compile_file(source)
            vm = C48VM(program, ZXScreen(FONT), argv=["probe"])
            self.assertEqual(vm.run(), 0)


if __name__ == "__main__":
    unittest.main()
