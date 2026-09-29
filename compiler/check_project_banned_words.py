# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Generic hook for an externally supplied project-content policy.

The repository intentionally carries no prohibited vocabulary, encoded
reconstruction, hashes, or equivalent rule material. Release execution
supplies the active rule set ephemerally outside the tracked tree.
"""
from __future__ import annotations
from pathlib import Path

class PolicyContextUnavailable(RuntimeError):
    pass

def check_tree(root: Path, *, terms: tuple[bytes, ...] | None = None) -> list[str]:
    if terms is None:
        raise PolicyContextUnavailable("external project-content policy context is required")
    errors=[]
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {".git","__pycache__",".pytest_cache"} for part in path.parts): continue
        rel=path.relative_to(root).as_posix(); path_bytes=rel.encode("utf-8").lower(); data=path.read_bytes().lower()
        for index,term in enumerate(terms,1):
            if term in path_bytes or term in data: errors.append(f"policy match #{index}: {rel}")
    return errors
