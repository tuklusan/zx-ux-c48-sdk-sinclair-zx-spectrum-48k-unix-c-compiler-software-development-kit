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
            "4f424a310100180007000000030002001f005b00512e7192"
            "cd0000cd0000c95f7374617274000000000000000000000000"
            "0001016d61696e000000000000000000000000000000016578"
            "69740000000000000000000000000000010100010001000400"
            "02000100"
        )
        self.assertEqual(encode_obj1(startup.obj), expected)

    def test_pinned_prebuilt_runtime_members_are_byte_exact(self) -> None:
        expected = {
            "startup": "f3af4f93f4a63ead2cdd48f10f6d3993cefca654d579c11b4af48d2874c45fee",
            "exit": "238e23c9514b209febfddffbba611130f5654f6fce42d2be09b3821ab3a196b6",
            "puts": "1becbe7b3c775a196a7b385120e95b279e43c97cae77bd96110bd186ef946dcb",
            "ink": "3d8526be642a90bbe4e8485006f573767c3e64e65f35232ce0e637062bfb6513",
            "plot": "7408256537bc816b2caa429156a242f96cd767e6cfb9524568b8620b7e16090c",
            "udg_clear": "de7406c6f48542f3ae7b80c288f58d89565192e8b8d65416c38b1f15e7519623",
        }
        import hashlib
        actual = {
            member.name: hashlib.sha256(encode_obj1(member.obj)).hexdigest()
            for member in RUNTIME_MEMBERS if member.name in expected
        }
        self.assertEqual(actual, expected)

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

    def test_cli_failure_does_not_replace_existing_output(self) -> None:
        program = compile_bytes(
            b"int main(void){return 1.0;}",
            source_name="bad.c",
            base_dir=Path.cwd(),
        )
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / "bad.c48b"
            out = d / "bad.obj"
            write(src, program)
            out.write_bytes(b"KEEP")
            cp = subprocess.run(
                [sys.executable, str(SDK / "compiler" / "c48b2tap.py"), "--obj", "--force", str(src), str(out)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertEqual(out.read_bytes(), b"KEEP")


if __name__ == "__main__":
    unittest.main()
