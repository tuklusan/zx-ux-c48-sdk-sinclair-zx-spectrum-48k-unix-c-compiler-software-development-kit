# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import hashlib

SOURCE_SIZE = 30 * 1024
CHUNK_SIZE = 7500
CHUNK_COUNT = 4


def generate_large_native_source() -> bytes:
    lines = [
        f'char payload{index}[{CHUNK_SIZE + 1}]="' + ("Z" * CHUNK_SIZE) + '";\n'
        for index in range(CHUNK_COUNT)
    ]
    lines.append(
        "int main(void){"
        "if(payload0[0]!='Z')return 1;"
        "if(payload1[7499]!='Z')return 2;"
        "if(payload2[0]!='Z')return 3;"
        "if(payload3[7499]!='Z')return 4;"
        "return 0;}\n"
    )
    body = "".join(lines).encode("ascii")
    remaining = SOURCE_SIZE - len(body)
    if remaining < 5:
        raise AssertionError("large native fixture body exceeds fixed source size")
    source = body + b"/*" + (b"P" * (remaining - 5)) + b"*/\n"
    if len(source) != SOURCE_SIZE:
        raise AssertionError("large native fixture source size drift")
    if max(len(line) for line in source.splitlines()) > 8192:
        raise AssertionError("large native fixture exceeds source-line safety ceiling")
    return source


def source_sha256() -> str:
    return hashlib.sha256(generate_large_native_source()).hexdigest()
