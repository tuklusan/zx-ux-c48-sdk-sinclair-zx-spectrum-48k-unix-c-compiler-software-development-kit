#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path.cwd()
DEMO = Path("usr/src/demos/demoapi.h")
MOBIUS = Path("usr/src/demos/mobius.c")
FIREWORK = Path("usr/src/demos/firework.c")
TEST = Path("compiler/tests/test_graphics_review.py")
EXPECT = Path("compiler/graphics_demo_expectations.json")
RELEASE = Path("compiler/release_expectations.json")
TEMP = {
    Path(".github/diag_batch5a.py"),
    Path(".github/land_batch5a.py"),
    Path(".github/land_batch5a_v2.py"),
    Path(".github/workflows/diag-batch5a.yml"),
    Path(".github/workflows/land-batch5a.yml"),
    Path(".github/workflows/land-batch5a-v2.yml"),
}


def run(args, cwd=None, timeout=3600):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(args, cwd=cwd or ROOT, check=True, timeout=timeout)


def read(path, root=ROOT):
    return (root / path).read_text(encoding="utf-8")


def write(path, value, root=ROOT):
    (root / path).write_text(value, encoding="utf-8", newline="\n")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path, root=ROOT):
    return sha_bytes((root / path).read_bytes())


def rep(path, old, new, label):
    value = read(path)
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"{label}: anchor count {count}")
    write(path, value.replace(old, new, 1))


def patch_sources():
    helper = '''int d_muldiv(int value, int scale, int div)\n{\n    int neg;\n    int n;\n    int chunk;\n    int rem;\n    int out;\n    int prod;\n    if (div <= 0 || scale < 0) return 0;\n    neg = 0;\n    if (value < 0) {\n        neg = 1;\n        n = -value;\n    }\n    else\n        n = value;\n    rem = 0;\n    out = 0;\n    while (n > 0) {\n        chunk = n;\n        if (chunk > 16) chunk = 16;\n        prod = chunk * scale + rem;\n        out = out + prod / div;\n        rem = prod % div;\n        n = n - chunk;\n    }\n    if (neg) return -out;\n    return out;\n}\n\n'''
    rep(
        DEMO,
        "int d_px(int x, int z)\n{\n",
        helper + "int d_px(int x, int z)\n{\n",
        "safe projection helper",
    )
    rep(
        DEMO,
        "    return 128 + x * 220 / q;\n",
        "    return 128 + d_muldiv(x, 220, q);\n",
        "safe d_px",
    )
    rep(
        DEMO,
        "    return 96 + y * 220 / q;\n",
        "    return 96 + d_muldiv(y, 220, q);\n",
        "safe d_py",
    )
    rep(
        MOBIUS,
        "        u2 = (i + 1) * 256 / 20;\n"
        "        if (i == 19) u2 = 0;\n",
        "        u2 = (i + 1) * 256 / 20;\n",
        "Mobius full-turn seam",
    )
    rep(
        FIREWORK,
        "        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n"
        "            y1 < 184 && y2 < 184) {\n",
        "        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n"
        "            y1 >= 16 && y1 < 184 &&\n"
        "            y2 >= 16 && y2 < 184) {\n",
        "firework burst label guard",
    )
    rep(
        FIREWORK,
        "        draw(x, 0, x, 18 + ((x * 7) % 30));\n",
        "        draw(x, 16, x, 18 + ((x * 7) % 30));\n",
        "firework sky label guard",
    )


def test_content():
    return '''# ============================================================================\n# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n# Proprietary rights reserved except as expressly licensed herein.\n#\n# ZX-UX C48 SDK\n# This file is governed by the SANYALnet Labs Non-Commercial License in the\n# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use\n# for AI/ML model training are prohibited unless separately authorized.\n#\n# Attribution is required: "Based on original work by Supratim Sanyal of\n# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,\n# patent, trademark, and governing-law provisions.\n# ============================================================================\n"""Permanent regression probes for graphics review Batch-5A."""\nfrom pathlib import Path\nimport shutil\nimport sys\nimport tempfile\nimport unittest\n\nHERE = Path(__file__).resolve().parent\nCOMPILER = HERE.parent\nSDK = COMPILER.parent\nSRC = SDK / "usr" / "src" / "demos"\nsys.path.insert(0, str(COMPILER))\n\nfrom c48.compiler import compile_file\nfrom c48.screen import Font4x8, ZXScreen\nfrom c48.vm import C48VM\n\nFONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")\n\n\nclass GraphicsReviewBatch5ATests(unittest.TestCase):\n    def test_mobius_seam_keeps_full_turn_endpoint(self):\n        src = (SRC / "mobius.c").read_text(encoding="ascii")\n        self.assertIn("u2 = (i + 1) * 256 / 20;", src)\n        self.assertNotIn("if (i == 19) u2 = 0;", src)\n\n    def test_firework_preserves_top_label_band(self):\n        src = (SRC / "firework.c").read_text(encoding="ascii")\n        self.assertIn("y1 >= 16 && y1 < 184", src)\n        self.assertIn("y2 >= 16 && y2 < 184", src)\n        self.assertIn("draw(x, 16, x, 18 +", src)\n        self.assertNotIn("draw(x, 0, x, 18 +", src)\n\n    def test_projection_muldiv_handles_large_values(self):\n        with tempfile.TemporaryDirectory() as td:\n            root = Path(td)\n            shutil.copy2(SRC / "demoapi.h", root / "demoapi.h")\n            source = root / "probe.c"\n            source.write_text(\n                '#include "demoapi.h"\\n'\n                'int main(void)\\n'\n                '{\\n'\n                '    if (d_px(154, 84) != 258) return 1;\\n'\n                '    if (d_px(-154, 84) != -2) return 2;\\n'\n                '    if (d_py(154, 84) != 226) return 3;\\n'\n                '    if (d_py(-154, 84) != -34) return 4;\\n'\n                '    return 0;\\n'\n                '}\\n',\n                encoding="ascii",\n                newline="\\n",\n            )\n            program = compile_file(source)\n            vm = C48VM(program, ZXScreen(FONT), argv=["probe"])\n            self.assertEqual(vm.run(), 0)\n\n\nif __name__ == "__main__":\n    unittest.main()\n'''


def add_tests():
    if (ROOT / TEST).exists():
        raise SystemExit(f"{TEST} already exists")
    write(TEST, test_content())


def update_test_count():
    data = json.loads((ROOT / RELEASE).read_text(encoding="ascii"))
    if data.get("test_count") != 342:
        raise SystemExit(f"unexpected test count {data.get('test_count')}")
    data["test_count"] = 345
    (ROOT / RELEASE).write_text(
        json.dumps(data, indent=2) + "\n", encoding="ascii", newline="\n"
    )


def load_graphics():
    return json.loads((ROOT / EXPECT).read_text(encoding="ascii"))


def import_graphics_verifier():
    sys.path.insert(0, str(ROOT / "compiler"))
    import verify_graphics_demos as v
    return v


def evidence(name, runner, out_dir):
    patch_sources()
    expect = load_graphics()
    if name not in expect.get("demos", {}):
        raise SystemExit(f"unknown demo {name}")
    exp = expect["demos"][name]
    if exp["runner"] != runner:
        raise SystemExit(f"runner mismatch {name}: {runner} != {exp['runner']}")
    v = import_graphics_verifier()
    if v.host_arch() != exp["architecture"]:
        raise SystemExit(
            f"architecture mismatch {name}: {v.host_arch()} != {exp['architecture']}"
        )
    data = v.compile_bytes(name)
    (v.BIN / f"{name}.c48b").write_bytes(data)
    first = v.run_demo(name, 1, 15.0)
    screen = v.run_demo(name, int(exp["frames"]), 15.0)
    v.run_demo(name, int(exp["stress_frames"]), 15.0)
    png = v.png_bytes(screen.render_rgb())
    lit, attrs = v.screen_metrics(screen)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.c48b").write_bytes(data)
    (out / f"{name}.scr").write_bytes(screen.bytes())
    (out / f"{name}.png").write_bytes(png)
    meta = {
        "demo": name,
        "runner": runner,
        "architecture": v.host_arch(),
        "frames": int(exp["frames"]),
        "stress_frames": int(exp["stress_frames"]),
        "source_sha256": v.sha(v.SRC / f"{name}.c"),
        "helper_sha256": v.sha(v.SRC / "demoapi.h"),
        "binary_sha256": v.sha_bytes(data),
        "first_screen_sha256": v.sha_bytes(first.bytes()),
        "screen_sha256": v.sha_bytes(screen.bytes()),
        "png_sha256": v.sha_bytes(png),
        "lit_pixels": lit,
        "attribute_values": attrs,
        "status": "PASS",
    }
    (out / f"{name}.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="ascii", newline="\n",
    )
    print(f"BATCH-5A EVIDENCE PASS: {name} / {runner}", flush=True)


def png_rgb(width, height, rgb):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(rgb[y * stride:(y + 1) * stride])

    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
        )

    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def consume_evidence(evidence_dir):
    v = import_graphics_verifier()
    expect = load_graphics()
    root = Path(evidence_dir)
    helper_hash = sha(DEMO)
    frames = []
    for name, exp in expect["demos"].items():
        meta_path = root / f"{name}.json"
        binary_path = root / f"{name}.c48b"
        screen_path = root / f"{name}.scr"
        png_path = root / f"{name}.png"
        for path in (meta_path, binary_path, screen_path, png_path):
            if not path.is_file():
                raise SystemExit(f"missing evidence file {path}")
        meta = json.loads(meta_path.read_text(encoding="ascii"))
        if meta.get("status") != "PASS" or meta.get("demo") != name:
            raise SystemExit(f"invalid evidence metadata {name}")
        if meta.get("runner") != exp["runner"]:
            raise SystemExit(f"runner evidence mismatch {name}")
        if meta.get("architecture") != exp["architecture"]:
            raise SystemExit(f"architecture evidence mismatch {name}")
        if meta.get("helper_sha256") != helper_hash:
            raise SystemExit(f"helper evidence mismatch {name}")
        if meta.get("source_sha256") != sha(Path("usr/src/demos") / f"{name}.c"):
            raise SystemExit(f"source evidence mismatch {name}")
        if sha_bytes(binary_path.read_bytes()) != meta["binary_sha256"]:
            raise SystemExit(f"binary evidence hash mismatch {name}")
        if sha_bytes(screen_path.read_bytes()) != meta["screen_sha256"]:
            raise SystemExit(f"screen evidence hash mismatch {name}")
        if sha_bytes(png_path.read_bytes()) != meta["png_sha256"]:
            raise SystemExit(f"PNG evidence hash mismatch {name}")
        if len(screen_path.read_bytes()) != 6912:
            raise SystemExit(f"screen evidence size mismatch {name}")
        shutil.copyfile(binary_path, ROOT / "usr/bin/demos" / f"{name}.c48b")
        shutil.copyfile(png_path, ROOT / "docs/images/demos" / f"{name}.png")
        for key in (
            "source_sha256", "binary_sha256", "first_screen_sha256",
            "screen_sha256", "png_sha256", "lit_pixels", "attribute_values",
        ):
            exp[key] = meta[key]
        screen = v.ZXScreen(v.FONT)
        screen.mem[:] = screen_path.read_bytes()
        frames.append(screen.render_rgb())
    expect["helper_sha256"] = helper_hash
    (ROOT / EXPECT).write_text(
        json.dumps(expect, indent=2) + "\n", encoding="ascii", newline="\n"
    )

    cols, rows = 4, 6
    width, height = cols * 256, rows * 192
    sheet = bytearray(width * height * 3)
    for index, rgb in enumerate(frames):
        ox = (index % cols) * 256
        oy = (index // cols) * 192
        for y in range(192):
            src = y * 256 * 3
            dst = ((oy + y) * width + ox) * 3
            sheet[dst:dst + 256 * 3] = rgb[src:src + 256 * 3]
    (ROOT / "docs/images/demos/contact-sheet.png").write_bytes(
        png_rgb(width, height, bytes(sheet))
    )
    print("BATCH-5A EVIDENCE AGGREGATION PASS: 21 demos", flush=True)


def target_checks(root=ROOT):
    demo = read(DEMO, root)
    mobius = read(MOBIUS, root)
    firework = read(FIREWORK, root)
    if "int d_muldiv(int value, int scale, int div)" not in demo:
        raise SystemExit("missing d_muldiv")
    if "x * 220 / q" in demo or "y * 220 / q" in demo:
        raise SystemExit("unsafe perspective multiply remains")
    if "if (i == 19) u2 = 0;" in mobius:
        raise SystemExit("stale Mobius seam collapse remains")
    if "y1 >= 16 && y1 < 184" not in firework:
        raise SystemExit("firework y1 label guard missing")
    if "y2 >= 16 && y2 < 184" not in firework:
        raise SystemExit("firework y2 label guard missing")
    if "draw(x, 16, x, 18 +" not in firework:
        raise SystemExit("firework sky label guard missing")
    if "draw(x, 0, x, 18 +" in firework:
        raise SystemExit("firework sky still overwrites label band")
    expect = json.loads((root / EXPECT).read_text(encoding="ascii"))
    if expect.get("helper_sha256") != sha(DEMO, root):
        raise SystemExit("graphics helper hash not frozen")
    rel = json.loads((root / RELEASE).read_text(encoding="ascii"))
    if rel.get("test_count") != 345:
        raise SystemExit("Batch-5A test count not frozen at 345")
    if not (root / TEST).is_file():
        raise SystemExit("Batch-5A regression test missing")
    print("BATCH-5A TARGET CHECKS PASS", flush=True)


def c48_source_scan(root=ROOT):
    count = 0
    for path in sorted((root / "usr/src").rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".c", ".h"}:
            continue
        data = path.read_bytes()
        try:
            data.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"non-ASCII C48 source {path}: {exc}") from exc
        for line_no, line in enumerate(data.splitlines(), 1):
            count += 1
            if b"\r" in line:
                raise SystemExit(f"CR in C48 source {path}:{line_no}")
            if len(line) > 64:
                raise SystemExit(
                    f"C48 source over 64 columns {path}:{line_no}={len(line)}"
                )
    print(f"C48 SOURCE BYTE-LINE SCAN PASS lines={count}", flush=True)


def verify_all():
    target_checks()
    c48_source_scan()
    run([
        sys.executable, "-B", "-m", "unittest", "discover",
        "-s", "compiler/tests", "-p", "test_graphics_review.py", "-v",
    ])
    run([sys.executable, "-B", "compiler/verify_graphics_demos.py", "--static"])
    run([sys.executable, "-B", "compiler/verify_release.py"])
    run(["git", "diff", "--check"])


def cleanup_temp():
    for path in sorted(TEMP):
        full = ROOT / path
        if full.exists():
            full.unlink()
            print(f"removed temporary {path}", flush=True)


def diff_scope_check():
    out = subprocess.check_output(["git", "status", "--short"], text=True)
    seen = {line[3:] for line in out.splitlines() if line.strip()}
    allowed = {
        str(DEMO), str(MOBIUS), str(FIREWORK), str(TEST), str(EXPECT), str(RELEASE),
        "docs/images/demos/contact-sheet.png",
    }
    allowed.update(str(p) for p in TEMP)
    allowed.update(
        str(p.relative_to(ROOT)) for p in (ROOT / "usr/bin/demos").glob("*.c48b")
    )
    allowed.update(
        str(p.relative_to(ROOT)) for p in (ROOT / "docs/images/demos").glob("*.png")
    )
    unexpected = seen - allowed
    if unexpected:
        raise SystemExit(f"unexpected Batch-5A diff paths: {sorted(unexpected)}")
    required = {str(DEMO), str(MOBIUS), str(FIREWORK), str(TEST), str(EXPECT), str(RELEASE)}
    missing = required - seen
    if missing:
        raise SystemExit(f"missing Batch-5A diff paths: {sorted(missing)}")
    print(f"BATCH-5A DIFF SCOPE PASS paths={len(seen)}", flush=True)


def byte_scan_fresh(root, pass_no, baseline=None):
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
    snap = {}
    files = lines = total = 0
    for raw in names:
        if not raw:
            continue
        rel = raw.decode("utf-8", "surrogateescape")
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"SoP {pass_no}: missing tracked file {rel}")
        h = hashlib.sha256()
        nbytes = nlines = 0
        with path.open("rb") as stream:
            while True:
                line = stream.readline()
                if line == b"":
                    break
                h.update(line)
                nbytes += len(line)
                nlines += 1
        snap[rel] = (h.hexdigest(), nbytes, nlines)
        files += 1
        lines += nlines
        total += nbytes
    target_checks(root)
    c48_source_scan(root)
    if any((root / path).exists() for path in TEMP):
        raise SystemExit(f"SoP {pass_no}: temporary Batch-5A scaffold remains")
    if baseline is not None and snap != baseline:
        raise SystemExit(f"SoP {pass_no}: fresh-copy bytes differ")
    print(
        f"SoP FRESH BYTE-LINE SCAN {pass_no} PASS "
        f"files={files} lines={lines} bytes={total}", flush=True,
    )
    return snap


def three_fresh_scans():
    baseline = None
    with tempfile.TemporaryDirectory(prefix="batch5a-sop-") as td:
        base = Path(td)
        for pass_no in (1, 2, 3):
            work = base / f"pass-{pass_no}"
            run(["git", "worktree", "add", "--detach", str(work), "HEAD"])
            try:
                run(["git", "lfs", "pull"], cwd=work)
                snap = byte_scan_fresh(work, pass_no, baseline)
                if baseline is None:
                    baseline = snap
            finally:
                run(["git", "worktree", "remove", "--force", str(work)])
    print("BATCH-5A SoP CERTIFIED: 3 successive fresh copies", flush=True)


def land(evidence_dir):
    patch_sources()
    add_tests()
    update_test_count()
    consume_evidence(evidence_dir)
    verify_all()
    cleanup_temp()
    target_checks()
    c48_source_scan()
    run([sys.executable, "-B", "compiler/verify_release.py"])
    run(["git", "diff", "--check"])
    diff_scope_check()
    run(["git", "config", "user.name", "github-actions[bot]"])
    run([
        "git", "config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    ])
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "fix: harden Batch-5A graphics demos"])
    three_fresh_scans()
    run(["git", "push", "origin", "HEAD:main"])


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: land_batch5a_v2.py evidence|land ...")
    mode = sys.argv[1]
    if mode == "evidence":
        if len(sys.argv) != 5:
            raise SystemExit("usage: ... evidence DEMO RUNNER OUT_DIR")
        evidence(sys.argv[2], sys.argv[3], sys.argv[4])
        return
    if mode == "land":
        if len(sys.argv) != 3:
            raise SystemExit("usage: ... land EVIDENCE_DIR")
        land(sys.argv[2])
        return
    raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
