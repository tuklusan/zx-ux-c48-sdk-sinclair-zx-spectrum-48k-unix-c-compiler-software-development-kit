# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes
from c48.format import write
from c48.native_backend import NativeBackend, NativeLoweringError
from c48.native_format import (
    decode_mex1,
    decode_obj1,
    parse_bin_tap,
    encode_obj1,
    encode_mex1,
)
from c48.native_link import link_mex, select_runtime
from c48.native_runtime import RUNTIME_MEMBERS
from tests.native_large_fixture import generate_large_native_source


def native_from_source(source: str):
    program = compile_bytes(source.encode("ascii"), source_name="native.c", base_dir=Path.cwd())
    return NativeBackend(program).build()


class NativeBackendTests(unittest.TestCase):
    def test_recursive_integer_program_emits_real_obj_and_mex(self) -> None:
        obj = native_from_source(
            "int f(int n){if(n<2)return 1;return n*f(n-1);}"
            "int main(void){if(f(5)==120)return 0;return 1;}"
        )
        obj_bytes = encode_obj1(obj)
        self.assertEqual(decode_obj1(obj_bytes), obj)
        self.assertIn(b"main", obj_bytes)
        startup = next(m for m in RUNTIME_MEMBERS if m.name == "startup")
        mex = link_mex(
            [("startup", startup.obj), ("user", obj)],
            tuple(m for m in RUNTIME_MEMBERS if m.name != "startup"),
        )
        self.assertEqual(decode_mex1(encode_mex1(mex)), mex)
        self.assertGreater(len(mex.image), 20)
        self.assertGreater(len(mex.relocs), 0)

    def test_startup_matches_pinned_native_crt0_obj1(self) -> None:
        startup = next(m for m in RUNTIME_MEMBERS if m.name == "startup")
        expected = bytes.fromhex(
            "4f424a310100180007000000030002001f005b00512e7192cd0000cd0000"
            "c95f737461727400000000000000000000000001016d61696e0000000000"
            "000000000000000000000165786974000000000000000000000000000000"
            "01010001000100040002000100"
        )
        self.assertEqual(encode_obj1(startup.obj), expected)

    def test_pinned_prebuilt_runtime_members_are_byte_exact(self) -> None:
        expected = {
            "startup": "f3af4f93f4a63ead2cdd48f10f6d3993cefca654d579c11b4af48d2874c45fee",
            "ink": "e596b39954272458d673b6e83eee69b24cd5fbee39a24dd1c3e1ae3cdf565c1a",
            "plot": "30744b5132e0bfe353c7093c3e6a335dbc89c0b93b2765c491bc0147a1222d29",
            "udg_clear": "c154f80d7aed3572b2c08dd58ad6146cd180957255c6e64c10573d17a83bdcf4",
        }
        import hashlib
        actual = {
            member.name: hashlib.sha256(encode_obj1(member.obj)).hexdigest()
            for member in RUNTIME_MEMBERS if member.name in expected
        }
        self.assertEqual(actual, expected)

    def test_float5_core_lowering_resolves_native_runtime(self) -> None:
        obj = native_from_source(
            "float sin(float);"
            "float add(float a,float b){return a+b;}"
            "int main(void){float x;x=1;x++;x=add(x,1);"
            "if((int)x!=3)return 1;x=sin(x-x);if(x!=0.0)return 2;return 0;}"
        )
        names = {symbol.name for symbol in obj.symbols}
        for name in ("__itof", "__ftoi", "__fadd", "__fcmp", "sin"):
            self.assertIn(name, names)
        startup = next(m for m in RUNTIME_MEMBERS if m.name == "startup")
        runtime = tuple(m for m in RUNTIME_MEMBERS if m.name != "startup")
        mex = link_mex([("startup", startup.obj), ("user", obj)], runtime)
        self.assertEqual(decode_mex1(encode_mex1(mex)), mex)
        self.assertGreater(mex.bss_size, 0)

    def test_left_to_right_six_argument_call_lowers(self) -> None:
        obj = native_from_source(
            "int f(int a,int b,int c,int d,int e,int f){return a+b+c+d+e+f;}"
            "int main(void){int i;i=1;return f(i++,i++,i++,i++,i++,i++);}"
        )
        self.assertGreater(len(obj.text), 40)

    def test_division_modulo_and_shifts_lower(self) -> None:
        obj = native_from_source(
            "int main(void){int a;a=-91;"
            "if(a/7!=-13)return 1;if(a%7!=0)return 2;"
            "if((3<<4)!=48)return 3;if((-16>>2)!=-4)return 4;return 0;}"
        )
        names = {s.name for s in obj.symbols}
        self.assertIn("c48_sdivmod", names)

    def test_runtime_members_are_valid_obj1_and_archive_selection_is_fixed_point(self) -> None:
        for member in RUNTIME_MEMBERS:
            raw = encode_obj1(member.obj)
            self.assertEqual(decode_obj1(raw), member.obj)
        user = native_from_source(
            "int strcmp(char *a,char *b);char *strcpy(char *d,char *s);"
            "int main(void){char a[4];char b[4];"
            "a[0]='x';a[1]=0;strcpy(b,a);return strcmp(a,b);}"
        )
        selected = select_runtime(
            [("user", user)],
            tuple(m for m in RUNTIME_MEMBERS if m.name != "startup"),
        )
        selected_names = [name for name, _ in selected]
        self.assertIn("runtime:strcpy", selected_names)
        self.assertIn("runtime:strcmp", selected_names)
        self.assertEqual(selected_names, [name for name, _ in select_runtime(
            [("user", user)],
            tuple(m for m in RUNTIME_MEMBERS if m.name != "startup"),
        )])

    def test_linker_matches_pinned_even_module_layout(self) -> None:
        user = native_from_source("int main(void){return 0;}")
        startup = next(m for m in RUNTIME_MEMBERS if m.name == "startup")
        runtime = tuple(m for m in RUNTIME_MEMBERS if m.name != "startup")
        mex = link_mex([("startup", startup.obj), ("user", user)], runtime)
        self.assertEqual(len(startup.obj.text), 7)
        self.assertEqual(mex.image[7], 0)
        self.assertEqual(int.from_bytes(mex.image[1:3], "little"), 8)
        self.assertEqual(len(mex.image) & 1, 0)
        self.assertEqual(mex.bss_size & 1, 0)

    def test_large_cross_development_fixture_is_deterministic_and_native_sized(self) -> None:
        source = generate_large_native_source()
        self.assertGreaterEqual(len(source), 29 * 1024)
        self.assertLessEqual(len(source), 31 * 1024)
        self.assertEqual(source, generate_large_native_source())
        program = compile_bytes(source, source_name="large.c", base_dir=Path.cwd())
        first = NativeBackend(program).build()
        second = NativeBackend(program).build()
        self.assertEqual(encode_obj1(first), encode_obj1(second))
        startup = next(m for m in RUNTIME_MEMBERS if m.name == "startup")
        runtime = tuple(m for m in RUNTIME_MEMBERS if m.name != "startup")
        mex = link_mex([("startup", startup.obj), ("user", first)], runtime)
        stored = encode_mex1(mex)
        self.assertGreaterEqual(len(stored), 29 * 1024)
        self.assertLessEqual(len(stored), 31 * 1024)
        self.assertLessEqual(len(mex.image) + mex.bss_size, 32768)
        self.assertLessEqual(len(stored), 32768)

    def test_cli_rejects_hardlink_output_alias_without_modifying_input(self) -> None:
        program = compile_bytes(
            b"int main(void){return 0;}",
            source_name="alias.c",
            base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "alias.c48b"
            out = d / "alias.obj"
            write(src, program)
            original = src.read_bytes()
            try:
                out.hardlink_to(src)
            except (OSError, NotImplementedError):
                self.skipTest("hardlinks unavailable on this host")
            cp = subprocess.run(
                [sys.executable, str(SDK / "compiler" / "c48b2tap.py"),
                 "--obj", "--force", str(src), str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(src.read_bytes(), original)
            self.assertEqual(out.read_bytes(), original)

    def test_cli_obj_mex_and_tap_are_deterministic(self) -> None:
        program = compile_bytes(
            b"int main(void){int x;x=6;return x*7-42;}",
            source_name="cli.c",
            base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "p.c48b"
            write(src, program)
            cli = SDK / "compiler" / "c48b2tap.py"
            outputs = []
            for mode, suffix in (("--obj", ".obj"), ("--mex", ".mex"), ("", ".tap")):
                out = d / ("p" + suffix)
                cmd = [sys.executable, str(cli)]
                if mode:
                    cmd.append(mode)
                cmd.extend([str(src), str(out)])
                cp = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                first = out.read_bytes()
                out.unlink()
                cp = subprocess.run(cmd, capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                self.assertEqual(out.read_bytes(), first)
                outputs.append(first)
            decode_obj1(outputs[0])
            decode_mex1(outputs[1])
            parsed = parse_bin_tap(outputs[2])
            decode_mex1(parsed.payload)

    def test_cli_rejects_odd_native_stack_atomically(self) -> None:
        program = compile_bytes(
            b"int main(void){return 0;}",
            source_name="stack.c",
            base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "stack.c48b"
            out = d / "stack.mex"
            write(src, program)
            out.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(SDK / "compiler" / "c48b2tap.py"),
                 "--mex", "--stack", "65", "--force", str(src), str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(out.read_bytes(), b"KEEP")

    def test_cli_rejects_corrupt_unresolved_and_path_inputs_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            cli = SDK / "compiler" / "c48b2tap.py"

            corrupt = d / "corrupt.c48b"
            corrupt.write_bytes(b"C48B1\n{not-json")
            out = d / "corrupt.obj"
            out.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(cli), "--obj", "--force", str(corrupt), str(out)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(out.read_bytes(), b"KEEP")

            unresolved_program = compile_bytes(
                b"int absent(void);int main(void){return absent();}",
                source_name="unresolved.c", base_dir=Path.cwd(),
            )
            unresolved = d / "unresolved.c48b"
            write(unresolved, unresolved_program)
            mex = d / "unresolved.mex"
            mex.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(cli), "--mex", "--force", str(unresolved), str(mex)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(mex.read_bytes(), b"KEEP")

            valid_program = compile_bytes(
                b"int main(void){return 0;}", source_name="valid.c", base_dir=Path.cwd(),
            )
            valid = d / "valid.c48b"
            write(valid, valid_program)
            tap = d / "valid.tap"
            tap.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(cli), "--name", "../BAD", "--force", str(valid), str(tap)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(tap.read_bytes(), b"KEEP")

            wrong_suffix = d / "wrong.TAP"
            cp = subprocess.run(
                [sys.executable, str(cli), str(valid), str(wrong_suffix)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertFalse(wrong_suffix.exists())

            missing_parent = d / "missing" / "x.tap"
            cp = subprocess.run(
                [sys.executable, str(cli), str(valid), str(missing_parent)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertFalse(missing_parent.exists())

    def test_cli_native_overflow_does_not_replace_existing_output(self) -> None:
        program = compile_bytes(
            b"char huge[32768];int main(void){return huge[0];}",
            source_name="overflow.c", base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "overflow.c48b"
            out = d / "overflow.mex"
            write(src, program)
            out.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(SDK / "compiler" / "c48b2tap.py"),
                 "--mex", "--force", str(src), str(out)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(out.read_bytes(), b"KEEP")

    def test_cli_failure_does_not_replace_existing_output(self) -> None:
        program = compile_bytes(
            b"int point(int,int);int main(void){return point(1,1);}",
            source_name="bad.c",
            base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "bad.c48b"
            out = d / "bad.mex"
            write(src, program)
            out.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(SDK / "compiler" / "c48b2tap.py"), "--mex", "--force", str(src), str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(out.read_bytes(), b"KEEP")


if __name__ == "__main__":
    unittest.main()
