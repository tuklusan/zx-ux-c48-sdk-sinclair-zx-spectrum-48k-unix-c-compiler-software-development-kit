#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def exact(path: str, old: str, new: str, count: int = 1) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{path}: expected {count} copies, found {found}: {old!r}")
    p.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_input(data: bytes) -> None:
    cp = subprocess.run(
        [sys.executable, "-B", "compiler/c48run.py", "--headless",
         "usr/bin/apps/write48.c48b"],
        cwd=ROOT, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise SystemExit(
            f"write48 input failed rc={cp.returncode}\n"
            + cp.stdout.decode("utf-8", "replace")
            + cp.stderr.decode("utf-8", "replace")
        )


def before() -> None:
    gui = (ROOT / "compiler/c48/gui.py").read_text(encoding="utf-8")
    api = (ROOT / "usr/src/apps/appapi.h").read_text(encoding="utf-8")
    wr = (ROOT / "usr/src/apps/write48.c").read_text(encoding="utf-8")
    assert 'if keysym == "Escape":\n        return (27,)' in gui
    assert "if (c == 11 || c == 27)" in api
    assert "CAPS+7 CMD" in wr
    assert "if (c == 11 || c == 27)" in wr
    print("BEFORE: host Esc=27, app cancel=11/27, WRITE48 label=CAPS+7")


def patch() -> None:
    exact(
        "compiler/c48/gui.py",
        'if keysym == "Escape":\n        return (27,)',
        'if keysym == "Escape":\n        return (7,)',
    )
    exact(
        "compiler/tests/test_gui_framebuffer.py",
        "    TkDisplay,\n    VISUAL_FRAME_DWELL_MS,",
        "    TkDisplay,\n    VISUAL_FRAME_DWELL_MS,\n    key_event_bytes,",
    )
    exact(
        "compiler/tests/test_gui_framebuffer.py",
        "    def test_typeahead_fifo_preserves_rapid_text(self):\n"
        "        display = TkDisplay(new_screen())",
        "    def test_typeahead_fifo_preserves_rapid_text(self):\n"
        "        self.assertEqual(key_event_bytes(\"Escape\", \"\"), (7,))\n"
        "        display = TkDisplay(new_screen())",
    )
    exact(
        "usr/src/apps/appapi.h",
        "        if (c == 11 || c == 27)\n            return 0;",
        "        if (c == 7)\n            return 0;",
    )
    exact(
        "usr/src/apps/write48.c",
        "INSERT: CAPS+7 CMD  BS DEL  ENTER NL",
        "INSERT: CAPS+1 CMD  BS DEL  ENTER NL",
    )
    exact(
        "usr/src/apps/write48.c",
        "    if (c == 11 || c == 27) {\n        wr_insert = 0;",
        "    if (c == 7) {\n        wr_insert = 0;",
    )
    print("PATCH: EDIT/code 7 is the application cancel key")


def hashes() -> None:
    p = ROOT / "compiler/app_expectations.json"
    data = json.loads(p.read_text(encoding="ascii"))
    data["helper_sha256"] = sha(ROOT / "usr/src/apps/appapi.h")
    for name in ("sheet48", "write48", "wire3d"):
        data["apps"][name]["source_sha256"] = sha(
            ROOT / f"usr/src/apps/{name}.c"
        )
        data["apps"][name]["binary_sha256"] = sha(
            ROOT / f"usr/bin/apps/{name}.c48b"
        )
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii", newline="\n")
    for name in ("sheet48", "write48", "wire3d"):
        print(
            "HASH", name,
            data["apps"][name]["source_sha256"],
            data["apps"][name]["binary_sha256"],
        )
    print("HASH helper", data["helper_sha256"])


def after() -> None:
    sys.path.insert(0, str(ROOT / "compiler"))
    from c48.gui import key_event_bytes

    if key_event_bytes("Escape", "") != (7,):
        raise SystemExit("host Escape did not map to EDIT/code 7")
    api = (ROOT / "usr/src/apps/appapi.h").read_text(encoding="utf-8")
    wr = (ROOT / "usr/src/apps/write48.c").read_text(encoding="utf-8")
    if "c == 11 || c == 27" in api or "c == 11 || c == 27" in wr:
        raise SystemExit("legacy cancel key remains in application path")
    if "CAPS+1 CMD" not in wr:
        raise SystemExit("WRITE48 status does not advertise CAPS+1")
    run_input(b"iabc\x07q")
    run_input(b"f\x07q")
    run_input(b"i\x0bq\x07q")
    print("AFTER: code 7 exits insert/FIND; code 11 is not cancel; host Esc=7")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: editkey7.py before|patch|hash|after")
    mode = sys.argv[1]
    {"before": before, "patch": patch, "hash": hashes, "after": after}[mode]()


if __name__ == "__main__":
    main()
