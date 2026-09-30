# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import hashlib

SOURCE_SIZE = 30 * 1024
PAYLOAD_SIZE = 30000


def generate_large_native_source() -> bytes:
    body = (
        'char payload[30001]="' + ("Z" * PAYLOAD_SIZE) + '";'
        "int main(void){"
        "if(payload[0]!='Z')return 1;"
        "if(payload[29999]!='Z')return 2;"
        "return 0;}"
    ).encode("ascii")
    if len(body) >= SOURCE_SIZE:
        raise AssertionError("large native fixture body exceeds fixed source size")
    source = body + b" " * (SOURCE_SIZE - len(body) - 1) + b"\n"
    if len(source) != SOURCE_SIZE:
        raise AssertionError("large native fixture source size drift")
    return source


def source_sha256() -> str:
    return hashlib.sha256(generate_large_native_source()).hexdigest()
