# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .native_format import (
    NativeFormatError,
    ObjImage,
    ObjReloc,
    ObjSymbol,
    OBJ_SECTION_BSS,
    OBJ_SECTION_TEXT,
    OBJ_SECTION_UNDEF,
    OBJ_SYMBOL_GLOBAL,
)
from .typesys import CType, align_up, arithmetic_common


class NativeLoweringError(NativeFormatError):
    pass


@dataclass(frozen=True)
class _Slot:
    offset: int
    ctype: CType


class _Emitter:
    def __init__(self) -> None:
        self.text = bytearray()
        self.symbols: list[ObjSymbol] = []
        self.symbol_index: dict[str, int] = {}
        self.reloc_names: list[tuple[int, str]] = []
        self.label_counter = 0

    def emit(self, *values: int) -> None:
        self.text.extend(v & 0xFF for v in values)

    def word(self, value: int) -> None:
        self.text.extend((value & 0xFF, (value >> 8) & 0xFF))

    def add_symbol(self, name: str, value: int, section: int, flags: int) -> int:
        existing = self.symbol_index.get(name)
        if existing is not None:
            old = self.symbols[existing]
            if old.section == OBJ_SECTION_UNDEF and section != OBJ_SECTION_UNDEF:
                self.symbols[existing] = ObjSymbol(name, value, section, flags)
                return existing
            if old.section == section and old.value == value and old.flags == flags:
                return existing
            raise NativeLoweringError(f"native symbol {name!r} is defined inconsistently")
        index = len(self.symbols)
        self.symbol_index[name] = index
        self.symbols.append(ObjSymbol(name, value, section, flags))
        return index

    def undef(self, name: str) -> None:
        self.add_symbol(name, 0, OBJ_SECTION_UNDEF, OBJ_SYMBOL_GLOBAL)

    def define(self, name: str, *, global_: bool) -> None:
        self.add_symbol(
            name,
            len(self.text),
            OBJ_SECTION_TEXT,
            OBJ_SYMBOL_GLOBAL if global_ else 0,
        )

    def label(self) -> str:
        self.label_counter += 1
        name = f"_L{self.label_counter:05d}"
        self.define(name, global_=False)
        return name

    def new_label_name(self) -> str:
        self.label_counter += 1
        return f"_L{self.label_counter:05d}"

    def place_label(self, name: str) -> None:
        self.define(name, global_=False)

    def abs16(self, opcode: int, target: str, addend: int = 0) -> None:
        self.emit(opcode)
        at = len(self.text)
        self.word(addend)
        self.reloc_names.append((at, target))
        if target not in self.symbol_index:
            self.undef(target)

    def jp(self, target: str) -> None:
        self.abs16(0xC3, target)

    def jp_cond(self, opcode: int, target: str) -> None:
        self.abs16(opcode, target)

    def call(self, target: str) -> None:
        self.abs16(0xCD, target)

    def address(self, target: str, addend: int = 0) -> None:
        self.emit(0x21)
        at = len(self.text)
        self.word(addend)
        self.reloc_names.append((at, target))
        if target not in self.symbol_index:
            self.undef(target)

    def finish(self, bss_size: int) -> ObjImage:
        relocs = [
            ObjReloc(offset, self.symbol_index[name])
            for offset, name in sorted(self.reloc_names)
        ]
        return ObjImage(bytes(self.text), bss_size, tuple(self.symbols), tuple(relocs))


class _Function:
    def __init__(self, owner: "NativeBackend", node: dict[str, Any]) -> None:
        self.owner = owner
        self.e = owner.e
        self.node = node
        self.scopes: list[dict[str, _Slot]] = []
        self.decl_slots: dict[int, _Slot] = {}
        self.call_slots: dict[int, tuple[_Slot, ...]] = {}
        self.next_bytes = 0
        self.break_stack: list[str] = []
        self.continue_stack: list[str] = []
        self.return_label = self.e.new_label_name()
        self._layout()

    def _alloc(self, ctype: CType) -> _Slot:
        align = max(1, min(ctype.alignment, 2))
        self.next_bytes = align_up(self.next_bytes, align)
        self.next_bytes += ctype.size
        if self.next_bytes > 12000:
            raise NativeLoweringError("native function frame exceeds 12000-byte safety limit")
        return _Slot(-self.next_bytes, ctype)

    def _layout(self) -> None:
        suffix = self.node["declarator"].get("suffix") or {}
        for param in suffix.get("params", []):
            self.decl_slots[id(param)] = self._alloc(CType.from_dict(param["ctype"]))

        def walk(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    walk(item)
                return
            if not isinstance(value, dict):
                return
            if value.get("kind") == "declaration":
                for idecl in value["declarators"]:
                    t = CType.from_dict(idecl["ctype"])
                    if t.is_function:
                        continue
                    if idecl.get("storage") == "static":
                        raise NativeLoweringError("block-scope static storage is not yet supported")
                    self.decl_slots[id(idecl)] = self._alloc(t)
            if value.get("kind") == "call":
                slots: list[_Slot] = []
                ft = CType.from_dict(value["function"]["ctype"])
                for p in ft.params or ():
                    if p.is_float or p.size > 2:
                        raise NativeLoweringError("native float call lowering is not yet enabled")
                    slots.append(self._alloc(CType("uint")))
                self.call_slots[id(value)] = tuple(slots)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child)
        walk(self.node["body"])
        self.frame_size = align_up(self.next_bytes, 2)

    def _addr_slot(self, slot: _Slot) -> None:
        self.e.emit(0xDD, 0xE5, 0xE1)  # PUSH IX / POP HL
        self.e.emit(0x11)
        self.e.word(slot.offset & 0xFFFF)
        self.e.emit(0x19)              # ADD HL,DE

    def _load_from_hl(self, t: CType) -> None:
        if t.size == 1:
            self.e.emit(0x7E, 0x6F, 0x26, 0x00)  # A=(HL); L=A; H=0
            return
        if t.size == 2:
            self.e.emit(0x5E, 0x23, 0x56, 0xEB)  # DE=word; EX DE,HL
            return
        raise NativeLoweringError(f"native scalar load is unsupported for {t}")

    def _store_to_de(self, t: CType) -> None:
        if t.size == 1:
            self.e.emit(0x7D, 0x12)  # A=L; (DE)=A
            return
        if t.size == 2:
            self.e.emit(0x7D, 0x12, 0x13, 0x7C, 0x12)
            return
        raise NativeLoweringError(f"native scalar store is unsupported for {t}")

    def _lookup(self, name: str) -> _Slot | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _lvalue(self, n: dict[str, Any]) -> CType:
        k = n["kind"]
        if k == "identifier":
            t = CType.from_dict(n["ctype"])
            slot = self._lookup(n["name"])
            if slot is not None:
                self._addr_slot(slot)
            else:
                self.e.address(n["name"])
            return t
        if k == "unary" and n["op"] == "*":
            self.expr(n["operand"])
            return CType.from_dict(n["ctype"])
        if k == "index":
            self.expr(n["base"])
            self.e.emit(0xE5)
            self.expr(n["index"])
            base_t = CType.from_dict(n["base"]["ctype"])
            if not base_t.is_pointer or base_t.base is None:
                raise NativeLoweringError("native index base lacks pointer type")
            size = base_t.base.size
            if size == 2:
                self.e.emit(0x29)
            elif size == 5:
                self.e.emit(0xD5, 0x54, 0x5D, 0x29, 0x29, 0x19, 0xD1)
            elif size != 1:
                raise NativeLoweringError("native pointer scaling is unsupported")
            self.e.emit(0xD1, 0x19)  # POP DE ; ADD HL,DE
            return CType.from_dict(n["ctype"])
        raise NativeLoweringError(f"native lvalue lowering does not support {k}")

    def _truth_branch_false(self, n: dict[str, Any], target: str) -> None:
        self.expr(n)
        t = CType.from_dict(n["ctype"])
        if t.is_float:
            raise NativeLoweringError("native float truth lowering is not yet enabled")
        self.e.emit(0x7C, 0xB5)  # LD A,H ; OR L
        self.e.jp_cond(0xCA, target)  # JP Z

    def _bool_from_flags(self, jump_true: int) -> None:
        yes = self.e.new_label_name()
        done = self.e.new_label_name()
        self.e.emit(0x21, 0x00, 0x00)
        self.e.jp_cond(jump_true, yes)
        self.e.jp(done)
        self.e.place_label(yes)
        self.e.emit(0x23)
        self.e.place_label(done)

    def _compare(self, op: str, signed: bool) -> None:
        # Inputs HL=lhs, DE=rhs. Equality is width-agnostic here because
        # eight-bit values are already zero-extended.
        if op in {"==", "!="}:
            self.e.emit(0xB7, 0xED, 0x52)  # OR A ; SBC HL,DE
            self._bool_from_flags(0xCA if op == "==" else 0xC2)
            return
        if signed:
            # Signed order: if sign differs, lhs sign decides; otherwise unsigned
            # subtract has the same order within one sign partition.
            same = self.e.new_label_name()
            less = self.e.new_label_name()
            greater = self.e.new_label_name()
            done = self.e.new_label_name()
            self.e.emit(0x7C, 0xAA, 0xE6, 0x80)  # A=H xor D; AND 80
            self.e.jp_cond(0xCA, same)
            self.e.emit(0x7C, 0xE6, 0x80)
            self.e.jp_cond(0xC2, less)
            self.e.jp(greater)
            self.e.place_label(same)
            self.e.emit(0xB7, 0xED, 0x52)
            self.e.jp_cond(0xDA, less)     # C
            self.e.jp_cond(0xC2, greater)  # NZ
            # equal
            result = op in {"<=", ">="}
            self.e.emit(0x21, 0x01 if result else 0x00, 0x00)
            self.e.jp(done)
            self.e.place_label(less)
            self.e.emit(0x21, 0x01 if op in {"<", "<="} else 0x00, 0x00)
            self.e.jp(done)
            self.e.place_label(greater)
            self.e.emit(0x21, 0x01 if op in {">", ">="} else 0x00, 0x00)
            self.e.place_label(done)
            return
        self.e.emit(0xB7, 0xED, 0x52)
        if op == "<":
            self._bool_from_flags(0xDA)
        elif op == ">=":
            self._bool_from_flags(0xD2)
        elif op == ">":
            not_greater = self.e.new_label_name()
            done = self.e.new_label_name()
            self.e.emit(0x21, 0x00, 0x00)
            self.e.jp_cond(0xDA, not_greater)
            self.e.jp_cond(0xCA, not_greater)
            self.e.emit(0x23)
            self.e.place_label(not_greater)
            self.e.place_label(done)
        elif op == "<=":
            yes = self.e.new_label_name()
            done = self.e.new_label_name()
            self.e.emit(0x21, 0x00, 0x00)
            self.e.jp_cond(0xDA, yes)
            self.e.jp_cond(0xCA, yes)
            self.e.jp(done)
            self.e.place_label(yes)
            self.e.emit(0x23)
            self.e.place_label(done)
        else:
            raise NativeLoweringError(f"unknown comparison {op}")

    def expr(self, n: dict[str, Any]) -> None:
        k = n["kind"]
        if k in {"integer_literal", "character_literal"}:
            self.e.emit(0x21)
            self.e.word(int(n["value"]) & 0xFFFF)
            return
        if k == "string_literal":
            name = self.owner.string_symbol(n)
            self.e.address(name)
            return
        if k in {"sizeof_type", "sizeof_expr"}:
            self.e.emit(0x21)
            self.e.word(int(n["sizeof_value"]))
            return
        if k == "identifier":
            t = CType.from_dict(n["ctype"])
            if t.is_array:
                self._lvalue(n)
                return
            if t.is_float:
                raise NativeLoweringError("native float object loading is not yet enabled")
            self._lvalue(n)
            self._load_from_hl(t)
            return
        if k == "index":
            t = self._lvalue(n)
            self._load_from_hl(t)
            return
        if k == "cast":
            src = CType.from_dict(n["operand"]["ctype"])
            dst = CType.from_dict(n["ctype"])
            if src.is_float or dst.is_float:
                raise NativeLoweringError("native float casts are not yet enabled")
            self.expr(n["operand"])
            if dst.size == 1:
                self.e.emit(0x26, 0x00)
            return
        if k == "assign":
            t = self._lvalue(n["left"])
            self.e.emit(0xE5)  # captured destination address first
            self.expr(n["right"])
            self.e.emit(0xD1)
            self._store_to_de(t)
            return
        if k in {"unary", "postfix"}:
            op = n["op"]
            if op == "&":
                self._lvalue(n["operand"])
                return
            if op == "*":
                t = self._lvalue(n)
                self._load_from_hl(t)
                return
            if op in {"++", "--"} or k == "postfix":
                t = self._lvalue(n["operand"])
                self.e.emit(0xE5)
                self._load_from_hl(t)
                if k == "postfix":
                    self.e.emit(0xE5)
                delta = 1 if op == "++" else -1
                if t.is_pointer and t.base is not None:
                    delta *= t.base.size
                self.e.emit(0x11)
                self.e.word(delta & 0xFFFF)
                self.e.emit(0x19)
                if k == "postfix":
                    self.e.emit(0xC1, 0xD1)  # BC=old value, DE=address
                    self._store_to_de(t)
                    self.e.emit(0x60, 0x69)  # restore old value to HL
                else:
                    self.e.emit(0xD1)
                    self._store_to_de(t)
                return
            self.expr(n["operand"])
            if op == "+":
                return
            if op == "-":
                self.e.emit(0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67, 0x23)
                return
            if op == "~":
                self.e.emit(0x7D, 0x2F, 0x6F, 0x7C, 0x2F, 0x67)
                return
            if op == "!":
                self.e.emit(0x7C, 0xB5)
                self._bool_from_flags(0xCA)
                return
            raise NativeLoweringError(f"native unary operator {op!r} is unsupported")
        if k == "call":
            self._call(n)
            return
        if k == "binary":
            op = n["op"]
            if op in {"&&", "||"}:
                self._logical(n)
                return
            self.expr(n["left"])
            self.e.emit(0xE5)
            self.expr(n["right"])
            self.e.emit(0xEB, 0xE1)  # EX DE,HL ; POP HL
            lt = CType.from_dict(n["left"]["ctype"])
            rt = CType.from_dict(n["right"]["ctype"])
            result_t = CType.from_dict(n["ctype"])
            if lt.is_float or rt.is_float:
                raise NativeLoweringError("native float arithmetic is not yet enabled")
            if lt.is_pointer or rt.is_pointer:
                self._pointer_binary(op, lt, rt)
                return
            if op == "+":
                self.e.emit(0x19)
            elif op == "-":
                self.e.emit(0xB7, 0xED, 0x52)
            elif op == "*":
                self.e.call("c48_mul16")
            elif op == "&":
                self.e.emit(0x7D, 0xA3, 0x6F, 0x7C, 0xA2, 0x67)
            elif op == "|":
                self.e.emit(0x7D, 0xB3, 0x6F, 0x7C, 0xB2, 0x67)
            elif op == "^":
                self.e.emit(0x7D, 0xAB, 0x6F, 0x7C, 0xAA, 0x67)
            elif op in {"==", "!=", "<", "<=", ">", ">="}:
                common_signed = arithmetic_common(lt, rt).is_signed
                self._compare(op, common_signed)
            elif op in {"/", "%", "<<", ">>"}:
                raise NativeLoweringError(f"native operator {op!r} is not yet enabled")
            else:
                raise NativeLoweringError(f"native binary operator {op!r} is unsupported")
            if result_t.size == 1:
                self.e.emit(0x26, 0x00)
            return
        raise NativeLoweringError(f"native expression kind {k!r} is unsupported")

    def _pointer_binary(self, op: str, lt: CType, rt: CType) -> None:
        if op in {"==", "!="}:
            self._compare(op, False)
            return
        if lt.is_pointer and rt.is_integer and op in {"+", "-"}:
            assert lt.base is not None
            size = lt.base.size
            if size == 2:
                self.e.emit(0xEB, 0x29, 0xEB)  # scale DE by 2
            elif size == 5:
                self.e.emit(0xEB, 0xD5, 0x54, 0x5D, 0x29, 0x29, 0x19, 0xD1, 0xEB)
            elif size != 1:
                raise NativeLoweringError("native pointer scaling is unsupported")
            if op == "+":
                self.e.emit(0x19)
            else:
                self.e.emit(0xB7, 0xED, 0x52)
            return
        if lt.is_integer and rt.is_pointer and op == "+":
            assert rt.base is not None
            size = rt.base.size
            # HL=integer, DE=pointer
            if size == 2:
                self.e.emit(0x29)
            elif size == 5:
                self.e.emit(0x54, 0x5D, 0x29, 0x29, 0x19)
            elif size != 1:
                raise NativeLoweringError("native pointer scaling is unsupported")
            self.e.emit(0x19)
            return
        raise NativeLoweringError("native pointer ordering/subtraction requires a later provenance proof")

    def _logical(self, n: dict[str, Any]) -> None:
        op = n["op"]
        short = self.e.new_label_name()
        done = self.e.new_label_name()
        self.expr(n["left"])
        self.e.emit(0x7C, 0xB5)
        if op == "&&":
            self.e.jp_cond(0xCA, short)
        else:
            self.e.jp_cond(0xC2, short)
        self.expr(n["right"])
        self.e.emit(0x7C, 0xB5, 0x21, 0x00, 0x00)
        self.e.jp_cond(0xCA, done)
        self.e.emit(0x23)
        if op == "&&":
            self.e.jp(done)
            self.e.place_label(short)
            self.e.emit(0x21, 0x00, 0x00)
        else:
            self.e.jp(done)
            self.e.place_label(short)
            self.e.emit(0x21, 0x01, 0x00)
        self.e.place_label(done)

    def _call(self, n: dict[str, Any]) -> None:
        name = n["function"]["name"]
        ft = CType.from_dict(n["function"]["ctype"])
        if ft.ret is not None and ft.ret.is_float:
            raise NativeLoweringError("native float return calls are not yet enabled")
        slots = self.call_slots[id(n)]
        if len(slots) != len(n["args"]):
            raise NativeLoweringError("native call scratch layout mismatch")
        # C48 freezes left-to-right evaluation/capture. Each call node has
        # distinct frame scratch so nested calls cannot overwrite earlier args.
        for arg, slot in zip(n["args"], slots):
            self.expr(arg)
            self.e.emit(0xE5)
            self._addr_slot(slot)
            self.e.emit(0xEB, 0xE1)  # DE=scratch address; HL=captured value
            self._store_to_de(slot.ctype)
        # Extra ABI words are pushed right-to-left.
        for slot in reversed(slots[3:]):
            self._addr_slot(slot)
            self._load_from_hl(slot.ctype)
            self.e.emit(0xE5)
        if len(slots) >= 3:
            self._addr_slot(slots[2]); self._load_from_hl(slots[2].ctype)
            self.e.emit(0x44, 0x4D)  # BC=HL
        if len(slots) >= 2:
            self._addr_slot(slots[1]); self._load_from_hl(slots[1].ctype)
            self.e.emit(0x54, 0x5D)  # DE=HL
        if len(slots) >= 1:
            self._addr_slot(slots[0]); self._load_from_hl(slots[0].ctype)
        self.e.call(name)
        extra = max(0, len(slots) - 3)
        for _ in range(extra):
            self.e.emit(0xF1)  # POP AF: caller cleanup; return HL preserved

    def stmt(self, s: dict[str, Any]) -> None:
        k = s["kind"]
        if k == "compound":
            self.compound(s)
            return
        if k == "expr_stmt":
            if s["value"] is not None:
                self.expr(s["value"])
            return
        if k == "return":
            if s["value"] is None:
                self.e.emit(0x21, 0x00, 0x00)
            else:
                self.expr(s["value"])
            self.e.jp(self.return_label)
            return
        if k == "if":
            otherwise = self.e.new_label_name()
            done = self.e.new_label_name()
            self._truth_branch_false(s["condition"], otherwise)
            self.stmt(s["then"])
            self.e.jp(done)
            self.e.place_label(otherwise)
            if s["otherwise"] is not None:
                self.stmt(s["otherwise"])
            self.e.place_label(done)
            return
        if k == "while":
            top = self.e.new_label_name()
            done = self.e.new_label_name()
            self.e.place_label(top)
            self._truth_branch_false(s["condition"], done)
            self.break_stack.append(done)
            self.continue_stack.append(top)
            self.stmt(s["body"])
            self.continue_stack.pop()
            self.break_stack.pop()
            self.e.jp(top)
            self.e.place_label(done)
            return
        if k == "do_while":
            top = self.e.new_label_name()
            check = self.e.new_label_name()
            done = self.e.new_label_name()
            self.e.place_label(top)
            self.break_stack.append(done)
            self.continue_stack.append(check)
            self.stmt(s["body"])
            self.continue_stack.pop()
            self.break_stack.pop()
            self.e.place_label(check)
            self._truth_branch_false(s["condition"], done)
            self.e.jp(top)
            self.e.place_label(done)
            return
        if k == "for":
            top = self.e.new_label_name()
            step = self.e.new_label_name()
            done = self.e.new_label_name()
            if s["init"] is not None:
                self.expr(s["init"])
            self.e.place_label(top)
            if s["condition"] is not None:
                self._truth_branch_false(s["condition"], done)
            self.break_stack.append(done)
            self.continue_stack.append(step)
            self.stmt(s["body"])
            self.continue_stack.pop()
            self.break_stack.pop()
            self.e.place_label(step)
            if s["step"] is not None:
                self.expr(s["step"])
            self.e.jp(top)
            self.e.place_label(done)
            return
        if k == "break":
            if not self.break_stack:
                raise NativeLoweringError("native break has no loop target")
            self.e.jp(self.break_stack[-1])
            return
        if k == "continue":
            if not self.continue_stack:
                raise NativeLoweringError("native continue has no loop target")
            self.e.jp(self.continue_stack[-1])
            return
        raise NativeLoweringError(f"native statement kind {k!r} is unsupported")

    def _initialize_slot(self, slot: _Slot, init: dict[str, Any]) -> None:
        if slot.ctype.is_array:
            raise NativeLoweringError("native local array initialization is not yet enabled")
        value = init["value"]
        self.expr(value)
        self.e.emit(0xE5)
        self._addr_slot(slot)
        self.e.emit(0xEB, 0xE1)  # DE=address; HL=value
        self._store_to_de(slot.ctype)

    def compound(self, b: dict[str, Any], *, root: bool = False) -> None:
        scope: dict[str, _Slot] = {}
        self.scopes.append(scope)
        try:
            if root:
                suffix = self.node["declarator"].get("suffix") or {}
                for p in suffix.get("params", []):
                    scope[p["name"]] = self.decl_slots[id(p)]
            for d in b["declarations"]:
                for idecl in d["declarators"]:
                    t = CType.from_dict(idecl["ctype"])
                    if t.is_function:
                        continue
                    slot = self.decl_slots[id(idecl)]
                    scope[idecl["declarator"]["name"]] = slot
                    if idecl.get("initializer") is not None:
                        self._initialize_slot(slot, idecl["initializer"])
            for statement in b["statements"]:
                self.stmt(statement)
        finally:
            self.scopes.pop()

    def generate(self) -> None:
        name = self.node["declarator"]["name"]
        global_ = self.node.get("storage") != "static"
        self.e.define(name, global_=global_)
        self.e.emit(0xDD, 0xE5, 0xDD, 0x21, 0x00, 0x00, 0xDD, 0x39)
        if self.frame_size:
            self.e.emit(0x21)
            self.e.word((-self.frame_size) & 0xFFFF)
            self.e.emit(0x39, 0xF9)
        self.scopes.append({})
        try:
            suffix = self.node["declarator"].get("suffix") or {}
            params = suffix.get("params", [])
            for index, p in enumerate(params):
                slot = self.decl_slots[id(p)]
                self.scopes[-1][p["name"]] = slot
                if index == 0:
                    self.e.emit(0xE5)
                elif index == 1:
                    self.e.emit(0xD5)
                elif index == 2:
                    self.e.emit(0xC5)
                else:
                    # stack arg at IX+4+2*(index-3)
                    self.e.emit(0xDD, 0xE5, 0xE1, 0x11)
                    self.e.word(4 + 2 * (index - 3))
                    self.e.emit(0x19)
                    self._load_from_hl(CType("uint"))
                    self.e.emit(0xE5)
                self._addr_slot(slot)
                self.e.emit(0xEB, 0xE1)
                self._store_to_de(slot.ctype)
            # Root compound reuses parameter scope.
            for d in self.node["body"]["declarations"]:
                for idecl in d["declarators"]:
                    t = CType.from_dict(idecl["ctype"])
                    if t.is_function:
                        continue
                    slot = self.decl_slots[id(idecl)]
                    self.scopes[-1][idecl["declarator"]["name"]] = slot
                    if idecl.get("initializer") is not None:
                        self._initialize_slot(slot, idecl["initializer"])
            for statement in self.node["body"]["statements"]:
                self.stmt(statement)
        finally:
            self.scopes.pop()
        # Non-void fall-through exits with status 1, matching host strictness.
        self.e.emit(0x21, 0x01, 0x00)
        self.e.place_label(self.return_label)
        self.e.emit(0xDD, 0xF9, 0xDD, 0xE1, 0xC9)


class NativeBackend:
    def __init__(self, program: dict[str, Any]) -> None:
        self.program = program
        self.e = _Emitter()
        self.bss_size = 0
        self.strings: dict[int, str] = {}
        self.string_nodes: dict[int, dict[str, Any]] = {}

    def string_symbol(self, node: dict[str, Any]) -> str:
        sid = int(node["sid"])
        if sid not in self.strings:
            self.strings[sid] = f"_S{sid:05d}"
            self.string_nodes[sid] = node
        return self.strings[sid]

    def _collect_strings(self, value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                self._collect_strings(item)
        elif isinstance(value, dict):
            if value.get("kind") == "string_literal":
                self.string_symbol(value)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    self._collect_strings(child)

    def _global_initializer(self, idecl: dict[str, Any], t: CType) -> tuple[bytes, list[tuple[int, str]]] | None:
        init = idecl.get("initializer")
        if init is None:
            return None
        if t.is_float:
            raise NativeLoweringError("native float global initialization is not yet enabled")
        if not t.is_array:
            value = init["value"]
            if value["kind"] in {"integer_literal", "character_literal"}:
                number = int(value["value"])
                return (number & ((1 << (8 * t.size)) - 1)).to_bytes(t.size, "little"), []
            if value["kind"] == "unary" and value["op"] == "&" and value["operand"]["kind"] == "identifier":
                return b"\0\0", [(0, value["operand"]["name"])]
            raise NativeLoweringError("native global initializer is not a link-time constant")
        assert t.base is not None and t.length is not None
        out = bytearray(t.size)
        rels: list[tuple[int, str]] = []
        if init["kind"] == "string_initializer":
            raw = bytes(init["value"]["bytes"]) + b"\0"
            if len(raw) > len(out):
                raise NativeLoweringError("native string initializer exceeds array")
            out[:len(raw)] = raw
            return bytes(out), rels
        if init["kind"] != "init_list":
            raise NativeLoweringError("native array initializer is unsupported")
        for i, value in enumerate(init["values"]):
            if value["kind"] not in {"integer_literal", "character_literal"}:
                raise NativeLoweringError("native aggregate initializer must be constant")
            n = int(value["value"])
            start = i * t.base.size
            out[start:start + t.base.size] = (n & ((1 << (8 * t.base.size)) - 1)).to_bytes(t.base.size, "little")
        return bytes(out), rels

    def build(self) -> ObjImage:
        self._collect_strings(self.program)
        data_records: list[tuple[str, CType, bytes, list[tuple[int, str]], bool]] = []
        for item in self.program["items"]:
            if item["kind"] != "declaration":
                continue
            for idecl in item["declarators"]:
                if not idecl.get("definition"):
                    continue
                t = CType.from_dict(idecl["ctype"])
                if t.is_function:
                    continue
                name = idecl["declarator"]["name"]
                global_ = idecl.get("linkage") != "internal"
                initial = self._global_initializer(idecl, t)
                if initial is None:
                    self.bss_size = align_up(self.bss_size, t.alignment)
                    self.e.add_symbol(
                        name,
                        self.bss_size,
                        OBJ_SECTION_BSS,
                        OBJ_SYMBOL_GLOBAL if global_ else 0,
                    )
                    self.bss_size += t.size
                else:
                    data_records.append((name, t, initial[0], initial[1], global_))

        for item in self.program["items"]:
            if item["kind"] == "function_definition":
                _Function(self, item).generate()

        for sid in sorted(self.strings):
            name = self.strings[sid]
            node = self.string_nodes[sid]
            self.e.define(name, global_=False)
            self.e.text.extend(bytes(node["bytes"]) + b"\0")

        for name, t, data, rels, global_ in data_records:
            while len(self.e.text) % max(1, t.alignment):
                self.e.emit(0)
            self.e.define(name, global_=global_)
            base = len(self.e.text)
            self.e.text.extend(data)
            for offset, target in rels:
                self.e.reloc_names.append((base + offset, target))
                if target not in self.e.symbol_index:
                    self.e.undef(target)

        if "main" not in self.e.symbol_index or self.e.symbols[self.e.symbol_index["main"]].section != OBJ_SECTION_TEXT:
            raise NativeLoweringError("native program has no main definition")
        return self.e.finish(self.bss_size)
