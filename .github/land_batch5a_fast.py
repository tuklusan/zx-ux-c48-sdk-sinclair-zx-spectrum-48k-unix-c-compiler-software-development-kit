#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "batch5a_v2", HERE / "land_batch5a_v2.py"
)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load Batch-5A v2 harness")
v2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v2)

FAST_SCRIPT = Path(".github/land_batch5a_fast.py")
v2.TEMP.add(FAST_SCRIPT)


def patch_sources():
    helper = '''int d_muldiv(int value, int scale, int div)\n{\n    int p;\n    int whole;\n    int rem;\n    int n;\n    int chunk;\n    int out;\n    int prod;\n    if (div <= 0 || scale != 220) return 0;\n    if (value >= -2978 && value <= 2978 &&\n        div <= 1638) {\n        p = value * 11;\n        whole = p / div;\n        rem = p % div;\n        return whole * 20 + rem * 20 / div;\n    }\n    n = value;\n    rem = 0;\n    out = 0;\n    while (n != 0) {\n        if (n > 16) chunk = 16;\n        else if (n < -16) chunk = -16;\n        else chunk = n;\n        prod = chunk * scale + rem;\n        out = out + prod / div;\n        rem = prod % div;\n        n = n - chunk;\n    }\n    return out;\n}\n\n'''
    v2.rep(
        v2.DEMO,
        "int d_px(int x, int z)\n{\n",
        helper + "int d_px(int x, int z)\n{\n",
        "safe projection helper",
    )
    v2.rep(
        v2.DEMO,
        "    return 128 + x * 220 / q;\n",
        "    return 128 + d_muldiv(x, 220, q);\n",
        "safe d_px",
    )
    v2.rep(
        v2.DEMO,
        "    return 96 + y * 220 / q;\n",
        "    return 96 + d_muldiv(y, 220, q);\n",
        "safe d_py",
    )
    v2.rep(
        v2.MOBIUS,
        "        u2 = (i + 1) * 256 / 20;\n"
        "        if (i == 19) u2 = 0;\n",
        "        u2 = (i + 1) * 256 / 20;\n",
        "Mobius full-turn seam",
    )
    v2.rep(
        v2.FIREWORK,
        "        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n"
        "            y1 < 184 && y2 < 184) {\n",
        "        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n"
        "            y1 >= 16 && y1 < 184 &&\n"
        "            y2 >= 16 && y2 < 184) {\n",
        "firework burst label guard",
    )
    v2.rep(
        v2.FIREWORK,
        "        draw(x, 0, x, 18 + ((x * 7) % 30));\n",
        "        draw(x, 16, x, 18 + ((x * 7) % 30));\n",
        "firework sky label guard",
    )


v2.patch_sources = patch_sources


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: land_batch5a_fast.py evidence|land ...")
    mode = sys.argv[1]
    if mode == "evidence":
        if len(sys.argv) != 5:
            raise SystemExit("usage: ... evidence DEMO RUNNER OUT_DIR")
        v2.evidence(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    if mode == "land":
        if len(sys.argv) != 3:
            raise SystemExit("usage: ... land EVIDENCE_DIR")
        v2.land(sys.argv[2])
        return
    raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
