#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
COMPILER = ROOT / "compiler"
if str(COMPILER) not in sys.path:
    sys.path.insert(0, str(COMPILER))

from c48.gui import FRAME_HEIGHT, FRAME_WIDTH, footer_text
from c48.screen import PALETTE_BRIGHT, PALETTE_NORMAL

TIMEOUT = 90.0


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def _wait_event(
    path: Path,
    event: str,
    *,
    process: subprocess.Popen | None = None,
    after_seq: int = 0,
    predicate=None,
    timeout: float = TIMEOUT,
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for record in _records(path):
            if int(record.get("seq", 0)) <= after_seq:
                continue
            if record.get("event") != event:
                continue
            if predicate is None or predicate(record):
                return record
        if process is not None and process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"GUI process exited {process.returncode} before {event}; "
                f"stdout={stdout!r} stderr={stderr!r}"
            )
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for GUI probe event {event}")


def _latest(path: Path, event: str) -> dict:
    matches = [r for r in _records(path) if r.get("event") == event]
    if not matches:
        raise AssertionError(f"missing GUI probe event {event}")
    return max(matches, key=lambda r: int(r["seq"]))


def _launcher_command(*args: str) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/d", "/c", str(ROOT / "c48run.bat"), *args]
    return [str(ROOT / "c48run"), *args]


def _check_version() -> str:
    result = subprocess.run(
        _launcher_command("--version"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"c48run --version failed: {result.returncode}: {result.stderr}"
        )
    text = result.stdout.strip()
    if text != "c48run 1.0.0":
        raise AssertionError(f"unexpected c48run version: {text!r}")
    return text


def _start(program: Path, probe: Path) -> subprocess.Popen:
    probe.unlink(missing_ok=True)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["C48_GUI_PROBE"] = str(probe)
    return subprocess.Popen(
        _launcher_command(str(program)),
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _finish(process: subprocess.Popen, expected: int) -> tuple[str, str]:
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise AssertionError("GUI process did not exit after requested close")
    if process.returncode != expected:
        raise AssertionError(
            f"GUI process returned {process.returncode}, expected {expected}; "
            f"stdout={stdout!r} stderr={stderr!r}"
        )
    if "Traceback (most recent call last)" in stderr:
        raise AssertionError(f"GUI process emitted traceback: {stderr}")
    return stdout, stderr


def _linux_find_window(title: str):
    from Xlib import X, display as xdisplay, error as xerror

    display = xdisplay.Display()
    root = display.screen().root
    pending = [root]
    while pending:
        window = pending.pop()
        try:
            name = window.get_wm_name()
            if isinstance(name, str) and name.startswith(title):
                window.set_input_focus(X.RevertToParent, X.CurrentTime)
                display.sync()
                return display, window
            pending.extend(window.query_tree().children)
        except (xerror.XError, OSError):
            continue
    display.close()
    raise AssertionError(f"X11 window not found: {title}")


def _linux_key(title: str, key: str, *, shift: bool = False) -> None:
    from Xlib import X, XK
    from Xlib.ext import xtest

    display, _window = _linux_find_window(title)
    try:
        if shift:
            shift_code = display.keysym_to_keycode(XK.string_to_keysym("Shift_L"))
            xtest.fake_input(display, X.KeyPress, shift_code)
        code = display.keysym_to_keycode(XK.string_to_keysym(key))
        if not code:
            raise AssertionError(f"X11 keycode unavailable for {key}")
        xtest.fake_input(display, X.KeyPress, code)
        xtest.fake_input(display, X.KeyRelease, code)
        if shift:
            xtest.fake_input(display, X.KeyRelease, shift_code)
        display.sync()
    finally:
        display.close()


def _windows_hwnd(title: str) -> int:
    user32 = ctypes.windll.user32
    found = []
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if buf.value.startswith(title):
            found.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(callback_type(callback), 0)
    if not found:
        raise AssertionError(f"Windows GUI window not found: {title}")
    return found[0]


def _windows_key(title: str, key: str, *, shift: bool = False) -> None:
    user32 = ctypes.windll.user32
    hwnd = _windows_hwnd(title)
    user32.ShowWindow(hwnd, 5)
    if not user32.SetForegroundWindow(hwnd):
        raise AssertionError(f"could not focus Windows GUI window: {title}")
    time.sleep(0.15)
    keyup = 0x0002
    if shift:
        user32.keybd_event(0x10, 0, 0, 0)
    vk = 0x20 if key == "space" else ord(key.upper())
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, keyup, 0)
    if shift:
        user32.keybd_event(0x10, 0, keyup, 0)


def _mac_activate(pid: int) -> None:
    script = (
        'tell application "System Events" to set frontmost of '
        f'(first process whose unix id is {pid}) to true'
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"macOS could not focus Tk process: {result.stderr}")


def _mac_key(pid: int, key: str, *, shift: bool = False) -> None:
    _mac_activate(pid)
    time.sleep(0.15)
    if key == "space" and shift:
        action = "key code 49 using shift down"
    elif key in {"q", "x"} and not shift:
        action = f'keystroke "{key}"'
    else:
        raise AssertionError(f"unsupported macOS injected key: {key}")
    script = f'tell application "System Events" to {action}'
    result = subprocess.run(
        ["osascript", "-e", script],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(f"macOS key injection failed: {result.stderr}")


def _send_key(process: subprocess.Popen, title: str, key: str, *, shift=False):
    if sys.platform.startswith("linux"):
        _linux_key(title, key, shift=shift)
    elif os.name == "nt":
        _windows_key(title, key, shift=shift)
    elif sys.platform == "darwin":
        _mac_key(process.pid, key, shift=shift)
    else:
        raise AssertionError(f"unsupported GUI host: {sys.platform}")


SPECTRUM_PALETTE = tuple(
    sorted(set(PALETTE_NORMAL) | set(PALETTE_BRIGHT))
)


def _rgb_linf(left, right) -> int:
    return max(abs(int(left[i]) - int(right[i])) for i in range(3))


_MIN_PALETTE_SEPARATION = min(
    _rgb_linf(left, right)
    for index, left in enumerate(SPECTRUM_PALETTE)
    for right in SPECTRUM_PALETTE[index + 1:]
)
AQUA_MAX_CHANNEL_DRIFT = (_MIN_PALETTE_SEPARATION - 1) // 2


def _aqua_palette_spatial_match(expected_pixels, actual_pixels):
    """Prove Aqua dithering preserved every Spectrum palette class in place.

    Some Aqua compositors color-manage solid Tk pixels with one-channel
    dithering, so one source RGB may legitimately appear as several adjacent
    RGB triplets. Accept that only when each captured pixel remains uniquely
    nearest to the exact Spectrum palette color expected at that same position
    and stays strictly inside half the minimum palette separation. Therefore a
    normal/bright swap, spatial shift, clipping, or cross-palette corruption
    cannot be hidden by this allowance.
    """
    expected_pixels = tuple(tuple(pixel) for pixel in expected_pixels)
    actual_pixels = tuple(tuple(pixel) for pixel in actual_pixels)
    if len(expected_pixels) != len(actual_pixels):
        return None
    palette = set(SPECTRUM_PALETTE)
    max_drift = 0
    for source, shown in zip(expected_pixels, actual_pixels):
        if source not in palette:
            return None
        distances = [
            (_rgb_linf(shown, color), color)
            for color in SPECTRUM_PALETTE
        ]
        best = min(distance for distance, _ in distances)
        nearest = [
            color for distance, color in distances if distance == best
        ]
        if (
            best > AQUA_MAX_CHANNEL_DRIFT
            or len(nearest) != 1
            or nearest[0] != source
        ):
            return None
        max_drift = max(max_drift, best)
    return {
        "max_channel_delta": max_drift,
        "limit": AQUA_MAX_CHANNEL_DRIFT,
        "minimum_palette_separation": _MIN_PALETTE_SEPARATION,
    }


def _palette_bijection(expected, actual) -> dict[str, list[int]] | None:
    """Return an exact spatial color bijection, or None if geometry/content differs.

    Aqua's compositor may color-manage the displayed Tk surface before ImageGrab
    returns RGB bytes.  A bijection permits that host color transform only when
    every source RGB triplet maps to exactly one captured RGB triplet and no two
    source colors collapse to the same captured color.  Pixel positions must
    still agree across the entire framebuffer.
    """
    mapping: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    reverse: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for source, shown in zip(expected.getdata(), actual.getdata()):
        source = tuple(source)
        shown = tuple(shown)
        prior = mapping.setdefault(source, shown)
        if prior != shown:
            return None
        reverse_prior = reverse.setdefault(shown, source)
        if reverse_prior != source:
            return None
    return {
        "%02x%02x%02x" % source: list(shown)
        for source, shown in sorted(mapping.items())
    }


def _screenshot(
    evidence: Path,
    name: str,
    window: dict,
    frame: dict,
) -> dict:
    try:
        from PIL import Image, ImageGrab
    except ImportError as exc:
        raise AssertionError(f"Pillow ImageGrab is required: {exc}") from exc

    probe_frame_path = evidence / str(frame.get("frame_ppm", ""))
    if not probe_frame_path.is_file():
        raise AssertionError(
            f"missing Tk-rendered frame evidence for {name}: {probe_frame_path}"
        )
    frame_path = evidence / f"{name}-frame.ppm"
    frame_path.write_bytes(probe_frame_path.read_bytes())
    expected = Image.open(frame_path).convert("RGB")
    if expected.size != (FRAME_WIDTH, FRAME_HEIGHT):
        raise AssertionError(
            f"unexpected Tk-rendered frame size for {name}: {expected.size}"
        )
    expected_hash = hashlib.sha256(expected.tobytes()).hexdigest()
    if expected_hash != str(frame["frame_sha256"]):
        raise AssertionError(
            f"Tk frame evidence hash mismatch for {name}: "
            f"ppm={expected_hash} probe={frame['frame_sha256']}"
        )

    screen_w = int(window["screen_width"])
    screen_h = int(window["screen_height"])
    if screen_w <= 0 or screen_h <= 0:
        raise AssertionError("Tk reported invalid screen geometry")
    canvas_w = int(frame["canvas_width"])
    canvas_h = int(frame["canvas_height"])
    required_w = FRAME_WIDTH * int(window["scale"])
    required_h = FRAME_HEIGHT * int(window["scale"])
    if (canvas_w, canvas_h) != (required_w, required_h):
        raise AssertionError(
            f"Tk canvas geometry is not fully mapped for {name}: "
            f"got={(canvas_w, canvas_h)} expected={(required_w, required_h)}"
        )

    full_path = evidence / f"{name}-desktop.png"
    crop_path = evidence / f"{name}-canvas.png"
    exact = False
    palette_map = None
    palette_spatial = None
    shot = crop = base = None
    rendered_hash = ""
    deadline = time.monotonic() + 3.0
    while True:
        # Give the host compositor a chance to present the Tk surface.  This is
        # especially important on Aqua, where window-server presentation trails
        # Tk's idle rendering by more than one application event-loop turn.
        time.sleep(0.15)
        shot = ImageGrab.grab()
        rx = shot.width / screen_w
        ry = shot.height / screen_h
        left = round(int(frame["canvas_x"]) * rx)
        top = round(int(frame["canvas_y"]) * ry)
        right = round((int(frame["canvas_x"]) + canvas_w) * rx)
        bottom = round((int(frame["canvas_y"]) + canvas_h) * ry)
        crop = shot.crop((left, top, right, bottom)).convert("RGB")
        base = crop.resize((FRAME_WIDTH, FRAME_HEIGHT), Image.Resampling.NEAREST)
        rendered_hash = hashlib.sha256(base.tobytes()).hexdigest()
        if rendered_hash == expected_hash:
            exact = True
            break
        if str(window.get("windowing_system")) == "aqua":
            palette_map = _palette_bijection(expected, base)
            if palette_map is not None:
                break
            palette_spatial = _aqua_palette_spatial_match(
                expected.getdata(),
                base.getdata(),
            )
            if palette_spatial is not None:
                break
        if time.monotonic() >= deadline:
            break

    assert shot is not None and crop is not None and base is not None
    shot.save(full_path)
    crop.save(crop_path)
    if not exact and palette_map is None and palette_spatial is None:
        raise AssertionError(
            f"desktop canvas pixels differ from Tk-rendered frame for {name}: "
            f"desktop={rendered_hash} expected={expected_hash}; "
            f"shot={shot.size} tk_screen=({screen_w},{screen_h}) "
            f"crop={crop.size} windowing={window.get('windowing_system')}"
        )
    if exact:
        comparison = "exact-rgb"
    elif palette_map is not None:
        comparison = "aqua-color-bijection"
    else:
        comparison = "aqua-palette-spatial"
    return {
        "desktop_png": full_path.name,
        "desktop_sha256": hashlib.sha256(full_path.read_bytes()).hexdigest(),
        "canvas_png": crop_path.name,
        "canvas_sha256": hashlib.sha256(crop_path.read_bytes()).hexdigest(),
        "frame_ppm": frame_path.name,
        "frame_ppm_sha256": hashlib.sha256(frame_path.read_bytes()).hexdigest(),
        "frame_sha256": expected_hash,
        "comparison": comparison,
        "aqua_color_bijection": palette_map,
        "aqua_palette_spatial": palette_spatial,
        "capture_size": list(shot.size),
        "canvas_capture_size": list(crop.size),
    }


def _forest(evidence: Path) -> dict:
    name = "forest"
    probe = evidence / f"probe-{name}.jsonl"
    process = _start(ROOT / "usr/bin/demos/forest.c48b", probe)
    title = "ZX-UX C48 - forest.c48b"
    try:
        window = _wait_event(probe, "window_ready", process=process)
        done = _wait_event(
            probe,
            "program_done",
            process=process,
            predicate=lambda r: int(r["status"]) == 0 and r["error_type"] is None,
        )
        footer = _wait_event(
            probe,
            "footer_done",
            process=process,
            after_seq=int(done["seq"]),
        )
        if footer["text"] != footer_text(True):
            raise AssertionError(f"wrong completed footer: {footer['text']!r}")
        frame = _latest(probe, "frame_rendered")
        capture = _screenshot(evidence, name, window, frame)
        _send_key(process, title, "space", shift=True)
        stdout, stderr = _finish(process, 0)
        break_event = _latest(probe, "break_key")
        if not break_event["done"] or break_event["break_running"]:
            raise AssertionError("completed Shift+Space was misclassified as BREAK")
        return {"capture": capture, "stdout": stdout, "stderr": stderr}
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def _fortune(evidence: Path) -> dict:
    name = "fortune"
    probe = evidence / f"probe-{name}.jsonl"
    process = _start(ROOT / "usr/bin/games/fortune.c48b", probe)
    title = "ZX-UX C48 - fortune.c48b"
    try:
        window = _wait_event(probe, "window_ready", process=process)
        first_wait = _wait_event(probe, "input_waiting", process=process)
        frame = _latest(probe, "frame_rendered")
        if int(frame["seq"]) >= int(first_wait["seq"]):
            raise AssertionError(
                "fortune framebuffer was not painted before getchar() began waiting"
            )
        capture = _screenshot(evidence, name, window, frame)
        _send_key(process, title, "x")
        accepted_x = _wait_event(
            probe,
            "key_accepted",
            process=process,
            after_seq=int(first_wait["seq"]),
            predicate=lambda r: int(r["value"]) == ord("x"),
        )
        second_wait = _wait_event(
            probe,
            "input_waiting",
            process=process,
            after_seq=int(accepted_x["seq"]),
        )
        _send_key(process, title, "q")
        _wait_event(
            probe,
            "key_accepted",
            process=process,
            after_seq=int(second_wait["seq"]),
            predicate=lambda r: int(r["value"]) == ord("q"),
        )
        done = _wait_event(
            probe,
            "program_done",
            process=process,
            predicate=lambda r: int(r["status"]) == 0 and r["error_type"] is None,
        )
        _wait_event(
            probe, "footer_done", process=process, after_seq=int(done["seq"])
        )
        _send_key(process, title, "space", shift=True)
        stdout, stderr = _finish(process, 0)
        return {"capture": capture, "stdout": stdout, "stderr": stderr}
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def _snake(evidence: Path) -> dict:
    name = "snake"
    probe = evidence / f"probe-{name}.jsonl"
    process = _start(ROOT / "usr/bin/games/snake.c48b", probe)
    title = "ZX-UX C48 - snake.c48b"
    try:
        window = _wait_event(probe, "window_ready", process=process)
        wait = _wait_event(probe, "input_waiting", process=process)
        frame = _latest(probe, "frame_rendered")
        capture = _screenshot(evidence, name, window, frame)
        _send_key(process, title, "space", shift=True)
        break_event = _wait_event(
            probe,
            "break_key",
            process=process,
            after_seq=int(wait["seq"]),
            predicate=lambda r: bool(r["break_running"]),
        )
        if break_event["done"]:
            raise AssertionError("active Shift+Space arrived after program completion")
        stdout, stderr = _finish(process, 130)
        return {"capture": capture, "stdout": stdout, "stderr": stderr}
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify the real Tk desktop event loop, painting and input path"
    )
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ns = ap.parse_args(argv)
    evidence = ns.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    for old in evidence.iterdir():
        if old.is_file():
            old.unlink()

    version = _check_version()
    results = {
        "schema": 1,
        "version": version.split()[-1],
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "commit": os.environ.get("C48_GUI_COMMIT", "local"),
        "runner": os.environ.get("C48_GUI_RUNNER", platform.system().lower()),
        "tests": {},
    }
    for name, test in (
        ("forest", _forest),
        ("fortune", _fortune),
        ("snake", _snake),
    ):
        results["tests"][name] = test(evidence)
        print(f"GUI PASS: {name}")

    tk_records = _records(evidence / "probe-forest.jsonl")
    window = next(r for r in tk_records if r["event"] == "window_ready")
    results["tk_patchlevel"] = window["tk_patchlevel"]
    results["tk_windowing_system"] = window["windowing_system"]
    result_path = evidence / "GUI-EVIDENCE.json"
    result_path.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    # The display process overwrites its probe-frame scratch file as newer
    # generations are painted.  Each screenshot already copied the exact frame
    # it proved to the stable <program>-frame.ppm evidence name.
    for scratch in evidence.glob("probe-*-frame.ppm"):
        scratch.unlink()
    members = sorted(p for p in evidence.iterdir() if p.is_file())
    (evidence / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in members
            if path.name != "SHA256SUMS"
        ),
        encoding="ascii",
        newline="\n",
    )
    print(
        "GUI VERIFY PASS: "
        f"{platform.system()} {platform.machine()} / Python {platform.python_version()} "
        f"/ Tk {results['tk_patchlevel']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
