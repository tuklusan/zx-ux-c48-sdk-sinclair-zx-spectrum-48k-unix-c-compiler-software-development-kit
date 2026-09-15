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
"""C48 host VM profile with Sinclair ROM math and read-only object I/O."""
from __future__ import annotations

from pathlib import Path

from . import rommath
from .errors import RuntimeExit
from .float5 import Float5Error
from .typesys import FLOAT, INT
from .vm import C48VM, Value


class RomMathVM(C48VM):
    """C48VM with ROM math and target-shaped read-only object I/O."""

    _OBJECT_CHARS = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._object_handles: dict[int, list[object]] = {}
        self.builtins["open"] = self._b_open
        self.builtins["close"] = self._b_close
        self.builtins["read"] = self._b_read
        self.builtins["seek"] = self._b_seek

    def _object_root(self) -> Path:
        return Path(self.argv[0]).resolve().parent

    def _object_path(self, raw: bytes) -> Path | None:
        try:
            name = raw.decode("ascii")
        except UnicodeDecodeError:
            return None
        if not 1 <= len(name) <= 10 or name in {".", ".."}:
            return None
        if any(ch not in self._OBJECT_CHARS for ch in name):
            return None
        root = self._object_root()
        path = (root / name).resolve()
        if path.parent != root:
            return None
        return path

    def _b_open(self, args):
        if len(args) != 2 or self._int_math(args[1]) != 1:
            return Value(INT, -1)
        raw = self._read_cstr(self._as_pointer(args[0]))
        path = self._object_path(raw)
        if path is None:
            return Value(INT, -1)
        try:
            if not path.is_file():
                return Value(INT, -1)
            data = path.read_bytes()
        except OSError:
            return Value(INT, -1)
        if len(data) > 65535:
            return Value(INT, -1)
        for handle in range(3, 16):
            if handle not in self._object_handles:
                self._object_handles[handle] = [data, 0]
                return Value(INT, handle)
        return Value(INT, -1)

    def _b_close(self, args):
        if len(args) != 1:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        if handle not in self._object_handles:
            return Value(INT, -1)
        del self._object_handles[handle]
        return Value(INT, 0)

    def _b_read(self, args):
        if len(args) != 3:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        state = self._object_handles.get(handle)
        if state is None:
            return Value(INT, -1)
        count = self._to_unsigned(args[2])
        if count == 0:
            return Value(INT, 0)
        data = state[0]
        pos = state[1]
        assert isinstance(data, bytes) and isinstance(pos, int)
        take = min(count, len(data) - pos)
        if take <= 0:
            return Value(INT, 0)
        ptr = self._as_pointer(args[1])
        self.mem.require_range(ptr, take, write=True)
        self.mem.write_bytes(ptr.address, data[pos:pos + take])
        state[1] = pos + take
        return Value(INT, take)

    def _b_seek(self, args):
        if len(args) != 2:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        state = self._object_handles.get(handle)
        if state is None:
            return Value(INT, -1)
        pos = self._to_unsigned(args[1])
        data = state[0]
        assert isinstance(data, bytes)
        if pos > len(data):
            return Value(INT, -1)
        state[1] = pos
        return Value(INT, 0)

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
