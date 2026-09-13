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
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
COMP = ROOT / "compiler"
if str(COMP) not in sys.path:
    sys.path.insert(0, str(COMP))

from c48.format import read
from c48.romvm import RomMathVM
from c48.screen import Font4x8, ZXScreen

A = ROOT / "usr" / "src" / "ailmzx48"
SRC = A / "ailmzx48.c"
CORPUS = A / "training" / "seed_corpus.json"
MODEL_DIR = A / "model"
CONV_DIR = A / "conversations"
BIN = ROOT / "usr" / "bin" / "ailmzx48" / "ailmzx48.c48b"

MD_HEADER = '''<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], timeout: int) -> None:
    cp = subprocess.run(cmd, cwd=ROOT, text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=timeout, check=False)
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout)
        sys.stderr.write(cp.stderr)
        raise RuntimeError("command failed: " + " ".join(cmd))


class TraceScreen(ZXScreen):
    def __init__(self, font):
        super().__init__(font)
        self.trace = bytearray()

    def putchar(self, c):
        self.trace.append(int(c) & 0xFF)
        return super().putchar(c)


class Feeder:
    def __init__(self, screen, prompts):
        self.screen = screen
        self.prompts = prompts
        self.queue = bytearray()
        self.pos = 0
        self.last = 0
        self.sent = 0
        self.events = []
        self.vm = None

    def diag(self):
        if self.vm is None:
            return {}
        out = {}
        for name in ("ai_turns", "ai_otokens", "ai_yields",
                     "ai_error", "ai_beeps"):
            lv = self.vm.global_lvalues.get(name)
            if lv is not None:
                out[name] = int(self.vm._load(lv).data)
        return out

    def boundary(self):
        raw = bytes(self.screen.trace[self.last:])
        self.last = len(self.screen.trace)
        self.events.append({
            "kind": "boundary",
            "raw_hex": raw.hex(),
            "text": raw.decode("ascii", errors="replace"),
            "diag": self.diag(),
        })
        if self.sent < len(self.prompts):
            line = self.prompts[self.sent] + "\n"
            self.queue.extend(line.encode("ascii"))
            self.sent += 1
        elif self.sent == len(self.prompts):
            self.queue.extend(b"q\n")
            self.sent += 1
        else:
            raise RuntimeError("unexpected input demand after q")

    def __call__(self):
        if self.pos >= len(self.queue):
            self.queue = bytearray()
            self.pos = 0
            self.boundary()
        value = self.queue[self.pos]
        self.pos += 1
        return value


def derived_reply(text: str) -> str:
    if text.endswith("> "):
        text = text[:-2]
    return text.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--max-seconds", type=int, default=600)
    ns = ap.parse_args()
    started = time.monotonic()
    req = json.loads(ns.request.read_text(encoding="utf-8"))
    iteration = int(req["iteration"])
    if iteration < 1:
        raise RuntimeError("iteration must be positive")
    limit = min(max(30, ns.max_seconds), 600)
    tag = f"iter-{iteration:04d}"
    out_dir = CONV_DIR / tag
    model_iter = MODEL_DIR / "iterations" / f"{tag}.json"
    if out_dir.exists() or model_iter.exists():
        raise RuntimeError("iteration output already exists: " + tag)
    out_dir.mkdir(parents=True)
    model_iter.parent.mkdir(parents=True, exist_ok=True)
    current_model = MODEL_DIR / "current-model.json"
    header = A / "aimod.h"
    builder = A / "tooling" / "build_starter_model.py"
    remaining = max(30, limit - int(time.monotonic() - started))
    run([sys.executable, "-B", str(builder),
         "--corpus", str(CORPUS),
         "--out-json", str(current_model),
         "--out-h", str(header),
         "--iteration", str(iteration)], remaining)
    model_iter.write_bytes(current_model.read_bytes())
    BIN.parent.mkdir(parents=True, exist_ok=True)
    remaining = max(30, limit - int(time.monotonic() - started))
    run([sys.executable, "-B", str(COMP / "c48.py"),
         str(SRC), "-o", str(BIN)], remaining)
    prompts = req.get("prompts") or [
        "who are you",
        "tell me about the spectrum",
        "what happened in 1982",
        "what about 48k memory",
        "why does memory matter",
        "can you chat locally",
    ]
    if not isinstance(prompts, list) or len(prompts) > 24:
        raise RuntimeError("prompts must be a list of at most 24 strings")
    for p in prompts:
        if not isinstance(p, str) or not p or len(p) > 160:
            raise RuntimeError("invalid prompt")
        p.encode("ascii")
    program = read(BIN)
    font = Font4x8.load(COMP / "assets" / "font4x8-tasword.bin")
    screen = TraceScreen(font)
    feeder = Feeder(screen, prompts)
    vm = RomMathVM(program, screen,
                   argv=[str(BIN)],
                   heap_size=0,
                   max_steps=2000000,
                   input_provider=feeder)
    feeder.vm = vm
    status = vm.run()
    if status != 0:
        raise RuntimeError(f"ailmzx48 exited with status {status}")
    final_raw = bytes(screen.trace[feeder.last:])
    if final_raw:
        feeder.events.append({
            "kind": "final",
            "raw_hex": final_raw.hex(),
            "text": final_raw.decode("ascii", errors="replace"),
            "diag": feeder.diag(),
        })
    if len(feeder.events) != len(prompts) + 1:
        raise RuntimeError("unexpected conversation boundary count")
    turns = []
    keyword_hits = 0
    expectations = req.get("expected_keywords")
    if expectations is None:
        expectations = [None] * len(prompts)
    if not isinstance(expectations, list):
        raise RuntimeError("expected_keywords must be a list")
    if len(expectations) != len(prompts):
        raise RuntimeError("expected_keywords length must match prompts")
    for expected in expectations:
        if expected is not None and not isinstance(expected, str):
            raise RuntimeError("expected keyword must be string or null")
    for i, prompt in enumerate(prompts):
        event = feeder.events[i + 1]
        reply = derived_reply(event["text"])
        expected = expectations[i] if i < len(expectations) else None
        hit = expected is None or expected in reply.lower()
        if hit:
            keyword_hits += 1
        turns.append({
            "turn": i + 1,
            "user": prompt,
            "assistant_raw": event["text"],
            "assistant": reply,
            "diag": event["diag"],
            "expected_keyword": expected,
            "keyword_hit": hit,
        })
    transcript = {
        "schema": 1,
        "iteration": iteration,
        "request": req,
        "startup_raw": feeder.events[0]["text"],
        "turns": turns,
        "exit_status": status,
        "final_diag": feeder.diag(),
        "exact_output_hex": bytes(screen.trace).hex(),
    }
    (out_dir / "transcript.json").write_text(
        json.dumps(transcript, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    md = [MD_HEADER, f"# ailmzx48 {tag} conversation\n",
          "## Startup\n", "```text", feeder.events[0]["text"],
          "```\n"]
    for turn in turns:
        md.extend([
            f"## Turn {turn['turn']}",
            "", f"User: {turn['user']}", "",
            "```text", turn["assistant_raw"], "```", "",
        ])
    (out_dir / "conversation.md").write_text(
        "\n".join(md), encoding="utf-8")
    score = {
        "iteration": iteration,
        "turns": len(turns),
        "keyword_hits": keyword_hits,
        "keyword_total": len(turns),
        "keyword_ratio": keyword_hits / len(turns),
        "clean_exit": status == 0,
        "beep_calls": feeder.diag().get("ai_beeps"),
        "accepted_turns": feeder.diag().get("ai_turns"),
    }
    (out_dir / "score.json").write_text(
        json.dumps(score, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    run_meta = {
        "schema": 1,
        "iteration": iteration,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "source_sha256": sha(SRC),
        "corpus_sha256": sha(CORPUS),
        "model_sha256": sha(current_model),
        "model_header_sha256": sha(header),
        "c48b_sha256": sha(BIN),
        "heap_size": 0,
        "max_steps": 2000000,
        "runner_max_seconds": limit,
    }
    (out_dir / "run.json").write_text(
        json.dumps(run_meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(score, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
