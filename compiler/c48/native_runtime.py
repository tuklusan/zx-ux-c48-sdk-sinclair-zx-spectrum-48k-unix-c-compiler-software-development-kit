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
    # CALL main ; CALL exit ; HALT
    text = bytes((0xCD, 0x00, 0x00, 0xCD, 0x00, 0x00, 0x76))
    symbols = (_sym("_start"), _undef("main"), _undef("exit"))
    relocs = (ObjReloc(1, 1), ObjReloc(4, 2))
    return NativeMember("startup", ObjImage(text, 0, symbols, relocs), ("_start",))


def _exit() -> NativeMember:
    # HL already carries C48 status. SYS_EXIT consumes it.
    return _single("exit", bytes((0x3E, 0x01, 0xCD, 0x00, 0xE0, 0x76)))


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

def _putchar() -> NativeMember:
    # Native string runtime convention: write low byte through stdout handle 1.
    # c48_stdio_byte lives in this member's BSS and is addressed through OBJ1.
    text = bytearray()
    # LD DE,c48_stdio_byte ; LD A,L ; LD (DE),A
    text.extend((0x11, 0x00, 0x00, 0x7D, 0x12))
    # LD HL,c48_stdio_byte ; LD DE,1 ; LD BC,1 ; LD A,SYS_WRITE ; CALL E000
    text.extend((0x21, 0x00, 0x00, 0x11, 0x01, 0x00, 0x01, 0x01, 0x00, 0x3E, 0x13, 0xCD, 0x00, 0xE0))
    # Return written low byte is not required by current proof fixtures; zero on success.
    text.extend((0x21, 0x00, 0x00, 0xC9))
    symbols = (
        _sym("putchar"),
        ObjSymbol("c48_stdio_byte", 0, 2, 0),
    )
    relocs = (ObjReloc(1, 1), ObjReloc(6, 1))
    return NativeMember("putchar", ObjImage(bytes(text), 1, symbols, relocs), ("putchar",))


def _graphics_attr(name: str, selector: int) -> NativeMember:
    # HL=value. Native wrapper uses D=selector and SYS_GFX_ATTR.
    text = bytes((
        0x16, selector,
        0x62,             # LD H,D
        0x3E, 0x43,
        0xCD, 0x00, 0xE0,
        0x21, 0x00, 0x00,
        0xC9,
    ))
    return _single(name, text)


RUNTIME_MEMBERS: tuple[NativeMember, ...] = (
    _startup(),
    _exit(),
    _mul16(),
    _div16(),
    _syscall_wrapper("yield", 0x02, zero_result=True),
    _syscall_wrapper("sleep", 0x03, zero_result=True),
    _syscall_wrapper("getpid", 0x04),
    _syscall_wrapper("cls", 0x33, zero_result=True),
    _syscall_wrapper("ticks", 0x62),
    _syscall_wrapper("udg_clear", 0x4B, zero_result=True),
    _graphics_attr("ink", 0),
    _graphics_attr("paper", 1),
    _graphics_attr("bright", 2),
    _graphics_attr("flash", 3),
    _graphics_attr("inverse", 4),
    _graphics_attr("over", 5),
    _syscall_wrapper("border", 0x44, zero_result=True),
    _single(
        "plot",
        bytes((0x65, 0x6B, 0x3E, 0x40, 0xCD, 0x00, 0xE0, 0x21, 0x00, 0x00, 0xC9)),
    ),
    _putchar(),
)
