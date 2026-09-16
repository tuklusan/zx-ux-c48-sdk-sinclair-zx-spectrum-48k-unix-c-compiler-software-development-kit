#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path.cwd()
HEADER = ROOT / 'usr/src/demos/demoapi.h'
BIN = ROOT / 'usr/bin/demos/mandel.c48b'
sys.path.insert(0, str(ROOT / 'compiler'))
import verify_graphics_demos as v

expect = json.loads((ROOT / 'compiler/graphics_demo_expectations.json').read_text())
frames = int(expect['demos']['mandel']['frames'])
want = expect['demos']['mandel']['screen_sha256']
old_header = HEADER.read_text(encoding='ascii')
old_bin = BIN.read_bytes()


def screen_hash():
    return v.sha_bytes(v.run_demo('mandel', frames, 15.0).bytes())


def compile_run(label):
    data = v.compile_bytes('mandel')
    BIN.write_bytes(data)
    got = screen_hash()
    print(f'{label}: screen={got} expected={want} equal={got == want}', flush=True)
    return got

base = screen_hash()
print(f'baseline: screen={base} expected={want} equal={base == want}', flush=True)
if base != want:
    raise SystemExit('baseline expectation mismatch before Batch-5A patch')

helper = '''int d_muldiv(int value, int scale, int div)\n{\n    int neg;\n    int n;\n    int chunk;\n    int rem;\n    int out;\n    int prod;\n    if (div <= 0 || scale < 0) return 0;\n    neg = 0;\n    if (value < 0) {\n        neg = 1;\n        n = -value;\n    }\n    else\n        n = value;\n    rem = 0;\n    out = 0;\n    while (n > 0) {\n        chunk = n;\n        if (chunk > 16) chunk = 16;\n        prod = chunk * scale + rem;\n        out = out + prod / div;\n        rem = prod % div;\n        n = n - chunk;\n    }\n    if (neg) return -out;\n    return out;\n}\n\n'''
anchor = 'int d_px(int x, int z)\n{\n'
if old_header.count(anchor) != 1:
    raise SystemExit('d_px anchor mismatch')
HEADER.write_text(old_header.replace(anchor, helper + anchor, 1), encoding='ascii', newline='\n')
helper_hash = compile_run('added-unused-helper-function')

HEADER.write_text(old_header, encoding='ascii', newline='\n')
BIN.write_bytes(old_bin)
old_px = '''int d_px(int x, int z)\n{\n    int q;\n    q = z + 176;\n    if (q < 32) q = 32;\n    return 128 + x * 220 / q;\n}\n'''
new_px = '''int d_px(int x, int z)\n{\n    int q;\n    int neg;\n    int n;\n    int chunk;\n    int rem;\n    int out;\n    int prod;\n    q = z + 176;\n    if (q < 32) q = 32;\n    neg = 0;\n    if (x < 0) { neg = 1; n = -x; }\n    else n = x;\n    rem = 0;\n    out = 0;\n    while (n > 0) {\n        chunk = n;\n        if (chunk > 16) chunk = 16;\n        prod = chunk * 220 + rem;\n        out = out + prod / q;\n        rem = prod % q;\n        n = n - chunk;\n    }\n    if (neg) out = -out;\n    return 128 + out;\n}\n'''
old_py = '''int d_py(int y, int z)\n{\n    int q;\n    q = z + 176;\n    if (q < 32) q = 32;\n    return 96 + y * 220 / q;\n}\n'''
new_py = '''int d_py(int y, int z)\n{\n    int q;\n    int neg;\n    int n;\n    int chunk;\n    int rem;\n    int out;\n    int prod;\n    q = z + 176;\n    if (q < 32) q = 32;\n    neg = 0;\n    if (y < 0) { neg = 1; n = -y; }\n    else n = y;\n    rem = 0;\n    out = 0;\n    while (n > 0) {\n        chunk = n;\n        if (chunk > 16) chunk = 16;\n        prod = chunk * 220 + rem;\n        out = out + prod / q;\n        rem = prod % q;\n        n = n - chunk;\n    }\n    if (neg) out = -out;\n    return 96 + out;\n}\n'''
value = old_header
if value.count(old_px) != 1 or value.count(old_py) != 1:
    raise SystemExit('projection body anchor mismatch')
value = value.replace(old_px, new_px, 1).replace(old_py, new_py, 1)
HEADER.write_text(value, encoding='ascii', newline='\n')
inline_hash = compile_run('same-function-count-inline-safe-projection')

HEADER.write_text(old_header, encoding='ascii', newline='\n')
BIN.write_bytes(old_bin)
print(f'result helper_changed={helper_hash != base} inline_changed={inline_hash != base}', flush=True)
