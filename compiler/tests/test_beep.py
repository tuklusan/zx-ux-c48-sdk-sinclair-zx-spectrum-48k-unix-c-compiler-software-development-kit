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

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import tempfile
import time
import unittest
import wave

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes, compile_file
from c48.float5 import Float5
from c48.screen import Font4x8, ZXScreen
from c48.romvm import RomMathVM
from c48.sound import (
    AudioBackendUnavailable,
    BeepArgumentError,
    WAV_SAMPLE_RATE,
    plan_beep,
    playsound3_player,
    write_square_wav,
)
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")
HEADER = (SDK / "usr" / "src" / "c48host.h").read_text(encoding="ascii")


def f(text: str) -> Float5:
    return Float5.from_decimal(text)


def compile_host(source: str):
    return compile_bytes(
        ("#include <c48.h>\n" + source).encode("ascii"),
        source_name="beep-test.c",
        builtin_header=HEADER,
    )


def wav_measure(path: Path) -> tuple[int, int, float, int]:
    with wave.open(str(path), "rb") as inp:
        rate = inp.getframerate()
        frames = inp.getnframes()
        data = inp.readframes(frames)
        if inp.getnchannels() != 1 or inp.getsampwidth() != 1:
            raise AssertionError("unexpected BEEP WAV format")
    runs = 0
    previous = None
    for sample in data:
        if sample != previous:
            runs += 1
            previous = sample
    seconds = frames / rate if rate else 0.0
    measured = (runs / 2.0) / seconds if seconds and runs else 0.0
    return rate, frames, measured, runs


class BeepRomModelTests(unittest.TestCase):
    def test_001_middle_c_rom_parameters(self):
        plan = plan_beep(f("1.0"), f("0.0"))
        self.assertEqual(plan.loop_hl, 1642)
        self.assertEqual(plan.cycles, 262)
        self.assertEqual(plan.period_tstates, 13372)
        self.assertAlmostEqual(float(plan.rom_frequency), 261.62556529045105, places=9)
        self.assertAlmostEqual(plan.frequency_hz, 261.7409512414, places=9)

    def test_002_fractional_pitch_uses_rom_linearization(self):
        plan = plan_beep(f("0.25"), f("0.5"))
        self.assertEqual(plan.loop_hl, 1595)
        self.assertEqual(plan.cycles, 67)
        self.assertAlmostEqual(float(plan.rom_frequency), 269.181607961655, places=9)
        self.assertAlmostEqual(plan.frequency_hz, 269.3136349646045, places=9)
        self.assertAlmostEqual(plan.duration_seconds, 0.24878057142857143, places=12)

    def test_003_octaves_follow_rom_exponent_adjustment(self):
        low = plan_beep(f("0.25"), f("-12"))
        high = plan_beep(f("0.25"), f("12"))
        self.assertEqual((low.loop_hl, low.cycles), (3314, 33))
        self.assertEqual((high.loop_hl, high.cycles), (806, 131))
        self.assertEqual(high.rom_frequency, low.rom_frequency * 4)

    def test_004_rom_argument_boundaries_use_post_round_sign(self):
        # FIND_INT applies INT(V+0.5) before its sign test.  Therefore the ROM
        # accepts a tiny negative duration if f*t also rounds to zero, and it
        # accepts a slightly negative timing-loop value when that rounds to 0.
        self.assertEqual(plan_beep(f("-0.001"), f("0")).cycles, 0)
        self.assertEqual(plan_beep(f("0.1"), f("69.8")).loop_hl, 0)
        for duration, pitch in (
            ("-0.01", "0"),
            ("10.5", "0"),
            ("0.1", "-60.1"),
            ("0.1", "69.9"),
            ("0.1", "70"),
        ):
            with self.subTest(duration=duration, pitch=pitch):
                with self.assertRaises(BeepArgumentError):
                    plan_beep(f(duration), f(pitch))

    def test_005_wav_numerically_matches_rom_timing(self):
        plan = plan_beep(f("0.25"), f("0.5"))
        with tempfile.TemporaryDirectory(prefix="c48-beep-test-") as td:
            path = Path(td) / "tone.wav"
            write_square_wav(path, plan)
            rate, frames, measured, runs = wav_measure(path)
        self.assertEqual(rate, WAV_SAMPLE_RATE)
        self.assertEqual(runs, plan.cycles * 2)
        self.assertAlmostEqual(frames / rate, plan.duration_seconds, delta=1.0 / rate)
        self.assertAlmostEqual(measured, plan.frequency_hz, delta=0.05)


class BeepVmTests(unittest.TestCase):
    def test_006_literal_calls_are_presynthesized_at_vm_load(self):
        program = compile_host(
            "int main(void){return beep(0.05,0.5);}\n"
        )
        calls: list[Path] = []
        vm = C48VM(
            program,
            ZXScreen(FONT),
            sound_player=lambda path: calls.append(path),
        )
        self.assertEqual(vm.sound.prepared_count, 1)
        self.assertEqual(vm.sound.generated_count, 1)
        self.assertEqual(vm.run(), 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(vm.sound.generated_count, 1)

    def test_007_dynamic_calls_generate_once_then_reuse_cache(self):
        program = compile_host(
            "int main(void){float d=0.05;float p=0.0;"
            "if(beep(d,p))return 1;return beep(d,p);}\n"
        )
        calls: list[Path] = []
        vm = C48VM(
            program,
            ZXScreen(FONT),
            sound_player=lambda path: calls.append(path),
        )
        self.assertEqual(vm.sound.prepared_count, 0)
        self.assertEqual(vm.run(), 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(vm.sound.generated_count, 1)
        self.assertEqual(calls[0], calls[1])

    def test_008_beep_blocks_vm_for_rendered_tone_duration(self):
        program = compile_host(
            "int main(void){return beep(0.06,0.0);}\n"
        )

        def blocking_player(path: Path) -> None:
            with wave.open(str(path), "rb") as inp:
                seconds = inp.getnframes() / inp.getframerate()
            time.sleep(seconds)

        vm = C48VM(
            program,
            ZXScreen(FONT),
            sound_player=blocking_player,
        )
        plan = next(iter(vm.sound.cache.values())).plan
        started = time.monotonic()
        self.assertEqual(vm.run(), 0)
        elapsed = time.monotonic() - started
        self.assertGreaterEqual(elapsed, plan.duration_seconds * 0.9)
        self.assertLess(elapsed, plan.duration_seconds + 0.5)

    def test_009_missing_playsound3_is_controlled(self):
        with tempfile.TemporaryDirectory(prefix="c48-beep-test-") as td:
            path = Path(td) / "empty.wav"
            path.write_bytes(b"")
            with patch.dict(sys.modules, {"playsound3": None}):
                with self.assertRaises(AudioBackendUnavailable):
                    playsound3_player(path)

    def test_010_playsound3_adapter_is_synchronous(self):
        calls = []

        class FakeError(Exception):
            pass

        fake = SimpleNamespace(
            PlaysoundException=FakeError,
            playsound=lambda sound, block=True: calls.append((sound, block)),
        )
        with tempfile.TemporaryDirectory(prefix="c48-beep-test-") as td:
            path = Path(td) / "tone.wav"
            path.write_bytes(b"RIFF")
            with patch.dict(sys.modules, {"playsound3": fake}):
                playsound3_player(path)
        self.assertEqual(calls, [(str(path), True)])

    def test_011_shipped_tune_runs_through_sdk_rom_vm(self):
        program = compile_file(SDK / "usr" / "src" / "tune.c")
        calls: list[Path] = []
        vm = RomMathVM(
            program,
            ZXScreen(FONT),
            argv=["tune"],
            sound_player=lambda path: calls.append(path),
        )
        self.assertEqual(vm.sound.prepared_count, 9)
        self.assertEqual(vm.run(), 0)
        self.assertEqual(len(calls), 9)
        self.assertEqual(vm.sound.generated_count, 9)


if __name__ == "__main__":
    unittest.main()
