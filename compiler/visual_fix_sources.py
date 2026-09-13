#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
sys.path.insert(0, str(ROOT))

from c48.compiler import compile_file
from c48.format import encode, read
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM


def rep(path, old, new):
    p = SDK / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise RuntimeError(f"bad anchor {path}: {old!r} count={s.count(old)}")
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())

rep("usr/src/demos/sprites.c",
    "    n = d_frames(argc, argv, 160);\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n        sleep(5u);\n    }\n",
    "    n = d_frames(argc, argv, 14);\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n    }\n")
for name in ("goblet", "mobius"):
    rep(f"usr/src/demos/{name}.c",
        "        yield();\n        if (argc < 2) sleep(75u);\n        else sleep(1u);\n",
        "        yield();\n")
rep("usr/src/demos/torus.c",
    "    n = d_frames(argc, argv, 4);\n    if (n > 4) n = 4;\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n        if (argc < 2) sleep(50u);\n    }\n",
    "    n = d_frames(argc, argv, 10);\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n    }\n")
rep("usr/src/demos/warp.c",
    "    n = d_frames(argc, argv, 80);\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n        if (argc < 2) sleep(4u);\n    }\n",
    "    n = d_frames(argc, argv, 20);\n    for (f = 0; f < n; f++) {\n        scene(f);\n        yield();\n    }\n")
rep("usr/src/examples/colors.c",
    "        border(c);\n        yield();\n        sleep(2u);\n",
    "        border(c);\n        yield();\n")

rep("doc/HOST-DIVERGENCES.md",
    "`ticks()` and `sleep()` in the provisional host API use host monotonic time and a 50-Hz\ninterpretation.  The host does not emulate cooperative ZX-UX scheduling, process tables,\npipes, cassette I/O or kernel syscalls.\n",
    "`ticks()` and `sleep()` in the provisional host API use host monotonic time and a 50-Hz\ninterpretation.  GUI presentation is deliberately allowed to run slower than that clock:\n`yield()` and animation `sleep()` boundaries apply visual backpressure until the published\nframe has passed the Tk draw/host-visible release fence.  Late presentation is never repaid\nby dropping later intentional frames.  `getchar()` commits its prompt before arming the\ninput rendezvous but does not add the animation dwell.  The host does not emulate cooperative\nZX-UX scheduling, process tables, pipes, cassette I/O or kernel syscalls.\n")
rep("doc/RELEASE-NOTES.md",
    "- 50-Hz Tk polling, accelerated byte-run framebuffer conversion, and explicit `yield()`/animation-sleep presentation barriers so intentional logical frames are painted rather than silently coalesced;\n",
    "- 50-Hz Tk polling, accelerated byte-run framebuffer conversion, and explicit visual-release backpressure for `yield()`/animation-sleep boundaries so intentional frames cannot outrun Tk/host presentation;\n")

font = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")
gpath = ROOT / "graphics_demo_expectations.json"
g = json.loads(gpath.read_text(encoding="ascii"))
for name in ("goblet", "mobius", "sprites", "torus", "warp"):
    src = SDK / "usr" / "src" / "demos" / f"{name}.c"
    out = SDK / "usr" / "bin" / "demos" / f"{name}.c48b"
    binary = encode(compile_file(src))
    out.write_bytes(binary)
    exp = g["demos"][name]
    exp["source_sha256"] = sha(src)
    exp["binary_sha256"] = sha_bytes(binary)
    for frames, key in ((1, "first_screen_sha256"),
                        (int(exp["frames"]), "screen_sha256")):
        screen = ZXScreen(font)
        status = C48VM(read(out), screen, argv=[name, str(frames)],
                       max_steps=10000000).run()
        if status != 0:
            raise RuntimeError(f"{name}: runtime status {status}")
        actual = sha_bytes(screen.bytes())
        if actual != exp[key]:
            raise RuntimeError(
                f"{name}: pacing cleanup changed {key}: {actual} != {exp[key]}"
            )
gpath.write_text(json.dumps(g, indent=2) + "\n",
                 encoding="ascii", newline="\n")

rpath = ROOT / "release_expectations.json"
r = json.loads(rpath.read_text(encoding="ascii"))
src = SDK / "usr" / "src" / "examples" / "colors.c"
out = SDK / "usr" / "bin" / "examples" / "colors.c48b"
binary = encode(compile_file(src))
out.write_bytes(binary)
exp = r["demos"]["colors"]
exp["source_sha256"] = sha(src)
exp["binary_sha256"] = sha_bytes(binary)
screen = ZXScreen(font)
status = C48VM(read(out), screen, argv=["colors.c48b"]).run()
if status != 0:
    raise RuntimeError(f"colors: runtime status {status}")
actual = sha_bytes(screen.bytes())
if actual != exp["screen_sha256"]:
    raise RuntimeError(
        f"colors pacing cleanup changed final framebuffer: {actual} != {exp['screen_sha256']}"
    )
rpath.write_text(json.dumps(r, indent=2) + "\n",
                 encoding="ascii", newline="\n")
