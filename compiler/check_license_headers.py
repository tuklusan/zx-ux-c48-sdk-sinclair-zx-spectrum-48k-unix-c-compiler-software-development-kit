#!/usr/bin/env python3
# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

LINE1 = 'ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com'
LINE2 = 'SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information'
C_HEADER = '// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs\n// supratim-sanyal.blogspot.com\n//\n// SANYALnet Labs Non-Commercial License, attribution to\n// SANYALnet Labs required, see LICENSE for more information\n'
OFFICE_SUFFIXES = {'.accdb', '.doc', '.docm', '.docx', '.dot', '.dotm', '.dotx', '.mdb', '.mpp', '.mpt', '.msg', '.one', '.onetoc2', '.ost', '.pot', '.potm', '.potx', '.pps', '.ppsm', '.ppsx', '.ppt', '.pptm', '.pptx', '.pst', '.pub', '.vsd', '.vsdm', '.vsdx', '.vst', '.vstm', '.vstx', '.xlam', '.xls', '.xlsb', '.xlsm', '.xlsx', '.xlt', '.xltm', '.xltx'}
HEADER_SUFFIXES = {".py", ".c", ".h", ".md", ".txt", ".runbook", ".bat", ".yml", ".yaml"}
HEADER_NAMES = {"c48", "c48run", "c48srctap", ".gitignore", ".gitattributes"}
EXEMPT_NAMES = {"LICENSE", "VERSION", "MANIFEST.sha256", "C48-SPECIFICATION.json"}
EXEMPT_SUFFIXES = {".json", ".bin", ".dat", ".png", ".c48b", ".tap", ".zip", ".rom"}
PINNED = {
    'usr/src/apps/appapi.h',
    'usr/src/apps/gp82.c',
    'usr/src/apps/sheet48.c',
    'usr/src/apps/wire3d.c',
    'usr/src/apps/write48.c',
    'usr/src/demos/city.c',
    'usr/src/demos/demoapi.h',
    'usr/src/demos/dizzy4k.c',
    'usr/src/demos/firework.c',
    'usr/src/demos/forest.c',
    'usr/src/demos/galaxy.c',
    'usr/src/demos/goblet.c',
    'usr/src/demos/hanoi.c',
    'usr/src/demos/julia.c',
    'usr/src/demos/kaleido.c',
    'usr/src/demos/mandel.c',
    'usr/src/demos/mobius.c',
    'usr/src/demos/moire.c',
    'usr/src/demos/morph3d.c',
    'usr/src/demos/ocean.c',
    'usr/src/demos/orrery.c',
    'usr/src/demos/plasma.c',
    'usr/src/demos/queens8.c',
    'usr/src/demos/raymaze.c',
    'usr/src/demos/recapi.h',
    'usr/src/demos/spriteanim.c',
    'usr/src/demos/sprites.c',
    'usr/src/demos/terrain.c',
    'usr/src/demos/torus.c',
    'usr/src/demos/tunnel.c',
    'usr/src/demos/warp.c',
    'usr/src/examples/argv.c',
    'usr/src/examples/colors.c',
    'usr/src/examples/exapi.h',
    'usr/src/examples/graphics.c',
    'usr/src/examples/hello.c',
    'usr/src/examples/maze.c',
    'usr/src/examples/udg.c',
}

def classify(rel: str) -> str:
    path=Path(rel); suffix=path.suffix.lower()
    if rel in {"README.md", "LICENSE"}: return "root-exempt"
    if rel in PINNED: return "pinned"
    if rel.startswith("docs/reference/"): return "imported"
    if path.name in HEADER_NAMES or suffix in HEADER_SUFFIXES: return "header"
    if path.name in EXEMPT_NAMES or suffix in EXEMPT_SUFFIXES or suffix in OFFICE_SUFFIXES: return "exempt"
    return "unknown"

def _expected(rel: str) -> str:
    suffix=Path(rel).suffix.lower()
    if suffix in {".c",".h"}: return C_HEADER
    if suffix==".md": return f"<!--\n{LINE1}\n\n{LINE2}\n-->\n\n"
    if suffix==".bat": return f"REM {LINE1}\nREM\nREM {LINE2}\n"
    if suffix in {".txt",".runbook"}: return f"{LINE1}\n\n{LINE2}\n\n"
    return f"# {LINE1}\n#\n# {LINE2}\n"

def _iter_files(root: Path):
    for dirpath,dirnames,filenames in os.walk(root,topdown=True):
        dirnames[:]=sorted(d for d in dirnames if d not in {".git","__pycache__",".pytest_cache"})
        base=Path(dirpath)
        for name in sorted(filenames): yield base/name

def check_tree(root: Path) -> list[str]:
    errors=[]
    for path in _iter_files(root):
        rel=path.relative_to(root).as_posix(); kind=classify(rel)
        if kind=="unknown": errors.append(f"unclassified artifact: {rel}"); continue
        if kind!="header": continue
        try:text=path.read_text(encoding="utf-8").replace("\r\n","\n")
        except UnicodeError as exc: errors.append(f"header-governed file is not UTF-8: {rel}: {exc}"); continue
        body=text
        if path.suffix.lower()==".bat":
            if not body.lower().startswith("@echo off\n"): errors.append(f"Windows launcher preamble missing: {rel}"); continue
            body=body[10:]
        elif body.startswith("#!"):
            end=body.find("\n")
            if end<0: errors.append(f"shebang newline missing: {rel}"); continue
            body=body[end+1:]
        expected=_expected(rel)
        if not body.startswith(expected): errors.append(f"canonical header missing or not immediately after preamble: {rel}"); continue
        if path.suffix.lower() in {".c",".h"} and rel.startswith("usr/src/"):
            for lineno,line in enumerate(expected.splitlines(),1):
                if len(line.encode("utf-8"))>64: errors.append(f"C48 header line exceeds 64 bytes at line {lineno}: {rel}")
        if body.startswith(expected+expected): errors.append(f"duplicate canonical header: {rel}")
    return errors

def main(argv=None):
    ap=argparse.ArgumentParser(description="Enforce ZX-UX C48 SDK canonical license headers")
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parent.parent)
    ns=ap.parse_args(argv); errors=check_tree(ns.root.resolve())
    if errors:
        for error in errors: print(f"LICENSE HEADER ERROR: {error}",file=sys.stderr)
        return 1
    print("LICENSE HEADER PASS"); return 0

if __name__=="__main__": raise SystemExit(main())
