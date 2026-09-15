from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "usr/src/apps/write48.c"
BIN = ROOT / "usr/bin/apps/write48.c48b"
EXPECT = ROOT / "compiler/app_expectations.json"

sys.path.insert(0, str(ROOT / "compiler"))
from c48.format import read
from c48.romvm import RomMathVM
from c48.screen import Font4x8, ZXScreen


def patch() -> None:
    s = SRC.read_text(encoding="utf-8")

    old = '''void wr_render(void)\n{\n    wr_build();\n    wr_diff();\n    wr_status();\n}\n'''
    new = '''int wr_down_view(void)\n{\n    int next;\n    next = wr_view + wr_rowlen[0];\n    if (next < wr_len && wr_doc[next] == '\\n')\n        next++;\n    if (next <= wr_view && wr_view < wr_len)\n        next = wr_view + 1;\n    if (next > wr_len)\n        next = wr_len;\n    if (next <= wr_view)\n        return 0;\n    wr_view = next;\n    return 1;\n}\n\nvoid wr_render(void)\n{\n    int n;\n    wr_build();\n    n = 0;\n    while (wr_ncursor < 0 && wr_cur > wr_view &&\n           n < 19) {\n        if (!wr_down_view())\n            break;\n        wr_build();\n        n++;\n    }\n    if (wr_ncursor < 0 && wr_cur < wr_view) {\n        wr_view = wr_cur - 120;\n        if (wr_view < 0)\n            wr_view = 0;\n        wr_build();\n    }\n    if (wr_ncursor < 0) {\n        wr_view = wr_cur;\n        wr_build();\n    }\n    wr_diff();\n    wr_status();\n}\n'''
    if s.count(old) != 1:
        raise SystemExit("wr_render anchor mismatch")
    s = s.replace(old, new)

    start = s.index("int wr_fmove(int d)\n")
    end = s.index("\nint wr_fins(int c)\n", start)
    body = s[start:end]
    needle = """if (row >= 18)\n                    return 0;"""
    count = body.count(needle)
    if count != 3:
        raise SystemExit(f"expected 3 indented bottom guards, found {count}")
    body = body.replace(
        needle,
        """if (row >= 18) {\n                    wr_down_view();\n                    return 0;\n                }""",
    )
    needle = """if (row >= 18)\n                return 0;"""
    count = body.count(needle)
    if count != 1:
        raise SystemExit(f"expected 1 bottom guard, found {count}")
    body = body.replace(
        needle,
        """if (row >= 18) {\n                wr_down_view();\n                return 0;\n            }""",
    )
    s = s[:start] + body + s[end:]

    bad = [(n, len(line)) for n, line in enumerate(s.splitlines(), 1)
           if len(line) > 64]
    if bad:
        raise SystemExit(f"64-column violations: {bad}")
    SRC.write_text(s, encoding="utf-8", newline="\n")


def update_hashes() -> None:
    data = json.loads(EXPECT.read_text(encoding="ascii"))
    app = data["apps"]["write48"]
    app["source_sha256"] = hashlib.sha256(SRC.read_bytes()).hexdigest()
    app["binary_sha256"] = hashlib.sha256(BIN.read_bytes()).hexdigest()
    EXPECT.write_text(json.dumps(data, indent=2) + "\n",
                      encoding="ascii", newline="\n")
    print("source", app["source_sha256"])
    print("binary", app["binary_sha256"])
    print("screen", app["screen_sha256"])


def run_state(payload: bytes) -> tuple[int, int, int, int]:
    program = read(BIN)
    font = Font4x8.load(
        ROOT / "compiler/assets/SANYALnet-Labs-4x8-font-FINAL.bin"
    )
    screen = ZXScreen(font)
    keys = iter(payload)

    def getchar() -> int:
        return next(keys, -1)

    vm = RomMathVM(
        program,
        screen,
        argv=[str(BIN)],
        input_provider=getchar,
    )
    status = vm.run()

    def gv(name: str) -> int:
        lv = vm.global_lvalues[name]
        return vm.mem.load_integer(lv.pointer.address, lv.ctype)

    return status, gv("wr_cur"), gv("wr_view"), gv("wr_pcursor")


def before() -> None:
    state = run_state(b"8" * 540 + b"q")
    print("BEFORE_540", state)
    if state[0] != 0 or state[1] != 540:
        raise SystemExit(f"unexpected pre-fix cursor state: {state}")
    if not (state[2] == 0 and state[3] < 0):
        raise SystemExit(
            "pre-fix regression did not reproduce invisible first-page cursor"
        )


def after() -> None:
    cases = [
        ("right-540", b"8" * 540 + b"q", 540),
        ("right-660", b"8" * 660 + b"q", 660),
        ("page-10", b"6" * 10 + b"q", 600),
    ]
    for name, payload, expected_cur in cases:
        state = run_state(payload)
        print(name, state)
        if state[0] != 0:
            raise SystemExit(f"{name}: rc {state[0]}")
        if state[1] != expected_cur:
            raise SystemExit(
                f"{name}: cursor {state[1]} != {expected_cur}"
            )
        if state[2] <= 0:
            raise SystemExit(f"{name}: view did not advance: {state}")
        if state[3] < 0 or state[3] >= 1140:
            raise SystemExit(f"{name}: cursor not visible: {state}")

    state = run_state(b"8" * 600 + b"5" * 120 + b"q")
    print("back-from-scrolled", state)
    if state[0] != 0 or state[1] != 480 or state[3] < 0:
        raise SystemExit(f"backward cursor regression: {state}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fix_write48_scroll.py MODE")
    mode = sys.argv[1]
    {"before": before, "patch": patch, "hash": update_hashes,
     "after": after}[mode]()


if __name__ == "__main__":
    main()
