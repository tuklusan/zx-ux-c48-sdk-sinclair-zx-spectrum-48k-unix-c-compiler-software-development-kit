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
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
UPSTREAM_REPO = "tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project"
UPSTREAM_BRANCH = "main"
SPEC_RE = re.compile(
    r"^04-C48 Language Specification Rev ([0-9]+(?:\.[0-9]+)*)\.docx$"
)
PROVENANCE_NAME = "C48-SPECIFICATION.json"
MANIFEST_NAME = "MANIFEST.sha256"
OBSOLETE_SPEC = "docs/C48 Language Specification Rev 0.11.docx"
LOCAL_SPEC_STUB = "docs/ZX-UX C48 Language Specification.md"


def fail(message: str) -> None:
    raise SystemExit(f"PACKAGE FAIL: {message}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_tracked_bytes(path: Path) -> bytes:
    """Return bytes used both in the release ZIP and its manifest.

    Git may check batch files out with CRLF on Windows. Normalize those files
    to the repository's canonical LF form so archives are host-independent.
    Other files, including binary/container formats, remain byte-for-byte exact.
    """
    data = path.read_bytes()
    if path.suffix.lower() == ".bat":
        data = data.replace(b"\r\n", b"\n")
    return data


def request_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "zx-ux-c48-sdk-release-packager",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def request_json(url: str) -> object:
    try:
        return json.loads(request_bytes(url).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON from {url}: {exc}")
        raise AssertionError("unreachable") from exc


def revision_key(name: str) -> tuple[int, ...]:
    match = SPEC_RE.fullmatch(name)
    if not match:
        fail(f"not a C48 specification filename: {name}")
    return tuple(int(part) for part in match.group(1).split("."))


def fetch_latest_spec() -> tuple[bytes, dict[str, object]]:
    repo_api = f"https://api.github.com/repos/{UPSTREAM_REPO}"
    commit_obj = request_json(f"{repo_api}/commits/{UPSTREAM_BRANCH}")
    if not isinstance(commit_obj, dict) or not isinstance(commit_obj.get("sha"), str):
        fail("upstream commit lookup did not return a commit SHA")
    commit = commit_obj["sha"]

    docs_obj = request_json(f"{repo_api}/contents/docs?ref={commit}")
    if not isinstance(docs_obj, list):
        fail("upstream docs lookup did not return a directory listing")
    matches = [
        item for item in docs_obj
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and SPEC_RE.fullmatch(item["name"])
    ]
    if not matches:
        fail("no upstream docs/04-C48 Language Specification Rev *.docx found")

    latest = max(matches, key=lambda item: revision_key(str(item["name"])))
    name = str(latest["name"])
    path = str(latest.get("path") or f"docs/{name}")
    blob_sha = str(latest.get("sha") or "")
    encoded_path = urllib.parse.quote(path, safe="/")
    raw_url = (
        f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/"
        f"{commit}/{encoded_path}"
    )
    spec_bytes = request_bytes(raw_url)
    if not spec_bytes.startswith(b"PK\x03\x04"):
        fail(f"upstream C48 specification is not a DOCX/ZIP container: {path}")

    package_path = f"docs/{name}"
    metadata: dict[str, object] = {
        "schema": 1,
        "source_repository": UPSTREAM_REPO,
        "source_branch": UPSTREAM_BRANCH,
        "source_commit": commit,
        "source_path": path,
        "source_blob_sha": blob_sha,
        "sha256": sha256_bytes(spec_bytes),
        "package_path": package_path,
        "note": (
            "The upstream docs/04-C48 Language Specification Rev xx.docx "
            "filename is revisioned and may change. This package carries the "
            "latest matching revision discovered on upstream main when the "
            "package was built."
        ),
    }
    return spec_bytes, metadata


def tracked_entries() -> list[tuple[str, int]]:
    raw = subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"], cwd=SDK
    )
    entries: list[tuple[str, int]] = []
    stub_seen = False
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, raw_path = record.split(b"\t", 1)
        mode, _oid, stage = meta.decode("ascii").split()
        if stage != "0":
            fail(f"unmerged path in release tree: {raw_path!r}")
        path = raw_path.decode("utf-8", "surrogateescape")
        if mode not in {"100644", "100755"}:
            fail(f"unsupported release-tree mode {mode}: {path}")
        if path == LOCAL_SPEC_STUB:
            stub_seen = True
            continue
        if path == OBSOLETE_SPEC:
            fail(f"obsolete local C48 specification is still tracked: {path}")
        if path.startswith("docs/04-C48 Language Specification Rev "):
            fail(f"canonical C48 specification must not be tracked here: {path}")
        if path == PROVENANCE_NAME:
            fail(f"generated package provenance must not be tracked: {path}")
        if path == MANIFEST_NAME:
            fail(f"generated package manifest must not be tracked: {path}")
        entries.append((path, int(mode[-3:], 8)))
    if not stub_seen:
        fail(f"source-tree C48 specification stub is not tracked: {LOCAL_SPEC_STUB}")
    return sorted(entries)


def build_archive(archive: Path, prefix: str) -> dict[str, object]:
    entries = tracked_entries()
    spec_bytes, spec_meta = fetch_latest_spec()
    spec_rel = str(spec_meta["package_path"])
    provenance_bytes = (
        json.dumps(spec_meta, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")

    package_manifest = {
        rel: sha256_bytes(canonical_tracked_bytes(SDK / rel))
        for rel, _perm in entries
    }
    package_manifest[spec_rel] = sha256_bytes(spec_bytes)
    package_manifest[PROVENANCE_NAME] = sha256_bytes(provenance_bytes)
    manifest_bytes = "".join(
        f"{digest}  {rel}\n" for rel, digest in sorted(package_manifest.items())
    ).encode("ascii")

    extras = {
        MANIFEST_NAME: (manifest_bytes, 0o644),
        spec_rel: (spec_bytes, 0o644),
        PROVENANCE_NAME: (provenance_bytes, 0o644),
    }
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for rel, perm in entries:
            data = canonical_tracked_bytes(SDK / rel)
            if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                fail(f"release archive would contain an LFS pointer: {rel}")
            info = zipfile.ZipInfo(prefix + rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100000 | perm) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(
                info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
        for rel, (data, perm) in sorted(extras.items()):
            info = zipfile.ZipInfo(prefix + rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100000 | perm) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(
                info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )

    return spec_meta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the C48 SDK release ZIP with the canonical upstream C48 spec."
    )
    parser.add_argument("--archive", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument(
        "--provenance-out",
        type=Path,
        help=(
            "optionally write C48 specification provenance outside the ZIP; "
            "omitted by default so a local packaging run does not dirty the SDK tree"
        ),
    )
    args = parser.parse_args()

    archive = Path(args.archive)
    if not archive.is_absolute():
        archive = SDK / archive
    spec_meta = build_archive(archive, args.prefix)
    if args.provenance_out is not None:
        provenance_out = args.provenance_out
        if not provenance_out.is_absolute():
            provenance_out = SDK / provenance_out
        provenance_out.parent.mkdir(parents=True, exist_ok=True)
        provenance_out.write_text(
            json.dumps(spec_meta, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(
        "C48 SPEC PACKAGE: "
        f"{spec_meta['source_path']} @ {spec_meta['source_commit']} "
        f"sha256={spec_meta['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
