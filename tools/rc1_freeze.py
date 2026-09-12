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
STAGING = [
    ROOT / '.github/workflows/apply-rc1-freeze.yml',
    ROOT / 'tools/rc1_freeze.py',
    ROOT / 'tools/.rc1_payload_patch',
    ROOT / 'tools/.rc1_payload_core',
    ROOT / 'tools/.rc1_payload_document',
    ROOT / 'tools/.rc1_payload_footer',
]
BASELINE = os.environ.get('RC1_BASELINE', '1deae0706dc731540c41134ee38ac035734a83d4')
DOCX = ROOT / 'doc/ZX-UX C48 SDK User Manual.docx'
BASE_DOCX_SHA256 = '43aebd4543c7859e01868f2bc62b6ab60371c18b4b02c2e60e11f3629829a669'


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


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


parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^'], cwd=ROOT, text=True).strip()
if parent != BASELINE:
    die(f'preparation commit parent {parent} != expected {BASELINE}')
if (ROOT / 'VERSION').read_text(encoding='ascii').strip() != '0.9.0-dev':
    die('baseline VERSION is not 0.9.0-dev')
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
if os.environ.get('RC1_FREEZE_NO_PUSH') != '1':
    run('git', 'push', 'origin', 'HEAD:main')
print('RC1 FREEZE PASS:', subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
