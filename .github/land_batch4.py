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

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
SCRIPT = Path('.github/land_batch4.py')
WORKFLOW = Path('.github/workflows/land-batch4.yml')
ARGV_SRC = Path('usr/src/examples/argv.c')
ARGV_BIN = Path('usr/bin/examples/argv.c48b')
EXPECT = Path('compiler/release_expectations.json')
README = Path('README.md')


def run(args, *, timeout=1800):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def read_text(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write_text(path, text):
    (ROOT / path).write_text(text, encoding='utf-8', newline='\n')


def replace_once(path, old, new, label):
    text = read_text(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: anchor count {count}')
    write_text(path, text.replace(old, new, 1))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def patch():
    replace_once(
        ARGV_SRC,
        'char *a_sample[17] = {',
        'char *a_sample[15] = {',
        'argv sample bound',
    )
    replace_once(
        ARGV_SRC,
        '    "in fog. ",\n    "",\n    ""\n};',
        '    "in fog. "\n};',
        'argv unreachable empty entries',
    )

    old = '''`usr/src/c48host.h` is the **Host Game API profile** used for practical development before the final native `<c48.h>` prototype surface is frozen by ZX-UX Phase 11.\n\nIt exposes useful host-side calls for text, graphics, UDGs, memory/string operations, and related experiments. The file is intentionally labeled as a host profile and must not be mistaken for the final native ZX-UX ABI.\n\nSee `docs/ZX-UX C48 SDK Technical Reference.docx` for the host/native divergence and conformance boundaries.\n'''
    new = '''`usr/src/c48host.h` is the **Host Game API profile** used for practical development before the final native `<c48.h>` prototype surface is frozen by ZX-UX Phase 11.\n\nIt exposes useful host-side calls for text, graphics, UDGs, memory/string operations, and related experiments. The file is intentionally labeled as a host profile and must not be mistaken for the final native ZX-UX ABI.\n\nFor this development-only host profile, integer-returning service calls use `0` for success and a nonzero status for failure. Screen, graphics, and UDG argument validation commonly returns `1`; `beep()` additionally uses host-side values `1` for invalid arguments, `5` for playback or I/O failure, and `14` when no audible host backend is available. These values describe the SDK host runtime only. They do not freeze or claim the final native ZX-UX P11.41 `<c48.h>` ABI or its error convention.\n\nSee `docs/ZX-UX C48 SDK Technical Reference.docx` for the host/native divergence and conformance boundaries.\n'''
    replace_once(README, old, new, 'host API return convention')


def rebuild_and_freeze():
    run([
        sys.executable, '-B', 'compiler/c48.py', str(ARGV_SRC),
        '-o', str(ARGV_BIN),
    ])
    data = json.loads((ROOT / EXPECT).read_text(encoding='ascii'))
    data['demos']['argv']['source_sha256'] = sha(ARGV_SRC)
    data['demos']['argv']['binary_sha256'] = sha(ARGV_BIN)
    (ROOT / EXPECT).write_text(
        json.dumps(data, indent=2) + '\n', encoding='ascii', newline='\n'
    )


def target_checks():
    source = read_text(ARGV_SRC)
    if 'char *a_sample[15] = {' not in source:
        raise SystemExit('argv sample bound was not updated')
    if '\n    "",\n    ""\n};' in source:
        raise SystemExit('unreachable argv entries remain')
    if 'These values describe the SDK host runtime only.' not in read_text(README):
        raise SystemExit('host-only return convention clarification missing')
    expectations = json.loads((ROOT / EXPECT).read_text(encoding='ascii'))
    argv = expectations['demos']['argv']
    if argv['source_sha256'] != sha(ARGV_SRC):
        raise SystemExit('argv source hash not frozen')
    if argv['binary_sha256'] != sha(ARGV_BIN):
        raise SystemExit('argv binary hash not frozen')
    with tempfile.TemporaryDirectory(prefix='batch4-argv-') as td:
        rebuilt = Path(td) / 'argv.c48b'
        run([
            sys.executable, '-B', 'compiler/c48.py', str(ARGV_SRC),
            '-o', str(rebuilt),
        ])
        if rebuilt.read_bytes() != (ROOT / ARGV_BIN).read_bytes():
            raise SystemExit('argv deterministic rebuild mismatch')
    print('BATCH-4 TARGET CHECKS PASS', flush=True)


def c48_source_scan():
    count = 0
    for path in sorted((ROOT / 'usr/src').rglob('*')):
        if not path.is_file() or path.suffix.lower() not in {'.c', '.h'}:
            continue
        data = path.read_bytes()
        try:
            data.decode('ascii')
        except UnicodeDecodeError as exc:
            raise SystemExit(f'non-ASCII C48 source {path}: {exc}') from exc
        for line_no, line in enumerate(data.splitlines(), 1):
            count += 1
            if b'\r' in line:
                raise SystemExit(f'CR in C48 source {path}:{line_no}')
            if len(line) > 64:
                raise SystemExit(
                    f'C48 source over 64 columns {path}:{line_no}={len(line)}'
                )
    print(f'C48 SOURCE BYTE-LINE SCAN PASS lines={count}', flush=True)


def tracked_byte_scan(pass_no, baseline=None):
    names = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=ROOT
    ).split(b'\0')
    snapshot = {}
    files = lines = total = 0
    for raw in names:
        if not raw:
            continue
        rel = raw.decode('utf-8')
        path = ROOT / rel
        if not path.is_file():
            continue
        h = hashlib.sha256()
        nbytes = nlines = 0
        with path.open('rb') as stream:
            while True:
                line = stream.readline()
                if line == b'':
                    break
                h.update(line)
                nbytes += len(line)
                nlines += 1
        snapshot[rel] = (h.hexdigest(), nbytes, nlines)
        files += 1
        lines += nlines
        total += nbytes
    if baseline is not None and snapshot != baseline:
        changed = sorted(
            set(snapshot) ^ set(baseline)
            | {p for p in set(snapshot) & set(baseline) if snapshot[p] != baseline[p]}
        )
        raise SystemExit(
            f'SoP scan {pass_no}: tracked bytes changed between scans: {changed}'
        )
    print(
        f'SoP TRACKED BYTE-LINE SCAN {pass_no} PASS '
        f'files={files} lines={lines} bytes={total}',
        flush=True,
    )
    return snapshot


def verify_all():
    target_checks()
    c48_source_scan()
    run([sys.executable, '-B', 'compiler/verify_release.py'])
    run(['git', 'diff', '--check'])


def expected_diff_check():
    allowed = {
        '.github/land_batch4.py',
        '.github/workflows/land-batch4.yml',
        'README.md',
        'compiler/release_expectations.json',
        'usr/bin/examples/argv.c48b',
        'usr/src/examples/argv.c',
    }
    out = subprocess.check_output(
        ['git', 'status', '--short'], cwd=ROOT, text=True
    )
    seen = {line[3:] for line in out.splitlines() if line.strip()}
    if seen != allowed:
        raise SystemExit(f'unexpected Batch-4 diff paths: {sorted(seen)}')
    print('BATCH-4 DIFF SCOPE PASS', flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    if mode not in {'verify', 'land'}:
        raise SystemExit('usage: land_batch4.py [verify|land]')
    patch()
    rebuild_and_freeze()
    if mode == 'verify':
        verify_all()
        return

    (ROOT / SCRIPT).unlink()
    (ROOT / WORKFLOW).unlink()
    verify_all()
    expected_diff_check()

    baseline = tracked_byte_scan(1)
    tracked_byte_scan(2, baseline)
    tracked_byte_scan(3, baseline)

    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run([
        'git', 'config', 'user.email',
        '41898282+github-actions[bot]@users.noreply.github.com',
    ])
    run(['git', 'add', '-A'])
    run(['git', 'commit', '-m', 'fix: apply Batch-4 source review cleanup'])
    run(['git', 'push', 'origin', 'HEAD:main'])


if __name__ == '__main__':
    main()
