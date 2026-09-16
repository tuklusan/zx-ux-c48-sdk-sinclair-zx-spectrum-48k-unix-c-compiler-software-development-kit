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
"""Regression tests for the 2026-09 forensic compiler/runtime review."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes
from c48.errors import PreprocessorError, RuntimeC48Error, TypeC48Error
from c48.format import MAGIC, canonical_payload, decode
from c48.limits import ResourceBudget
from c48.sound import discover_literal_beeps


def rehashed(program: dict) -> bytes:
    payload = canonical_payload(program)
    digest = hashlib.sha256(payload).hexdigest().encode("ascii")
    return MAGIC + digest + b"\n" + payload + b"\n"


def compile_program(source: bytes = b"int x;int main(void){return 0;}\n") -> dict:
    return compile_bytes(source, source_name="review.c", base_dir=Path.cwd())


class LoaderForensicReviewTests(unittest.TestCase):
    def assert_rejected(self, program: dict, pattern: str) -> None:
        with self.assertRaisesRegex(RuntimeC48Error, pattern):
            decode(rehashed(program))

    def test_valid_compiler_output_still_loads(self):
        program = compile_program()
        self.assertEqual(decode(rehashed(program))["kind"], "translation_unit")

    def test_void_object_type_is_rejected_before_vm_indexing(self):
        program = compile_program()
        idecl = program["items"][0]["declarators"][0]
        idecl["ctype"] = {"kind": "void"}
        program["symbols"]["x"]["type"] = {"kind": "void"}
        self.assert_rejected(program, r"void.*object")

    def test_illegal_array_element_types_are_rejected(self):
        bad_bases = (
            {"kind": "void"},
            {"kind": "array", "base": {"kind": "int"}, "length": 1},
            {"kind": "function", "params": [], "ret": {"kind": "int"}},
        )
        for base in bad_bases:
            with self.subTest(base=base["kind"]):
                program = compile_program(b"int x[1];int main(void){return 0;}\n")
                forged = {"kind": "array", "base": base, "length": 1}
                program["items"][0]["declarators"][0]["ctype"] = forged
                program["symbols"]["x"]["type"] = forged
                self.assert_rejected(program, "array element type")

    def test_array_total_byte_size_over_65535_is_rejected(self):
        program = compile_program(b"float x[1];int main(void){return 0;}\n")
        forged = {"kind": "array", "base": {"kind": "float"}, "length": 65535}
        program["items"][0]["declarators"][0]["ctype"] = forged
        program["symbols"]["x"]["type"] = forged
        self.assert_rejected(program, "array object size exceeds 65535")

    def test_missing_expr_stmt_value_is_rejected(self):
        program = compile_program(b"int main(void){;return 0;}\n")
        del program["items"][0]["body"]["statements"][0]["value"]
        self.assert_rejected(program, "value is missing")

    def test_missing_if_otherwise_is_rejected(self):
        program = compile_program(
            b"int main(void){if(1)return 0;return 1;}\n"
        )
        del program["items"][0]["body"]["statements"][0]["otherwise"]
        self.assert_rejected(program, "otherwise is missing")

    def test_missing_for_optional_fields_are_rejected(self):
        for field in ("init", "condition", "step"):
            with self.subTest(field=field):
                program = compile_program(
                    b"int main(void){for(;;)break;return 0;}\n"
                )
                del program["items"][0]["body"]["statements"][0][field]
                self.assert_rejected(program, rf"{field} is missing")

    def test_invalid_type_spelling_is_rejected(self):
        program = compile_program()
        program["items"][0]["base_type"]["spelling"] = ["signed"]
        self.assert_rejected(program, "spelling is invalid")


class CompilerForensicReviewTests(unittest.TestCase):
    def test_extern_void_object_is_rejected(self):
        with self.assertRaisesRegex(TypeC48Error, "void object is invalid"):
            compile_program(b"extern void x;int main(void){return 0;}\n")

    def test_builtin_header_cannot_open_quoted_local_include(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "local.h").write_text("int y;\n", encoding="ascii")
            source = b"#include <c48.h>\nint main(void){return 0;}\n"
            with self.assertRaisesRegex(PreprocessorError, "nesting exceeds one level"):
                compile_bytes(
                    source,
                    source_name="review.c",
                    base_dir=root,
                    builtin_header='#include "local.h"\n',
                )

    def test_casted_beep_argument_is_not_pre_synthesized_under_wrong_key(self):
        program = {
            "kind": "call",
            "function": {"kind": "identifier", "name": "beep"},
            "args": [
                {
                    "kind": "cast",
                    "operand": {"kind": "floating_literal", "float5": "8100000000"},
                },
                {"kind": "integer_literal", "value": 0},
            ],
        }
        self.assertEqual(discover_literal_beeps(program), [])

    def test_type_dicts_do_not_consume_ast_node_budget(self):
        budget = ResourceBudget()
        budget.check_ast(
            {
                "kind": "translation_unit",
                "type": {
                    "kind": "pointer",
                    "base": {"kind": "pointer", "base": {"kind": "int"}},
                },
            }
        )
        self.assertEqual(budget.ast_nodes, 1)


if __name__ == "__main__":
    unittest.main()
