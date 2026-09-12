#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '1deae0706dc731540c41134ee38ac035734a83d4'
BASE_TREE = '0167a8d5fb35780777df38555e0a188411d630d8'
DOCX = ROOT / 'doc/ZX-UX C48 SDK User Manual.docx'
BASE_DOCX_SHA256 = '43aebd4543c7859e01868f2bc62b6ab60371c18b4b02c2e60e11f3629829a669'
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


def api(method: str, endpoint: str, payload: dict) -> dict:
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo:
        die('GITHUB_TOKEN/GITHUB_REPOSITORY unavailable')
    req = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/{endpoint}',
        data=json.dumps(payload, separators=(',', ':')).encode('utf-8'),
        method=method,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


prep_sha = output('git', 'rev-parse', 'HEAD')
if output('git', 'merge-base', '--is-ancestor', BASELINE, 'HEAD') not in ('',):
    die('baseline is not an ancestor of preparation commit')
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

entries = []
for line in output('git', 'diff', '--name-status', BASELINE, 'HEAD').splitlines():
    status, path = line.split('\t', 1)
    if status.startswith('D'):
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': None})
        continue
    if status[0] not in 'AM':
        die(f'unexpected diff status {status} for {path}')
    mode = output('git', 'ls-tree', 'HEAD', '--', path).split()[0]
    data = (ROOT / path).read_bytes()
    blob = api('POST', 'git/blobs', {
        'content': base64.b64encode(data).decode('ascii'),
        'encoding': 'base64',
    })
    expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob.get('sha') != expected:
        die(f'blob SHA mismatch for {path}: {blob.get("sha")} != {expected}')
    entries.append({'path': path, 'mode': mode, 'type': 'blob', 'sha': expected})

remote_tree = api('POST', 'git/trees', {'base_tree': BASE_TREE, 'tree': entries})
remote_commit = api('POST', 'git/commits', {
    'message': 'Freeze C48 SDK 1.0.0-RC1 candidate',
    'tree': remote_tree['sha'],
    'parents': [prep_sha],
})
print('RC1_REMOTE_TREE_SHA=' + remote_tree['sha'])
print('RC1_REMOTE_CANDIDATE_SHA=' + remote_commit['sha'])
print('RC1 OBJECT PREPARATION PASS')
