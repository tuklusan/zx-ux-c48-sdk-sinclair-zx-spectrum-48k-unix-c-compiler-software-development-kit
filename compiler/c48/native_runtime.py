# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from dataclasses import dataclass

from .native_format import (
    ObjImage,
    ObjReloc,
    ObjSymbol,
    OBJ_SECTION_TEXT,
    OBJ_SECTION_UNDEF,
    OBJ_SYMBOL_GLOBAL,
)
from .native_link import NativeMember

SYSCALL_GATEWAY = 0xE000


class _Code:
    def __init__(self) -> None:
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.jr_fixups: list[tuple[int, str]] = []

    def emit(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate runtime label {name}")
        self.labels[name] = len(self.data)

    def jr(self, opcode: int, label: str) -> None:
        self.emit(opcode, 0)
        self.jr_fixups.append((len(self.data) - 1, label))

    def finish(self) -> bytes:
        for pos, label in self.jr_fixups:
            if label not in self.labels:
                raise ValueError(f"missing runtime label {label}")
            displacement = self.labels[label] - (pos + 1)
            if not -128 <= displacement <= 127:
                raise ValueError("runtime JR displacement is out of range")
            self.data[pos] = displacement & 0xFF
        return bytes(self.data)


def _sym(name: str, value: int = 0) -> ObjSymbol:
    return ObjSymbol(name, value, OBJ_SECTION_TEXT, OBJ_SYMBOL_GLOBAL)


def _undef(name: str) -> ObjSymbol:
    return ObjSymbol(name, 0, OBJ_SECTION_UNDEF, OBJ_SYMBOL_GLOBAL)


def _single(name: str, code: bytes) -> NativeMember:
    return NativeMember(name, ObjImage(code, 0, (_sym(name),), ()), (name,))


def _syscall_wrapper(name: str, number: int, *, zero_result: bool = False) -> NativeMember:
    code = bytearray((0x3E, number, 0xCD, 0x00, 0xE0))
    if zero_result:
        code.extend((0x21, 0x00, 0x00))
    code.append(0xC9)
    return _single(name, bytes(code))


def _startup() -> NativeMember:
    # Exact pinned crt0 TEXT: CALL main ; CALL exit ; RET
    text = bytes((0xCD, 0x00, 0x00, 0xCD, 0x00, 0x00, 0xC9))
    symbols = (_sym("_start"), _undef("main"), _undef("exit"))
    relocs = (ObjReloc(1, 1), ObjReloc(4, 2))
    return NativeMember("startup", ObjImage(text, 0, symbols, relocs), ("_start",))


def _exit() -> NativeMember:
    # Exact pinned compact runtime archive member.
    return _single("exit", bytes((0xC9,)))


def _mul16() -> NativeMember:
    # HL=multiplicand, DE=multiplier, modulo-16-bit result in HL.
    c = _Code()
    c.emit(0x01, 0x00, 0x00)       # LD BC,0 (result)
    c.emit(0x3E, 0x10)             # LD A,16
    c.label("loop")
    c.emit(0xCB, 0x43)             # BIT 0,E
    c.jr(0x28, "noadd")           # JR Z,noadd
    c.emit(0xE5)                   # PUSH HL
    c.emit(0x09)                   # ADD HL,BC
    c.emit(0x44, 0x4D)             # LD B,H / LD C,L
    c.emit(0xE1)                   # POP HL
    c.label("noadd")
    c.emit(0x29)                   # ADD HL,HL
    c.emit(0xCB, 0x3A, 0xCB, 0x1B) # SRL D / RR E
    c.emit(0x3D)                   # DEC A
    c.jr(0x20, "loop")            # JR NZ,loop
    c.emit(0x60, 0x69, 0xC9)       # LD H,B / LD L,C / RET
    return _single("c48_mul16", c.finish())



def _div16() -> NativeMember:
    # Unsigned core returns quotient in HL and remainder in DE. The signed entry
    # converts magnitudes, reuses the same core, then restores C48 signs.
    c = _Code()
    uoff = len(c.data)
    c.emit(0x7A, 0xB3)              # LD A,D ; OR E
    c.jr(0x20, "u_valid")           # JR NZ
    c.emit(0x21, 0x01, 0x00, 0x3E, 0x01, 0xCD, 0x00, 0xE0, 0x76)
    c.label("u_valid")
    c.emit(0x42, 0x4B)              # BC=divisor
    c.emit(0x11, 0x00, 0x00)        # DE=remainder
    c.emit(0x3E, 0x10)              # A=16 iterations
    c.label("u_loop")
    c.emit(0xF5, 0x29, 0xCB, 0x13, 0xCB, 0x12)
    c.emit(0x7A, 0xB8)              # compare remainder high to divisor high
    c.jr(0x38, "u_no_sub")
    c.jr(0x20, "u_sub")
    c.emit(0x7B, 0xB9)
    c.jr(0x38, "u_no_sub")
    c.label("u_sub")
    c.emit(0xEB, 0xB7, 0xED, 0x42, 0xEB, 0xCB, 0xC5)
    c.label("u_no_sub")
    c.emit(0xF1, 0x3D)
    c.jr(0x20, "u_loop")
    c.emit(0xC9)

    soff = len(c.data)
    c.emit(0x7C, 0xE6, 0x80, 0xF5)  # save dividend sign
    c.emit(0x7C, 0xAA, 0xE6, 0x80, 0xF5)  # save quotient sign
    c.emit(0xCB, 0x7C)
    c.jr(0x28, "s_lhs_ok")
    c.emit(0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67, 0x23)
    c.label("s_lhs_ok")
    c.emit(0xCB, 0x7A)
    c.jr(0x28, "s_rhs_ok")
    c.emit(0xEB, 0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67, 0x23, 0xEB)
    c.label("s_rhs_ok")
    call_pos = len(c.data)
    c.emit(0xCD, 0x00, 0x00)
    c.emit(0xF1, 0xB7)
    c.jr(0x28, "s_q_ok")
    c.emit(0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67, 0x23)
    c.label("s_q_ok")
    c.emit(0xF1, 0xB7)
    c.jr(0x28, "s_done")
    c.emit(0xEB, 0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67, 0x23, 0xEB)
    c.label("s_done")
    c.emit(0xC9)
    text = c.finish()
    symbols = (
        ObjSymbol("c48_udivmod", uoff, OBJ_SECTION_TEXT, OBJ_SYMBOL_GLOBAL),
        ObjSymbol("c48_sdivmod", soff, OBJ_SECTION_TEXT, OBJ_SYMBOL_GLOBAL),
    )
    relocs = (ObjReloc(call_pos + 1, 0),)
    return NativeMember("div16", ObjImage(text, 0, symbols, relocs), ("c48_udivmod", "c48_sdivmod"))



def _getchar() -> NativeMember:
    c = _Code()
    c.emit(0x21, 0x00, 0x00, 0xE5)  # PUSH zero word as one-byte buffer
    c.emit(0x21, 0x00, 0x00, 0x39)  # HL=SP
    c.emit(0x11, 0x00, 0x00, 0x01, 0x01, 0x00)
    c.emit(0x3E, 0x12, 0xCD, 0x00, 0xE0)
    c.emit(0xD1)                     # DE=buffer, flags retained
    c.jr(0x38, "error")
    c.emit(0x7C, 0xB5)
    c.jr(0x28, "eof")
    c.emit(0x63, 0x26, 0x00, 0xC9)  # L=E; H=0; RET
    c.label("eof")
    c.emit(0x21, 0xFF, 0xFF, 0xC9)
    c.label("error")
    c.emit(0x6F, 0x26, 0x00, 0xB7, 0xC9)
    return _single("getchar", c.finish())


def _putchar_exact() -> NativeMember:
    c = _Code()
    c.emit(0x7D, 0xF5, 0xE5)        # save char in AF; push HL as byte buffer
    c.emit(0x21, 0x00, 0x00, 0x39)  # HL=SP
    c.emit(0x11, 0x01, 0x00, 0x01, 0x01, 0x00)
    c.emit(0x3E, 0x13, 0xCD, 0x00, 0xE0)
    c.emit(0xD1)                     # discard buffer, keep syscall flags/A
    c.jr(0x38, "error")
    c.emit(0xF1, 0x6F, 0x26, 0x00, 0xB7, 0xC9)
    c.label("error")
    c.emit(0xC1, 0x6F, 0x26, 0x00, 0xB7, 0xC9)
    return _single("putchar", c.finish())


def _puts() -> NativeMember:
    # Exact pinned P11.35 target-native archive member.
    return _single(
        "puts",
        bytes.fromhex(
            "e50100007eb72804230318f8e11101003e13cd00e0381a210a00"
            "e5210000391101000101003e13cd00e0c13804210000c96f2600b7c9"
        ),
    )


def _strlen() -> NativeMember:
    c = _Code()
    c.emit(0x11, 0x00, 0x00)        # DE=0
    c.label("loop")
    c.emit(0x7E, 0xB7)
    c.jr(0x28, "done")
    c.emit(0x23, 0x13)
    c.jr(0x18, "loop")
    c.label("done")
    c.emit(0xEB, 0xB7, 0xC9)
    return _single("strlen", c.finish())


def _strcmp() -> NativeMember:
    c = _Code()
    c.label("loop")
    c.emit(0x7E, 0x4F, 0x1A, 0x47, 0x79, 0xB8)
    c.jr(0x38, "less")
    c.jr(0x20, "greater")
    c.emit(0xB7)
    c.jr(0x28, "equal")
    c.emit(0x23, 0x13)
    c.jr(0x18, "loop")
    c.label("less")
    c.emit(0x21, 0x00, 0x00, 0x2B, 0xB7, 0xC9)
    c.label("greater")
    c.emit(0x21, 0x01, 0x00, 0xB7, 0xC9)
    c.label("equal")
    c.emit(0x21, 0x00, 0x00, 0xB7, 0xC9)
    return _single("strcmp", c.finish())


def _strcpy() -> NativeMember:
    c = _Code()
    c.emit(0xE5)
    c.label("loop")
    c.emit(0x1A, 0x77, 0x13, 0x23, 0xB7)
    c.jr(0x20, "loop")
    c.emit(0xE1, 0xB7, 0xC9)
    return _single("strcpy", c.finish())


def _strncpy() -> NativeMember:
    c = _Code()
    c.emit(0xE5, 0x78, 0xB1)
    c.jr(0x28, "done")
    c.label("copy")
    c.emit(0x1A, 0x77, 0x23, 0x13, 0x0B, 0xB7)
    c.jr(0x28, "pad_check")
    c.emit(0x78, 0xB1)
    c.jr(0x20, "copy")
    c.jr(0x18, "done")
    c.label("pad_check")
    c.emit(0x78, 0xB1)
    c.jr(0x28, "done")
    c.label("pad")
    c.emit(0xAF, 0x77, 0x23, 0x0B, 0x78, 0xB1)
    c.jr(0x20, "pad")
    c.label("done")
    c.emit(0xE1, 0xB7, 0xC9)
    return _single("strncpy", c.finish())


def _memcpy() -> NativeMember:
    return _single("memcpy", bytes((0xE5, 0x78, 0xB1, 0x28, 0x03, 0xEB, 0xED, 0xB0, 0xE1, 0xB7, 0xC9)))


def _memchr() -> NativeMember:
    c = _Code()
    c.emit(0x78, 0xB1)
    c.jr(0x28, "miss")
    c.emit(0x7B, 0xED, 0xB1)
    c.jr(0x20, "miss")
    c.emit(0x2B, 0xB7, 0xC9)
    c.label("miss")
    c.emit(0x21, 0x00, 0x00, 0xB7, 0xC9)
    return _single("memchr", c.finish())


def _memset() -> NativeMember:
    c = _Code()
    c.emit(0x53, 0xE5, 0x78, 0xB1)  # D=E; save return pointer
    c.jr(0x28, "done")
    c.label("loop")
    c.emit(0x7A, 0x77, 0x23, 0x0B, 0x78, 0xB1)
    c.jr(0x20, "loop")
    c.label("done")
    c.emit(0xE1, 0xB7, 0xC9)
    return _single("memset", c.finish())


def _memmove() -> NativeMember:
    c = _Code()
    c.emit(0xE5, 0xD5)              # saved return dest, saved src
    c.emit(0x78, 0xB1)
    c.jr(0x28, "ret_saved")
    c.emit(0xE5, 0xB7, 0xED, 0x52, 0xE1)  # compare dest-src
    c.jr(0x38, "forward")
    c.jr(0x28, "ret_saved")
    # Compare source+count to destination.
    c.emit(0xEB, 0x09, 0xB7, 0xED, 0x52)
    c.jr(0x38, "forward")
    c.jr(0x28, "forward")
    # Backward overlap.
    c.emit(0xD1, 0xE1, 0xE5)        # DE=src, HL=dest, resave return
    c.emit(0x09, 0x2B, 0xE5, 0xEB, 0x09, 0x2B, 0xD1, 0xED, 0xB8)
    c.emit(0xE1, 0xB7, 0xC9)
    c.label("forward")
    c.emit(0xD1, 0xE1, 0xE5, 0xEB, 0xED, 0xB0, 0xE1, 0xB7, 0xC9)
    c.label("ret_saved")
    c.emit(0xD1, 0xE1, 0xB7, 0xC9)
    return _single("memmove", c.finish())

def _graphics_attr(name: str, selector: int) -> NativeMember:
    # Native-compatible fallback for selectors without a frozen prebuilt member.
    text = bytes((
        0x16, selector,
        0x62,
        0x3E, 0x43,
        0xCD, 0x00, 0xE0,
        0x21, 0x00, 0x00,
        0xC9,
    ))
    return _single(name, text)


def _ink_exact() -> NativeMember:
    return _single(
        "ink",
        bytes.fromhex("7cb7200f1600623e43cd00e0380a210000afc9210100afc96f2600b7c9"),
    )


def _plot_exact() -> NativeMember:
    return _single(
        "plot",
        bytes.fromhex("7cb2200e656b3e40cd00e0380a210000afc9210100afc96f2600b7c9"),
    )


def _udg_clear_exact() -> NativeMember:
    return _single(
        "udg_clear",
        bytes.fromhex("7cb7200c3e4bcd00e0380a210000afc9210100afc96f2600b7c9"),
    )


RUNTIME_MEMBERS: tuple[NativeMember, ...] = (
    _startup(),
    _exit(),
    _mul16(),
    _div16(),
    _getchar(),
    _putchar_exact(),
    _puts(),
    _strlen(),
    _strcmp(),
    _strcpy(),
    _strncpy(),
    _memcpy(),
    _memmove(),
    _memchr(),
    _memset(),
    _syscall_wrapper("yield", 0x02, zero_result=True),
    _syscall_wrapper("sleep", 0x03, zero_result=True),
    _syscall_wrapper("getpid", 0x04),
    _syscall_wrapper("cls", 0x33, zero_result=True),
    _syscall_wrapper("ticks", 0x62),
    _udg_clear_exact(),
    _ink_exact(),
    _graphics_attr("paper", 1),
    _graphics_attr("bright", 2),
    _graphics_attr("flash", 3),
    _graphics_attr("inverse", 4),
    _graphics_attr("over", 5),
    _syscall_wrapper("border", 0x44, zero_result=True),
    _plot_exact(),
)
