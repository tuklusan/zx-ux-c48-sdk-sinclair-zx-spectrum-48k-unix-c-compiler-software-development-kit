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
"""Sinclair-compatible host support for the architecture-frozen C48 beep().

The arithmetic and timing constants below come from the repository's frozen
48K ROM disassembly under ``docs/reference/rom-disassemblies``:

* BEEP command: $03F8-$0469
* BEEPER routine: $03B5-$03F7
* semitone table: $046E-$04A9
* FP_TO_BC rounding: $2DA2-$2DC0
* STK_DATA literal decoder: $33C6-$33F6

The host synthesizes the square wave that the ROM timing loop describes and
uses Windows winsound or playsound3 as the optional host playback adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import os
import shutil
import tempfile
import wave
import weakref
from typing import Any, Callable

from .float5 import Float5, Float5Error

ZX48_CLOCK_HZ = 3_500_000
WAV_SAMPLE_RATE = 48_000
E_INVAL = 1
E_IO = 5
E_NOTSUP = 14

# The $03FD STK_DATA literal EC 6C 98 1F F5 decodes, by $33C6, to
# Float5 bytes 7C 6C 98 1F F5.  It is the ROM's fractional-semitone
# linearization constant K (documented there as approximately 0.0577622606).
_ROM_FRACTIONAL_K = Float5(bytes.fromhex("7c6c981ff5"))
_ROM_437500 = Float5.from_int(437500)
_ROM_30_125 = Float5.from_decimal("30.125")
_ROM_ONE = Float5.from_int(1)

# Exact five-byte values from the ROM semitone table at $046E.
_ROM_SEMITONES = tuple(
    Float5(bytes.fromhex(raw))
    for raw in (
        "8902d01286",  # C
        "890a976075",  # C#
        "8912d5171f",  # D
        "891b904102",  # D#
        "8924d053ca",  # E
        "892e9d36b1",  # F
        "8938ff493e",  # F#
        "8943ff6a73",  # G
        "894fa70054",  # G#
        "895c000000",  # A
        "896914f624",  # A#
        "8976f11005",  # B
    )
)


class BeepArgumentError(ValueError):
    """The requested duration/pitch would be rejected by the 48K ROM path."""


class AudioBackendUnavailable(RuntimeError):
    """No usable audible host playback backend is available."""


class AudioPlaybackError(RuntimeError):
    """The configured host audio player failed."""


@dataclass(frozen=True)
class BeepPlan:
    duration_raw: bytes
    pitch_raw: bytes
    pitch_integer: int
    semitone_index: int
    octave: int
    rom_frequency: Fraction
    loop_hl: int
    cycles: int
    period_tstates: int
    physical_frequency: Fraction
    physical_duration: Fraction

    @property
    def duration_seconds(self) -> float:
        return float(self.physical_duration)

    @property
    def frequency_hz(self) -> float:
        return float(self.physical_frequency)


@dataclass(frozen=True)
class ToneArtifact:
    plan: BeepPlan
    path: Path | None


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def _rom_find_int(value: Fraction, *, maximum: int = 0xFFFF) -> int:
    """Model FIND_INT/FP_TO_BC: INT(V+0.5), then reject negative/overflow."""
    rounded = _floor_fraction(value + Fraction(1, 2))
    if rounded < 0 or rounded > maximum:
        raise BeepArgumentError("ROM integer conversion is negative or out of range")
    return rounded


def _scale_float5_power_of_two(value: Float5, octave: int) -> Float5:
    """Model BEEP $043B-$043D, which changes only the Float5 exponent."""
    raw = bytearray(value.raw)
    if raw[0] == 0:
        if value.is_zero():
            return value
        raise BeepArgumentError("ROM frequency unexpectedly used integer Float5 form")
    exponent = raw[0] + octave
    if not 1 <= exponent <= 255:
        raise BeepArgumentError("pitch is outside the Spectrum Float5 exponent range")
    raw[0] = exponent
    return Float5(bytes(raw))


def plan_beep(duration: Float5, pitch: Float5) -> BeepPlan:
    """Derive the exact ROM-facing BEEPER parameters and physical square wave.

    This follows BEEP $03F8-$0469.  Core Float5 +,-,*,/ operations use the
    SDK's deterministic five-byte arithmetic model; ROM table bytes, literal
    constants, integer rounding, and BEEPER timing are taken directly from the
    frozen ROM disassembly.
    """
    try:
        duration_fraction = duration.to_fraction()
        pitch_fraction = pitch.to_fraction()
    except Float5Error as exc:
        raise BeepArgumentError(str(exc)) from exc

    # BEEP uses INT P, and Spectrum INT rounds downward for negative values.
    pitch_integer = _floor_fraction(pitch_fraction)
    if pitch_integer < -60 or pitch_integer > 127:
        raise BeepArgumentError("pitch integer part is outside the ROM BEEP range")

    # The octave-selection loop uses (i+60) modulo 12, with middle C at i=0.
    shifted = pitch_integer + 60
    semitone_index = shifted % 12
    octave = shifted // 12 - 5

    try:
        integer_pitch = Float5.from_int(pitch_integer)
        fractional_pitch = pitch.sub(integer_pitch)
        factor = fractional_pitch.mul(_ROM_FRACTIONAL_K).add(_ROM_ONE)
        base_frequency = _ROM_SEMITONES[semitone_index].mul(factor)
        # The ROM multiplier leaves the value in normalized floating form for
        # the exponent-byte octave adjustment at $043B-$043D.  The generic
        # SDK Float5 helper may canonicalize an exact integral result (notably
        # A=440) to small-integer form, so restore the ROM-required form here.
        if base_frequency.raw[0] == 0 and not base_frequency.is_zero():
            base_frequency = Float5.from_fraction(
                base_frequency.to_fraction(), prefer_integer=False
            )
        rom_frequency_f5 = _scale_float5_power_of_two(base_frequency, octave)
        rom_frequency = rom_frequency_f5.to_fraction()
    except Float5Error as exc:
        raise BeepArgumentError(str(exc)) from exc

    # FIND_INT1 at $0443 uses FP_TO_BC rounding, not host truncation.  The
    # sign test is applied *after* INT(t+0.5), so tiny negative durations that
    # round to zero are not rejected here; the later f*t conversion decides
    # whether they are a zero-cycle no-op or Report B.
    rounded_duration = _rom_find_int(duration_fraction, maximum=0xFF)
    if rounded_duration >= 11:
        raise BeepArgumentError("duration is outside the ROM BEEP range")

    try:
        cycle_value = duration.mul(rom_frequency_f5).to_fraction()
        loop_value = (
            _ROM_437500.div(rom_frequency_f5)
            .sub(_ROM_30_125)
            .to_fraction()
        )
    except Float5Error as exc:
        raise BeepArgumentError(str(exc)) from exc

    # FIND_INT2 rounds first, then rejects negative results/overflow.  This
    # distinction is observable near the upper pitch boundary: a slightly
    # negative timing-loop value may still round to HL=0 and is ROM-valid.
    loop_hl = _rom_find_int(loop_value)
    cycles = _rom_find_int(cycle_value)

    # BEEPER $03B5-$03F7 produces a 50% square wave.  Cycle timing is exactly
    # 236 + 8*HL T-states (118 + 4*HL per half-cycle) at 3.5 MHz.
    period_tstates = 236 + 8 * loop_hl
    physical_frequency = Fraction(ZX48_CLOCK_HZ, period_tstates)
    physical_duration = (
        Fraction(cycles * period_tstates, ZX48_CLOCK_HZ)
        if cycles
        else Fraction(0, 1)
    )
    return BeepPlan(
        duration_raw=duration.raw,
        pitch_raw=pitch.raw,
        pitch_integer=pitch_integer,
        semitone_index=semitone_index,
        octave=octave,
        rom_frequency=rom_frequency,
        loop_hl=loop_hl,
        cycles=cycles,
        period_tstates=period_tstates,
        physical_frequency=physical_frequency,
        physical_duration=physical_duration,
    )


def _round_fraction_positive(value: Fraction) -> int:
    if value < 0:
        raise ValueError("positive fraction required")
    return _floor_fraction(value + Fraction(1, 2))


def write_square_wav(path: Path, plan: BeepPlan, *, sample_rate: int = WAV_SAMPLE_RATE) -> None:
    """Write an 8-bit mono PCM rendering of the ROM BEEPER square wave."""
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    if plan.cycles == 0:
        frames = 0
        data = b""
    else:
        frames = max(
            1,
            _round_fraction_positive(plan.physical_duration * sample_rate),
        )
        # At sample n, half-cycle index is floor(2*f*n/sample_rate).  Use only
        # integer arithmetic so host floating point cannot move an edge.
        divisor = sample_rate * plan.period_tstates
        data = bytes(
            224 if ((n * 2 * ZX48_CLOCK_HZ) // divisor) % 2 == 0 else 32
            for n in range(frames)
        )
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(1)
        out.setframerate(sample_rate)
        out.writeframes(data)


def winsound_player(path: Path) -> None:
    """Play one WAV synchronously with the Windows standard library."""
    try:
        import winsound
    except (ImportError, ModuleNotFoundError) as exc:
        raise AudioBackendUnavailable(
            "Windows winsound is unavailable for audible C48 beep() playback"
        ) from exc
    try:
        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    except (OSError, RuntimeError) as exc:
        raise AudioPlaybackError(str(exc)) from exc


def playsound3_player(path: Path) -> None:
    """Play one WAV synchronously through the optional playsound3 package."""
    try:
        import playsound3
    except ModuleNotFoundError as exc:
        raise AudioBackendUnavailable(
            "playsound3 is required for audible C48 beep() playback"
        ) from exc
    try:
        playsound3.playsound(str(path), block=True)
    except playsound3.PlaysoundException as exc:
        raise AudioPlaybackError(str(exc)) from exc
    except OSError as exc:
        raise AudioPlaybackError(str(exc)) from exc


def default_audio_player(path: Path) -> None:
    """Use stdlib winsound on Windows, playsound3 elsewhere."""
    if os.name == "nt":
        winsound_player(path)
    else:
        playsound3_player(path)


def _static_float_arg(node: dict[str, Any]) -> Float5 | None:
    kind = node.get("kind")
    if kind == "floating_literal":
        return Float5(bytes.fromhex(node["float5"]))
    if kind in {"integer_literal", "character_literal"}:
        return Float5.from_int(int(node["value"]))
    if kind == "cast":
        # The cast can change the value before the call (notably float->int).
        # Rather than pre-synthesizing under a false cache key, leave casted
        # arguments to the normal runtime path.
        return None
    if kind == "unary" and node.get("op") in {"+", "-"}:
        value = _static_float_arg(node["operand"])
        if value is None:
            return None
        return value if node["op"] == "+" else value.neg()
    return None


def discover_literal_beeps(program: dict[str, Any]) -> list[tuple[Float5, Float5]]:
    """Find statically known beep(duration,pitch) argument pairs in C48B1 AST."""
    found: list[tuple[Float5, Float5]] = []
    stack: list[Any] = [program]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            stack.extend(current)
            continue
        if not isinstance(current, dict):
            continue
        if current.get("kind") == "call":
            fn = current.get("function")
            args = current.get("args")
            if (
                isinstance(fn, dict)
                and fn.get("kind") == "identifier"
                and fn.get("name") == "beep"
                and isinstance(args, list)
                and len(args) == 2
            ):
                duration = _static_float_arg(args[0])
                pitch = _static_float_arg(args[1])
                if duration is not None and pitch is not None:
                    found.append((duration, pitch))
        stack.extend(current.values())
    return found


def _remove_cache_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


class BeepEngine:
    """Per-VM WAV cache with load-time pre-synthesis and synchronous playback."""

    def __init__(
        self,
        program: dict[str, Any],
        *,
        player: Callable[[Path], None] | None = None,
        sample_rate: int = WAV_SAMPLE_RATE,
    ) -> None:
        self.player = player or default_audio_player
        self.sample_rate = sample_rate
        self.root: Path | None = None
        self._finalizer: Any = None
        self.cache: dict[tuple[bytes, bytes], ToneArtifact] = {}
        self.prepared_count = 0
        self.generated_count = 0
        self._prepare(program)

    @staticmethod
    def _key(duration: Float5, pitch: Float5) -> tuple[bytes, bytes]:
        return duration.raw, pitch.raw

    def _cache_root(self) -> Path:
        if self.root is None:
            self.root = Path(tempfile.mkdtemp(prefix="c48-beep-"))
            self._finalizer = weakref.finalize(
                self, _remove_cache_tree, self.root
            )
        return self.root

    def _make_artifact(self, duration: Float5, pitch: Float5) -> ToneArtifact:
        plan = plan_beep(duration, pitch)
        path: Path | None = None
        if plan.cycles:
            key_text = duration.hex() + "-" + pitch.hex()
            path = self._cache_root() / f"beep-{key_text}.wav"
            write_square_wav(path, plan, sample_rate=self.sample_rate)
            self.generated_count += 1
        return ToneArtifact(plan, path)

    def _prepare(self, program: dict[str, Any]) -> None:
        for duration, pitch in discover_literal_beeps(program):
            key = self._key(duration, pitch)
            if key in self.cache:
                continue
            try:
                artifact = self._make_artifact(duration, pitch)
            except (BeepArgumentError, OSError, ValueError):
                # Pre-synthesis is an optimization only.  Invalid/unwritable
                # tones retain normal runtime error behavior if actually called.
                continue
            self.cache[key] = artifact
            self.prepared_count += 1

    def artifact(self, duration: Float5, pitch: Float5) -> ToneArtifact:
        key = self._key(duration, pitch)
        artifact = self.cache.get(key)
        if artifact is None:
            artifact = self._make_artifact(duration, pitch)
            self.cache[key] = artifact
        return artifact

    def play(self, duration: Float5, pitch: Float5) -> BeepPlan:
        artifact = self.artifact(duration, pitch)
        if artifact.path is not None:
            self.player(artifact.path)
        return artifact.plan
