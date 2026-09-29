# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.gui import footer_config, footer_text


class RoundRegressions(unittest.TestCase):
    def test_running_footer_is_unchanged(self) -> None:
        self.assertEqual(footer_text(False), "Shift+Space = BREAK")
        self.assertEqual(
            footer_config(False),
            {"text": "Shift+Space = BREAK"},
        )

    def test_completed_footer_is_yellow_and_red(self) -> None:
        self.assertEqual(
            footer_config(True),
            {
                "text": "Program ended - Shift+Space to close",
                "background": "yellow",
                "foreground": "red",
            },
        )

    def test_incremental_games_keep_clear_out_of_input_path(self) -> None:
        games = SDK / "usr" / "src" / "games"
        expectations = {
            "hangman.c": 1,
            "maze.c": 1,
            "advent.c": 1,
            "bgammon.c": 1,
            "fish.c": 1,
            "trek.c": 1,
        }
        for name, clears in expectations.items():
            text = (games / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("cls();"), clears, name)

        snake = (games / "snake.c").read_text(encoding="utf-8")
        self.assertEqual(snake.count("cls();"), 3)
        self.assertIn("s_draw_board();\n    while (1)", snake)


if __name__ == "__main__":
    unittest.main()
