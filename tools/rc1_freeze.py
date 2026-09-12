#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '1deae0706dc731540c41134ee38ac035734a83d4'
DOCX = ROOT / 'doc/ZX-UX C48 SDK User Manual.docx'
BASE_DOCX_SHA256 = '43aebd4543c7859e01868f2bc62b6ab60371c18b4b02c2e60e11f3629829a669'
TRANSPORT = ROOT / 'doc/.rc1-transport'
STAGING = [
    ROOT / '.github/workflows/apply-rc1-freeze.yml',
    ROOT / 'tools/rc1_freeze.py',
    ROOT / 'tools/.rc1_payload_patch',
    ROOT / 'tools/.rc1_payload_core',
    ROOT / 'tools/.rc1_payload_document',
    ROOT / 'tools/.rc1_payload_footer',
]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def output(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def die(message: str) -> None:
    raise SystemExit(f'RC1 FREEZE FAIL: {message}')


def decode_payload(name: str) -> bytes:
    data = (ROOT / f'tools/.rc1_payload_{name}').read_text(encoding='ascii')
    return zlib.decompress(base64.b64decode(data))


def manifest_sha(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() == '.bat':
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


prep_sha = output('git', 'rev-parse', 'HEAD')
run('git', 'merge-base', '--is-ancestor', BASELINE, 'HEAD')
if (ROOT / 'VERSION').read_text(encoding='ascii').strip() != '0.9.0-dev':
    die('preparation VERSION is not 0.9.0-dev')
if hashlib.sha256(DOCX.read_bytes()).hexdigest() != BASE_DOCX_SHA256:
    die('baseline SDK manual hash mismatch')

patch = decode_payload('patch')
with tempfile.NamedTemporaryFile(prefix='rc1-', suffix='.patch', delete=False) as f:
    f.write(patch)
    patch_path = Path(f.name)
try:
    run('git', 'apply', '--whitespace=nowarn', str(patch_path))
finally:
    patch_path.unlink(missing_ok=True)

replacement = {
    'docProps/core.xml': decode_payload('core'),
    'word/document.xml': decode_payload('document'),
    'word/footer1.xml': decode_payload('footer'),
}
with tempfile.NamedTemporaryFile(prefix='sdk-manual-', suffix='.docx', delete=False) as f:
    temp_docx = Path(f.name)
try:
    with zipfile.ZipFile(DOCX, 'r') as src, zipfile.ZipFile(temp_docx, 'w') as dst:
        for info in src.infolist():
            dst.writestr(info, replacement.get(info.filename, src.read(info.filename)))
    shutil.copymode(DOCX, temp_docx)
    os.replace(temp_docx, DOCX)
finally:
    temp_docx.unlink(missing_ok=True)

for path in STAGING:
    path.unlink(missing_ok=True)

members = sorted(
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob('*')
    if p.is_file() and p.name != 'MANIFEST.sha256' and '.git' not in p.relative_to(ROOT).parts
)
(ROOT / 'MANIFEST.sha256').write_text(
    ''.join(f'{manifest_sha(ROOT / rel)}  {rel}\n' for rel in members),
    encoding='ascii', newline='\n'
)

run('git', 'add', '-A')
run('git', '-c', 'user.name=Supratim Sanyal', '-c', 'user.email=tuklusan@users.noreply.github.com',
    'commit', '-m', 'Freeze C48 SDK 1.0.0-RC1 candidate')
run('python', '-B', 'compiler/verify_release.py')
verified_tree = output('git', 'rev-parse', 'HEAD^{tree}')
changed = [
    line.split('\t', 1)[1]
    for line in output('git', 'diff', '--name-status', BASELINE, 'HEAD').splitlines()
    if line and line[0] in 'AM'
]
if len(changed) != 21:
    die(f'expected 21 candidate file blobs, found {len(changed)}')

with tempfile.TemporaryDirectory(prefix='rc1-transport-') as td:
    cache = Path(td)
    for rel in changed:
        src = ROOT / rel
        dst = cache / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    run('git', 'reset', '--hard', prep_sha)
    if TRANSPORT.exists():
        shutil.rmtree(TRANSPORT)
    shutil.copytree(cache, TRANSPORT)

run('git', 'add', '-f', 'doc/.rc1-transport')
staged_raw = subprocess.check_output(
    ['git', 'diff', '--cached', '--name-only', '-z'], cwd=ROOT
)
staged = [
    item.decode('utf-8')
    for item in staged_raw.split(b'\0')
    if item
]
if not staged or any(not path.startswith('doc/.rc1-transport/') for path in staged):
    die('transport commit contains staged paths outside doc/.rc1-transport')
if len(staged) != len(changed):
    die(f'transport staged {len(staged)} files, expected {len(changed)}')
run('git', '-c', 'user.name=Supratim Sanyal', '-c', 'user.email=tuklusan@users.noreply.github.com',
    'commit', '-m', 'Transport audited RC1 blobs')
transport_sha = output('git', 'rev-parse', 'HEAD')
run('git', 'push', 'origin', 'HEAD:main')
print('RC1_VERIFIED_TREE_SHA=' + verified_tree)
print('RC1_TRANSPORT_COMMIT_SHA=' + transport_sha)
print('RC1 BLOB TRANSPORT PASS')
