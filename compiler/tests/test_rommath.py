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

from c48 import rommath
from c48.float5 import Float5, Float5Error


class RomMathTests(unittest.TestCase):
    def f(self, text: str) -> Float5:
        return Float5.from_decimal(text)

    def assert_hex(self, actual: Float5, expected: str) -> None:
        self.assertEqual(actual.hex(), expected)

    def test_rom_reference_points(self) -> None:
        zero = self.f("0")
        one = self.f("1")
        half = self.f("0.5")
        self.assert_hex(rommath.sin(zero), "0000000000")
        self.assert_hex(rommath.cos(zero), "0000010000")
        self.assert_hex(rommath.atan(one), "80490fdaa2")
        self.assert_hex(rommath.asin(one), "81490fdaa2")
        self.assert_hex(rommath.acos(one), "0000000000")
        self.assert_hex(rommath.exp(zero), "8100000000")
        self.assert_hex(rommath.log(one), "0000000000")
        self.assert_hex(rommath.sqrt(self.f("4")), "8200000000")
        self.assert_hex(rommath.sin(half), "7f757743a3")
        self.assert_hex(rommath.cos(half), "8060a94033")

    def test_rom_zero_power_rules(self) -> None:
        zero = self.f("0")
        self.assert_hex(rommath.pow(zero, zero), "0000010000")
        self.assert_hex(rommath.pow(zero, self.f("2")), "0000000000")
        with self.assertRaises(Float5Error):
            rommath.pow(zero, self.f("-1"))

    def test_rom_negative_base_and_domains(self) -> None:
        with self.assertRaises(Float5Error):
            rommath.pow(self.f("-2"), self.f("2"))
        with self.assertRaises(Float5Error):
            rommath.log(self.f("0"))
        with self.assertRaises(Float5Error):
            rommath.log(self.f("-1"))
        with self.assertRaises(Float5Error):
            rommath.sqrt(self.f("-1"))
        with self.assertRaises(Float5Error):
            rommath.asin(self.f("1.01"))
        with self.assertRaises(Float5Error):
            rommath.acos(self.f("-1.01"))

    def test_unary_dispatch(self) -> None:
        value = self.f("0.25")
        for name in (
            "sin", "cos", "tan", "asin", "acos",
            "atan", "sqrt", "exp", "log",
        ):
            direct = getattr(rommath, name)(value)
            self.assertEqual(rommath.unary(name, value), direct)
        with self.assertRaises(Float5Error):
            rommath.unary("bogus", value)


if __name__ == "__main__":
    unittest.main()
