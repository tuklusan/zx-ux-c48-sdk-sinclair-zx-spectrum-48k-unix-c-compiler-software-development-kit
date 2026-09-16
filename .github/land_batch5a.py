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
SCRIPT = Path('.github/land_batch5a.py')
WORKFLOW = Path('.github/workflows/land-batch5a.yml')
DEMO = Path('usr/src/demos/demoapi.h')
MOBIUS = Path('usr/src/demos/mobius.c')
FIREWORK = Path('usr/src/demos/firework.c')
TEST = Path('compiler/tests/test_graphics_review.py')
EXPECT = Path('compiler/graphics_demo_expectations.json')
RELEASE = Path('compiler/release_expectations.json')
MANIFEST = Path('MANIFEST.sha256')


def run(args, cwd=None, timeout=1800):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(args, cwd=cwd or ROOT, check=True, timeout=timeout)


def text(path, root=ROOT):
    return (root / path).read_text(encoding='utf-8')


def write(path, value, root=ROOT):
    (root / path).write_text(value, encoding='utf-8', newline='\n')


def sha(path, root=ROOT):
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def rep(path, old, new, label):
    value = text(path)
    count = value.count(old)
    if count != 1:
        raise SystemExit(f'{label}: anchor count {count}')
    write(path, value.replace(old, new, 1))


def patch_sources():
    helper = '''int d_muldiv(int value, int scale, int div)
{
    int neg;
    int n;
    int chunk;
    int rem;
    int out;
    int prod;
    if (div <= 0 || scale < 0) return 0;
    neg = 0;
    if (value < 0) {
        neg = 1;
        n = -value;
    }
    else
        n = value;
    rem = 0;
    out = 0;
    while (n > 0) {
        chunk = n;
        if (chunk > 16) chunk = 16;
        prod = chunk * scale + rem;
        out = out + prod / div;
        rem = prod % div;
        n = n - chunk;
    }
    if (neg) return -out;
    return out;
}

'''
    rep(
        DEMO,
        'int d_px(int x, int z)\n{\n',
        helper + 'int d_px(int x, int z)\n{\n',
        'safe projection helper',
    )
    rep(
        DEMO,
        '    return 128 + x * 220 / q;\n',
        '    return 128 + d_muldiv(x, 220, q);\n',
        'safe d_px',
    )
    rep(
        DEMO,
        '    return 96 + y * 220 / q;\n',
        '    return 96 + d_muldiv(y, 220, q);\n',
        'safe d_py',
    )
    rep(
        MOBIUS,
        '        u2 = (i + 1) * 256 / 20;\n'
        '        if (i == 19) u2 = 0;\n',
        '        u2 = (i + 1) * 256 / 20;\n',
        'Mobius full-turn seam',
    )
    rep(
        FIREWORK,
        '        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n'
        '            y1 < 184 && y2 < 184) {\n',
        '        if (d_ok(x1, y1) && d_ok(x2, y2) &&\n'
        '            y1 >= 16 && y1 < 184 &&\n'
        '            y2 >= 16 && y2 < 184) {\n',
        'firework burst label guard',
    )
    rep(
        FIREWORK,
        '        draw(x, 0, x, 18 + ((x * 7) % 30));\n',
        '        draw(x, 16, x, 18 + ((x * 7) % 30));\n',
        'firework sky label guard',
    )


def add_tests():
    content = '''# ============================================================================
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
"""Permanent regression probes for graphics review Batch-5A."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
SRC = SDK / "usr" / "src" / "demos"
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_file
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")


class GraphicsReviewBatch5ATests(unittest.TestCase):
    def test_mobius_seam_keeps_full_turn_endpoint(self):
        src = (SRC / "mobius.c").read_text(encoding="ascii")
        self.assertIn("u2 = (i + 1) * 256 / 20;", src)
        self.assertNotIn("if (i == 19) u2 = 0;", src)

    def test_firework_preserves_top_label_band(self):
        src = (SRC / "firework.c").read_text(encoding="ascii")
        self.assertIn("y1 >= 16 && y1 < 184", src)
        self.assertIn("y2 >= 16 && y2 < 184", src)
        self.assertIn("draw(x, 16, x, 18 +", src)
        self.assertNotIn("draw(x, 0, x, 18 +", src)

    def test_projection_muldiv_handles_large_goblet_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copy2(SRC / "demoapi.h", root / "demoapi.h")
            source = root / "probe.c"
            source.write_text(
                '#include "demoapi.h"\\n'
                'int main(void)\\n'
                '{\\n'
                '    if (d_px(154, 84) != 258) return 1;\\n'
                '    if (d_px(-154, 84) != -2) return 2;\\n'
                '    if (d_py(154, 84) != 226) return 3;\\n'
                '    if (d_py(-154, 84) != -34) return 4;\\n'
                '    return 0;\\n'
                '}\\n',
                encoding="ascii",
                newline="\\n",
            )
            program = compile_file(source)
            vm = C48VM(program, ZXScreen(FONT), argv=["probe"])
            self.assertEqual(vm.run(), 0)


if __name__ == "__main__":
    unittest.main()
'''
    if (ROOT / TEST).exists():
        raise SystemExit(f'{TEST} already exists')
    write(TEST, content)


def update_test_count():
    data = json.loads((ROOT / RELEASE).read_text(encoding='ascii'))
    if data.get('test_count') != 342:
        raise SystemExit(
            f"unexpected pre-Batch-5A test count {data.get('test_count')}"
        )
    data['test_count'] = 345
    (ROOT / RELEASE).write_text(
        json.dumps(data, indent=2) + '\n', encoding='ascii', newline='\n'
    )


def png_rgb(width, height, rgb):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(rgb[y * stride:(y + 1) * stride])

    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack('>I', len(data)) + body
            + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
        )

    head = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', head)
        + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
        + chunk(b'IEND', b'')
    )


def regenerate_graphics(old_expect):
    sys.path.insert(0, str(ROOT / 'compiler'))
    import verify_graphics_demos as v

    expect = json.loads(json.dumps(old_expect))
    frames = []
    changed_visuals = set()
    changed_binaries = set()
    for name, exp in expect['demos'].items():
        old = old_expect['demos'][name]
        old_binary = old['binary_sha256']
        data = v.compile_bytes(name)
        (v.BIN / f'{name}.c48b').write_bytes(data)
        first = v.run_demo(name, 1, 15.0)
        screen = v.run_demo(name, int(exp['frames']), 15.0)
        rgb = screen.render_rgb()
        png = v.png_bytes(rgb)
        (v.IMG / f'{name}.png').write_bytes(png)
        lit, attrs = v.screen_metrics(screen)
        exp['source_sha256'] = v.sha(v.SRC / f'{name}.c')
        exp['binary_sha256'] = v.sha_bytes(data)
        exp['first_screen_sha256'] = v.sha_bytes(first.bytes())
        exp['screen_sha256'] = v.sha_bytes(screen.bytes())
        exp['png_sha256'] = v.sha_bytes(png)
        exp['lit_pixels'] = lit
        exp['attribute_values'] = attrs
        frames.append(rgb)
        if exp['binary_sha256'] != old_binary:
            changed_binaries.add(name)
        for key in (
            'first_screen_sha256', 'screen_sha256', 'png_sha256',
            'lit_pixels', 'attribute_values',
        ):
            if exp[key] != old[key]:
                changed_visuals.add(name)
    allowed_visuals = {'mobius', 'firework'}
    if not changed_visuals:
        raise SystemExit('Batch-5A produced no visual evidence change')
    if not changed_visuals <= allowed_visuals:
        raise SystemExit(
            'unexpected visual changes: '
            + ', '.join(sorted(changed_visuals - allowed_visuals))
        )
    if changed_visuals != allowed_visuals:
        raise SystemExit(
            'expected both Mobius and Firework visual evidence to change; got '
            + ', '.join(sorted(changed_visuals))
        )
    expect['helper_sha256'] = v.sha(v.SRC / 'demoapi.h')
    v.EXPECT_PATH.write_text(
        json.dumps(expect, indent=2) + '\n',
        encoding='ascii', newline='\n',
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
    (v.IMG / 'contact-sheet.png').write_bytes(
        png_rgb(width, height, bytes(sheet))
    )
    print(
        'BATCH-5A REGEN: binary changes='
        f'{len(changed_binaries)}/21 visual changes='
        + ','.join(sorted(changed_visuals)),
        flush=True,
    )


def rebuild_manifest(root=ROOT):
    names = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root
    ).split(b'\0')
    lines = []
    for raw in names:
        if not raw:
            continue
        rel = raw.decode('utf-8', 'surrogateescape')
        if rel == str(MANIFEST):
            continue
        path = root / rel
        if not path.is_file():
            raise SystemExit(f'tracked file missing for manifest: {rel}')
        data = path.read_bytes()
        if path.suffix.lower() == '.bat':
            data = data.replace(b'\r\n', b'\n')
        lines.append((rel, hashlib.sha256(data).hexdigest()))
    (root / MANIFEST).write_text(
        ''.join(f'{digest}  {rel}\n' for rel, digest in sorted(lines)),
        encoding='ascii', newline='\n',
    )


def target_checks(root=ROOT):
    demo = text(DEMO, root)
    mobius = text(MOBIUS, root)
    firework = text(FIREWORK, root)
    if 'int d_muldiv(int value, int scale, int div)' not in demo:
        raise SystemExit('missing d_muldiv')
    if 'x * 220 / q' in demo or 'y * 220 / q' in demo:
        raise SystemExit('unsafe perspective multiply remains')
    if 'if (i == 19) u2 = 0;' in mobius:
        raise SystemExit('stale Mobius seam collapse remains')
    if 'y1 >= 16 && y1 < 184' not in firework:
        raise SystemExit('firework y1 label guard missing')
    if 'y2 >= 16 && y2 < 184' not in firework:
        raise SystemExit('firework y2 label guard missing')
    if 'draw(x, 16, x, 18 +' not in firework:
        raise SystemExit('firework sky label guard missing')
    if 'draw(x, 0, x, 18 +' in firework:
        raise SystemExit('firework sky still overwrites label band')
    exp = json.loads((root / EXPECT).read_text(encoding='ascii'))
    if exp.get('helper_sha256') != sha(DEMO, root):
        raise SystemExit('graphics helper hash not frozen')
    rel = json.loads((root / RELEASE).read_text(encoding='ascii'))
    if rel.get('test_count') != 345:
        raise SystemExit('Batch-5A test count not frozen at 345')
    print('BATCH-5A TARGET CHECKS PASS', flush=True)


def c48_source_scan(root=ROOT):
    count = 0
    for path in sorted((root / 'usr/src').rglob('*')):
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


def verify_all():
    target_checks()
    c48_source_scan()
    run([
        sys.executable, '-B', '-m', 'unittest', 'discover',
        '-s', 'compiler/tests', '-p', 'test_graphics_review.py', '-v',
    ])
    run([sys.executable, '-B', 'compiler/verify_graphics_demos.py', '--release'])
    run([sys.executable, '-B', 'compiler/verify_release.py'])
    run(['git', 'diff', '--check'])


def diff_scope_check():
    out = subprocess.check_output(
        ['git', 'status', '--short'], cwd=ROOT, text=True
    )
    seen = {line[3:] for line in out.splitlines() if line.strip()}
    required = {
        str(SCRIPT), str(WORKFLOW), str(DEMO), str(MOBIUS),
        str(FIREWORK), str(TEST), str(EXPECT), str(RELEASE),
        str(MANIFEST), 'docs/images/demos/contact-sheet.png',
        'docs/images/demos/mobius.png',
        'docs/images/demos/firework.png',
    }
    missing = required - seen
    if missing:
        raise SystemExit(f'missing expected Batch-5A diff paths: {sorted(missing)}')
    allowed = set(required)
    allowed.update(
        str(p.relative_to(ROOT))
        for p in (ROOT / 'usr/bin/demos').glob('*.c48b')
    )
    unexpected = seen - allowed
    if unexpected:
        raise SystemExit(f'unexpected Batch-5A diff paths: {sorted(unexpected)}')
    print(f'BATCH-5A DIFF SCOPE PASS paths={len(seen)}', flush=True)


def byte_scan_fresh(root, pass_no, baseline=None):
    names = subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=root
    ).split(b'\0')
    snap = {}
    files = lines = total = 0
    for raw in names:
        if not raw:
            continue
        rel = raw.decode('utf-8', 'surrogateescape')
        path = root / rel
        if not path.is_file():
            raise SystemExit(f'SoP {pass_no}: missing tracked file {rel}')
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
        snap[rel] = (h.hexdigest(), nbytes, nlines)
        files += 1
        lines += nlines
        total += nbytes
    target_checks(root)
    c48_source_scan(root)
    manifest_text = (root / MANIFEST).read_text(encoding='ascii')
    for rel, (digest, _, _) in snap.items():
        if rel == str(MANIFEST):
            continue
        data = (root / rel).read_bytes()
        if (root / rel).suffix.lower() == '.bat':
            data = data.replace(b'\r\n', b'\n')
        md = hashlib.sha256(data).hexdigest()
        if f'{md}  {rel}\n' not in manifest_text:
            raise SystemExit(f'SoP {pass_no}: manifest mismatch {rel}')
    if baseline is not None and snap != baseline:
        raise SystemExit(f'SoP {pass_no}: fresh-copy bytes differ')
    print(
        f'SoP FRESH BYTE-LINE SCAN {pass_no} PASS '
        f'files={files} lines={lines} bytes={total}',
        flush=True,
    )
    return snap


def three_fresh_scans():
    baseline = None
    with tempfile.TemporaryDirectory(prefix='batch5a-sop-') as td:
        base = Path(td)
        for pass_no in (1, 2, 3):
            work = base / f'pass-{pass_no}'
            run(['git', 'worktree', 'add', '--detach', str(work), 'HEAD'])
            try:
                snap = byte_scan_fresh(work, pass_no, baseline)
                if baseline is None:
                    baseline = snap
            finally:
                run(['git', 'worktree', 'remove', '--force', str(work)])
    print('BATCH-5A SoP CERTIFIED: 3 successive fresh copies', flush=True)


def prepare():
    old_expect = json.loads((ROOT / EXPECT).read_text(encoding='ascii'))
    patch_sources()
    add_tests()
    update_test_count()
    regenerate_graphics(old_expect)
    rebuild_manifest()
    return old_expect


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    if mode not in {'verify', 'land'}:
        raise SystemExit('usage: land_batch5a.py [verify|land]')
    prepare()
    verify_all()
    if mode == 'verify':
        return

    (ROOT / SCRIPT).unlink()
    (ROOT / WORKFLOW).unlink()
    rebuild_manifest()
    target_checks()
    c48_source_scan()
    run([sys.executable, '-B', 'compiler/verify_release.py'])
    run(['git', 'diff', '--check'])
    diff_scope_check()

    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run([
        'git', 'config', 'user.email',
        '41898282+github-actions[bot]@users.noreply.github.com',
    ])
    run(['git', 'add', '-A'])
    run(['git', 'commit', '-m', 'fix: harden Batch-5A graphics demos'])
    three_fresh_scans()
    run(['git', 'push', 'origin', 'HEAD:main'])


if __name__ == '__main__':
    main()
