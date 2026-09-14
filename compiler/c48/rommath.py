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
"""Native Sinclair ZX Spectrum 48K ROM floating-point math.

The routines below are a source-level port of the calculator bytecode in the
48K ROM disassembly shipped in ``docs/reference/rom-disassemblies/spectrum-48k``.
Every calculator arithmetic step is quantized back to :class:`Float5`, and the
ROM's compressed constants and Chebyshev series are used verbatim.
"""
from __future__ import annotations

from .float5 import Float5, Float5Error


ZERO = Float5.zero()
ONE = Float5.from_int(1)
HALF = Float5(bytes((0x80, 0x00, 0x00, 0x00, 0x00)))
PI_OVER_2 = Float5(bytes((0x81, 0x49, 0x0F, 0xDA, 0xA2)))


def _stk_data(*data: int) -> Float5:
    """Expand one ROM ``stk-data`` compressed numeric literal."""
    if not data:
        raise AssertionError("empty stk-data literal")
    header = data[0]
    count = ((header >> 6) & 0x03) + 1
    exponent = header & 0x3F
    pos = 1
    if exponent == 0:
        if pos >= len(data):
            raise AssertionError("truncated stk-data exponent")
        exponent = data[pos]
        pos += 1
    exponent += 0x50
    mantissa = list(data[pos:pos + count])
    if len(mantissa) != count:
        raise AssertionError("truncated stk-data mantissa")
    mantissa.extend([0] * (4 - count))
    return Float5(bytes((exponent, *mantissa)))


def _restack(value: Float5) -> Float5:
    if value.is_zero():
        return ZERO
    return Float5.from_fraction(value.to_fraction(), prefer_integer=False)


def _neg(value: Float5) -> Float5:
    if value.is_zero():
        return value
    raw = bytearray(value.raw)
    if raw[0] != 0:
        raw[1] ^= 0x80
        return Float5(bytes(raw))
    return Float5.from_fraction(-value.to_fraction())


def _abs(value: Float5) -> Float5:
    if value.is_zero():
        return value
    raw = bytearray(value.raw)
    if raw[0] != 0:
        raw[1] &= 0x7F
        return Float5(bytes(raw))
    return Float5.from_fraction(abs(value.to_fraction()))


def _floor(value: Float5) -> Float5:
    f = value.to_fraction()
    n = f.numerator // f.denominator
    return Float5.from_int(n)


def _series(x: Float5, coefficients: tuple[Float5, ...]) -> Float5:
    """Port of ROM routine ``series-xx`` at 0x3449."""
    twice_x = x.add(x)
    current = ZERO
    mem1 = ZERO
    mem2 = ZERO
    for coefficient in coefficients:
        mem1 = mem2
        new_value = current.mul(twice_x).sub(mem2).add(coefficient)
        mem2 = current
        current = new_value
    return current.sub(mem1)


_INV_2PI = _stk_data(0xEE, 0x22, 0xF9, 0x83, 0x6E)
_LOG2_E = _stk_data(0xF1, 0x38, 0xAA, 0x3B, 0x29)
_POINT_EIGHT = _stk_data(0xF0, 0x4C, 0xCC, 0xCC, 0xCD)
_LN_2 = _stk_data(0xF0, 0x31, 0x72, 0x17, 0xF8)
_TWO_POINT_FIVE = _stk_data(0x32, 0x20)

_SIN_COEFFICIENTS = tuple(
    _stk_data(*data)
    for data in (
        (0x14, 0xE6),
        (0x5C, 0x1F, 0x0B),
        (0xA3, 0x8F, 0x38, 0xEE),
        (0xE9, 0x15, 0x63, 0xBB, 0x23),
        (0xEE, 0x92, 0x0D, 0xCD, 0xED),
        (0xF1, 0x23, 0x5D, 0x1B, 0xEA),
    )
)

_EXP_COEFFICIENTS = tuple(
    _stk_data(*data)
    for data in (
        (0x13, 0x36),
        (0x58, 0x65, 0x66),
        (0x9D, 0x78, 0x65, 0x40),
        (0xA2, 0x60, 0x32, 0xC9),
        (0xE7, 0x21, 0xF7, 0xAF, 0x24),
        (0xEB, 0x2F, 0xB0, 0xB0, 0x14),
        (0xEE, 0x7E, 0xBB, 0x94, 0x58),
        (0xF1, 0x3A, 0x7E, 0xF8, 0xCF),
    )
)

_LN_COEFFICIENTS = tuple(
    _stk_data(*data)
    for data in (
        (0x11, 0xAC),
        (0x14, 0x09),
        (0x56, 0xDA, 0xA5),
        (0x59, 0x30, 0xC5),
        (0x5C, 0x90, 0xAA),
        (0x9E, 0x70, 0x6F, 0x61),
        (0xA1, 0xCB, 0xDA, 0x96),
        (0xA4, 0x31, 0x9F, 0xB4),
        (0xE7, 0xA0, 0xFE, 0x5C, 0xFC),
        (0xEA, 0x1B, 0x43, 0xCA, 0x36),
        (0xED, 0xA7, 0x9C, 0x7E, 0x5E),
        (0xF0, 0x6E, 0x23, 0x80, 0x93),
    )
)

_ATAN_COEFFICIENTS = tuple(
    _stk_data(*data)
    for data in (
        (0x10, 0xB2),
        (0x13, 0x0E),
        (0x55, 0xE4, 0x8D),
        (0x58, 0x39, 0xBC),
        (0x5B, 0x98, 0xFD),
        (0x9E, 0x00, 0x36, 0x75),
        (0xA0, 0xDB, 0xE8, 0xB4),
        (0x63, 0x42, 0xC4),
        (0xE6, 0xB5, 0x09, 0x36, 0xBE),
        (0xE9, 0x36, 0x73, 0x1B, 0x5D),
        (0xEC, 0xD8, 0xDE, 0x63, 0xBE),
        (0xF0, 0x61, 0xA1, 0xB3, 0x0C),
    )
)


def _get_argt(value: Float5) -> tuple[Float5, bool]:
    """Port of ROM ``get-argt``; return reduced argument and cosine sign flag."""
    x = _restack(value)
    turns = x.mul(_INV_2PI)
    nearest = _floor(turns.add(HALF))
    y = turns.sub(nearest)
    y = y.add(y)
    y = y.add(y)
    z = _abs(y).sub(ONE)
    cosine_negative = z.compare(ZERO) > 0
    if not cosine_negative:
        return y, False
    z = z.sub(ONE)
    if y.compare(ZERO) < 0:
        return z, True
    return _neg(z), True


def sin(value: Float5) -> Float5:
    y, _ = _get_argt(value)
    z = y.mul(y)
    z = z.add(z).sub(ONE)
    return y.mul(_series(z, _SIN_COEFFICIENTS))


def cos(value: Float5) -> Float5:
    y, cosine_negative = _get_argt(value)
    y = _abs(y).sub(ONE)
    if not cosine_negative:
        y = _neg(y)
    z = y.mul(y)
    z = z.add(z).sub(ONE)
    return y.mul(_series(z, _SIN_COEFFICIENTS))


def tan(value: Float5) -> Float5:
    return sin(value).div(cos(value))


def atan(value: Float5) -> Float5:
    x = _restack(value)
    if x.raw[0] < 0x81:
        argument = x
        offset = ZERO
    else:
        argument = _neg(ONE).div(x)
        offset = PI_OVER_2 if argument.compare(ZERO) < 0 else _neg(PI_OVER_2)
    z = argument.mul(argument)
    z = z.add(z).sub(ONE)
    correction = argument.mul(_series(z, _ATAN_COEFFICIENTS))
    return offset.add(correction)


def sqrt(value: Float5) -> Float5:
    if value.is_zero():
        return value
    return pow(value, HALF)


def asin(value: Float5) -> Float5:
    x = value
    y2 = ONE.sub(x.mul(x))
    y = sqrt(y2)
    half_angle = atan(x.div(y.add(ONE)))
    return half_angle.add(half_angle)


def acos(value: Float5) -> Float5:
    return PI_OVER_2.sub(asin(value))


def _scale_pow2(value: Float5, exponent: int) -> Float5:
    if value.is_zero():
        return value
    value = _restack(value)
    raw = bytearray(value.raw)
    scaled = raw[0] + exponent
    if scaled <= 0:
        return ZERO
    if scaled > 0xFF:
        raise Float5Error("exp range failure")
    raw[0] = scaled
    return Float5(bytes(raw))


def exp(value: Float5) -> Float5:
    x = _restack(value)
    scaled = x.mul(_LOG2_E)
    whole = _floor(scaled)
    fraction = scaled.sub(whole)
    z = fraction.add(fraction).sub(ONE)
    result = _series(z, _EXP_COEFFICIENTS)
    return _scale_pow2(result, whole.trunc_int())


def log(value: Float5) -> Float5:
    x = _restack(value)
    if x.compare(ZERO) <= 0:
        raise Float5Error("log domain/range failure")

    original_exponent = x.raw[0]
    raw = bytearray(x.raw)
    raw[0] = 0x80
    mantissa = Float5(bytes(raw))
    exponent = Float5.from_int(original_exponent - 0x80)

    if mantissa.sub(_POINT_EIGHT).compare(ZERO) <= 0:
        exponent = exponent.sub(ONE)
        raw = bytearray(mantissa.raw)
        raw[0] += 1
        mantissa = Float5(bytes(raw))

    exponent_term = exponent.mul(_LN_2)
    u = mantissa.sub(HALF).sub(HALF)
    z = u.mul(_TWO_POINT_FIVE).sub(HALF)
    return exponent_term.add(u.mul(_series(z, _LN_COEFFICIENTS)))


def pow(base: Float5, exponent: Float5) -> Float5:
    if base.is_zero():
        if exponent.is_zero():
            return ONE
        if exponent.compare(ZERO) > 0:
            return ZERO
        raise Float5Error("pow domain/range failure")
    return exp(exponent.mul(log(base)))


_UNARY = {
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "asin": asin,
    "acos": acos,
    "atan": atan,
    "sqrt": sqrt,
    "exp": exp,
    "log": log,
}


def unary(name: str, value: Float5) -> Float5:
    try:
        fn = _UNARY[name]
    except KeyError as exc:
        raise Float5Error(f"unknown ROM math function {name}") from exc
    return fn(value)
