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
"""Executable corpus for the review's 84 additional pre-1.0 attacks.

The method order is deliberately identical to doc/SECURITY-TEST-RESULTS.md:
MEM-01..20, B1-01..22, LEX-01..22, PAR-01..20.  Each test either executes a
C48 program, compiles hostile C48 bytes, or mutates C48B1 produced from a C48
program.  Host exceptions are failures, not acceptable security outcomes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes, compile_file
from c48.errors import C48Error, IOC48Error, LexicalError, ResourceLimitError, RuntimeC48Error
from c48.format import MAGIC, canonical_payload, decode, encode, read
from c48.limits import C48B1_AST_NODES, C48B1_BYTES, SOURCE_LINE_BYTES, SOURCE_OBJECT_BYTES
from c48.memory import C48Memory, PointerRecord, SCREEN_HI, SCREEN_LO, USER_HI, USER_LO
from c48.screen import Font4x8, ZXScreen
from c48.typesys import CHAR, INT
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")
HOST_HEADER = (SDK / "usr" / "src" / "c48host.h").read_bytes()


def _compile_host(source: str):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "c48host.h").write_bytes(HOST_HEADER)
        path = root / "attack.c"
        path.write_text(source, encoding="ascii")
        return compile_file(path)


def _run(source: str, *, heap_size: int = 1024, max_steps: int | None = 200000) -> int:
    program = _compile_host(source)
    return C48VM(
        program,
        ZXScreen(FONT),
        argv=["attack"],
        heap_size=heap_size,
        max_steps=max_steps,
    ).run()


def _blob(program: dict) -> bytes:
    payload = canonical_payload(program)
    digest = hashlib.sha256(payload).hexdigest().encode("ascii")
    return MAGIC + digest + b"\n" + payload + b"\n"


def _base(source: bytes = b"int main(void){return 0;}\n") -> dict:
    return compile_bytes(source, source_name="attack.c", base_dir=Path.cwd())


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first(program: dict, kind: str) -> dict:
    return next(node for node in _walk(program) if node.get("kind") == kind)


class SecurityReview01MemoryProvenanceTests(unittest.TestCase):
    def test_001_mem_01_cross_object_pointer_subtraction(self):
        src = "int a[2];int b[2];int main(void){return &a[1]-&b[0];}\n"
        with self.assertRaisesRegex(RuntimeC48Error, "unrelated pointer"):
            _run(src)

    def test_002_mem_02_cross_object_and_incompatible_pointer_comparisons(self):
        src = "int a[2];int b[2];int main(void){return &a[0]<&b[0];}\n"
        with self.assertRaisesRegex(RuntimeC48Error, "unrelated pointer"):
            _run(src)
        with self.assertRaises(C48Error):
            compile_bytes(
                b"int a;char b;int main(void){return &a==&b;}\n",
                source_name="ptrcmp.c",
                base_dir=Path.cwd(),
            )

    def test_003_mem_03_one_past_decrement_then_dereference(self):
        src = "int main(void){int a[2];int *p;a[1]=7;p=a+2;p--;return *p;}\n"
        self.assertEqual(_run(src), 7)

    def test_004_mem_04_copied_pointer_bytes_stay_stale_after_free(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){char *p;char *q;p=malloc(2);*p=7;"
            "memcpy(&q,&p,2);free(p);return *q;}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
            _run(src)

    def test_005_mem_05_byte_write_invalidates_pointer_shadow(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){char *p;void *v;unsigned char *b;"
            "p=malloc(2);*p=7;v=&p;b=v;b[0]=b[0];return *p;}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
            _run(src)

    def test_006_mem_06_overlapping_memmove_preserves_pointer_provenance(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){char *p;char *s[3];p=malloc(2);*p=7;"
            "s[0]=p;s[1]=p;memmove(&s[1],&s[0],4);return *s[2];}\n"
        )
        self.assertEqual(_run(src), 7)

    def test_007_mem_07_char_byte_writes_cannot_forge_provenance(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){int x;int *real;int *fake;void *v;"
            "unsigned char *s;unsigned char *d;x=7;real=&x;v=&real;"
            "s=v;v=&fake;d=v;d[0]=s[0];d[1]=s[1];return *fake;}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
            _run(src)

    def test_008_mem_08_stale_pointer_traps_after_same_address_reuse(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){char *a;char *b;a=malloc(2);if(a==0)return 1;"
            "*a=7;free(a);b=malloc(2);if(b==0)return 2;*b=9;return *a;}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
            _run(src)

    def test_009_mem_09_allocation_ids_prevent_aba_resurrection(self):
        mem = C48Memory()
        first = mem.allocate(2, 2, None, "heap")
        stale = mem.pointer_for(first)
        mem.free(first.aid)
        second = mem.allocate(2, 2, None, "heap")
        self.assertEqual(first.start, second.start)
        self.assertNotEqual(first.aid, second.aid)
        self.assertNotEqual(stale.aid, mem.pointer_for(second).aid)
        with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
            mem.check_access(stale, CHAR)

    def test_010_mem_10_heap_exhaustion_and_reuse_loop(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){int i;char *p;char *q;i=0;while(i<200){"
            "p=malloc(2);if(p==0)return 1;*p=7;free(p);i++;}"
            "p=malloc(1024);if(p==0)return 2;q=malloc(2);if(q!=0)return 3;"
            "free(p);q=malloc(1024);if(q==0)return 4;free(q);return 0;}\n"
        )
        self.assertEqual(_run(src), 0)

    def test_011_mem_11_zero_length_memory_builtins_touch_no_pointer(self):
        src = (
            '#include "c48host.h"\n'
            "int main(void){char a[1];char *one;char *dead;char *raw;"
            "void *v;unsigned char *b;one=a+1;dead=malloc(2);free(dead);"
            "v=&raw;b=v;b[0]=0;b[1]=96;"
            "memcpy(0,0,0);memmove(0,0,0);memset(0,1,0);memchr(0,1,0);"
            "memcpy(one,one,0);memmove(one,one,0);memset(one,1,0);memchr(one,1,0);"
            "memcpy(dead,dead,0);memmove(dead,dead,0);memset(dead,1,0);memchr(dead,1,0);"
            "memcpy(raw,raw,0);memmove(raw,raw,0);memset(raw,1,0);memchr(raw,1,0);"
            "return 0;}\n"
        )
        self.assertEqual(_run(src), 0)

    def test_012_mem_12_strcpy_destination_one_byte_short(self):
        src = '#include "c48host.h"\nint main(void){char d[3];strcpy(d,"abc");return 0;}\n'
        with self.assertRaisesRegex(RuntimeC48Error, "byte range"):
            _run(src)

    def test_013_mem_13_strncpy_at_source_end_n_zero_one_large(self):
        zero = (
            '#include "c48host.h"\n'
            "int main(void){char s[1];char d[1];char *p;p=s+1;"
            "strncpy(d,p,0);return 0;}\n"
        )
        self.assertEqual(_run(zero), 0)
        for n in (1, 65535):
            src = (
                '#include "c48host.h"\n'
                f"int main(void){{char s[1];char d[2];char *p;p=s+1;"
                f"strncpy(d,p,{n}u);return 0;}}\n"
            )
            with self.subTest(n=n), self.assertRaises(RuntimeC48Error):
                _run(src)

    def test_014_mem_14_unterminated_source_in_every_string_builtin(self):
        calls = {
            "puts": "puts(s)",
            "strlen": "strlen(s)",
            "strcmp": 'strcmp(s,"x")',
            "strcpy": "strcpy(d,s)",
            "strncpy": "strncpy(d,s,3)",
            "print_at": "print_at(0,0,s)",
        }
        for name, call in calls.items():
            src = (
                '#include "c48host.h"\n'
                "int main(void){char s[2];char d[8];s[0]=97;s[1]=98;"
                f"{call};return 0;}}\n"
            )
            with self.subTest(name=name), self.assertRaisesRegex(
                RuntimeC48Error, "unterminated|bounded string read"
            ):
                _run(src)

    def test_015_mem_15_readonly_literal_aliases_reject_writes(self):
        calls = {
            "strcpy": 'strcpy("abc","x")',
            "strncpy": 'strncpy("abc","x",1)',
            "memcpy": 'memcpy("abc","x",1)',
            "memmove": 'memmove("abc","x",1)',
            "memset": 'memset("abc",120,1)',
        }
        for name, call in calls.items():
            src = '#include "c48host.h"\nint main(void){' + call + ';return 0;}\n'
            with self.subTest(name=name), self.assertRaisesRegex(
                RuntimeC48Error, "read-only"
            ):
                _run(src)

    def test_016_mem_16_misaligned_pointer_from_char_level_movement(self):
        src = (
            "int main(void){int x;void *v;char *p;int *q;"
            "v=&x;p=v;p=p+1;v=p;q=v;return *q;}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "misaligned"):
            _run(src)

    def test_017_mem_17_pointer_arithmetic_cannot_wrap_at_ffff(self):
        src = "int main(void){char a[1];char *p;p=a;p=p+65535u;return 0;}\n"
        with self.assertRaisesRegex(RuntimeC48Error, "leaves object"):
            _run(src)

    def test_018_mem_18_screen_and_user_boundary_addresses_are_isolated(self):
        screen = ZXScreen(FONT)
        mem = C48Memory(screen)
        self.assertEqual((SCREEN_LO, SCREEN_HI, USER_LO, USER_HI), (0x4000, 0x5B00, 0x6000, 0xE000))
        mem.write8(0x5AFF, 0x5A)
        self.assertEqual(mem.read8(0x5AFF), 0x5A)
        for address in (0x5B00, 0x5FFF, 0x6000, 0xDFFF, 0xE000):
            forged = PointerRecord(address, None, None)
            with self.subTest(address=hex(address)), self.assertRaises(RuntimeC48Error):
                mem.check_access(forged, CHAR)
        with self.assertRaises(C48Error):
            compile_bytes(
                b"int main(void){char *p;p=(char *)0x5b00;return *p;}\n",
                source_name="reserved.c",
                base_dir=Path.cwd(),
            )

    def test_019_mem_19_object_can_end_exactly_at_user_hi_minus_one(self):
        src = "char a[32768];int main(void){a[32767]=7;return a[32767];}\n"
        self.assertEqual(_run(src), 7)

    def test_020_mem_20_two_byte_access_cannot_cross_allocation_end(self):
        for op in ("return *p;", "*p=1;return 0;"):
            src = "int main(void){char a[1];void *v;int *p;v=a;p=v;" + op + "}\n"
            with self.subTest(op=op), self.assertRaisesRegex(
                RuntimeC48Error, "outside live object"
            ):
                _run(src)


class SecurityReview02ForgedC48B1Tests(unittest.TestCase):
    def assert_rejected(self, program: dict, pattern: str = "invalid C48B1|resource limit") -> None:
        with self.assertRaisesRegex(RuntimeC48Error, pattern):
            decode(_blob(program))

    def test_021_b1_01_wrong_expression_ctype(self):
        p = _base(b"int main(void){return 7;}\n")
        lit = _first(p, "integer_literal")
        lit["ctype"] = {"kind": "char"}
        self.assert_rejected(p)

    def test_022_b1_02_identifier_metadata_disagrees_with_symbol_table(self):
        p = _base(b"int x;int main(void){x=1;return x;}\n")
        ident = next(n for n in _walk(p) if n.get("kind") == "identifier" and n.get("name") == "x")
        ident["ctype"] = {"kind": "char"}
        self.assert_rejected(p)

    def test_023_b1_03_call_result_type_disagrees_with_function(self):
        p = _base(b"int f(void){return 1;}int main(void){return f();}\n")
        call = _first(p, "call")
        call["ctype"] = {"kind": "float"}
        self.assert_rejected(p)

    def test_024_b1_04_pointer_arithmetic_result_type_is_forged(self):
        p = _base(b"int a[2];int main(void){int *p;p=a;return *(p+1);}\n")
        binary = next(n for n in _walk(p) if n.get("kind") == "binary" and n.get("op") == "+")
        binary["ctype"] = {"kind": "int"}
        self.assert_rejected(p)

    def test_025_b1_05_array_declaration_and_type_length_mismatch(self):
        p = _base(b"int a[3];int main(void){return 0;}\n")
        idecl = p["items"][0]["declarators"][0]
        idecl["ctype"]["length"] = 4
        self.assert_rejected(p)

    def test_026_b1_06_sizeof_value_mismatch(self):
        p = _base(b"int main(void){return sizeof(int);}\n")
        node = _first(p, "sizeof_type")
        node["sizeof_value"] = 3
        self.assert_rejected(p)

    def test_027_b1_07_string_sid_collision(self):
        p = _base(b'int main(void){char *a;char *b;a="a";b="b";return 0;}\n')
        strings = [n for n in _walk(p) if n.get("kind") == "string_literal"]
        self.assertEqual(len(strings), 2)
        strings[1]["sid"] = strings[0]["sid"]
        self.assert_rejected(p)

    def test_028_b1_08_duplicate_symbol_identity_conflict(self):
        p = _base(b"int a;char b;int main(void){return 0;}\n")
        second = p["items"][1]["declarators"][0]
        second["declarator"]["name"] = "a"
        self.assert_rejected(p)

    def test_029_b1_09_block_declaration_cannot_carry_file_metadata(self):
        p = _base(b"int main(void){int x;return 0;}\n")
        idecl = _first(p["items"][0]["body"], "init_declarator")
        idecl["definition"] = True
        idecl["linkage"] = "external"
        self.assert_rejected(p)

    def test_030_b1_10_huge_integer_field_is_rejected(self):
        p = _base(b"int main(void){return 1;}\n")
        _first(p, "integer_literal")["value"] = 10 ** 200
        self.assert_rejected(p)

    def test_031_b1_11_negative_source_derived_counter_is_rejected(self):
        p = _base(b'int main(void){char *p;p="x";return 0;}\n')
        _first(p, "string_literal")["sid"] = -1
        self.assert_rejected(p)

    def test_032_b1_12_thousands_of_symbols_hit_explicit_budget(self):
        p = _base()
        template = {"type": {"kind": "int"}, "entity": "object", "linkage": "external", "defined": False, "storage": "extern"}
        for i in range(5000):
            p["symbols"][f"s{i}"] = copy.deepcopy(template)
        self.assert_rejected(p, "resource limit")

    def test_033_b1_13_deep_ast_nesting_hits_budget(self):
        p = _base(b"int main(void){return 1;}\n")
        value = p["items"][0]["body"]["statements"][0]["value"]
        for _ in range(70):
            value = {
                "kind": "unary", "op": "+", "operand": value,
                "ctype": {"kind": "int"}, "lvalue": False,
                "modifiable": False,
            }
        p["items"][0]["body"]["statements"][0]["value"] = value
        self.assert_rejected(p, "resource limit")

    def test_034_b1_14_wide_structural_lists_hit_budget(self):
        p = _base()
        body = p["items"][0]["body"]
        body["statements"] = [
            {"kind": "break"} for _ in range(4097)
        ]
        self.assert_rejected(p, "width")

    def test_035_b1_15_multimegabyte_string_byte_array_is_bounded(self):
        p = _base(b'int main(void){char *p;p="x";return 0;}\n')
        node = _first(p, "string_literal")
        node["bytes"] = [65] * 700000
        self.assert_rejected(p, "resource limit")

    def test_036_b1_16_duplicate_json_keys_are_rejected(self):
        payload = canonical_payload(_base())
        marker = b'{"items"'
        self.assertTrue(payload.startswith(marker))
        altered = b'{"kind":"translation_unit",' + payload[1:]
        digest = hashlib.sha256(altered).hexdigest().encode("ascii")
        data = MAGIC + digest + b"\n" + altered + b"\n"
        with self.assertRaises(RuntimeC48Error):
            decode(data)

    def test_037_b1_17_noncanonical_whitespace_or_order_is_rejected(self):
        payload = canonical_payload(_base())
        obj = json.loads(payload)
        altered = json.dumps(obj, ensure_ascii=True, sort_keys=False, indent=1).encode("ascii")
        digest = hashlib.sha256(altered).hexdigest().encode("ascii")
        with self.assertRaisesRegex(RuntimeC48Error, "noncanonical"):
            decode(MAGIC + digest + b"\n" + altered + b"\n")

    def test_038_b1_18_valid_digest_with_trailing_garbage_is_rejected(self):
        payload = canonical_payload(_base()) + b"X"
        digest = hashlib.sha256(payload).hexdigest().encode("ascii")
        with self.assertRaisesRegex(RuntimeC48Error, "malformed"):
            decode(MAGIC + digest + b"\n" + payload + b"\n")

    def test_039_b1_19_truncated_digest_and_payload_are_rejected(self):
        good = encode(_base())
        cases = [MAGIC + b"0" * 63 + b"\n{}\n", good[:-1], MAGIC + b"abcd"]
        for data in cases:
            with self.subTest(length=len(data)), self.assertRaises(RuntimeC48Error):
                decode(data)

    def test_040_b1_20_nul_and_nonascii_payload_bytes_are_rejected(self):
        for bad in (b"\x00", b"\xff"):
            payload = b'{' + bad + b'}'
            digest = hashlib.sha256(payload).hexdigest().encode("ascii")
            with self.subTest(bad=bad), self.assertRaisesRegex(RuntimeC48Error, "malformed"):
                decode(MAGIC + digest + b"\n" + payload + b"\n")

    def test_041_b1_21_gigabyte_sparse_file_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "huge.c48b"
            with path.open("wb") as stream:
                stream.truncate(1024 * 1024 * 1024)
            with self.assertRaisesRegex(RuntimeC48Error, "resource limit"):
                read(path)

    def test_042_b1_22_repeated_ast_subtrees_hit_node_budget(self):
        p = _base()
        body = p["items"][0]["body"]
        body["statements"] = [{"kind": "break"} for _ in range(C48B1_AST_NODES + 1)]
        self.assert_rejected(p, "resource limit")


class SecurityReview03LexicalPreprocessorTests(unittest.TestCase):
    def assert_controlled(self, data: bytes, *, base_dir: Path | None = None) -> None:
        try:
            compile_bytes(data, source_name="attack.c", base_dir=base_dir or Path.cwd())
        except C48Error:
            pass

    def test_043_lex_01_all_byte_values_at_sensitive_positions(self):
        templates = (
            (b"", b"\nint main(void){return 0;}\n"),
            (b"int x", b";int main(void){return 0;}\n"),
            (b'int main(void){char *p;p="a', b'b";return 0;}\n'),
            (b"int main(void){int x;x='", b"';return 0;}\n"),
            (b"int main(void){return 1", b"0;}\n"),
            (b"/*", b"*/\nint main(void){return 0;}\n"),
            (b"#define X ", b"\nint main(void){return 0;}\n"),
        )
        for prefix, suffix in templates:
            for byte in range(256):
                with self.subTest(prefix=prefix[:8], byte=byte):
                    self.assert_controlled(prefix + bytes([byte]) + suffix)

    def test_044_lex_02_bom_utf8_del_controls_and_newline_forms(self):
        rejected = (
            b"\xef\xbb\xbfint main(void){return 0;}\n",
            b"\xc2\xa9int main(void){return 0;}\n",
            b"\x7fint main(void){return 0;}\n",
            b"\x0bint main(void){return 0;}\n",
            b"\x0cint main(void){return 0;}\n",
            b"int x;\rint main(void){return 0;}\r",
        )
        for data in rejected:
            with self.subTest(data=data[:8]), self.assertRaises(C48Error):
                compile_bytes(data, source_name="bytes.c", base_dir=Path.cwd())
        mixed = b"int x;\r\nint main(void){\nreturn 0;\r\n}\n"
        compile_bytes(mixed, source_name="mixed.c", base_dir=Path.cwd())

    def test_045_lex_03_unterminated_literals_and_comments(self):
        cases = (
            b'int main(void){char *p;p="abc',
            b"int main(void){int x;x='a",
            b"int main(void){/*abc",
            b'int main(void){char *p;p="abc\nreturn 0;}\n',
            b"int main(void){int x;x='a\nreturn 0;}\n",
        )
        for data in cases:
            with self.subTest(data=data[:20]), self.assertRaises(C48Error):
                compile_bytes(data, source_name="unterminated.c", base_dir=Path.cwd())

    def test_046_lex_04_extremely_long_physical_line_is_bounded(self):
        data = b" " * (SOURCE_LINE_BYTES + 1)
        with self.assertRaises(ResourceLimitError):
            compile_bytes(data, source_name="long.c", base_dir=Path.cwd())

    def test_047_lex_05_extremely_many_empty_lines_are_bounded(self):
        data = b"\n" * 16385
        with self.assertRaises(ResourceLimitError):
            compile_bytes(data, source_name="lines.c", base_dir=Path.cwd())

    def test_048_lex_06_extremely_many_comments_are_bounded(self):
        ok = (b"/**/\n" * 6000) + b"int main(void){return 0;}\n"
        compile_bytes(ok, source_name="comments-ok.c", base_dir=Path.cwd())
        huge = (b"/**/\n" * 7000) + b"int main(void){return 0;}\n"
        with self.assertRaises(ResourceLimitError):
            compile_bytes(huge, source_name="comments-huge.c", base_dir=Path.cwd())

    def test_049_lex_07_long_runs_of_sensitive_punctuation_are_bounded(self):
        for ch in (b"/", b"*", b'"', b"\\", b"#", b"+", b"<"):
            with self.subTest(ch=ch), self.assertRaises(ResourceLimitError):
                compile_bytes(ch * (SOURCE_LINE_BYTES + 1), source_name="run.c", base_dir=Path.cwd())

    def test_050_lex_08_numeric_grammar_neighbors_are_controlled(self):
        valid = ("0", "00", "07", "0x0", "0xffff", "65535u", "1.", ".1", "1e1", "1.f", ".1F", "1e+1")
        for token in valid:
            with self.subTest(valid=token):
                compile_bytes(f"int main(void){{return {token};}}\n".encode("ascii"), source_name="num.c", base_dir=Path.cwd())
        invalid = ("0x", "08", "65536", "1e", "1e+", "1.0ff", "0x1g", "1uu", ".e1")
        for token in invalid:
            with self.subTest(invalid=token), self.assertRaises(C48Error):
                compile_bytes(f"int main(void){{return {token};}}\n".encode("ascii"), source_name="num.c", base_dir=Path.cwd())

    def test_051_lex_09_very_long_integer_literals_are_controlled(self):
        tokens = ("9" * 5000, "0" + "7" * 4999, "0x" + "f" * 4998)
        for token in tokens:
            with self.subTest(prefix=token[:2]), self.assertRaises(C48Error):
                compile_bytes(f"int main(void){{return {token};}}\n".encode("ascii"), source_name="longint.c", base_dir=Path.cwd())

    def test_052_lex_10_very_long_float_mantissas_and_exponents_controlled(self):
        tokens = ("1" * 2000 + ".0", "1." + "0" * 2000 + "1", "1e" + "9" * 2000, "1e-" + "9" * 2000)
        for token in tokens:
            with self.subTest(shape=token[:8]):
                self.assert_controlled(f"int main(void){{float x;x={token};return 0;}}\n".encode("ascii"))

    def test_053_lex_11_repeated_maximal_munch_operators_controlled(self):
        for op in ("+", "-", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||"):
            source = "int main(void){return " + (op * 1000) + "1;}\n"
            with self.subTest(op=op):
                self.assert_controlled(source.encode("ascii"))

    def test_054_lex_12_identifier_visible_length_boundary(self):
        good = "abcdefghijklmno"
        bad = good + "p"
        compile_bytes(f"int {good};int main(void){{return 0;}}\n".encode("ascii"), source_name="id.c", base_dir=Path.cwd())
        with self.assertRaises(LexicalError):
            compile_bytes(f"int {bad};int main(void){{return 0;}}\n".encode("ascii"), source_name="id.c", base_dir=Path.cwd())

    def test_055_lex_13_tens_of_thousands_unique_identifiers_prebounded(self):
        declarations = "".join(f"int a{i};" for i in range(20000)) + "int main(void){return 0;}\n"
        self.assertGreater(len(declarations.encode("ascii")), SOURCE_OBJECT_BYTES)
        with self.assertRaises(ResourceLimitError):
            compile_bytes(declarations.encode("ascii"), source_name="symbols.c", base_dir=Path.cwd())

    def test_056_lex_14_tens_of_thousands_repeated_declarations_prebounded(self):
        declarations = ("extern int x;" * 20000) + "int main(void){return 0;}\n"
        self.assertGreater(len(declarations.encode("ascii")), SOURCE_OBJECT_BYTES)
        with self.assertRaises(ResourceLimitError):
            compile_bytes(declarations.encode("ascii"), source_name="redecl.c", base_dir=Path.cwd())

    def test_057_lex_15_macro_doubling_tripling_and_wide_fanout_bounded(self):
        for factor in (2, 3):
            lines = ["#define A0 1"]
            for i in range(1, 12):
                body = "+".join([f"A{i-1}"] * factor)
                lines.append(f"#define A{i} {body}")
            lines.append("int main(void){return A11;}")
            with self.subTest(factor=factor), self.assertRaises(ResourceLimitError):
                compile_bytes(("\n".join(lines) + "\n").encode("ascii"), source_name="macro.c", base_dir=Path.cwd())
        wide = "#define W " + "+".join(["1"] * 1100) + "\nint main(void){return W;}\n"
        with self.assertRaises(ResourceLimitError):
            compile_bytes(wide.encode("ascii"), source_name="wide.c", base_dir=Path.cwd())

    def test_058_lex_16_parenthesized_macro_chain_is_controlled(self):
        lines = ["#define A0 1"]
        for i in range(1, 100):
            lines.append(f"#define A{i} (A{i-1})")
        lines.append("int main(void){return A99;}")
        self.assert_controlled(("\n".join(lines) + "\n").encode("ascii"))

    def test_059_lex_17_macro_expansion_to_huge_string_is_bounded(self):
        text = "x" * 7000
        source = f'#define S "{text}"\nint main(void){{char *p;p=S;return p[0];}}\n'
        program = compile_bytes(source.encode("ascii"), source_name="stringmacro.c", base_dir=Path.cwd())
        self.assertIsInstance(program, dict)

    def test_060_lex_18_many_identical_macro_redefinitions_remain_bounded(self):
        source = ("#define A 1\n" * 1000) + "int main(void){return A;}\n"
        # Identical redefinitions do not multiply semantic state and must remain controlled.
        self.assert_controlled(source.encode("ascii"))

    def test_061_lex_19_include_basename_and_suffix_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            legal = {"a.h": "int a;\n", "123456.c": "int b;\n", "x-y_z.txt": "int c;\n"}
            for name, body in legal.items():
                (root / name).write_text(body, encoding="ascii")
                compile_bytes(f'#include "{name}"\nint main(void){{return 0;}}\n'.encode("ascii"), source_name="inc.c", base_dir=root)
            invalid = ("1234567.c", "x.hpp", "../a.h", ".", "..", "")
            for name in invalid:
                with self.subTest(name=name), self.assertRaises(C48Error):
                    compile_bytes(f'#include "{name}"\nint main(void){{return 0;}}\n'.encode("ascii"), source_name="inc.c", base_dir=root)

    def test_062_lex_20_include_case_collision_is_exact_case_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Case.h").write_text("int upper;\n", encoding="ascii")
            with self.assertRaises(IOC48Error):
                compile_bytes(b'#include "case.h"\nint main(void){return 0;}\n', source_name="case.c", base_dir=root)
            compile_bytes(b'#include "Case.h"\nint main(void){return 0;}\n', source_name="case.c", base_dir=root)

    def test_063_lex_21_symlink_or_reparse_include_cannot_escape_sibling_rule(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outside = root / "outside"
            source_dir = root / "src"
            outside.mkdir(); source_dir.mkdir()
            target = outside / "evil.h"
            target.write_text("int escaped;\n", encoding="ascii")
            link = source_dir / "alias.h"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("host cannot create symlink/reparse-point test fixture")
            with self.assertRaises(C48Error):
                compile_bytes(b'#include "alias.h"\nint main(void){return 0;}\n', source_name="link.c", base_dir=source_dir)

    def test_064_lex_22_source_output_aliases_do_not_destroy_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "a.c"
            original = b"int main(void){return 0;}\n"
            src.write_bytes(original)

            def invoke(output: Path):
                return subprocess.run(
                    [sys.executable, "-B", str(COMPILER / "c48.py"),
                     str(src), "-o", str(output)],
                    capture_output=True, text=True, timeout=10,
                )

            # Lexical alias through '..' must be detected before replacement.
            (root / "sub").mkdir()
            cp = invoke(root / "sub" / ".." / "a.c")
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(src.read_bytes(), original)

            # If an output pathname is a hard link to the source, atomic replace
            # may safely replace that directory entry but must not mutate source.
            hard = root / "hard.c48b"
            try:
                os.link(src, hard)
            except OSError:
                hard = None
            if hard is not None:
                cp = invoke(hard)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                self.assertEqual(src.read_bytes(), original)
                decode(hard.read_bytes())

            # Directory symlink/junction alias must resolve back to the source.
            alias_dir = root / "aliasdir"
            if os.name == "nt":
                cp_link = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(alias_dir), str(root)],
                    capture_output=True, text=True, timeout=10,
                )
                made_alias = cp_link.returncode == 0
            else:
                try:
                    alias_dir.symlink_to(root, target_is_directory=True)
                    made_alias = True
                except (OSError, NotImplementedError):
                    made_alias = False
            if made_alias:
                cp = invoke(alias_dir / "a.c")
                self.assertNotEqual(cp.returncode, 0)
                self.assertEqual(src.read_bytes(), original)

            # Windows path equality is case-folded; a case-only output alias must
            # be rejected as the same source object.
            if os.name == "nt":
                cp = invoke(root / "A.C")
                self.assertNotEqual(cp.returncode, 0)
                self.assertEqual(src.read_bytes(), original)


class SecurityReview04ParserSemanticTests(unittest.TestCase):
    def assert_resource(self, source: str) -> None:
        with self.assertRaises(ResourceLimitError):
            compile_bytes(source.encode("ascii"), source_name="parse.c", base_dir=Path.cwd())

    def test_065_par_01_deep_parentheses_bounded(self):
        self.assert_resource("int main(void){return " + "(" * 100 + "1" + ")" * 100 + ";}\n")

    def test_066_par_02_deep_blocks_bounded(self):
        self.assert_resource("int main(void){" + "{" * 600 + "return 0;" + "}" * 600 + "}\n")

    def test_067_par_03_deep_unary_chains_bounded(self):
        self.assert_resource("int main(void){return " + "! " * 200 + "1;}\n")
        self.assert_resource("int main(void){return " + "~ " * 200 + "1;}\n")
        self.assert_resource("int main(void){return " + "+ " * 200 + "1;}\n")

    def test_068_par_04_deep_pointer_types_bounded(self):
        self.assert_resource("int " + "*" * 100 + "p;int main(void){return 0;}\n")

    def test_069_par_05_long_left_associative_binary_chain_bounded(self):
        source = "int main(void){return " + "+".join(["1"] * 1000) + ";}\n"
        self.assert_resource(source)

    def test_070_par_06_long_right_parenthesized_constant_tree_bounded(self):
        expr = "1"
        for _ in range(100):
            expr = "(1+" + expr + ")"
        self.assert_resource("int main(void){return " + expr + ";}\n")

    def test_071_par_07_huge_initializer_list_is_prebounded(self):
        source = "int a[20000]={" + ",".join(["0"] * 20000) + "};int main(void){return 0;}\n"
        self.assertGreater(len(source.encode("ascii")), SOURCE_OBJECT_BYTES)
        self.assert_resource(source)

    def test_072_par_08_huge_parameter_list_is_prebounded(self):
        params = ",".join(f"int a{i}" for i in range(5000))
        source = f"int f({params});int main(void){{return 0;}}\n"
        self.assertGreater(len(source.encode("ascii")), SOURCE_OBJECT_BYTES)
        self.assert_resource(source)

    def test_073_par_09_huge_argument_list_is_prebounded(self):
        args = ",".join(["0"] * 20000)
        source = "int f(int x);int main(void){return f(" + args + ");}\n"
        self.assertGreater(len(source.encode("ascii")), SOURCE_OBJECT_BYTES)
        self.assert_resource(source)

    def test_074_par_10_long_comma_declaration_list_is_prebounded(self):
        decls = ",".join(f"a{i}" for i in range(10000))
        source = "int " + decls + ";int main(void){return 0;}\n"
        self.assertGreater(len(source.encode("ascii")), SOURCE_OBJECT_BYTES)
        self.assert_resource(source)

    def test_075_par_11_deep_if_else_chain_bounded(self):
        source = "int main(void){" + ("if(1){" * 100) + "return 0;" + ("}else{return 1;}" * 100) + "}\n"
        self.assert_resource(source)

    def test_076_par_12_deep_loop_chain_bounded(self):
        source = "int main(void){" + ("while(1){" * 100) + "return 0;" + ("}" * 100) + "}\n"
        self.assert_resource(source)

    def test_077_par_13_chained_indexing_respects_pointer_depth_ceiling(self):
        stars = "*" * 32
        indexes = "[0]" * 32
        good = f"int {stars}p;int main(void){{return p{indexes};}}\n"
        compile_bytes(good.encode("ascii"), source_name="index.c", base_dir=Path.cwd())
        bad = "int " + "*" * 33 + "p;int main(void){return 0;}\n"
        self.assert_resource(bad)

    def test_078_par_14_call_graph_width_and_runtime_depth_are_bounded(self):
        wide = "".join(f"int f{i}(void){{return {i & 1};}}" for i in range(128))
        wide += "int main(void){return f0()+f127()-1;}\n"
        self.assertEqual(_run(wide), 0)
        funcs = []
        for i in range(70):
            if i == 69:
                funcs.append(f"int f{i}(void){{return 0;}}")
            else:
                funcs.append(f"int f{i}(void);" if i == 0 else "")
        # Source-order prototypes allow a deterministic deep chain.
        protos = "".join(f"int f{i}(void);" for i in range(70))
        defs = "".join(f"int f{i}(void){{return f{i+1}();}}" for i in range(69)) + "int f69(void){return 0;}"
        deep = protos + defs + "int main(void){return f0();}\n"
        with self.assertRaisesRegex(RuntimeC48Error, "call.*depth"):
            _run(deep)

    def test_079_par_15_mutual_recursion_with_prototypes_is_controlled(self):
        src = (
            "int a(int n);int b(int n);"
            "int a(int n){if(n==0)return 0;return b(n-1);}"
            "int b(int n){if(n==0)return 0;return a(n-1);}"
            "int main(void){return a(20);}\n"
        )
        self.assertEqual(_run(src), 0)
        infinite = (
            "int a(void);int b(void);"
            "int a(void){return b();}int b(void){return a();}"
            "int main(void){return a();}\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "call.*depth"):
            _run(infinite)

    def test_080_par_16_large_symbol_table_and_shadowing_scopes_controlled(self):
        globals_ = "".join(f"int g{i};\n" for i in range(1500))
        shadows = ""
        for _ in range(40):
            shadows += "{int x;x=1;"
        shadows += "return 0;" + "}" * 40
        source = globals_ + "int main(void){" + shadows + "}\n"
        program = compile_bytes(source.encode("ascii"), source_name="symbols.c", base_dir=Path.cwd())
        self.assertGreaterEqual(len(program["symbols"]), 1501)
        self.assertEqual(C48VM(program, ZXScreen(FONT), argv=["symbols"], max_steps=200000).run(), 0)

    def test_081_par_17_sizeof_cast_pointer_type_pathologies_controlled(self):
        valid = (
            "int main(void){int x;"
            "x=(int)(unsigned int)(char)sizeof(int ********);"
            "if(x!=2)return 1;"
            "return sizeof(char **************)==2?0:0;}\n"
        )
        # C48 deliberately rejects the ternary operator, but must do so in a
        # controlled way even after a pathological but valid type prefix.
        with self.assertRaises(C48Error):
            compile_bytes(
                valid.encode("ascii"), source_name="types.c",
                base_dir=Path.cwd(),
            )
        executable = (
            "int main(void){int x;"
            "x=(int)(unsigned int)(char)sizeof(int ********);"
            "if(x!=2)return 1;return sizeof(char **************)!=2;}\n"
        )
        self.assertEqual(_run(executable), 0)

    def test_082_par_18_constant_division_remainder_shift_boundaries(self):
        src = (
            "int main(void){int a;a=32767/1;if(a!=32767)return 1;"
            "a=-32767-1;a=a%3;if(a!=-2)return 2;"
            "if((1<<16)!=1)return 3;if((1>>16)!=1)return 4;return 0;}\n"
        )
        self.assertEqual(_run(src), 0)
        with self.assertRaises(C48Error):
            compile_bytes(b"int x=1/0;int main(void){return 0;}\n", source_name="div0.c", base_dir=Path.cwd())

    def test_083_par_19_float_underflow_overflow_literals_are_controlled(self):
        for token in ("1e-9999", "1e9999", "1e-38", "1e38", "3.4e38"):
            source = f"int main(void){{float x;x={token};return 0;}}\n".encode("ascii")
            with self.subTest(token=token):
                try:
                    compile_bytes(source, source_name="float.c", base_dir=Path.cwd())
                except C48Error:
                    pass

    def test_084_par_20_large_error_line_and_column_positions_remain_exact(self):
        data = (b"\n" * 10000) + b"int main(void){return @;}\n"
        with self.assertRaises(C48Error) as cm:
            compile_bytes(data, source_name="line.c", base_dir=Path.cwd())
        self.assertIsNotNone(cm.exception.pos)
        self.assertEqual(cm.exception.pos.line, 10001)
        long_prefix = b"int main(void){" + (b" " * 7900) + b"@}\n"
        with self.assertRaises(C48Error) as cm2:
            compile_bytes(long_prefix, source_name="column.c", base_dir=Path.cwd())
        self.assertIsNotNone(cm2.exception.pos)
        self.assertGreater(cm2.exception.pos.column, 7900)


if __name__ == "__main__":
    unittest.main()
