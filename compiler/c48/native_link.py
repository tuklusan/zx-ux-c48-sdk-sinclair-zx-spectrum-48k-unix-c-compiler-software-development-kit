# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from dataclasses import dataclass

from .native_format import (
    MAX_NATIVE_IMAGE,
    MexImage,
    NativeFormatError,
    ObjImage,
    OBJ_SECTION_ABS,
    OBJ_SECTION_BSS,
    OBJ_SECTION_TEXT,
    OBJ_SECTION_UNDEF,
    OBJ_SYMBOL_GLOBAL,
)


@dataclass(frozen=True)
class NativeMember:
    name: str
    obj: ObjImage
    provides: tuple[str, ...]


@dataclass(frozen=True)
class _Placed:
    name: str
    obj: ObjImage
    text_base: int
    bss_base: int


def _definitions(modules: list[tuple[str, ObjImage]]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for mi, (_, obj) in enumerate(modules):
        for si, sym in enumerate(obj.symbols):
            if sym.section == OBJ_SECTION_UNDEF or not (sym.flags & OBJ_SYMBOL_GLOBAL):
                continue
            if sym.name in result:
                raise NativeFormatError(f"duplicate global definition {sym.name!r}")
            result[sym.name] = (mi, si)
    return result


def select_runtime(
    roots: list[tuple[str, ObjImage]],
    members: tuple[NativeMember, ...],
) -> list[tuple[str, ObjImage]]:
    selected = list(roots)
    available: dict[str, NativeMember] = {}
    for member in members:
        for symbol in member.provides:
            if symbol in available:
                raise NativeFormatError(f"runtime symbol {symbol!r} is provided twice")
            available[symbol] = member
    chosen: set[str] = set()
    while True:
        definitions = _definitions(selected)
        unresolved: list[str] = []
        for _, obj in selected:
            for sym in obj.symbols:
                if (
                    sym.section == OBJ_SECTION_UNDEF
                    and (sym.flags & OBJ_SYMBOL_GLOBAL)
                    and sym.name not in definitions
                    and sym.name not in unresolved
                ):
                    unresolved.append(sym.name)
        if not unresolved:
            return selected
        added = False
        for name in unresolved:
            member = available.get(name)
            if member is None:
                raise NativeFormatError(f"unresolved native symbol {name!r}")
            if member.name not in chosen:
                selected.append((f"runtime:{member.name}", member.obj))
                chosen.add(member.name)
                added = True
        if not added:
            raise NativeFormatError("runtime archive selection made no progress")


def link_mex(
    roots: list[tuple[str, ObjImage]],
    runtime_members: tuple[NativeMember, ...],
    *,
    entry_symbol: str = "_start",
    min_stack: int = 1024,
) -> MexImage:
    modules = select_runtime(roots, runtime_members)
    total_text = sum(len(obj.text) for _, obj in modules)
    total_bss = sum(obj.bss_size for _, obj in modules)
    if total_text + total_bss > MAX_NATIVE_IMAGE:
        raise NativeFormatError("linked image+BSS exceeds native 32768-byte arena")

    placed: list[_Placed] = []
    text_cursor = 0
    bss_cursor = 0
    for name, obj in modules:
        placed.append(_Placed(name, obj, text_cursor, bss_cursor))
        text_cursor += len(obj.text)
        bss_cursor += obj.bss_size

    definitions: dict[str, tuple[_Placed, object]] = {}
    for module in placed:
        for sym in module.obj.symbols:
            if sym.section == OBJ_SECTION_UNDEF or not (sym.flags & OBJ_SYMBOL_GLOBAL):
                continue
            if sym.name in definitions:
                raise NativeFormatError(f"duplicate global definition {sym.name!r}")
            definitions[sym.name] = (module, sym)

    def value_of(module: _Placed, sym) -> tuple[int, bool]:
        if sym.section == OBJ_SECTION_UNDEF:
            target = definitions.get(sym.name)
            if target is None:
                raise NativeFormatError(f"unresolved native symbol {sym.name!r}")
            return value_of(target[0], target[1])
        if sym.section == OBJ_SECTION_TEXT:
            return module.text_base + sym.value, True
        if sym.section == OBJ_SECTION_BSS:
            return total_text + module.bss_base + sym.value, True
        if sym.section == OBJ_SECTION_ABS:
            return sym.value, False
        raise NativeFormatError("invalid linked symbol section")

    image = bytearray().join(module.obj.text for module in placed)
    mex_relocs: list[int] = []
    for module in placed:
        for rel in module.obj.relocs:
            sym = module.obj.symbols[rel.symbol]
            target, load_relative = value_of(module, sym)
            at = module.text_base + rel.offset
            addend_raw = int.from_bytes(image[at:at + 2], "little")
            addend = addend_raw - 0x10000 if addend_raw & 0x8000 else addend_raw
            value = target + addend
            if not 0 <= value <= 0xFFFF:
                raise NativeFormatError("linked ABS16 relocation overflows 16 bits")
            image[at:at + 2] = value.to_bytes(2, "little")
            if load_relative:
                mex_relocs.append(at)

    entry = definitions.get(entry_symbol)
    if entry is None:
        raise NativeFormatError(f"entry symbol {entry_symbol!r} is not defined")
    entry_value, entry_relative = value_of(entry[0], entry[1])
    if not entry_relative or not 0 <= entry_value < len(image):
        raise NativeFormatError("linked entry point is not in executable text")
    return MexImage(
        bytes(image),
        total_bss,
        entry_value,
        min_stack,
        tuple(sorted(mex_relocs)),
    )
