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

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .errors import RuntimeC48Error
from .limits import (
    AST_NODE_KINDS,
    C48B1_AST_NODES,
    C48B1_BYTES,
    C48B1_CONTAINERS,
    C48B1_JSON_DEPTH,
    C48B1_STRING_BYTES,
    C48B1_TYPE_DEPTH,
    C48B1_SEQUENCE_ITEMS,
    C48B1_SYMBOLS,
    POINTER_DEPTH,
)
from .typesys import CHAR, FLOAT, INT, UINT, CType, ptr

MAGIC = b"C48B1\n"

_TYPE_SCALARS = {"void", "char", "uchar", "short", "ushort", "int", "uint", "float"}
_AST_KINDS = AST_NODE_KINDS


def _invalid(detail: str) -> None:
    raise RuntimeC48Error(f"invalid C48B1 schema: {detail}")


def _resource(detail: str) -> None:
    raise RuntimeC48Error(f"C48B1 resource limit: {detail}")


def _check_json_nesting(payload: bytes) -> None:
    """Bound JSON nesting before handing attacker bytes to json.loads()."""
    depth = 0
    in_string = False
    escaped = False
    for byte in payload:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:  # backslash
                escaped = True
            elif byte == 0x22:  # quote
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):  # { [
            depth += 1
            if depth > C48B1_JSON_DEPTH:
                _resource(f"JSON nesting exceeds {C48B1_JSON_DEPTH}")
        elif byte in (0x7D, 0x5D):  # } ]
            depth -= 1
            if depth < 0:
                # json.loads() will provide the controlled malformed-JSON result.
                return


def _check_loaded_structure(value: Any) -> None:
    """Iteratively bound decoded container/AST width and depth."""
    containers = 0
    ast_nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if isinstance(current, dict):
            containers += 1
            if current.get("kind") in _AST_KINDS:
                ast_nodes += 1
            if depth > C48B1_JSON_DEPTH:
                _resource(f"decoded nesting exceeds {C48B1_JSON_DEPTH}")
            if containers > C48B1_CONTAINERS:
                _resource(f"container count exceeds {C48B1_CONTAINERS}")
            if ast_nodes > C48B1_AST_NODES:
                _resource(f"AST node count exceeds {C48B1_AST_NODES}")
            for child in current.values():
                if isinstance(child, (dict, list)):
                    stack.append((child, depth + 1))
        elif isinstance(current, list):
            containers += 1
            if depth > C48B1_JSON_DEPTH:
                _resource(f"decoded nesting exceeds {C48B1_JSON_DEPTH}")
            if containers > C48B1_CONTAINERS:
                _resource(f"container count exceeds {C48B1_CONTAINERS}")
            for child in current:
                if isinstance(child, (dict, list)):
                    stack.append((child, depth + 1))


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _str_choice(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _optional_str_choice(value: Any, allowed: set[str]) -> bool:
    return value is None or _str_choice(value, allowed)


def _check_sequence(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        _invalid(f"{where} is not a list")
    if len(value) > C48B1_SEQUENCE_ITEMS:
        _resource(
            f"{where} width exceeds {C48B1_SEQUENCE_ITEMS}"
        )
    return value


def _validate_ctype(d: Any, where: str = "type", depth: int = 0) -> None:
    if depth > C48B1_TYPE_DEPTH:
        _resource(f"type nesting exceeds {C48B1_TYPE_DEPTH}")
    if not isinstance(d, dict) or not isinstance(d.get("kind"), str):
        _invalid(f"{where} is not a type object")
    k = d["kind"]
    if k in _TYPE_SCALARS:
        if set(d) != {"kind"}:
            _invalid(f"{where} scalar type has unexpected fields")
        return
    if k == "pointer":
        if set(d) != {"kind", "base"}:
            _invalid(f"{where} pointer type has invalid fields")
        _validate_ctype(d["base"], f"{where}.base", depth + 1)
        if d["base"]["kind"] in {"array", "function"}:
            _invalid(f"{where} pointer base type is not representable in C48 Version 1")
        return
    if k == "array":
        if set(d) != {"kind", "base", "length"} or not _is_int(d["length"]) or d["length"] <= 0:
            _invalid(f"{where} array type is invalid")
        if d["length"] > 65535:
            _resource("array length exceeds 65535")
        _validate_ctype(d["base"], f"{where}.base", depth + 1)
        if d["base"]["kind"] in {"void", "array", "function"}:
            _invalid(f"{where} array element type must be a complete non-array object type")
        try:
            size = CType.from_dict(d["base"]).size * d["length"]
        except (AssertionError, ValueError):
            _invalid(f"{where} array element type is not a complete object type")
        if size > 65535:
            _resource("array object size exceeds 65535")
        return
    if k == "function":
        if set(d) != {"kind", "params", "ret"}:
            _invalid(f"{where} function type is invalid")
        params = _check_sequence(d.get("params"), f"{where}.params")
        for i, p in enumerate(params):
            _validate_ctype(p, f"{where}.params[{i}]", depth + 1)
            if p["kind"] in {"void", "array", "function"}:
                _invalid(f"{where}.params[{i}] must be a scalar or pointer type")
        _validate_ctype(d["ret"], f"{where}.ret", depth + 1)
        if d["ret"]["kind"] in {"array", "function"}:
            _invalid(f"{where}.ret cannot be an array or function type")
        return
    _invalid(f"{where} has unknown type kind {k!r}")


def _validate_const(c: Any, where: str) -> None:
    if not isinstance(c, dict) or set(c) != {"ctype", "value"}:
        _invalid(f"{where} constant record is invalid")
    _validate_ctype(c["ctype"], f"{where}.ctype")
    v = c["value"]
    if _is_int(v):
        return
    if not isinstance(v, dict):
        _invalid(f"{where}.value is invalid")
    if set(v) == {"float5"}:
        h = v["float5"]
        if not isinstance(h, str) or len(h) != 10 or any(ch not in "0123456789abcdef" for ch in h):
            _invalid(f"{where} Float5 constant is invalid")
        return
    if set(v) == {"string"}:
        b = v["string"]
        if not isinstance(b, list) or any(not _is_int(x) or not 0 <= x <= 255 for x in b):
            _invalid(f"{where} string constant is invalid")
        if len(b) > C48B1_STRING_BYTES:
            _resource(f"string constant exceeds {C48B1_STRING_BYTES} bytes")
        return
    if set(v) == {"global", "offset"}:
        if not isinstance(v["global"], str) or not _is_int(v["offset"]):
            _invalid(f"{where} global-address constant is invalid")
        return
    _invalid(f"{where}.value has unknown constant representation")


def _validate_type_name(n: Any, where: str) -> None:
    if not isinstance(n, dict) or n.get("kind") != "type_name":
        _invalid(f"{where} is not a type_name")
    if not isinstance(n.get("spelling"), list) or any(not isinstance(x, str) for x in n["spelling"]):
        _invalid(f"{where}.spelling is invalid")
    if tuple(n["spelling"]) not in _TYPE_NAME_MAP:
        _invalid(f"{where}.spelling is invalid")
    if not _is_int(n.get("pointers")) or n["pointers"] < 0:
        _invalid(f"{where}.pointers is invalid")
    if n["pointers"] > POINTER_DEPTH:
        _resource(f"pointer indirection exceeds {POINTER_DEPTH}")


def _validate_declarator(n: Any, where: str) -> None:
    if not isinstance(n, dict) or n.get("kind") != "declarator" or not isinstance(n.get("name"), str):
        _invalid(f"{where} is not a declarator")
    if not _is_int(n.get("pointers")) or n["pointers"] < 0:
        _invalid(f"{where}.pointers is invalid")
    if n["pointers"] > POINTER_DEPTH:
        _resource(f"pointer indirection exceeds {POINTER_DEPTH}")
    s = n.get("suffix")
    if s is None:
        return
    if not isinstance(s, dict):
        _invalid(f"{where}.suffix is invalid")
    if s.get("kind") == "array":
        if set(s) - {"kind", "bound", "length", "base"}:
            _invalid(f"{where}.array suffix has unexpected fields")
        if s.get("bound") is not None:
            _validate_node(s["bound"], f"{where}.suffix.bound")
        if "length" in s and (not _is_int(s["length"]) or s["length"] <= 0):
            _invalid(f"{where}.suffix.length is invalid")
        return
    if s.get("kind") == "function":
        params = _check_sequence(s.get("params"), f"{where}.function params")
        for i, p in enumerate(params):
            _validate_node(p, f"{where}.suffix.params[{i}]")
        return
    _invalid(f"{where}.suffix has unknown kind")


def _validate_node(n: Any, where: str = "program") -> None:
    if not isinstance(n, dict) or not isinstance(n.get("kind"), str):
        _invalid(f"{where} is not an AST node")
    k = n["kind"]
    if k not in _AST_KINDS:
        _invalid(f"{where} has unknown AST kind {k!r}")

    if k == "translation_unit":
        items = _check_sequence(n.get("items"), "translation_unit.items")
        if not isinstance(n.get("symbols"), dict):
            _invalid("translation_unit requires symbols object")
        if len(n["symbols"]) > C48B1_SYMBOLS:
            _resource(f"symbol count exceeds {C48B1_SYMBOLS}")
        for i, x in enumerate(items): _validate_node(x, f"items[{i}]")
        for name, s in n["symbols"].items():
            if not isinstance(name, str) or not isinstance(s, dict): _invalid("symbol table entry invalid")
            if set(s) != {"type", "entity", "linkage", "defined", "storage"}: _invalid(f"symbol {name!r} fields invalid")
            _validate_ctype(s["type"], f"symbol {name!r}.type")
            if (
                not _str_choice(s["entity"], {"object", "function"})
                or not _str_choice(s["linkage"], {"internal", "external"})
                or not isinstance(s["defined"], bool)
            ):
                _invalid(f"symbol {name!r} metadata invalid")
            if s["entity"] == "object" and s["type"]["kind"] == "void":
                _invalid(f"symbol {name!r} has invalid void object type")
            if not _optional_str_choice(s["storage"], {"static", "extern"}):
                _invalid(f"symbol {name!r} storage invalid")
        return

    if k == "type_name": _validate_type_name(n, where); return
    if k == "declarator": _validate_declarator(n, where); return
    if k == "parameter":
        _validate_type_name(n.get("type"), f"{where}.type"); _validate_ctype(n.get("ctype"), f"{where}.ctype")
        if n["ctype"]["kind"] in {"void", "array", "function"}:
            _invalid(f"{where}.ctype must be a scalar or pointer type")
        if n.get("name") is not None and not isinstance(n["name"], str): _invalid(f"{where}.name invalid")
        if not _is_int(n.get("pointers")) or n["pointers"] < 0:
            _invalid(f"{where}.pointers invalid")
        if n["pointers"] > POINTER_DEPTH:
            _resource(f"pointer indirection exceeds {POINTER_DEPTH}")
        return
    if k == "declaration":
        _validate_type_name(n.get("base_type"), f"{where}.base_type")
        scope = n.get("scope")
        if (
            not _str_choice(scope, {"file", "block"})
            or not _optional_str_choice(n.get("storage"), {"static", "extern"})
        ):
            _invalid(f"{where} declaration metadata invalid")
        declarators = _check_sequence(
            n.get("declarators"), f"{where}.declarators"
        )
        for i, x in enumerate(declarators):
            _validate_node(x, f"{where}.declarators[{i}]")
            # File-scope semantic records carry linkage/definition metadata used by
            # the host loader.  Block-scope records deliberately do not: their
            # storage/lifetime is established by the containing declaration.
            if scope == "file":
                if (
                    not isinstance(x.get("definition"), bool)
                    or not _str_choice(
                        x.get("linkage"), {"internal", "external"}
                    )
                ):
                    _invalid(
                        f"{where}.declarators[{i}] file-scope flags invalid"
                    )
            elif "definition" in x or "linkage" in x:
                _invalid(f"{where}.declarators[{i}] block-scope flags invalid")
        return
    if k == "init_declarator":
        _validate_declarator(n.get("declarator"), f"{where}.declarator"); _validate_ctype(n.get("ctype"), f"{where}.ctype")
        if n["ctype"]["kind"] == "void":
            _invalid(f"{where}.ctype cannot be void for an object declaration")
        if "definition" in n and not isinstance(n["definition"], bool): _invalid(f"{where}.definition invalid")
        if "linkage" in n and not _str_choice(
            n["linkage"], {"internal", "external"}
        ):
            _invalid(f"{where}.linkage invalid")
        if n.get("initializer") is not None: _validate_node(n["initializer"], f"{where}.initializer")
        return
    if k == "function_definition":
        _validate_type_name(n.get("base_type"), f"{where}.base_type")
        decl = n.get("declarator")
        _validate_declarator(decl, f"{where}.declarator")
        suffix = decl.get("suffix") if isinstance(decl, dict) else None
        if not isinstance(suffix, dict) or suffix.get("kind") != "function":
            _invalid(f"{where}.declarator must declare a function")
        _validate_ctype(n.get("ctype"), f"{where}.ctype")
        ctype = n.get("ctype")
        if not isinstance(ctype, dict) or ctype.get("kind") != "function":
            _invalid(f"{where}.ctype must be a function type")
        if not _optional_str_choice(n.get("storage"), {"static"}):
            _invalid(f"{where}.storage invalid")
        _validate_node(n.get("body"), f"{where}.body"); return
    if k == "compound":
        declarations = _check_sequence(
            n.get("declarations"), f"{where}.declarations"
        )
        statements = _check_sequence(
            n.get("statements"), f"{where}.statements"
        )
        for i,x in enumerate(declarations): _validate_node(x,f"{where}.declarations[{i}]")
        for i,x in enumerate(statements): _validate_node(x,f"{where}.statements[{i}]")
        return
    if k in {"break", "continue"}: return
    if k == "expr_stmt":
        if "value" not in n: _invalid(f"{where}.value is missing")
        if n["value"] is not None: _validate_node(n["value"], f"{where}.value")
        return
    if k == "return":
        _validate_ctype(n.get("return_type"), f"{where}.return_type")
        if n.get("value") is not None: _validate_node(n["value"], f"{where}.value")
        return
    if k == "if":
        _validate_node(n.get("condition"), f"{where}.condition"); _validate_node(n.get("then"), f"{where}.then")
        if "otherwise" not in n: _invalid(f"{where}.otherwise is missing")
        if n["otherwise"] is not None: _validate_node(n["otherwise"], f"{where}.otherwise")
        return
    if k in {"while", "do_while"}:
        _validate_node(n.get("condition"), f"{where}.condition"); _validate_node(n.get("body"), f"{where}.body"); return
    if k == "for":
        for fld in ("init", "condition", "step"):
            if fld not in n: _invalid(f"{where}.{fld} is missing")
            if n[fld] is not None: _validate_node(n[fld], f"{where}.{fld}")
        _validate_node(n.get("body"), f"{where}.body"); return

    if k in {"scalar_initializer", "string_initializer"}:
        _validate_node(n.get("value"), f"{where}.value"); _validate_const(n.get("const"), f"{where}.const"); return
    if k == "init_list":
        values = _check_sequence(n.get("values"), f"{where}.values")
        const_items = _check_sequence(
            n.get("const_items"), f"{where}.const_items"
        )
        for i,x in enumerate(values): _validate_node(x,f"{where}.values[{i}]")
        for i,x in enumerate(const_items): _validate_const(x,f"{where}.const_items[{i}]")
        return

    # All remaining kinds are expressions and require a semantic result type.
    _validate_ctype(n.get("ctype"), f"{where}.ctype")
    if not isinstance(n.get("lvalue"), bool) or not isinstance(n.get("modifiable"), bool): _invalid(f"{where} expression value-category flags invalid")
    if k == "identifier":
        if (
            not isinstance(n.get("name"), str)
            or not _str_choice(n.get("entity"), {"object", "function"})
        ):
            _invalid(f"{where} identifier invalid")
        return
    if k == "integer_literal":
        if (
            not _is_int(n.get("value"))
            or not 0 <= n["value"] <= 65535
            or not isinstance(n.get("unsigned_suffix"), bool)
            or not isinstance(n.get("spelling"), str)
        ):
            _invalid(f"{where} integer literal invalid")
        return
    if k == "character_literal":
        if (
            not _is_int(n.get("value"))
            or not 0 <= n["value"] <= 255
            or not isinstance(n.get("spelling"), str)
        ):
            _invalid(f"{where} character literal invalid")
        return
    if k == "floating_literal":
        h = n.get("float5")
        if (
            not isinstance(n.get("value"), str)
            or not isinstance(n.get("spelling"), str)
            or not isinstance(h, str)
            or len(h) != 10
            or any(ch not in "0123456789abcdef" for ch in h)
        ):
            _invalid(f"{where} floating literal invalid")
        return
    if k == "string_literal":
        if not isinstance(n.get("bytes"), list) or any(not _is_int(x) or not 0 <= x <= 255 for x in n["bytes"]) or not _is_int(n.get("sid")) or not 0 <= n["sid"] <= 65535 or not isinstance(n.get("spelling"), str):
            _invalid(f"{where} string literal invalid")
        if len(n["bytes"]) > C48B1_STRING_BYTES:
            _resource(f"string literal exceeds {C48B1_STRING_BYTES} bytes")
        return
    if k == "sizeof_type":
        _validate_type_name(n.get("type_name"), f"{where}.type_name")
        if not _is_int(n.get("sizeof_value")): _invalid(f"{where}.sizeof_value invalid")
        return
    if k == "sizeof_expr":
        _validate_node(n.get("operand"), f"{where}.operand")
        if not _is_int(n.get("sizeof_value")): _invalid(f"{where}.sizeof_value invalid")
        return
    if k == "cast":
        _validate_type_name(n.get("type_name"), f"{where}.type_name"); _validate_node(n.get("operand"), f"{where}.operand"); return
    if k == "assign":
        _validate_node(n.get("left"), f"{where}.left"); _validate_node(n.get("right"), f"{where}.right"); return
    if k in {"unary", "postfix"}:
        allowed = {"++","--"} if k == "postfix" else {"++","--","+","-","!","~","&","*"}
        if not _str_choice(n.get("op"), allowed):
            _invalid(f"{where}.op invalid")
        _validate_node(n.get("operand"), f"{where}.operand"); return
    if k == "index":
        _validate_node(n.get("base"), f"{where}.base"); _validate_node(n.get("index"), f"{where}.index"); return
    if k == "call":
        _validate_node(n.get("function"), f"{where}.function")
        if n["function"].get("kind") != "identifier": _invalid(f"{where}.function must be a direct identifier")
        args = _check_sequence(n.get("args"), f"{where}.args")
        for i,x in enumerate(args): _validate_node(x,f"{where}.args[{i}]")
        return
    if k == "binary":
        if not _str_choice(
            n.get("op"),
            {"+","-","*","/","%","<<",">>","<","<=",">",">=",
             "==","!=","&","|","^","&&","||"},
        ):
            _invalid(f"{where}.op invalid")
        _validate_node(n.get("left"), f"{where}.left"); _validate_node(n.get("right"), f"{where}.right")
        if "shift_width" in n and (
            not _is_int(n["shift_width"]) or n["shift_width"] not in (8, 16)
        ):
            _invalid(f"{where}.shift_width invalid")
        return
    _invalid(f"{where} contains unsupported or unknown C48B1 node kind {k!r}")


_TYPE_NAME_MAP = {
    ("void",): {"kind": "void"},
    ("char",): {"kind": "char"},
    ("unsigned", "char"): {"kind": "uchar"},
    ("short",): {"kind": "short"},
    ("unsigned", "short"): {"kind": "ushort"},
    ("int",): {"kind": "int"},
    ("unsigned", "int"): {"kind": "uint"},
    ("float",): {"kind": "float"},
}


def _ctype_from_type_name(node: dict[str, Any], where: str) -> CType:
    spelling = tuple(node.get("spelling", []))
    base = _TYPE_NAME_MAP.get(spelling)
    if base is None:
        _invalid(f"{where} has invalid type spelling")
    ctype = CType.from_dict(base)
    for _ in range(node.get("pointers", 0)):
        ctype = ptr(ctype)
    return ctype


def _expected_literal_type(node: dict[str, Any]) -> CType | None:
    kind = node.get("kind")
    if kind == "integer_literal":
        return UINT if node["unsigned_suffix"] or node["value"] > 32767 else INT
    if kind == "character_literal":
        return INT
    if kind == "floating_literal":
        return FLOAT
    if kind == "string_literal":
        return ptr(CHAR)
    if kind in {"sizeof_type", "sizeof_expr"}:
        return UINT
    return None


def _check_identifier_metadata(
    node: dict[str, Any], declared_dict: dict[str, Any], entity: str
) -> None:
    actual = CType.from_dict(node["ctype"])
    declared = CType.from_dict(declared_dict)
    allowed = {declared}
    if declared.is_array and declared.base is not None:
        allowed.add(ptr(declared.base))
    if actual not in allowed or node["entity"] != entity:
        _invalid(
            f"identifier {node['name']!r} metadata disagrees with declaration"
        )


def _validate_identifier_scopes(program: dict[str, Any]) -> None:
    """Cross-check identifier metadata against its nearest lexical declaration."""
    global_scope: dict[str, tuple[dict[str, Any], str]] = {
        name: (record["type"], record["entity"])
        for name, record in program["symbols"].items()
    }

    def lookup(
        name: str, scopes: list[dict[str, tuple[dict[str, Any], str]]]
    ) -> tuple[dict[str, Any], str] | None:
        for scope in reversed(scopes):
            if name in scope:
                return scope[name]
        return None

    def walk(
        node: Any, scopes: list[dict[str, tuple[dict[str, Any], str]]]
    ) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child, scopes)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("kind")
        if kind == "identifier":
            declaration = lookup(node["name"], scopes)
            if declaration is None:
                _invalid(f"identifier {node['name']!r} has no declaration")
            _check_identifier_metadata(node, declaration[0], declaration[1])
            return
        if kind == "compound":
            local: dict[str, tuple[dict[str, Any], str]] = {}
            nested = scopes + [local]
            for declaration in node["declarations"]:
                if declaration.get("kind") != "declaration":
                    walk(declaration, nested)
                    continue
                for idecl in declaration["declarators"]:
                    ctype = idecl["ctype"]
                    entity = (
                        "function" if ctype.get("kind") == "function" else "object"
                    )
                    local[idecl["declarator"]["name"]] = (ctype, entity)
                    initializer = idecl.get("initializer")
                    if initializer is not None:
                        walk(initializer, nested)
            for statement in node["statements"]:
                walk(statement, nested)
            return
        for child in node.values():
            if isinstance(child, (dict, list)):
                walk(child, scopes)

    for item in program["items"]:
        if item["kind"] == "declaration":
            for idecl in item["declarators"]:
                initializer = idecl.get("initializer")
                if initializer is not None:
                    walk(initializer, [global_scope])
        elif item["kind"] == "function_definition":
            parameters: dict[str, tuple[dict[str, Any], str]] = {}
            suffix = item["declarator"].get("suffix") or {}
            for param in suffix.get("params", []):
                name = param.get("name")
                if name:
                    parameters[name] = (param["ctype"], "object")
            walk(item["body"], [global_scope, parameters])


def _validate_semantic_consistency(program: dict[str, Any]) -> None:
    """Reject semantically forged C48B1 annotations before VM indexing.

    This deliberately checks invariants that are already frozen by the compiler
    and consumed as trusted metadata by the VM.  It is not a second compiler;
    it cross-checks redundant executable annotations against each other.  Array
    bound syntax is deliberately removed by _runtime_tree(), so the loader
    validates the frozen resolved CType rather than trying to re-run semantic
    constant evaluation from syntax that is no longer present.
    """
    symbols = program["symbols"]
    declarations: dict[str, tuple[dict[str, Any], str]] = {}

    for i, item in enumerate(program["items"]):
        kind = item["kind"]
        records: list[tuple[str, dict[str, Any], str]] = []
        if kind == "declaration":
            for j, idecl in enumerate(item["declarators"]):
                records.append((
                    idecl["declarator"]["name"], idecl["ctype"],
                    f"items[{i}].declarators[{j}]",
                ))
        elif kind == "function_definition":
            records.append((
                item["declarator"]["name"], item["ctype"],
                f"items[{i}]",
            ))
        for name, ctype, where in records:
            previous = declarations.get(name)
            if previous is not None and previous[0] != ctype:
                _invalid(f"{where} conflicts with prior declaration of {name!r}")
            declarations[name] = (ctype, where)
            sym = symbols.get(name)
            if sym is None:
                _invalid(f"{where} has no matching symbol-table entry for {name!r}")
            if sym["type"] != ctype:
                _invalid(f"{where} type disagrees with symbol {name!r}")
            entity = "function" if ctype.get("kind") == "function" else "object"
            if sym["entity"] != entity:
                _invalid(f"{where} entity disagrees with symbol {name!r}")

    _validate_identifier_scopes(program)

    sid_bytes: dict[int, tuple[int, ...]] = {}
    stack: list[Any] = [program]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            stack.extend(reversed(current))
            continue
        if not isinstance(current, dict):
            continue
        kind = current.get("kind")
        if kind in _AST_KINDS:
            expected = _expected_literal_type(current)
            if kind == "string_literal":
                actual_string = CType.from_dict(current["ctype"])
                string_array = CType(
                    "array", base=CHAR, length=len(current["bytes"]) + 1
                )
                if actual_string not in {ptr(CHAR), string_array}:
                    _invalid("string_literal result type is inconsistent")
            elif expected is not None and CType.from_dict(current["ctype"]) != expected:
                _invalid(f"{kind} result type is inconsistent")
            if kind == "call":
                fn_type = CType.from_dict(current["function"]["ctype"])
                actual = CType.from_dict(current["ctype"])
                if not fn_type.is_function or fn_type.ret is None or actual != fn_type.ret:
                    _invalid("call result type disagrees with function declaration")
            elif kind == "binary" and current.get("op") in {"+", "-"}:
                left = CType.from_dict(current["left"]["ctype"])
                right = CType.from_dict(current["right"]["ctype"])
                actual = CType.from_dict(current["ctype"])
                expected_binary: CType | None = None
                if left.is_pointer and right.is_integer:
                    expected_binary = left if current["op"] in {"+", "-"} else None
                elif current["op"] == "+" and left.is_integer and right.is_pointer:
                    expected_binary = right
                elif current["op"] == "-" and left.is_pointer and right.is_pointer:
                    expected_binary = INT
                if expected_binary is not None and actual != expected_binary:
                    _invalid("pointer arithmetic result type is inconsistent")
            elif kind == "sizeof_type":
                target = _ctype_from_type_name(current["type_name"], "sizeof type")
                try:
                    expected_size = target.size
                except (AssertionError, ValueError):
                    _invalid("sizeof type is not a complete object type")
                if current["sizeof_value"] != expected_size:
                    _invalid("sizeof_value disagrees with type")
            elif kind == "sizeof_expr":
                target = CType.from_dict(current["operand"]["ctype"])
                try:
                    expected_size = target.size
                except (AssertionError, ValueError):
                    _invalid("sizeof operand is not a complete object type")
                if current["sizeof_value"] != expected_size:
                    _invalid("sizeof_value disagrees with operand type")
            elif kind == "string_literal":
                sid = current["sid"]
                value = tuple(current["bytes"])
                prior = sid_bytes.get(sid)
                if prior is not None and prior != value:
                    _invalid(f"string SID {sid} aliases different literal bytes")
                sid_bytes[sid] = value
        for child in current.values():
            if isinstance(child, (dict, list)):
                stack.append(child)


def validate_program(program: Any) -> dict[str, Any]:
    _check_loaded_structure(program)
    try:
        _validate_node(program)
    except RecursionError:
        _resource("schema nesting exceeded host recursion safety")
    if not isinstance(program, dict):
        _invalid("program root is not an object")
    _validate_semantic_consistency(program)
    return program



def _runtime_tree(value: Any) -> Any:
    """Remove compile-only source locations from the executable tree.

    The host IR is intentionally deterministic across filesystem locations.
    All semantically relevant annotations remain; only `pos` dictionaries are
    omitted because diagnostics have already been emitted before serialization.
    """
    if isinstance(value, dict):
        # Array declarator `bound` expressions are compile-time syntax only.  The
        # semantic C type stored on the declaration already contains the frozen
        # resolved element count, and the VM never re-evaluates source bounds.
        # Omitting them also avoids carrying partially annotated parser syntax in
        # the runtime executable.
        omit = {"pos"}
        if value.get("kind") == "array" and "bound" in value:
            omit.add("bound")
        return {k: _runtime_tree(v) for k, v in sorted(value.items()) if k not in omit}
    if isinstance(value, list):
        return [_runtime_tree(v) for v in value]
    return value


def canonical_payload(program: dict[str, Any]) -> bytes:
    tree = _runtime_tree(program)
    return json.dumps(tree, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def encode(program: dict[str, Any]) -> bytes:
    payload = canonical_payload(program)
    digest = hashlib.sha256(payload).hexdigest().encode("ascii")
    return MAGIC + digest + b"\n" + payload + b"\n"


def decode(data: bytes) -> dict[str, Any]:
    if len(data) > C48B1_BYTES:
        _resource(f"file exceeds {C48B1_BYTES} bytes")
    if not data.startswith(MAGIC):
        raise RuntimeC48Error("not a C48B1 host executable")
    rest = data[len(MAGIC):]
    try:
        digest, payload_line = rest.split(b"\n", 1)
    except ValueError:
        raise RuntimeC48Error("truncated C48B1 header") from None
    if len(digest) != 64 or any(c not in b"0123456789abcdef" for c in digest):
        raise RuntimeC48Error("invalid C48B1 SHA-256 field")
    if not payload_line.endswith(b"\n"):
        raise RuntimeC48Error("truncated C48B1 payload")
    payload = payload_line[:-1]
    _check_json_nesting(payload)
    if hashlib.sha256(payload).hexdigest().encode("ascii") != digest:
        raise RuntimeC48Error("C48B1 payload integrity failure")
    try:
        obj = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeC48Error("malformed C48B1 JSON payload") from None
    except RecursionError:
        _resource("JSON nesting exceeded host recursion safety")
    except MemoryError:
        _resource("JSON allocation exceeded host memory safety")
    if not isinstance(obj, dict) or obj.get("kind") != "translation_unit":
        raise RuntimeC48Error("invalid C48B1 translation-unit payload")
    # Reject structurally malformed but correctly re-hashed internal IR before
    # it can reach the VM and leak host KeyError/TypeError exceptions.
    validate_program(obj)
    # C48B1 is a canonical deterministic format, not merely arbitrary JSON with
    # a matching digest.  Re-encoding also rejects duplicate-key or noncanonical
    # representations that Python's JSON parser would otherwise normalize.
    try:
        canonical = canonical_payload(obj)
    except (RecursionError, MemoryError):
        _resource("canonicalization exceeded host safety")
    if canonical != payload:
        raise RuntimeC48Error("noncanonical C48B1 JSON payload")
    return obj


def write(path: Path, program: dict[str, Any]) -> None:
    data = encode(program)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        # The temp must be unique, owned by this invocation, and on the same
        # filesystem as the destination so os.replace() is an atomic commit.
        fd, raw_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        tmp = Path(raw_name)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # Re-read and validate the complete executable before commit.
        decode(tmp.read_bytes())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass


def read(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise RuntimeC48Error(f"cannot stat C48B1 program: {exc}") from None
    if size > C48B1_BYTES:
        _resource(f"file exceeds {C48B1_BYTES} bytes")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeC48Error(f"cannot read C48B1 program: {exc}") from None
    return decode(data)
