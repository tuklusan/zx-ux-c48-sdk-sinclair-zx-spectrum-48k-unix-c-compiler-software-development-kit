# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SDK = HERE.parent
sys.path.insert(0, str(HERE))

from c48.compiler import compile_bytes
from c48.native_backend import NativeBackend
from c48.native_format import (
    OBJ_SECTION_BSS,
    OBJ_SECTION_TEXT,
    OBJ_SECTION_UNDEF,
    OBJ_SYMBOL_GLOBAL,
    encode_mex1,
    encode_obj1,
)
from c48.native_link import link_mex
from c48.native_runtime import RUNTIME_MEMBERS

REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"
FIXTURE_BASE = 0xC000


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def run(argv: list[str | Path], *, cwd: Path, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        [str(item) for item in argv],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    require(cp.returncode == 0, f"command failed: {argv!r}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    return cp


def asm_bytes(data: bytes, indent: str = "    ") -> str:
    if not data:
        return indent + "db 0"
    lines = []
    for start in range(0, len(data), 20):
        chunk = data[start:start + 20]
        lines.append(indent + "db " + ",".join(f"$" + format(byte, "02X") for byte in chunk))
    return "\n".join(lines)


def name_field(name: str) -> str:
    raw = name.encode("ascii")
    require(1 <= len(raw) <= 15 and b"\0" not in raw, f"invalid linker proof symbol {name!r}")
    suffix = 16 - len(raw)
    return f'    db "{name}"\n    defs {suffix},0'


def symbol_address(path: Path, name: str) -> int:
    prefix = name.lower() + ":"
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.lower().startswith(prefix):
            parts = line.split()
            if len(parts) >= 3 and parts[1].lower() == "equ":
                return int(parts[2], 0)
    raise RuntimeError(f"missing fixture symbol {name}")


def align2(value: int) -> int:
    return (value + 1) & ~1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    ns = parser.parse_args()
    root = ns.native_root.resolve()
    require(run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip() == REFERENCE_COMMIT,
            "native reference commit drift")

    program = compile_bytes(
        b"int main(void){return 0;}",
        source_name="native-link.c",
        base_dir=SDK,
    )
    user = NativeBackend(program).build()
    startup = next(member for member in RUNTIME_MEMBERS if member.name == "startup")
    exit_member = next(member for member in RUNTIME_MEMBERS if member.name == "exit")
    runtime = tuple(member for member in RUNTIME_MEMBERS if member.name != "startup")
    host_mex = link_mex([("startup", startup.obj), ("user", user)], runtime, min_stack=1024)
    host_bytes = encode_mex1(host_mex)

    modules = (("startup", startup.obj), ("user", user), ("exit", exit_member.obj))
    expected_text_bases: list[int] = []
    expected_bss_bases: list[int] = []
    text_cursor = 0
    bss_cursor = 0
    for _, obj in modules:
        text_cursor = align2(text_cursor)
        bss_cursor = align2(bss_cursor)
        expected_text_bases.append(text_cursor)
        expected_bss_bases.append(bss_cursor)
        text_cursor += len(obj.text)
        bss_cursor += obj.bss_size
    require(align2(text_cursor) == len(host_mex.image), "host/native TEXT layout contract drift")
    require(align2(bss_cursor) == host_mex.bss_size, "host/native BSS layout contract drift")

    defs: list[tuple[str, int, int, int, int]] = []
    for module_index, (_, obj) in enumerate(modules):
        for sym in obj.symbols:
            if sym.section == OBJ_SECTION_UNDEF or not (sym.flags & OBJ_SYMBOL_GLOBAL):
                continue
            defs.append((
                sym.name,
                sym.value,
                sym.section,
                expected_text_bases[module_index],
                expected_bss_bases[module_index],
            ))
    names = [item[0] for item in defs]
    require(names == ["_start", "main", "exit"], f"unexpected proof definition set: {names}")

    relocation_cases: list[tuple[int, str | None, int, int | None, int | None]] = []
    total_text = len(host_mex.image)
    for module_index, (_, obj) in enumerate(modules):
        for rel in obj.relocs:
            sym = obj.symbols[rel.symbol]
            patch = expected_text_bases[module_index] + rel.offset
            addend_raw = int.from_bytes(obj.text[rel.offset:rel.offset + 2], "little")
            addend = addend_raw - 0x10000 if addend_raw & 0x8000 else addend_raw
            if sym.section == OBJ_SECTION_UNDEF:
                require(bool(sym.flags & OBJ_SYMBOL_GLOBAL),
                        "undefined proof relocation must be global")
                relocation_cases.append((patch, sym.name, addend, None, None))
            elif sym.section == OBJ_SECTION_TEXT:
                relocation_cases.append((
                    patch, None, addend,
                    expected_text_bases[module_index] + sym.value,
                    OBJ_SECTION_TEXT,
                ))
            elif sym.section == OBJ_SECTION_BSS:
                relocation_cases.append((
                    patch, None, addend,
                    total_text + expected_bss_bases[module_index] + sym.value,
                    OBJ_SECTION_BSS,
                ))
            else:
                relocation_cases.append((patch, None, addend, sym.value, sym.section))
    require(len(relocation_cases) <= 8, "native proof exceeds pinned relocation fixture capacity")

    obj_records = []
    copy_records = []
    for index, (_, obj) in enumerate(modules):
        raw = encode_obj1(obj)
        obj_records.append(f"p_obj{index}:\n{asm_bytes(raw)}\np_obj{index}_end:")
        base = expected_text_bases[index]
        copy_records.append(
            f"    ld hl,p_obj{index}+24\n"
            f"    ld de,p_image+{base}\n"
            f"    ld bc,{len(obj.text)}\n"
            "    ldir"
        )

    def_records = []
    for name, value, section, text_base, bss_base in defs:
        def_records.append(
            name_field(name)
            + f"\n    dw {value}\n    db {section}\n    dw {text_base}\n    dw {bss_base}"
        )

    query_records = []
    query_labels: dict[str, str] = {}
    for index, name in enumerate(sorted({name for _, name, _, _, _ in relocation_cases if name is not None})):
        label = f"p_query{index}"
        query_labels[name] = label
        query_records.append(f"{label}:\n{name_field(name)}")

    validate_calls = []
    for index in range(len(modules)):
        validate_calls.append(
            f"    ld hl,p_obj{index}\n"
            f"    ld bc,p_obj{index}_end-p_obj{index}\n"
            "    call ld_p1021_validate_memory\n"
            "    ret c"
        )

    reloc_calls = []
    for patch, name, addend, direct_value, direct_section in relocation_cases:
        if name is not None:
            resolve = (
                f"    ld hl,{query_labels[name]}\n"
                "    ld de,p_defs\n"
                f"    ld b,{len(defs)}\n"
                "    call ld_p1025_resolve\n"
                "    ret c\n"
                "    ld hl,(ld_p1025_resolved_value)\n"
                "    ld (ld_p1026_symbol_value),hl\n"
                "    ld a,(ld_p1025_resolved_section)\n"
                "    ld (ld_p1026_symbol_section),a\n"
            )
        else:
            require(direct_value is not None and direct_section is not None,
                    "direct relocation proof metadata is incomplete")
            resolve = (
                f"    ld hl,{direct_value}\n"
                "    ld (ld_p1026_symbol_value),hl\n"
                f"    ld a,{direct_section}\n"
                "    ld (ld_p1026_symbol_section),a\n"
            )
        reloc_calls.append(
            resolve
            + f"    ld hl,{patch}\n"
            "    ld (ld_p1026_patch_loc),hl\n"
            f"    ld hl,{addend & 0xFFFF}\n"
            "    ld (ld_p1026_addend),hl\n"
            "    call ld_p1026_apply\n"
            "    ret c"
        )

    size_words = "\n".join(
        f"    dw {len(obj.text)},{obj.bss_size}" for _, obj in modules
    )
    text_base_bytes = b"".join(value.to_bytes(2, "little") for value in expected_text_bases)
    bss_base_bytes = b"".join(value.to_bytes(2, "little") for value in expected_bss_bases)

    asm = f"""    DEVICE ZXSPECTRUM48
    INCLUDE "{(root / 'v1/include/zx48ux.inc').as_posix()}"
    INCLUDE "{(root / 'tools/ld.asm').as_posix()}"
    ORG $C000
fixture:
    EMIT_P10_LD_INPUT_LOADER
    EMIT_P10_LD_LAYOUT_ROUTINES
    EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES
    EMIT_P10_LD_RELOCATION_ROUTINES
    EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES
    EMIT_P10_LD_STACK_OPTION_ROUTINES
    EMIT_P10_LD_HEAP_OPTION_ROUTINES
    EMIT_P10_LD_MEX1_WRITER_ROUTINES

p_sizes:
{size_words}
p_defs:
{chr(10).join(def_records)}
{chr(10).join(query_records)}
{chr(10).join(obj_records)}
p_expected_text:
{asm_bytes(text_base_bytes)}
p_expected_bss:
{asm_bytes(bss_base_bytes)}
p_host_mex:
{asm_bytes(host_bytes)}
p_host_mex_end:
p_image: defs {len(host_mex.image)},0
p_out: defs {len(host_bytes) + 16},0

p_fail:
    ld a,E_FORMAT
    scf
    ret

p_compare_layout:
    ld hl,(ld_p1024_image_size)
    ld de,{len(host_mex.image)}
    or a
    sbc hl,de
    jp nz,p_fail
    ld hl,(ld_p1024_heap_base)
    ld de,{host_mex.bss_size}
    or a
    sbc hl,de
    jp nz,p_fail
    ld hl,ld_p1024_text_bases
    ld de,p_expected_text
    ld b,{2 * len(modules)}
p_text_loop:
    ld a,(de)
    cp (hl)
    jp nz,p_fail
    inc de
    inc hl
    djnz p_text_loop
    ld hl,ld_p1024_bss_bases
    ld de,p_expected_bss
    ld b,{2 * len(modules)}
p_bss_loop:
    ld a,(de)
    cp (hl)
    jp nz,p_fail
    inc de
    inc hl
    djnz p_bss_loop
    xor a
    ret

p_native_link:
{chr(10).join(validate_calls)}
    ld hl,p_sizes
    ld b,{len(modules)}
    ld de,0
    call ld_p1024_layout
    ret c
    call p_compare_layout
    ret c

{chr(10).join(copy_records)}

    ld hl,p_image
    ld (ld_p1026_image),hl
    ld hl,{len(host_mex.image)}
    ld (ld_p1026_image_size),hl
    ld (ld_p1025_image_size),hl
    call ld_p1026_reset

{chr(10).join(reloc_calls)}

    call ld_p1026_finalize
    ret c
    ld a,(ld_p1026_rel_count)
    cp {len(host_mex.relocs)}
    jp nz,p_fail

    ld de,p_defs
    ld b,{len(defs)}
    call ld_p1027_default_entry
    ret c
    ld hl,(ld_p1027_entry)
    ld de,{host_mex.entry_offset}
    or a
    sbc hl,de
    jp nz,p_fail

    ld hl,1024
    call ld_p1030_stack_set
    ret c
    ld hl,{len(host_mex.image)}
    ld de,{host_mex.bss_size}
    ld bc,0
    call ld_p1031_place
    ret c

    ld hl,p_image
    ld (ld_p1032_image),hl
    ld hl,{len(host_mex.image)}
    ld (ld_p1032_image_size),hl
    ld hl,{host_mex.bss_size}
    ld (ld_p1032_bss_size),hl
    ld hl,{host_mex.entry_offset}
    ld (ld_p1032_entry),hl
    ld hl,1024
    ld (ld_p1032_stack),hl
    ld hl,ld_p1026_rel_locs
    ld (ld_p1032_relocs),hl
    ld hl,{len(host_mex.relocs)}
    ld (ld_p1032_reloc_count),hl
    ld hl,p_out
    ld (ld_p1032_output),hl
    ld hl,{len(host_bytes) + 16}
    ld (ld_p1032_capacity),hl
    call ld_p1032_write
    ret c
    ld hl,(ld_p1032_stored_length)
    ld de,p_host_mex_end-p_host_mex
    or a
    sbc hl,de
    jp nz,p_fail

    ld hl,p_out
    ld de,p_host_mex
    ld bc,p_host_mex_end-p_host_mex
p_mex_loop:
    ld a,b
    or c
    jr z,p_mex_equal
    ld a,(de)
    cp (hl)
    jp nz,p_fail
    inc de
    inc hl
    dec bc
    jr p_mex_loop
p_mex_equal:
    xor a
    ret

fixture_end:
    SAVEBIN "sdk-native-linker.bin",fixture,fixture_end-fixture
"""

    with tempfile.TemporaryDirectory(prefix="c48-native-linker-") as td:
        temp = Path(td)
        source = temp / "sdk-native-linker.asm"
        source.write_text(asm, encoding="utf-8", newline="\n")
        assembler = root / "tools/runtime/sjasmplus/bin/sjasmplus"
        require(assembler.is_file(), "project-local assembler missing")
        run([assembler, "--nologo", "--sym=sdk-native-linker.sym", source.name], cwd=temp)
        fixture = (temp / "sdk-native-linker.bin").read_bytes()
        require(0 < len(fixture) < 0x4000, f"native linker fixture unsafe size {len(fixture)}")
        entry = symbol_address(temp / "sdk-native-linker.sym", "p_native_link")

        driver_dir = root / "v1/tools-host/test-driver"
        sys.path.insert(0, str(driver_dir))
        from fuse_harness import FAIL_PC, PASS_PC, jp, run_sna

        def word(value: int) -> bytes:
            return bytes((value & 0xFF, value >> 8))

        def patch(ram: bytearray) -> None:
            offset = FIXTURE_BASE - 0x4000
            ram[offset:offset + len(fixture)] = fixture

        code = b"\xF3\x31\xC0\xBF\xCD" + word(entry) + b"\xDA" + word(FAIL_PC) + jp(PASS_PC)
        run_sna(root, code, patch=patch, timeout=30)

    print(
        "NATIVE LINKER PASS "
        + REFERENCE_COMMIT
        + " obj="
        + hashlib.sha256(encode_obj1(user)).hexdigest()
        + " mex="
        + hashlib.sha256(host_bytes).hexdigest()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
