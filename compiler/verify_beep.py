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
"""Numerical and synchronization proof for C48's ROM-derived beep()."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tempfile
import threading
import wave

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from c48.compiler import compile_bytes, compile_file
from c48.float5 import Float5
from c48.format import encode
from c48.screen import Font4x8, ZXScreen
from c48.romvm import RomMathVM
from c48.sound import BeepPlan, WAV_SAMPLE_RATE, plan_beep
from c48.vm import C48VM

HEADER = (SDK / "usr" / "src" / "c48host.h").read_text(encoding="ascii")
FONT = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")


def fail(message: str) -> None:
    raise SystemExit(f"BEEP VERIFY FAIL: {message}")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wav_measure(path: Path) -> tuple[int, int, int, float, float]:
    with wave.open(str(path), "rb") as inp:
        channels = inp.getnchannels()
        width = inp.getsampwidth()
        rate = inp.getframerate()
        frames = inp.getnframes()
        data = inp.readframes(frames)
    if channels != 1 or width != 1 or rate != WAV_SAMPLE_RATE:
        fail(
            f"unexpected WAV format channels={channels} width={width} rate={rate}"
        )
    runs = 0
    previous = None
    for sample in data:
        if sample != previous:
            runs += 1
            previous = sample
    seconds = frames / rate if rate else 0.0
    measured_hz = (runs / 2.0) / seconds if seconds and runs else 0.0
    return rate, frames, runs, seconds, measured_hz


def compile_probe(duration: str, pitch: str) -> dict:
    source = (
        "#include <c48.h>\n"
        "int main(void){return beep("
        + duration
        + ","
        + pitch
        + ");}\n"
    )
    return compile_bytes(
        source.encode("ascii"),
        source_name="beep-proof.c",
        builtin_header=HEADER,
    )


def verify_case(duration: str, pitch: str) -> None:
    requested_duration = Float5.from_decimal(duration)
    requested_pitch = Float5.from_decimal(pitch)
    expected = plan_beep(requested_duration, requested_pitch)
    observed: dict[str, float | int] = {}
    entered = threading.Event()
    release = threading.Event()
    result: dict[str, object] = {}

    def blocking_probe(path: Path) -> None:
        _rate, frames, runs, seconds, measured = wav_measure(path)
        observed["frames"] = frames
        observed["runs"] = runs
        observed["seconds"] = seconds
        observed["hz"] = measured
        entered.set()
        if not release.wait(timeout=30.0):
            raise RuntimeError("blocking sound probe release timeout")

    program = compile_probe(duration, pitch)
    vm = RomMathVM(
        program,
        ZXScreen(FONT),
        argv=["beep-proof"],
        sound_player=blocking_probe,
    )
    if vm.sound.prepared_count != 1 or vm.sound.generated_count != 1:
        fail(
            f"literal preload mismatch for pitch={pitch}: "
            f"prepared={vm.sound.prepared_count} generated={vm.sound.generated_count}"
        )

    if expected.cycles == 0:
        if vm.run() != 0:
            fail(f"VM returned nonzero for duration={duration} pitch={pitch}")
        if entered.is_set():
            fail(f"zero-cycle beep unexpectedly invoked sound player for pitch={pitch}")
        return

    def run_vm() -> None:
        result["status"] = vm.run()

    worker = threading.Thread(target=run_vm, daemon=True)
    worker.start()
    try:
        if not entered.wait(timeout=10.0):
            fail(f"sound callback was not entered for pitch={pitch}")
        if not worker.is_alive():
            fail(f"beep returned before blocking sound callback for pitch={pitch}")
    finally:
        release.set()
    worker.join(timeout=10.0)
    if worker.is_alive():
        fail(f"VM did not resume after sound callback release for pitch={pitch}")
    status = result.get("status")
    if status != 0:
        fail(f"VM returned {status} for duration={duration} pitch={pitch}")

    runs = int(observed.get("runs", -1))
    wav_seconds = float(observed.get("seconds", -1.0))
    wav_hz = float(observed.get("hz", -1.0))
    if runs != expected.cycles * 2:
        fail(
            f"wave edge count mismatch for pitch={pitch}: "
            f"runs={runs} expected={expected.cycles * 2}"
        )
    if abs(wav_seconds - expected.duration_seconds) > (1.0 / WAV_SAMPLE_RATE):
        fail(
            f"WAV duration mismatch for pitch={pitch}: "
            f"wav={wav_seconds:.9f} model={expected.duration_seconds:.9f}"
        )
    if abs(wav_hz - expected.frequency_hz) > 0.10:
        fail(
            f"WAV frequency mismatch for pitch={pitch}: "
            f"wav={wav_hz:.9f} model={expected.frequency_hz:.9f}"
        )

    print(
        "BEEP PROOF PASS: "
        f"pitch={pitch} requested_s={duration} "
        f"rom_hz={float(expected.rom_frequency):.9f} "
        f"HL={expected.loop_hl} cycles={expected.cycles} "
        f"physical_hz={expected.frequency_hz:.9f} "
        f"wav_hz={wav_hz:.9f} "
        f"model_s={expected.duration_seconds:.9f} "
        f"wav_s={wav_seconds:.9f} blocking=confirmed "
        "speaker_output=not_asserted",
        flush=True,
    )


def verify_shipped_tune() -> None:
    source = SDK / "usr" / "src" / "sound" / "tune.c"
    frozen = SDK / "usr" / "bin" / "sound" / "tune.c48b"
    if not source.is_file() or not frozen.is_file():
        fail("shipped tune.c/tune.c48b pair is missing")
    program = compile_file(source)
    rebuilt = encode(program)
    if rebuilt != frozen.read_bytes():
        fail("tune.c48b deterministic rebuild mismatch")
    calls = 0

    def no_wait_player(path: Path) -> None:
        nonlocal calls
        _rate, _frames, _runs, _seconds, measured = wav_measure(path)
        if measured <= 0:
            fail("shipped tune produced a non-tone WAV")
        calls += 1

    vm = RomMathVM(
        program,
        ZXScreen(FONT),
        argv=["tune"],
        sound_player=no_wait_player,
    )
    if vm.sound.prepared_count != 9:
        fail(f"tune literal preload count is {vm.sound.prepared_count}, expected 9")
    if vm.run() != 0 or calls != 9:
        fail(f"tune execution mismatch: calls={calls}")
    print(
        "BEEP TUNE PASS: "
        f"preloaded=9 played=9 c48b_sha256={sha_bytes(rebuilt)}",
        flush=True,
    )


def verify_playsound3() -> None:
    try:
        import playsound3
    except ModuleNotFoundError as exc:
        fail(f"playsound3 import failed: {exc}")
    if not callable(getattr(playsound3, "playsound", None)):
        fail("playsound3.playsound is not callable")
    print(
        "PLAYSOUND3 PASS: "
        f"version={getattr(playsound3, '__version__', 'unknown')} "
        f"default_backend={getattr(playsound3, 'DEFAULT_BACKEND', 'unknown')} "
        f"available_backends={getattr(playsound3, 'AVAILABLE_BACKENDS', 'unknown')}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify C48 BEEP numerically")
    ap.add_argument(
        "--require-playsound3",
        action="store_true",
        help="also require the real playsound3 package to import",
    )
    ns = ap.parse_args(argv)
    if ns.require_playsound3:
        verify_playsound3()
    verify_shipped_tune()
    for duration, pitch in (
        ("0.12", "-12.0"),
        ("0.12", "0.0"),
        ("0.25", "0.5"),
        ("0.12", "12.0"),
    ):
        verify_case(duration, pitch)
    print(
        "BEEP VERIFY PASS: 4 ROM/WAV/synchronization probes; "
        "audible speaker emission intentionally not asserted in CI",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
