# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from c48 import __version__
from c48.format import read as read_c48b
from c48.native_backend import NativeLoweringError, NativeBackend
from c48.native_format import (
    NativeFormatError,
    build_bin_tap,
    encode_mex1,
    encode_obj1,
)
from c48.native_link import link_mex
from c48.native_runtime import RUNTIME_MEMBERS


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="c48b2tap",
        description="Lower a validated C48B1 program to native ZX-UX OBJ1, MEX1, or BIN tape.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--obj", action="store_true", help="write relocatable OBJ1 (.obj)")
    mode.add_argument("--mex", action="store_true", help="write linked MEX1 (.mex)")
    p.add_argument("--name", metavar="NAME", help="1..10 byte ZX-UX BIN object name for TAP output")
    p.add_argument("--stack", type=int, default=1024, metavar="BYTES", help="MEX1 minimum FAST stack request (64..4096; default 1024)")
    p.add_argument("--force", action="store_true", help="replace an existing regular output file")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--about",
        action="version",
        version=(
            f"%(prog)s {__version__}\\n"
            "ZX-UX C48 SDK native cross-backend\\n"
            "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\\n"
            "SANYALnet Labs Non-Commercial License; see the root LICENSE file."
        ),
    )
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    return p


def _validate_paths(ns) -> tuple[str, str | None]:
    src: Path = ns.input
    dst: Path = ns.output
    if src.suffix != ".c48b":
        raise NativeFormatError("input must use the lowercase .c48b suffix")
    if src.is_symlink() or not src.is_file():
        raise NativeFormatError("input must be an existing regular non-symlink file")
    mode = "obj" if ns.obj else "mex" if ns.mex else "tap"
    expected = {"obj": ".obj", "mex": ".mex", "tap": ".tap"}[mode]
    if dst.suffix != expected:
        raise NativeFormatError(f"{mode} output must use the lowercase {expected} suffix")
    if src.resolve() == dst.resolve():
        raise NativeFormatError("input and output paths must be different")
    if dst.exists():
        if dst.is_symlink() or not dst.is_file():
            raise NativeFormatError("existing output must be a regular non-symlink file")
        src_stat = src.stat()
        dst_stat = dst.stat()
        if (src_stat.st_dev, src_stat.st_ino) == (dst_stat.st_dev, dst_stat.st_ino):
            raise NativeFormatError("input and output paths must not alias the same file")
        if not ns.force:
            raise NativeFormatError("output already exists; use --force to replace it")
    if not dst.parent.is_dir() or dst.parent.is_symlink():
        raise NativeFormatError("output parent must be an existing regular directory")
    if mode != "tap" and ns.name is not None:
        raise NativeFormatError("--name is valid only for TAP output")
    return mode, ns.name


def _atomic_write(path: Path, data: bytes) -> None:
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp = Path(handle.name)
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def main(argv: list[str] | None = None) -> int:
    p = _parser()
    ns = p.parse_args(argv)
    try:
        mode, tape_name = _validate_paths(ns)
        if not 64 <= ns.stack <= 4096:
            raise NativeFormatError("--stack must be in the native 64..4096 byte range")
        program = read_c48b(ns.input)
        user = NativeBackend(program).build()
        if mode == "obj":
            output = encode_obj1(user)
        else:
            mex = link_mex(
                [("startup", next(m.obj for m in RUNTIME_MEMBERS if m.name == "startup")), ("user", user)],
                tuple(m for m in RUNTIME_MEMBERS if m.name != "startup"),
                min_stack=ns.stack,
            )
            mex_bytes = encode_mex1(mex)
            if mode == "mex":
                output = mex_bytes
            else:
                name = tape_name if tape_name is not None else ns.output.stem
                output = build_bin_tap(name, mex_bytes)
        _atomic_write(ns.output, output)
        print(f"c48b2tap: wrote {ns.output} ({mode}, {len(output)} bytes)")
        return 0
    except (OSError, NativeFormatError, NativeLoweringError) as exc:
        print(f"c48b2tap: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
