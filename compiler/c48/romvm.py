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
"""C48 host VM profile with the Sinclair 48K ROM math path enabled."""
from __future__ import annotations

from . import rommath
from .errors import RuntimeExit
from .float5 import Float5Error
from .typesys import FLOAT
from .vm import C48VM, Value


class RomMathVM(C48VM):
    """C48VM that uses the ROM-derived transcendental implementation."""

    def _math1(self, name, args):
        if self.approximate_rom_math:
            return super()._math1(name, args)
        try:
            return Value(FLOAT, rommath.unary(name, self._farg(args, 0)))
        except Float5Error:
            raise RuntimeExit(1)

    def _b_pow(self, args):
        if self.approximate_rom_math:
            return super()._b_pow(args)
        try:
            base = self._farg(args, 0)
            exponent = self._farg(args, 1)
            return Value(FLOAT, rommath.pow(base, exponent))
        except Float5Error:
            raise RuntimeExit(1)
