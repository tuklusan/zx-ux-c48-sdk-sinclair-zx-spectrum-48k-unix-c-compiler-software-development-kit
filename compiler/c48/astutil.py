# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from typing import Any


def pos_dict(pos) -> dict[str, Any]:
    return {"source": pos.source, "line": pos.line, "column": pos.column}


def node(kind: str, pos, **kw) -> dict[str, Any]:
    d: dict[str, Any] = {"kind": kind, "pos": pos_dict(pos)}
    d.update(kw)
    return d
