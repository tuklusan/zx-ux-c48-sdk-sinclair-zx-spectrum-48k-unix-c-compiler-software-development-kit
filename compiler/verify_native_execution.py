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

REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"
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
            "test_proc1",
            "test_alloc_index",
            "test_expect_screen",
            "p514_committed",
            "zx48_p511_format",
            "zx48_p514_tape_format",
            "zx48_p514_tape_finish_ok",
            "zx48_p514_format_abort",
            "zx48_p514_format_rollback",
            "gateway_write_bytes",
            "gateway_attr_calls",
            "gateway_plot_calls",
            "gateway_udg_calls",
        ),
    )
    return cp, main, gate, syms


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


def host_status(program, temp: Path, stem: str) -> int:
    path = temp / f"{stem}.c48b"
    write_c48b(path, program)
    cp = subprocess.run(
        [sys.executable, str(HERE / "c48run.py"), "--headless", str(path)],
        cwd=SDK,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    require(cp.returncode == 0, f"host semantic fixture failed: {stem}: {cp.stderr}")
    return cp.returncode


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
) -> None:
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
        (syms["zx48_p514_tape_finish_ok"], 35),
        (syms["zx48_p514_format_abort"], 33),
        (syms["zx48_p514_format_rollback"], 34),
    )
    for index, (address, status) in enumerate(internal_failures, 2):
        debugger_parts.append(
            f"breakpoint 0x{address:04x}\ncommands {index}\nexit {status}\nend\n"
        )
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
        cp.returncode == 0,
        f"native tape execution failed: {stem}: exit={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.native_root.resolve()
    verify_native_identity(root)

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
            (
                b"int fact(int n){if(n<2)return 1;return n*fact(n-1);}"
                b"int main(void){if(fact(5)!=120)return 1;return 0;}"
            ),
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
        float_service, float_gateway = assemble_float_service(root, temp)
        records: list[str] = []
        for stem, source, mode in cases:
            program, obj, mex = build_native(source, stem + ".c")
            host_status(program, temp, stem)
            obj_bytes = encode_obj1(obj)
            mex_bytes = encode_mex1(mex)
            tap_bytes = build_bin_tap("NATIVE", mex_bytes)
            decoded = decode_mex1(mex_bytes)
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
            run_tape_case(
                root, temp, fixture,
                float_gateway if mode == "float5" else screen_gateway,
                syms, tap_bytes, decoded.entry_offset,
                stem=stem, counters=mode == "screen",
                service=float_service if mode == "float5" else None,
            )
            records.append(
                f"{stem}:src={len(source)}:{sha256(source)} "
                f"obj={len(obj_bytes)}:{sha256(obj_bytes)} "
                f"mex={len(mex_bytes)}:{sha256(mex_bytes)} "
                f"tap={len(tap_bytes)}:{sha256(tap_bytes)}"
            )

    for record in records:
        print(record)
    print(f"NATIVE EXECUTION PASS {REFERENCE_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
