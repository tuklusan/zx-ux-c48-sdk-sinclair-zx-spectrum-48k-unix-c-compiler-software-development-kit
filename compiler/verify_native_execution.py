# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SDK = HERE.parent
sys.path.insert(0, str(HERE))

from c48.compiler import compile_bytes
from c48.format import write as write_c48b
from c48.native_backend import NativeBackend
from c48.native_format import build_bin_tap, decode_mex1, encode_mex1, encode_obj1
from c48.native_link import link_mex
from c48.native_runtime import RUNTIME_MEMBERS
from tests.native_large_fixture import generate_large_native_source
from tests.native_semantic_fixtures import SHARED_RECURSION_SOURCE

REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"
DIRECT_TAPE_ERRATUM = "P514 image byte is not restored after CRC update"
NAMESPACE_ERRATUM = "P509 uses invalid LD B,(nn) form for M48O type"
IMAGE_BASE = 0x8000
FIXTURE_BASE = 0x4000
TEST_ENTRY = 0x7A00
TEST_STACK = 0x79F0
PASS_PC = 0x7FF0
FAIL_PC = 0x7FF1
FAIL_LOAD_PC = 0x7FE1
FAIL_BASE_PC = 0x7FE2
FAIL_COMMIT_PC = 0x7FE3
FAIL_RETURN_PC = 0x7FE4
FAIL_PROGRAM_PC = 0x7FE5
FAIL_SCREEN_PC = 0x7FE6
FAIL_LOAD_FORMAT_PC = 0x7FD1
FAIL_LOAD_IO_PC = 0x7FD2
FAIL_LOAD_NOMEM_PC = 0x7FD3
FAIL_LOAD_NOSPC_PC = 0x7FD4
FAIL_LOAD_AGAIN_PC = 0x7FD5
FAIL_LOAD_OTHER_PC = 0x7FD6
SNAPSHOT_STACK = 0x79E0
RAM_START = 0x4000
RAM_SIZE = 0xC000


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def call(address: int) -> bytes:
    return b"\xCD" + word(address)


def jp(address: int) -> bytes:
    return b"\xC3" + word(address)


def jp_c(address: int) -> bytes:
    return b"\xDA" + word(address)


def jp_nz(address: int) -> bytes:
    return b"\xC2" + word(address)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def verify_native_identity(root: Path) -> None:
    cp = run(["git", "rev-parse", "HEAD"], cwd=root)
    require(cp.stdout.strip() == REFERENCE_COMMIT, "native reference commit drift")


def verify_pinned_direct_tape_erratum(root: Path) -> None:
    source = (root / "v1/src/kernel/process.asm").read_text(encoding="utf-8")
    start = source.index("zx48_p514_image_loop:")
    end = source.index("zx48_p514_zero_bss:", start)
    block = source[start:end]
    require(
        "call zx48_p514_tape_stream_byte" in block
        and "call zx48_p514_crc16_update" in block
        and "ld (hl),a" in block,
        "pinned direct-tape image loop shape drifted",
    )
    update = block.index("call zx48_p514_crc16_update")
    write = block.index("ld (hl),a", update)
    between = block[update:write]
    require(
        "ld a,(p514_tape_byte)" not in between
        and "push af" not in between
        and "pop af" not in between,
        "pinned direct-tape erratum is no longer present; remove the overlay",
    )


def verify_pinned_namespace_erratum(root: Path) -> None:
    source = (root / "v1/src/kernel/tape.asm").read_text(encoding="utf-8")
    start = source.index("zx48_p509_match:")
    end = source.index("zx48_p509_load_raw:", start)
    block = source[start:end]
    require(
        "ld a,(p509_header+M48O_HDR_DIRECTORY)" in block
        and "ld b,(p509_header+M48O_HDR_TYPE)" in block
        and "call zx48_object_public_type_allowed" in block,
        "pinned namespace placement-check shape drifted",
    )
    require(
        "ld a,(p509_header+M48O_HDR_TYPE)" not in block,
        "pinned namespace erratum is no longer present; remove the overlay",
    )


def symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    found: dict[str, int] = {}
    for name in names:
        prefix = name + ":"
        for raw in text.splitlines():
            line = raw.strip()
            if not line.lower().startswith(prefix.lower()):
                continue
            parts = line.split()
            if len(parts) >= 3 and parts[1].lower() == "equ" and parts[2].lower().startswith("0x"):
                found[name] = int(parts[2], 16)
                break
        require(name in found, f"fixture symbol missing: {name}")
    return found


def make_sna(code: bytes, patch) -> bytes:
    require(TEST_ENTRY + len(code) <= PASS_PC, "test driver overlaps pass marker")
    ram = bytearray(RAM_SIZE)
    ram[TEST_ENTRY - RAM_START:TEST_ENTRY - RAM_START + len(code)] = code
    struct.pack_into("<H", ram, SNAPSHOT_STACK - RAM_START, TEST_ENTRY)
    patch(ram)
    header = bytearray(27)
    header[0] = 0xFE
    header[19] = 0x04
    struct.pack_into("<H", header, 23, SNAPSHOT_STACK)
    header[25] = 1
    return bytes(header) + bytes(ram)


def fixture_source(root: Path) -> str:
    inc = root / "v1/include"
    kernel = root / "v1/src/kernel"
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "{(inc / 'zx48ux.inc').as_posix()}"
    INCLUDE "{(inc / 'mex1.inc').as_posix()}"
    INCLUDE "{(inc / 'tapeobj.inc').as_posix()}"
PROC1_PATH_PTR EQU 0
PROC1_ARG1_PTR EQU 2
PROC1_ARG1_LEN EQU 4
PROC1_ENV1_PTR EQU 6
PROC1_ENV1_LEN EQU 8
PROC1_FLAGS EQU 13
PROC1_ALLOW_TAPE EQU 1
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
P417_STATE_SIZE EQU 272
PATH_KIND_BASE EQU 1
ROM_LD_BYTES EQU $0556
    INCLUDE "{(kernel / 'tape.asm').as_posix()}"
    INCLUDE "{(kernel / 'process.asm').as_posix()}"

    ORG $4000
fixture_start:
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
    EMIT_P511_SCAN_ROUTINES
    EMIT_P514_DIRECT_TAPE_STREAM_ROUTINES
    EMIT_P514_DIRECT_TAPE_MEX1_ROUTINES

zx48_alloc:
    ld a,(test_alloc_index)
    inc a
    ld (test_alloc_index),a
    dec a
    jr z,test_alloc_scratch
    dec a
    jr z,test_alloc_image
    dec a
    jr z,test_alloc_stack
    dec a
    jr z,test_alloc_boot
    ld a,E_NOMEM
    scf
    ret
test_alloc_scratch:
    ld hl,$7000
    xor a
    ret
test_alloc_image:
    ld hl,$8000
    xor a
    ret
test_alloc_stack:
    ld hl,$7200
    xor a
    ret
test_alloc_boot:
    ld hl,$7600
    xor a
    ret
zx48_free:
    xor a
    ret

zx48_tape_load_block:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,test_tape_error
    xor a
    ret
test_tape_error:
    ld a,E_IO
    scf
    ret
zx48_tape_save_block:
    ld a,E_IO
    scf
    ret

zx48_p514_resolve_tape_name:
    ld hl,test_name
    xor a
    ret
zx48_p514_commit_ready:
    xor a
    ret
zx48_arg1_validate:
    xor a
    ret
zx48_env1_validate:
    xor a
    ret

zx48_object_public_type_allowed:
    xor a
    ret
zx48_process_lookup:
    ld a,E_NOENT
    scf
    ret
zx48_object_lookup:
    ld a,E_NOENT
    scf
    ret
zx48_object_create:
    ld a,E_NOSPC
    scf
    ret
zx48_od_object_any_live:
    xor a
    ret
zx48_p424_candidate_clear:
    xor a
    ret
zx48_p513_prompt_play:
    xor a
    ret
zx48_p513_prompt_record:
    xor a
    ret
zx48_path_resolve:
    ld a,E_NOENT
    scf
    ret
zx48_p505_packed_load:
    ld a,E_IO
    scf
    ret
zx48_p504_raw_load:
    ld a,E_IO
    scf
    ret

test_name:
    db "NATIVE",0,0,0,0
test_arg:
    db 0
test_env:
    db 0
test_proc1:
    dw 0
    dw test_arg
    dw 1
    dw test_env
    dw 1
    defs 3,0
    db PROC1_ALLOW_TAPE
    defs 2,0
test_alloc_index:
    db 0
test_expect_screen:
    db 0
current_pid:
    db 1
path_dir:
    db 0
path_name:
    defs 10,0
fixture_end:
    SAVEBIN "sdk-native-exec.bin",fixture_start,fixture_end-fixture_start

    ORG $E000
gateway_start:
    cp SYS_EXIT
    jr z,gateway_exit
    cp SYS_WRITE
    jr z,gateway_write
    cp SYS_GFX_ATTR
    jr z,gateway_attr
    cp SYS_GFX_PLOT
    jr z,gateway_plot
    cp SYS_UDG_CLEAR
    jr z,gateway_udg
    ld a,E_NOTSUP
    scf
    ret
gateway_write:
    ld hl,(gateway_write_bytes)
    add hl,bc
    ld (gateway_write_bytes),hl
    ld h,b
    ld l,c
    xor a
    ret
gateway_attr:
    ld a,(gateway_attr_calls)
    inc a
    ld (gateway_attr_calls),a
    ld hl,0
    xor a
    ret
gateway_plot:
    ld a,(gateway_plot_calls)
    inc a
    ld (gateway_plot_calls),a
    ld hl,0
    xor a
    ret
gateway_udg:
    ld a,(gateway_udg_calls)
    inc a
    ld (gateway_udg_calls),a
    ld hl,0
    xor a
    ret
gateway_exit:
    ld a,h
    or l
    jp nz,${FAIL_PROGRAM_PC:04X}
    ld a,(test_expect_screen)
    or a
    jp z,$7FF0
    ld hl,(gateway_write_bytes)
    ld de,3
    or a
    sbc hl,de
    jp nz,${FAIL_SCREEN_PC:04X}
    ld a,(gateway_attr_calls)
    cp 1
    jp nz,${FAIL_SCREEN_PC:04X}
    ld a,(gateway_plot_calls)
    cp 1
    jp nz,${FAIL_SCREEN_PC:04X}
    ld a,(gateway_udg_calls)
    cp 1
    jp nz,${FAIL_SCREEN_PC:04X}
    jp $7FF0
gateway_write_bytes:
    dw 0
gateway_attr_calls:
    db 0
gateway_plot_calls:
    db 0
gateway_udg_calls:
    db 0
gateway_end:
    SAVEBIN "sdk-native-gateway.bin",gateway_start,gateway_end-gateway_start
"""


def assemble_fixture(root: Path, temp: Path):
    source = temp / "sdk-native-exec.asm"
    source.write_text(fixture_source(root), encoding="utf-8", newline="\n")
    assembler = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    require(assembler.is_file(), "project-local assembler missing")
    cp = run(
        [assembler, "--nologo", "--sym=sdk-native-exec.sym", source.name],
        cwd=temp,
        timeout=60,
    )
    main = (temp / "sdk-native-exec.bin").read_bytes()
    gate = (temp / "sdk-native-gateway.bin").read_bytes()
    require(0 < len(main) < 0x3000, f"native fixture has unsafe size {len(main)}")
    syms = symbols(
        temp / "sdk-native-exec.sym",
        (
            "zx48_p514_spawn_tape_backed",
            "zx48_p514_image_loop",
            "zx48_p514_zero_bss",
            "zx48_p514_crc16_update",
            "test_proc1",
            "test_alloc_index",
            "test_expect_screen",
            "p514_committed",
            "zx48_p511_format",
            "zx48_p514_tape_format",
            "p514_remaining",
            "p514_reloc_offset",
            "p514_previous_reloc",
            "p514_image_size",
            "p514_image_base",
            "p514_have_previous",
            "zx48_p514_format_abort",
            "zx48_p514_format_rollback",
            "gateway_write_bytes",
            "gateway_attr_calls",
            "gateway_plot_calls",
            "gateway_udg_calls",
        ),
    )
    return cp, main, gate, syms


def apply_direct_tape_erratum_overlay(
    fixture: bytes, syms: dict[str, int],
) -> tuple[bytes, str]:
    start = syms["zx48_p514_image_loop"] - FIXTURE_BASE
    end = syms["zx48_p514_zero_bss"] - FIXTURE_BASE
    require(0 <= start < end <= len(fixture), "direct-tape image-loop range drifted")
    original_call = call(syms["zx48_p514_crc16_update"])
    hits = []
    pos = start
    while True:
        pos = fixture.find(original_call, pos, end)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    require(len(hits) == 1, f"expected one direct-tape CRC call, found {len(hits)}")
    call_offset = hits[0]
    trampoline = FIXTURE_BASE + len(fixture)
    patch = b"\xF5" + call(syms["zx48_p514_crc16_update"]) + b"\xF1\xC9"
    require(trampoline + len(patch) <= 0x7000, "no safe room for direct-tape erratum trampoline")
    out = bytearray(fixture)
    require(out[call_offset:call_offset + 3] == original_call, "direct-tape call bytes drifted")
    out[call_offset + 1:call_offset + 3] = word(trampoline)
    out.extend(patch)
    note = (
        f"call=0x{FIXTURE_BASE + call_offset:04x} "
        f"target=0x{syms['zx48_p514_crc16_update']:04x} "
        f"trampoline=0x{trampoline:04x} original={original_call.hex()}"
    )
    return bytes(out), note



def namespace_fixture_source(root: Path) -> str:
    inc = root / "v1/include"
    kernel = root / "v1/src/kernel"
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "{(inc / 'zx48ux.inc').as_posix()}"
    INCLUDE "{(inc / 'tapeobj.inc').as_posix()}"
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
PATH_KIND_BASE EQU 1
ROM_LD_BYTES EQU $0556
    INCLUDE "{(kernel / 'tape.asm').as_posix()}"
    ORG $4000
namespace_fixture_start:
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES

zx48_objects_init:
    xor a
    ld hl,object_table
    ld de,object_table+1
    ld bc,OBJ_RECORD_SIZE-1
    ld (hl),a
    ldir
    ret

zx48_alloc:
    ld hl,$8000
    xor a
    ret
zx48_free:
    xor a
    ret
zx48_tape_load_block:
    ld a,M48O_ROM_DATA_FLAG
    scf
    call ROM_LD_BYTES
    jr nc,namespace_tape_error
    xor a
    ret
namespace_tape_error:
    ld a,E_IO
    scf
    ret
zx48_tape_save_block:
    ld a,E_IO
    scf
    ret

zx48_path_resolve:
    ld a,DIR_BIN
    ld (path_dir),a
    ld hl,test_namespace_name
    ld de,path_name
    ld bc,M48O_NAME_SIZE
    ldir
    ld c,PATH_KIND_BASE
    xor a
    ret

zx48_object_public_type_allowed:
    ld (test_allow_dir),a
    ld a,b
    ld (test_allow_type),a
    ld a,(test_allow_dir)
    cp DIR_BIN
    jr nz,namespace_perm
    ld a,(test_allow_type)
    cp OBJ_BIN
    jr nz,namespace_perm
    xor a
    ret
namespace_perm:
    ld a,E_PERM
    scf
    ret

zx48_object_lookup:
    cp DIR_BIN
    jr nz,namespace_noent
    ld a,(object_table+OBJ_TYPE_ID)
    or a
    jr z,namespace_noent
    ld ix,object_table
    ld c,0
    xor a
    ret
namespace_noent:
    ld a,E_NOENT
    scf
    ret

zx48_object_create:
    cp DIR_BIN
    jr nz,namespace_perm
    ld a,b
    cp OBJ_BIN
    jr nz,namespace_perm
    push hl
    ld de,object_table
    ld bc,M48O_NAME_SIZE
    ldir
    pop hl
    ld a,DIR_BIN
    ld (object_table+OBJ_DIR_ID),a
    ld a,OBJ_BIN
    ld (object_table+OBJ_TYPE_ID),a
    xor a
    ld (object_table+OBJ_FLAGS_BYTE),a
    ld (object_table+OBJ_RESERVED_BYTE),a
    ld (object_table+OBJ_LOGICAL_LENGTH),a
    ld (object_table+OBJ_LOGICAL_LENGTH+1),a
    ld (object_table+OBJ_STORAGE_LENGTH),a
    ld (object_table+OBJ_STORAGE_LENGTH+1),a
    ld (object_table+OBJ_ALLOCATION_PTR),a
    ld (object_table+OBJ_ALLOCATION_PTR+1),a
    ld ix,object_table
    ld c,0
    xor a
    ret

zx48_od_object_any_live:
    xor a
    or a
    ret
zx48_p424_candidate_clear:
    xor a
    ret
zx48_p505_packed_load:
    ld a,E_NOTSUP
    scf
    ret
zx48_p513_prompt_play:
    xor a
    ret
zx48_p513_prompt_record:
    xor a
    ret

test_namespace_path:
    db "/bin/NATIVE",0
test_namespace_name:
    db "NATIVE",0,0,0,0
test_allow_dir:
    db $ff
test_allow_type:
    db $ff
path_dir:
    db 0
path_name:
    defs M48O_NAME_SIZE,0
object_table:
    defs OBJ_RECORD_SIZE,0
namespace_fixture_end:
    SAVEBIN "sdk-native-namespace.bin",namespace_fixture_start,namespace_fixture_end-namespace_fixture_start
"""


def assemble_namespace_fixture(root: Path, temp: Path) -> tuple[bytes, dict[str, int]]:
    source = temp / "sdk-native-namespace.asm"
    source.write_text(namespace_fixture_source(root), encoding="utf-8", newline="\n")
    assembler = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    run(
        [assembler, "--nologo", "--sym=sdk-native-namespace.sym", source.name],
        cwd=temp,
        timeout=60,
    )
    binary = (temp / "sdk-native-namespace.bin").read_bytes()
    require(0 < len(binary) < TEST_ENTRY - FIXTURE_BASE,
            f"native namespace fixture has unsafe size {len(binary)}")
    syms = symbols(
        temp / "sdk-native-namespace.sym",
        (
            "zx48_objects_init",
            "zx48_p509_load_path",
            "zx48_p509_match",
            "p509_header",
            "zx48_object_public_type_allowed",
            "test_allow_dir",
            "test_allow_type",
            "zx48_p509_locked_error",
            "zx48_p509_commit_drop_new",
            "zx48_p509_free_error",
            "zx48_p509_format",
            "zx48_p509_inval",
            "zx48_p504_format",
            "zx48_p504_cleanup",
            "zx48_object_lookup",
            "test_namespace_path",
            "test_namespace_name",
            "object_table",
            "DIR_BIN",
            "OBJ_BIN",
            "OBJ_DIR_ID",
            "OBJ_TYPE_ID",
            "OBJ_FLAGS_BYTE",
            "OBJ_RESERVED_BYTE",
            "OBJ_LOGICAL_LENGTH",
            "OBJ_STORAGE_LENGTH",
            "OBJ_ALLOCATION_PTR",
        ),
    )
    return binary, syms


def apply_namespace_type_erratum_overlay(
    fixture: bytes, syms: dict[str, int],
) -> tuple[bytes, str]:
    start = syms["zx48_p509_match"] - FIXTURE_BASE
    end = syms["zx48_p509_locked_error"] - FIXTURE_BASE
    require(0 <= start < end <= len(fixture), "namespace match range drifted")
    wrong_imm = (syms["p509_header"] + 5) & 0xFF
    original = b"\x06" + bytes((wrong_imm,)) + call(syms["zx48_object_public_type_allowed"])
    hits: list[int] = []
    pos = start
    while True:
        pos = fixture.find(original, pos, end)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    require(len(hits) == 1, f"expected one namespace type-check sequence, found {len(hits)}")
    patch_offset = hits[0]
    trampoline = FIXTURE_BASE + len(fixture)
    trampoline_bytes = (
        b"\xF5"
        + b"\x3A" + word(syms["p509_header"] + 5)
        + b"\x47"
        + b"\xF1"
        + call(syms["zx48_object_public_type_allowed"])
        + b"\xC9"
    )
    require(
        trampoline + len(trampoline_bytes) <= TEST_ENTRY,
        "no safe room for namespace erratum trampoline",
    )
    out = bytearray(fixture)
    require(
        out[patch_offset:patch_offset + len(original)] == original,
        "namespace erratum original bytes drifted",
    )
    replacement = call(trampoline) + b"\x00\x00"
    require(len(replacement) == len(original), "namespace overlay must preserve patched span size")
    out[patch_offset:patch_offset + len(original)] = replacement
    out.extend(trampoline_bytes)
    note = (
        f"site=0x{FIXTURE_BASE + patch_offset:04x} "
        f"wrong_type=0x{wrong_imm:02x} "
        f"allow=0x{syms['zx48_object_public_type_allowed']:04x} "
        f"trampoline=0x{trampoline:04x} original={original.hex()}"
    )
    return bytes(out), note


def namespace_driver(syms: dict[str, int], mex_bytes: bytes, expected_addr: int) -> bytes:
    code = bytearray()
    code += b"\xF3"
    code += b"\x31" + word(TEST_STACK)
    code += call(syms["zx48_objects_init"])
    code += b"\x21" + word(syms["test_namespace_path"])
    code += call(syms["zx48_p509_load_path"])
    code += jp_c(FAIL_LOAD_PC)
    code += bytes((0x3E, syms["DIR_BIN"] & 0xFF))
    code += b"\x21" + word(syms["test_namespace_name"])
    code += call(syms["zx48_object_lookup"])
    code += jp_c(FAIL_BASE_PC)
    record = syms["object_table"]
    code += check_byte(record + syms["OBJ_DIR_ID"], syms["DIR_BIN"], FAIL_COMMIT_PC)
    code += check_byte(record + syms["OBJ_TYPE_ID"], syms["OBJ_BIN"], FAIL_COMMIT_PC)
    code += check_byte(record + syms["OBJ_FLAGS_BYTE"], 0, FAIL_COMMIT_PC)
    code += check_byte(record + syms["OBJ_RESERVED_BYTE"], 0, FAIL_COMMIT_PC)
    code += check_word(record + syms["OBJ_LOGICAL_LENGTH"], len(mex_bytes), FAIL_COMMIT_PC)
    code += check_word(record + syms["OBJ_STORAGE_LENGTH"], len(mex_bytes), FAIL_COMMIT_PC)
    code += check_word(record + syms["OBJ_ALLOCATION_PTR"], IMAGE_BASE, FAIL_COMMIT_PC)
    for index, value in enumerate(b"NATIVE\0\0\0\0"):
        code += check_byte(record + index, value, FAIL_COMMIT_PC)
    code += b"\x21" + word(IMAGE_BASE)
    code += b"\x11" + word(expected_addr)
    code += b"\x01" + word(len(mex_bytes))
    loop = TEST_ENTRY + len(code)
    code += b"\x1A\xBE" + jp_nz(FAIL_PROGRAM_PC)
    code += b"\x23\x13\x0B\x78\xB1" + jp_nz(loop)
    code += jp(PASS_PC)
    return bytes(code)


def run_namespace_case(
    root: Path,
    temp: Path,
    fixture: bytes,
    syms: dict[str, int],
    tap: bytes,
    mex_bytes: bytes,
    *,
    expect_erratum: bool = False,
) -> None:
    expected_addr = 0xA000
    require(expected_addr + len(mex_bytes) < 0xC000, "namespace proof MEX is too large")
    tape = temp / "namespace.tap"
    sna = temp / "namespace.sna"
    tape.write_bytes(tap)
    code = namespace_driver(syms, mex_bytes, expected_addr)

    def patch(ram: bytearray) -> None:
        start = FIXTURE_BASE - RAM_START
        ram[start:start + len(fixture)] = fixture
        expected = expected_addr - RAM_START
        ram[expected:expected + len(mex_bytes)] = mex_bytes

    sna.write_bytes(make_sna(code, patch))
    fuse = root / "tools/runtime/fuse/bin/fuse"
    debugger_parts = [
        f"breakpoint 0x{PASS_PC:04x}\ncommands 1\nexit 0\nend\n",
        f"breakpoint 0x{FAIL_LOAD_PC:04x}\ncommands 2\nprint z80:a\nexit 1\nend\n",
        f"breakpoint 0x{FAIL_BASE_PC:04x}\ncommands 3\nprint z80:a\nexit 2\nend\n",
        f"breakpoint 0x{FAIL_COMMIT_PC:04x}\ncommands 4\nexit 3\nend\n",
        f"breakpoint 0x{FAIL_PROGRAM_PC:04x}\ncommands 5\nexit 4\nend\n",
    ]
    for index, (name, status) in enumerate(
        (
            ("zx48_p509_locked_error", 11),
            ("zx48_p509_commit_drop_new", 12),
            ("zx48_p509_free_error", 13),
            ("zx48_p509_format", 14),
            ("zx48_p509_inval", 15),
            ("zx48_p504_format", 16),
            ("zx48_p504_cleanup", 17),
        ),
        6,
    ):
        debugger_parts.append(
            f"breakpoint 0x{syms[name]:04x}\ncommands {index}\n"
            f"print z80:a\n"
        )
        if name == "zx48_p509_locked_error":
            header = syms["p509_header"]
            debugger_parts.append(
                f"print [0x{header + 5:04x}]\n"
                f"print [0x{header + 7:04x}]\n"
                f"print [0x{syms['test_allow_dir']:04x}]\n"
                f"print [0x{syms['test_allow_type']:04x}]\n"
                "print z80:b\n"
            )
        debugger_parts.append(f"exit {status}\nend\n")
    debugger_parts.append("continue")
    debugger = "".join(debugger_parts)
    env = dict(**__import__("os").environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    cp = subprocess.run(
        [
            str(fuse), "--machine", "48", "--no-sound", "--no-confirm-actions",
            "--tape", str(tape), "--debugger-command", debugger, str(sna),
        ],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if expect_erratum:
        wrong_type = (syms["p509_header"] + 5) & 0xFF
        require(wrong_type != syms["OBJ_BIN"], "namespace erratum no longer produces a wrong type")
        require(
            cp.returncode == 11,
            f"unmodified native namespace erratum signature drifted: exit={cp.returncode}\n"
            f"stdout={cp.stdout}\nstderr={cp.stderr}",
        )
        values = [line.strip().lower() for line in cp.stdout.splitlines() if line.strip().lower().startswith("0x")]
        expected_tail = [
            "0x7",
            f"0x{syms['OBJ_BIN'] & 0xff:x}",
            f"0x{syms['DIR_BIN'] & 0xff:x}",
            f"0x{syms['DIR_BIN'] & 0xff:x}",
            f"0x{wrong_type:x}",
            f"0x{wrong_type:x}",
        ]
        require(
            values[-6:] == expected_tail,
            f"unmodified native namespace erratum trace drifted: got={values[-6:]} expected={expected_tail}",
        )
        return
    require(
        cp.returncode == 0,
        f"native namespace tape proof failed: exit={cp.returncode}\n"
        f"stdout={cp.stdout}\nstderr={cp.stderr}",
    )



def resident_fixture_source(root: Path) -> str:
    inc = root / "v1/include"
    process = root / "v1/src/kernel/process.asm"
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "{(inc / 'zx48ux.inc').as_posix()}"
    INCLUDE "{(inc / 'mex1.inc').as_posix()}"
PROC1_PATH_PTR EQU 0
PROC1_ARG1_PTR EQU 2
PROC1_ARG1_LEN EQU 4
PROC1_ENV1_PTR EQU 6
PROC1_ENV1_LEN EQU 8
PROC1_STDIN_HANDLE EQU 10
PROC1_STDOUT_HANDLE EQU 11
PROC1_STDERR_HANDLE EQU 12
PROC1_FLAGS EQU 13
OBJ_NAME EQU 0
OBJ_DIR_ID EQU 10
OBJ_TYPE_ID EQU 11
OBJ_FLAGS_BYTE EQU 12
OBJ_RESERVED_BYTE EQU 13
OBJ_LOGICAL_LENGTH EQU 14
OBJ_STORAGE_LENGTH EQU 16
OBJ_ALLOCATION_PTR EQU 18
    INCLUDE "{process.as_posix()}"

    ORG $4000
resident_fixture_start:
    EMIT_MEX1_RELOCATION_ROUTINES
    EMIT_MEX1_IMAGE_LOAD_ROUTINES
    EMIT_SPAWN_TRANSACTION_ROUTINES

zx48_alloc:
    ld hl,$8000
    xor a
    ret
zx48_free:
    xor a
    ret
zx48_process_find_free_slot:
    ld a,E_AGAIN
    scf
    ret
zx48_spawn_resolve_ram_object:
    ld a,E_NOENT
    scf
    ret
zx48_arg1_validate:
    xor a
    ret
zx48_env1_validate:
    xor a
    ret
zx48_handle_lookup:
    ld a,E_NOENT
    scf
    ret
zx48_process_lookup:
    ld a,E_NOENT
    scf
    ret
zx48_process_build_initial_context:
    ld a,E_NOTSUP
    scf
    ret
zx48_od_retain:
    xor a
    ret
zx48_od_release:
    xor a
    ret
current_pid:
    db 1
resident_fixture_end:
    SAVEBIN "sdk-native-resident.bin",resident_fixture_start,resident_fixture_end-resident_fixture_start

    ORG $E000
resident_gateway_start:
    cp SYS_EXIT
    jr z,resident_gateway_exit
    ld a,E_NOTSUP
    scf
    ret
resident_gateway_exit:
    ld a,h
    or l
    jp nz,$7FE5
    jp $7FF0
resident_gateway_end:
    SAVEBIN "sdk-native-resident-gateway.bin",resident_gateway_start,resident_gateway_end-resident_gateway_start
"""


def assemble_resident_fixture(root: Path, temp: Path) -> tuple[bytes, bytes, dict[str, int]]:
    source = temp / "sdk-native-resident.asm"
    source.write_text(resident_fixture_source(root), encoding="utf-8", newline="\n")
    assembler = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    run(
        [assembler, "--nologo", "--sym=sdk-native-resident.sym", source.name],
        cwd=temp,
        timeout=60,
    )
    binary = (temp / "sdk-native-resident.bin").read_bytes()
    gateway = (temp / "sdk-native-resident-gateway.bin").read_bytes()
    require(0 < len(binary) < TEST_ENTRY - FIXTURE_BASE,
            f"native resident fixture has unsafe size {len(binary)}")
    require(0 < len(gateway) < 0x0200, "native resident gateway is too large")
    syms = symbols(
        temp / "sdk-native-resident.sym",
        (
            "zx48_process_spawn_validate_mex1",
            "zx48_mex1_load_image",
        ),
    )
    return binary, gateway, syms


def resident_driver(syms: dict[str, int], mex_bytes: bytes, mex_entry: int) -> bytes:
    mex_source = 0x9000
    code = bytearray()
    code += b"\xF3"
    code += b"\x31" + word(TEST_STACK)
    code += b"\xDD\x21" + word(mex_source)
    code += b"\x01" + word(len(mex_bytes))
    code += call(syms["zx48_process_spawn_validate_mex1"])
    code += jp_c(FAIL_LOAD_PC)
    code += b"\xDD\x21" + word(mex_source)
    code += call(syms["zx48_mex1_load_image"])
    code += jp_c(FAIL_LOAD_PC)
    code += b"\x11" + word(IMAGE_BASE) + b"\xB7\xED\x52" + jp_nz(FAIL_BASE_PC)
    code += call(IMAGE_BASE + mex_entry)
    code += jp(FAIL_RETURN_PC)
    return bytes(code)


def run_resident_case(
    root: Path,
    temp: Path,
    fixture: bytes,
    gateway: bytes,
    syms: dict[str, int],
    mex_bytes: bytes,
    mex_entry: int,
) -> None:
    mex_source = 0x9000
    require(mex_source + len(mex_bytes) < 0xE000, "resident proof MEX is too large")
    sna = temp / "resident.sna"
    code = resident_driver(syms, mex_bytes, mex_entry)

    def patch(ram: bytearray) -> None:
        start = FIXTURE_BASE - RAM_START
        ram[start:start + len(fixture)] = fixture
        source = mex_source - RAM_START
        ram[source:source + len(mex_bytes)] = mex_bytes
        gate = 0xE000 - RAM_START
        ram[gate:gate + len(gateway)] = gateway

    sna.write_bytes(make_sna(code, patch))
    fuse = root / "tools/runtime/fuse/bin/fuse"
    failures = (
        (FAIL_LOAD_PC, 1),
        (FAIL_BASE_PC, 2),
        (FAIL_RETURN_PC, 3),
        (FAIL_PROGRAM_PC, 4),
    )
    parts = [f"breakpoint 0x{PASS_PC:04x}\ncommands 1\nexit 0\nend\n"]
    for index, (address, status) in enumerate(failures, 2):
        parts.append(
            f"breakpoint 0x{address:04x}\ncommands {index}\nexit {status}\nend\n"
        )
    parts.append("continue")
    env = dict(**__import__("os").environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    cp = subprocess.run(
        [
            str(fuse), "--machine", "48", "--no-sound", "--no-confirm-actions",
            "--debugger-command", "".join(parts), str(sna),
        ],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    require(
        cp.returncode == 0,
        f"native resident MEX proof failed: exit={cp.returncode}\n"
        f"stdout={cp.stdout}\nstderr={cp.stderr}",
    )


def float_service_source(root: Path) -> str:
    inc = root / "v1/include/zx48ux.inc"
    syscall = root / "v1/src/kernel/syscall.asm"
    rom = root / "v1/src/kernel/rom_services.asm"
    return f"""    DEVICE ZXSPECTRUM48
    INCLUDE "{inc.as_posix()}"
    INCLUDE "{syscall.as_posix()}"
    INCLUDE "{rom.as_posix()}"

    ORG $C000
float_service_start:
altreg_busy: db 0
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES
    EMIT_P1117_ROM_FP_EXEC_ROUTINES
    EMIT_P1118_FP_CAST_SYSCALL_ROUTINES
    EMIT_P1118_ROM_FP_CAST_ROUTINES
    EMIT_P1119_FP_CMP_SYSCALL_ROUTINES
    EMIT_P1119_ROM_FP_CMP_ROUTINES
float_exit_seen: db 0
float_service_end:
    SAVEBIN "sdk-native-float-service.bin",float_service_start,float_service_end-float_service_start

    ORG $E000
float_gateway_start:
    cp SYS_FP_EXEC
    jr z,float_g_fp
    cp SYS_INT_TO_FP
    jr z,float_g_itof
    cp SYS_FP_TO_INT
    jr z,float_g_ftoi
    cp SYS_FP_CMP
    jr z,float_g_cmp
    cp SYS_EXIT
    jr z,float_g_exit
    ld a,E_NOTSUP
    scf
    ret
float_g_fp:
    ld (syscall_arg_hl),hl
    jp zx48_p1117_sys_fp_exec
float_g_itof:
    ld (syscall_arg_hl),hl
    jp zx48_p1118_sys_int_to_fp
float_g_ftoi:
    ld (syscall_arg_hl),hl
    jp zx48_p1118_sys_fp_to_int
float_g_cmp:
    ld (syscall_arg_hl),hl
    jp zx48_p1119_sys_fp_cmp
float_g_exit:
    ld a,l
    ld (float_exit_seen),a
    ld a,h
    or l
    jp nz,${FAIL_PROGRAM_PC:04X}
    jp $7FF0
float_gateway_end:
    SAVEBIN "sdk-native-float-gateway.bin",float_gateway_start,float_gateway_end-float_gateway_start
"""


def assemble_float_service(root: Path, temp: Path) -> tuple[bytes, bytes]:
    source = temp / "sdk-native-float-service.asm"
    source.write_text(float_service_source(root), encoding="utf-8", newline="\n")
    assembler = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    cp = run([assembler, "--nologo", source.name], cwd=temp, timeout=60)
    del cp
    service = (temp / "sdk-native-float-service.bin").read_bytes()
    gateway = (temp / "sdk-native-float-gateway.bin").read_bytes()
    require(0 < len(service) < 0x2000, f"native Float5 service unsafe size {len(service)}")
    require(0 < len(gateway) < 0x0200, f"native Float5 gateway unsafe size {len(gateway)}")
    return service, gateway


def build_native(source: bytes, source_name: str):
    program = compile_bytes(source, source_name=source_name, base_dir=SDK)
    user = NativeBackend(program).build()
    startup = next(member for member in RUNTIME_MEMBERS if member.name == "startup")
    runtime = tuple(member for member in RUNTIME_MEMBERS if member.name != "startup")
    mex = link_mex([("startup", startup.obj), ("user", user)], runtime)
    return program, user, mex


def host_artifact(program, temp: Path, stem: str) -> bytes:
    path = temp / f"{stem}.c48b"
    write_c48b(path, program)
    c48b = path.read_bytes()
    cp = subprocess.run(
        [sys.executable, str(HERE / "c48run.py"), "--headless", str(path)],
        cwd=SDK,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    require(cp.returncode == 0, f"host semantic fixture failed: {stem}: {cp.stderr}")
    return c48b


def check_byte(address: int, value: int, fail_pc: int = FAIL_PC) -> bytes:
    return b"\x3A" + word(address) + bytes((0xFE, value & 0xFF)) + jp_nz(fail_pc)


def check_word(address: int, value: int, fail_pc: int = FAIL_PC) -> bytes:
    return b"\x2A" + word(address) + b"\x11" + word(value) + b"\xB7\xED\x52" + jp_nz(fail_pc)


def execution_driver(syms: dict[str, int], mex_entry: int, *, counters: bool) -> bytes:
    code = bytearray()
    code += b"\xF3"
    code += b"\x31" + word(TEST_STACK)
    code += b"\xFD\x21\x3A\x5C"
    code += b"\xAF\x32" + word(syms["test_alloc_index"])
    code += bytes((0x3E, 1 if counters else 0, 0x32)) + word(syms["test_expect_screen"])
    code += b"\x21" + word(syms["test_proc1"])
    code += call(syms["zx48_p514_spawn_tape_backed"])
    load_ok = TEST_ENTRY + len(code) + 31
    code += b"\xD2" + word(load_ok)
    for errno, target in (
        (0x0B, FAIL_LOAD_FORMAT_PC),
        (0x05, FAIL_LOAD_IO_PC),
        (0x03, FAIL_LOAD_NOMEM_PC),
        (0x0C, FAIL_LOAD_NOSPC_PC),
        (0x0D, FAIL_LOAD_AGAIN_PC),
    ):
        code += bytes((0xFE, errno)) + b"\xCA" + word(target)
    code += jp(FAIL_LOAD_OTHER_PC)
    code += b"\x11" + word(IMAGE_BASE) + b"\xB7\xED\x52" + jp_nz(FAIL_BASE_PC)
    code += check_byte(syms["p514_committed"], 1, FAIL_COMMIT_PC)
    code += call(IMAGE_BASE + mex_entry)
    # A conforming exit never returns. Reaching here means the startup/exit
    # contract failed even if main itself returned zero.
    code += jp(FAIL_RETURN_PC)
    return bytes(code)


def run_tape_case(
    root: Path,
    temp: Path,
    fixture: bytes,
    gateway: bytes | None,
    syms: dict[str, int],
    tap: bytes,
    mex_entry: int,
    *,
    stem: str,
    counters: bool,
    service: bytes | None = None,
    expected_exit: int = 0,
) -> subprocess.CompletedProcess[str]:
    tape = temp / f"{stem}.tap"
    sna = temp / f"{stem}.sna"
    tape.write_bytes(tap)
    code = execution_driver(syms, mex_entry, counters=counters)

    def patch(ram: bytearray) -> None:
        start = FIXTURE_BASE - RAM_START
        ram[start:start + len(fixture)] = fixture
        if service is not None:
            service_start = 0xC000 - RAM_START
            ram[service_start:service_start + len(service)] = service
        if gateway is not None:
            gate_start = 0xE000 - RAM_START
            ram[gate_start:gate_start + len(gateway)] = gateway

    sna.write_bytes(make_sna(code, patch))
    fuse = root / "tools/runtime/fuse/bin/fuse"
    require(fuse.is_file(), "project-local FUSE executable missing")
    failures = (
        (FAIL_PC, 1),
        (FAIL_LOAD_PC, 11),
        (FAIL_BASE_PC, 12),
        (FAIL_COMMIT_PC, 13),
        (FAIL_RETURN_PC, 14),
        (FAIL_PROGRAM_PC, 15),
        (FAIL_SCREEN_PC, 16),
        (FAIL_LOAD_FORMAT_PC, 21),
        (FAIL_LOAD_IO_PC, 22),
        (FAIL_LOAD_NOMEM_PC, 23),
        (FAIL_LOAD_NOSPC_PC, 24),
        (FAIL_LOAD_AGAIN_PC, 25),
        (FAIL_LOAD_OTHER_PC, 26),
    )
    debugger_parts = [f"breakpoint 0x{PASS_PC:04x}\ncommands 1\nexit 0\nend\n"]
    internal_failures = (
        (syms["zx48_p511_format"], 31),
        (syms["zx48_p514_tape_format"], 32),
        (syms["zx48_p514_format_abort"], 33),
        (syms["zx48_p514_format_rollback"], 34),
    )
    for index, (address, status) in enumerate(internal_failures, 2):
        debugger_parts.append(f"breakpoint 0x{address:04x}\ncommands {index}\n")
        if status == 34:
            for field in (
                "p514_remaining",
                "p514_reloc_offset",
                "p514_previous_reloc",
                "p514_image_size",
                "p514_image_base",
            ):
                address = syms[field]
                debugger_parts.append(
                    f"print [0x{address:04x}] + 256 * [0x{address + 1:04x}]\n"
                )
            debugger_parts.append(
                f"print [0x{syms['p514_have_previous']:04x}]\n"
                "print z80:hl\nprint z80:de\nprint z80:a\n"
            )
        debugger_parts.append(f"exit {status}\nend\n")
    for index, (address, status) in enumerate(failures, 2 + len(internal_failures)):
        debugger_parts.append(
            f"breakpoint 0x{address:04x}\ncommands {index}\nexit {status}\nend\n"
        )
    debugger_parts.append("continue")
    debugger = "".join(debugger_parts)
    env = dict(**__import__("os").environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    cp = subprocess.run(
        [
            str(fuse), "--machine", "48", "--no-sound", "--no-confirm-actions",
            "--tape", str(tape), "--debugger-command", debugger, str(sna),
        ],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    require(
        cp.returncode == expected_exit,
        f"native tape execution result mismatch: {stem}: expected={expected_exit} "
        f"exit={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}",
    )
    return cp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.native_root.resolve()
    verify_native_identity(root)
    verify_pinned_direct_tape_erratum(root)
    verify_pinned_namespace_erratum(root)

    cases = (
        (
            "globals",
            (
                b"char msg[4]=\"XYZ\";int g=7;"
                b"int main(void){if(g!=7)return 1;if(msg[2]!='Z')return 2;return 0;}"
            ),
            "plain",
        ),
        (
            "division",
            (
                b"int main(void){if((-91/7)!=-13)return 1;"
                b"if((-91%7)!=0)return 2;return 0;}"
            ),
            "plain",
        ),
        (
            "recursion",
            SHARED_RECURSION_SOURCE.encode("ascii"),
            "plain",
        ),
        (
            "screen",
            (
                b"int puts(char *s);int ink(int x);int plot(int x,int y);int udg_clear(int x);"
                b"int main(void){if(puts(\"OK\")!=0)return 1;if(ink(2)!=0)return 2;"
                b"if(plot(1,2)!=0)return 3;if(udg_clear(3)!=0)return 4;return 0;}"
            ),
            "screen",
        ),
        (
            "float5",
            (
                b"float sin(float);"
                b"int main(void){float x;x=1;x++;if(x!=2.0)return 1;"
                b"x=sin(x-x);if(x!=0.0)return 2;return 0;}"
            ),
            "float5",
        ),
        ("large", generate_large_native_source(), "plain"),
    )

    with tempfile.TemporaryDirectory(prefix="c48-native-exec-") as td:
        temp = Path(td)
        _, fixture, screen_gateway, syms = assemble_fixture(root, temp)
        overlay_fixture, overlay_note = apply_direct_tape_erratum_overlay(fixture, syms)
        namespace_fixture, namespace_syms = assemble_namespace_fixture(root, temp)
        namespace_overlay_fixture, namespace_overlay_note = apply_namespace_type_erratum_overlay(
            namespace_fixture, namespace_syms,
        )
        resident_fixture, resident_gateway, resident_syms = assemble_resident_fixture(root, temp)
        float_service, float_gateway = assemble_float_service(root, temp)
        records: list[str] = []
        for stem, source, mode in cases:
            program, obj, mex = build_native(source, stem + ".c")
            c48b_bytes = host_artifact(program, temp, stem)
            obj_bytes = encode_obj1(obj)
            mex_bytes = encode_mex1(mex)
            tap_bytes = build_bin_tap("NATIVE", mex_bytes)
            decoded = decode_mex1(mex_bytes)
            if stem == "globals":
                words = [
                    (offset, int.from_bytes(decoded.image[offset:offset + 2], "little"))
                    for offset in decoded.relocs
                ]
                print(
                    f"GLOBALS MEX image={len(decoded.image)} bss={decoded.bss_size} "
                    f"entry={decoded.entry_offset} relocs={decoded.relocs} words={words}",
                    flush=True,
                )
            second = build_native(source, stem + ".c")
            require(obj_bytes == encode_obj1(second[1]), f"{stem}: OBJ1 rebuild drift")
            require(mex_bytes == encode_mex1(second[2]), f"{stem}: MEX1 rebuild drift")
            require(tap_bytes == build_bin_tap("NATIVE", encode_mex1(second[2])), f"{stem}: TAP rebuild drift")
            if stem == "large":
                require(29 * 1024 <= len(source) <= 31 * 1024, "large source outside acceptance band")
                require(29 * 1024 <= len(mex_bytes) <= 31 * 1024, "large MEX1 outside acceptance band")
            if mode == "float5":
                require(len(mex.image) + mex.bss_size < 0x4000,
                        "Float5 proof image would overlap pinned service fixture")
            if stem == "globals":
                run_namespace_case(
                    root, temp, namespace_fixture, namespace_syms,
                    tap_bytes, mex_bytes, expect_erratum=True,
                )
                run_namespace_case(
                    root, temp, namespace_overlay_fixture, namespace_syms,
                    tap_bytes, mex_bytes,
                )
                run_resident_case(
                    root, temp, resident_fixture, resident_gateway, resident_syms,
                    mex_bytes, decoded.entry_offset,
                )
                run_tape_case(
                    root, temp, fixture, screen_gateway,
                    syms, tap_bytes, decoded.entry_offset,
                    stem="globals-unmodified", counters=False,
                    expected_exit=34,
                )
            run_tape_case(
                root, temp, overlay_fixture,
                float_gateway if mode == "float5" else screen_gateway,
                syms, tap_bytes, decoded.entry_offset,
                stem=stem, counters=mode == "screen",
                service=float_service if mode == "float5" else None,
            )
            records.append(
                f"{stem}:src={len(source)}:{sha256(source)} "
                f"c48b={len(c48b_bytes)}:{sha256(c48b_bytes)} "
                f"obj={len(obj_bytes)}:{sha256(obj_bytes)} "
                f"mex={len(mex_bytes)}:{sha256(mex_bytes)} "
                f"tap={len(tap_bytes)}:{sha256(tap_bytes)}"
            )

    for record in records:
        print(record)
    print(f"NATIVE NAMESPACE ERRATUM {NAMESPACE_ERRATUM}: {namespace_overlay_note}")
    print(f"NATIVE DIRECT TAPE ERRATUM {DIRECT_TAPE_ERRATUM}: {overlay_note}")
    print(f"NATIVE EXECUTION PASS {REFERENCE_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
