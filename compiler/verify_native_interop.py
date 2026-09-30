# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SDK = HERE.parent
sys.path.insert(0, str(HERE))

from c48.compiler import compile_bytes
from c48.native_backend import NativeBackend
from c48.native_format import build_bin_tap, encode_mex1, encode_obj1
from c48.native_link import link_mex
from c48.native_runtime import RUNTIME_MEMBERS

REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(source: str):
    program = compile_bytes(
        source.encode("ascii"),
        source_name="interop.c",
        base_dir=SDK,
    )
    user = NativeBackend(program).build()
    startup = next(member for member in RUNTIME_MEMBERS if member.name == "startup")
    mex = link_mex(
        [("startup", startup.obj), ("user", user)],
        tuple(member for member in RUNTIME_MEMBERS if member.name != "startup"),
    )
    return user, mex


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.native_root.resolve()

    obj_oracle = load_module(root / "v1/tools-host/inspect-obj/inspect.py", "zxux_obj_oracle")
    mex_oracle = load_module(root / "v1/tools-host/inspect-mex/inspect.py", "zxux_mex_oracle")
    tape_tool = load_module(root / "v1/tools-host/maketap/maketap.py", "zxux_tape_tool")
    sys.path.insert(0, str(root / "v1/tools-host/test-driver"))
    tape_oracle = load_module(
        root / "v1/tools-host/test-driver/phase5_roundtrip.py",
        "zxux_tape_oracle",
    )

    sources = (
        "int f(int n){if(n<2)return 1;return n*f(n-1);}int main(void){return f(5)==120?0:1;}",
        "int g;int main(void){g=17;if(g!=17)return 1;puts(\"native\");return 0;}",
    )
    # Conditional expressions are outside C48 version 1; keep the recursive
    # fixture in the supported control-flow surface.
    sources = (
        "int f(int n){if(n<2)return 1;return n*f(n-1);}int main(void){if(f(5)==120)return 0;return 1;}",
        "int puts(char *s);int g;int main(void){g=17;if(g!=17)return 1;puts(\"native\");return 0;}",
    )

    with tempfile.TemporaryDirectory(prefix="c48-native-interop-") as td:
        temp = Path(td)
        for index, source in enumerate(sources):
            obj, mex = build(source)
            obj_bytes = encode_obj1(obj)
            mex_bytes = encode_mex1(mex)
            name = f"P{index + 1}"
            tap_bytes = build_bin_tap(name, mex_bytes)

            obj_info = obj_oracle.inspect_bytes(obj_bytes)
            mex_info = mex_oracle.inspect_bytes(mex_bytes, base=0x6000)
            decoded = tape_oracle.parse_stream(tape_tool, tap_bytes)

            require(obj_info["magic"] == "OBJ1", "native OBJ1 oracle rejected identity")
            require(obj_info["stored_length"] == len(obj_bytes), "native OBJ1 oracle length mismatch")
            require(mex_info["magic"] == "MEX1", "native MEX1 oracle rejected identity")
            require(mex_info["stored_length"] == len(mex_bytes), "native MEX1 oracle length mismatch")
            require(decoded == [(name, tape_tool.M48O_BIN, tape_tool.DIR_BIN, mex_bytes)],
                    "native cassette oracle payload mismatch")

            (temp / f"{name}.obj").write_bytes(obj_bytes)
            (temp / f"{name}.mex").write_bytes(mex_bytes)
            (temp / f"{name}.tap").write_bytes(tap_bytes)

    print(f"NATIVE INTEROP PASS {REFERENCE_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
