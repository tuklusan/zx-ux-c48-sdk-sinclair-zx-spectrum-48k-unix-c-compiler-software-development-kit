#!/usr/bin/env python3
# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Verify the four shipped interactive C48 applications."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
SRC = SDK / "usr" / "src" / "apps"
BIN = SDK / "usr" / "bin" / "apps"
IMG = SDK / "docs" / "images" / "apps"
EXPECT_PATH = ROOT / "app_expectations.json"

sys.path.insert(0, str(ROOT))
from c48.compiler import compile_bytes as compile_source, compile_file
from c48.format import encode, read
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM

FONT = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")


class VerifyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerifyError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def compile_bytes(name: str) -> bytes:
    return encode(compile_file(SRC / f"{name}.c"))


def run_startup(name: str) -> ZXScreen:
    program = read(BIN / f"{name}.c48b")
    screen = ZXScreen(FONT)
    vm = C48VM(
        program,
        screen,
        argv=[name, "verify"],
        max_steps=10000000,
    )
    status = vm.run()
    if status != 0:
        fail(f"{name}: runtime status {status}")
    return screen


def _probe_main_cut(name: str, source: str) -> int:
    """Locate the sole final main definition without matching comments/strings."""
    matches = list(re.finditer(r"(?m)^int main\(", source))
    if len(matches) != 1:
        fail(f"{name}: probe expected exactly one main definition")
    start = matches[0].start()
    brace = source.find("{", matches[0].end())
    if brace < 0:
        fail(f"{name}: probe main definition has no body")

    depth = 0
    state = "code"
    i = brace
    end = -1
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                state = "line-comment"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block-comment"
                i += 2
                continue
            if ch == '"':
                state = "string"
            elif ch == "'":
                state = "char"
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        elif state == "line-comment":
            if ch == "\n":
                state = "code"
        elif state == "block-comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
        elif state in {"string", "char"}:
            if ch == "\\":
                i += 2
                continue
            if state == "string" and ch == '"':
                state = "code"
            elif state == "char" and ch == "'":
                state = "code"
        i += 1

    if end < 0:
        fail(f"{name}: probe could not find the end of main")
    if source[end:].strip():
        fail(f"{name}: probe requires main to be the final source definition")
    return start


def run_probe(name: str, main_text: str) -> None:
    source = (SRC / f"{name}.c").read_text(encoding="ascii")
    cut = _probe_main_cut(name, source)
    probe = source[:cut] + main_text
    program = compile_source(
        probe.encode("ascii"),
        source_name=f"{name}-probe.c",
        base_dir=SRC,
    )
    screen = ZXScreen(FONT)
    status = C48VM(
        program,
        screen,
        argv=[f"{name}-probe"],
        max_steps=10000000,
    ).run()
    if status != 0:
        fail(f"{name}: regression probe status {status}")


def check_regressions() -> None:
    run_probe(
        "sheet48",
        r'''int main(void)
{
    sh_seed();
    app_field(0, 0, "X", 40, 0);
    sh_set(0, 1, "=SUM(B0:B7)");
    if (sh_value(0, 1, 0) != 0u)
        return 1;
    sh_set(0, 1, "=B2+B3+X");
    if (sh_value(0, 1, 0) != 0u)
        return 2;
    sh_set(0, 1, "=SUM(B7:B1)");
    if (sh_value(0, 1, 0) != 0u)
        return 3;
    sh_set(0, 1, "=B+B2");
    if (sh_value(0, 1, 0) != 0u)
        return 4;
    sh_set(0, 1, "=B2+B3");
    if (sh_value(0, 1, 0) != 15000u)
        return 5;
    sh_set(0, 1, "=SUM(B2:B7)");
    if (sh_value(0, 1, 0) != 41000u)
        return 6;
    if (sh_value(-1, 0, 0) != 0u)
        return 7;
    if (sh_value(0, 4, 0) != 0u)
        return 8;
    return 0;
}
''',
    )
    run_probe(
        "write48",
        r'''int main(void)
{
    int next;
    wr_seed();
    next = wr_nextrow(0);
    if (next <= 0)
        return 1;
    if (wr_prevrow(next) != 0)
        return 2;
    wr_cur = next;
    wr_view = next;
    wr_insert = 0;
    wr_start();
    wr_render();
    if (wr_command('5') != 1)
        return 3;
    if (wr_view != 0)
        return 4;
    if (wr_cur != next - 1)
        return 5;
    if (wr_command('?') != 0)
        return 6;
    wr_cur = 0;
    wr_view = 0;
    if (wr_command('7') != 0)
        return 7;
    return 0;
}
''',
    )
    run_probe(
        "wire3d",
        r'''int main(void)
{
    int sx;
    int sy;
    w_yaw = 0;
    w_pitch = 0;
    w_zoom = 360;
    if (!w_project(100, 0, 100, &sx, &sy))
        return 1;
    if (sx != 252 || sy != 100)
        return 2;
    w_sel = 0;
    w_w[0] = 77;
    w_h[0] = 29;
    w_z[0] = 109;
    w_zoom = 354;
    w_edit('d');
    w_edit('w');
    w_edit('x');
    w_edit('+');
    if (w_w[0] != 78 || w_h[0] != 30)
        return 3;
    if (w_z[0] != 110 || w_zoom != 360)
        return 4;
    w_w[0] = 3;
    w_h[0] = 3;
    w_z[0] = -109;
    w_edit('a');
    w_edit('s');
    w_edit('z');
    if (w_w[0] != 2 || w_h[0] != 2)
        return 5;
    if (w_z[0] != -110)
        return 6;
    return 0;
}
''',
    )
    run_probe(
        "gp82",
        r'''int main(void)
{
    gp_seed();
    if (gp_wins[0] != 3 || gp_wins[1] != 4)
        return 1;
    if (gp_wins[2] != 4 || gp_wins[3] != 1)
        return 2;
    if (gp_podiums[0] != 11 || gp_podiums[3] != 7)
        return 3;
    if (gp_poles[0] != 3 || gp_poles[2] != 10)
        return 4;
    if (gp_owner[0] != 0 || gp_owner[4] != 1)
        return 5;
    if (gp_owner[8] != 2 || gp_owner[11] != 3)
        return 6;
    if (gp_owner[13] != 4 || gp_owner[15] != 6)
        return 7;
    if (gp_sector(0, 40) != 0)
        return 8;
    if (gp_sector(40, 0) != 4)
        return 9;
    return 0;
}
''',
    )
    print("APP REGRESSION PROBES PASS", flush=True)


def main() -> int:
    expect = json.loads(EXPECT_PATH.read_text(encoding="ascii"))
    if expect.get("schema") != 1:
        fail("app expectation schema mismatch")
    names = set(expect.get("apps", {}))
    if names != {"sheet48", "write48", "wire3d", "gp82"}:
        fail("app expectation member set mismatch")
    source_names = {p.stem for p in SRC.glob("*.c")}
    binary_names = {p.stem for p in BIN.glob("*.c48b")}
    if source_names != names:
        fail("app source member set mismatch")
    if binary_names != names:
        fail("app binary member set mismatch")
    image_files = {p.name for p in IMG.glob("*.png")}
    expected_images = {f"{name}.png" for name in names}
    expected_images.add("contact-sheet.png")
    if image_files != expected_images:
        fail("app image member set mismatch")
    if sha(IMG / "contact-sheet.png") != expect["contact_sheet_sha256"]:
        fail("application contact-sheet hash mismatch")
    if sha(SRC / "appapi.h") != expect["helper_sha256"]:
        fail("appapi.h hash mismatch")
    for name, item in expect["apps"].items():
        source = SRC / f"{name}.c"
        frozen = BIN / f"{name}.c48b"
        if sha(source) != item["source_sha256"]:
            fail(f"{name}: source hash mismatch")
        if sha(frozen) != item["binary_sha256"]:
            fail(f"{name}: binary hash mismatch")
        if compile_bytes(name) != frozen.read_bytes():
            fail(f"{name}: deterministic rebuild mismatch")
        screen = run_startup(name)
        if sha_bytes(screen.bytes()) != item["screen_sha256"]:
            fail(f"{name}: startup screen hash mismatch")
        if "png_sha256" in item:
            image = IMG / f"{name}.png"
            if not image.is_file():
                fail(f"{name}: checked-in image missing")
            if sha(image) != item["png_sha256"]:
                fail(f"{name}: checked-in image hash mismatch")
        print(f"APP VERIFY: {name} PASS", flush=True)
    check_regressions()
    print("APP VERIFY PASS: 4 apps", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerifyError as exc:
        print(f"APP VERIFY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
