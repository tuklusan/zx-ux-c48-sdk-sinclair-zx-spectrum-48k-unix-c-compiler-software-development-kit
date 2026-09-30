# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from dataclasses import dataclass
import struct

NATIVE_REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"

OBJ1_MAGIC = b"OBJ1"
MEX1_MAGIC = b"MEX1"
M48O_MAGIC = b"M48O"
FORMAT_VERSION = 1
OBJ1_HEADER_SIZE = 24
MEX1_HEADER_SIZE = 24
M48O_HEADER_SIZE = 32
OBJ1_SYMBOL_SIZE = 20
OBJ1_RELOC_SIZE = 6
MEX1_RELOC_SIZE = 2
MAX_NATIVE_IMAGE = 32768
MIN_FAST_STACK = 64
MAX_FAST_STACK = 4096

OBJ_SECTION_UNDEF = 0
OBJ_SECTION_TEXT = 1
OBJ_SECTION_BSS = 2
OBJ_SECTION_ABS = 3
OBJ_SYMBOL_GLOBAL = 1
OBJ_RELOC_ABS16 = 1

M48O_TYPE_BIN = 2
M48O_TARGET_BIN = 1
M48O_CODEC_RAW = 0
TAP_DATA_FLAG = 0xFF
TAP_CHUNK_SIZE = 512
PORTABLE_NAME_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
)


class NativeFormatError(ValueError):
    pass


@dataclass(frozen=True)
class ObjSymbol:
    name: str
    value: int
    section: int
    flags: int = OBJ_SYMBOL_GLOBAL


@dataclass(frozen=True)
class ObjReloc:
    offset: int
    symbol: int
    kind: int = OBJ_RELOC_ABS16


@dataclass(frozen=True)
class ObjImage:
    text: bytes
    bss_size: int
    symbols: tuple[ObjSymbol, ...]
    relocs: tuple[ObjReloc, ...]


@dataclass(frozen=True)
class MexImage:
    image: bytes
    bss_size: int
    entry_offset: int
    min_stack: int
    relocs: tuple[int, ...]


@dataclass(frozen=True)
class TapeBinary:
    name: str
    payload: bytes


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _u16(value: int, what: str) -> int:
    if not 0 <= value <= 0xFFFF:
        raise NativeFormatError(f"{what} is outside unsigned 16-bit range")
    return value


def _checked_add(a: int, b: int, what: str, limit: int = MAX_NATIVE_IMAGE) -> int:
    value = int(a) + int(b)
    if value < 0 or value > limit:
        raise NativeFormatError(f"{what} exceeds {limit} bytes")
    return value


def _checked_mul(a: int, b: int, what: str, limit: int = MAX_NATIVE_IMAGE) -> int:
    value = int(a) * int(b)
    if value < 0 or value > limit:
        raise NativeFormatError(f"{what} exceeds {limit} bytes")
    return value


def _symbol_name_bytes(name: str) -> bytes:
    try:
        raw = name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise NativeFormatError("OBJ1 symbol name is not ASCII") from exc
    if not 1 <= len(raw) <= 15:
        raise NativeFormatError("OBJ1 symbol name must contain 1..15 visible bytes")
    first = raw[0]
    if not (first == 95 or 65 <= first <= 90 or 97 <= first <= 122):
        raise NativeFormatError("OBJ1 symbol name has an invalid first byte")
    for byte in raw[1:]:
        if not (byte == 95 or 48 <= byte <= 57 or 65 <= byte <= 90 or 97 <= byte <= 122):
            raise NativeFormatError("OBJ1 symbol name has an invalid byte")
    return raw


def _decode_symbol_name(field: bytes) -> str:
    try:
        end = field.index(0)
    except ValueError:
        raise NativeFormatError("OBJ1 symbol name lacks a NUL terminator") from None
    if end == 0 or end > 15 or any(field[end + 1 :]):
        raise NativeFormatError("OBJ1 symbol name padding is invalid")
    name = field[:end].decode("ascii", errors="strict")
    _symbol_name_bytes(name)
    return name


def encode_obj1(obj: ObjImage) -> bytes:
    text = bytes(obj.text)
    bss = _u16(obj.bss_size, "OBJ1 BSS size")
    _checked_add(len(text), bss, "OBJ1 text+BSS")
    symbol_bytes = _checked_mul(len(obj.symbols), OBJ1_SYMBOL_SIZE, "OBJ1 symbol table")
    reloc_bytes = _checked_mul(len(obj.relocs), OBJ1_RELOC_SIZE, "OBJ1 relocation table")
    symbol_offset = _checked_add(OBJ1_HEADER_SIZE, len(text), "OBJ1 symbol offset")
    reloc_offset = _checked_add(symbol_offset, symbol_bytes, "OBJ1 relocation offset")
    total = _checked_add(reloc_offset, reloc_bytes, "OBJ1 stored length")
    if total > MAX_NATIVE_IMAGE:
        raise NativeFormatError("OBJ1 stored length exceeds native limit")

    seen: set[str] = set()
    sym_blob = bytearray()
    for sym in obj.symbols:
        raw = _symbol_name_bytes(sym.name)
        if sym.name in seen:
            raise NativeFormatError(f"duplicate OBJ1 symbol {sym.name!r}")
        seen.add(sym.name)
        if sym.section not in {OBJ_SECTION_UNDEF, OBJ_SECTION_TEXT, OBJ_SECTION_BSS, OBJ_SECTION_ABS}:
            raise NativeFormatError("OBJ1 symbol section is invalid")
        if sym.flags & ~OBJ_SYMBOL_GLOBAL:
            raise NativeFormatError("OBJ1 symbol flags are invalid")
        value = _u16(sym.value, "OBJ1 symbol value")
        if sym.section == OBJ_SECTION_UNDEF and (value != 0 or not (sym.flags & OBJ_SYMBOL_GLOBAL)):
            raise NativeFormatError("undefined OBJ1 symbols must be global with value zero")
        if sym.section == OBJ_SECTION_TEXT and value > len(text):
            raise NativeFormatError("OBJ1 text symbol is out of range")
        if sym.section == OBJ_SECTION_BSS and value > bss:
            raise NativeFormatError("OBJ1 BSS symbol is out of range")
        sym_blob.extend(raw.ljust(16, b"\0"))
        sym_blob.extend(struct.pack("<HBB", value, sym.section, sym.flags))

    reloc_blob = bytearray()
    previous = -2
    for rel in obj.relocs:
        offset = _u16(rel.offset, "OBJ1 relocation offset")
        index = _u16(rel.symbol, "OBJ1 relocation symbol")
        if rel.kind != OBJ_RELOC_ABS16:
            raise NativeFormatError("OBJ1 relocation type is invalid")
        if index >= len(obj.symbols):
            raise NativeFormatError("OBJ1 relocation symbol index is out of range")
        if offset + 2 > len(text):
            raise NativeFormatError("OBJ1 relocation word is out of range")
        if offset < previous + 2:
            raise NativeFormatError("OBJ1 relocations must be strictly increasing and non-overlapping")
        previous = offset
        reloc_blob.extend(struct.pack("<HHBB", offset, index, rel.kind, 0))

    body = text + bytes(sym_blob) + bytes(reloc_blob)
    header = bytearray(OBJ1_HEADER_SIZE)
    header[:4] = OBJ1_MAGIC
    header[4] = FORMAT_VERSION
    header[5] = 0
    struct.pack_into(
        "<HHHHHHH",
        header,
        6,
        OBJ1_HEADER_SIZE,
        len(text),
        bss,
        len(obj.symbols),
        len(obj.relocs),
        symbol_offset,
        reloc_offset,
    )
    struct.pack_into("<H", header, 20, crc16_ccitt_false(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, crc16_ccitt_false(bytes(header)))
    return bytes(header) + body


def decode_obj1(data: bytes) -> ObjImage:
    raw = bytes(data)
    if len(raw) < OBJ1_HEADER_SIZE or raw[:4] != OBJ1_MAGIC:
        raise NativeFormatError("OBJ1 header identity is invalid")
    if raw[4] != FORMAT_VERSION or raw[5] != 0:
        raise NativeFormatError("OBJ1 version or flags are invalid")
    header_size, text_size, bss_size, symbol_count, reloc_count, symbol_offset, reloc_offset = struct.unpack_from(
        "<HHHHHHH", raw, 6
    )
    if header_size != OBJ1_HEADER_SIZE:
        raise NativeFormatError("OBJ1 header size is invalid")
    _checked_add(text_size, bss_size, "OBJ1 text+BSS")
    symbol_bytes = _checked_mul(symbol_count, OBJ1_SYMBOL_SIZE, "OBJ1 symbol table")
    reloc_bytes = _checked_mul(reloc_count, OBJ1_RELOC_SIZE, "OBJ1 relocation table")
    expected_symbol = _checked_add(OBJ1_HEADER_SIZE, text_size, "OBJ1 symbol offset")
    expected_reloc = _checked_add(expected_symbol, symbol_bytes, "OBJ1 relocation offset")
    expected_total = _checked_add(expected_reloc, reloc_bytes, "OBJ1 stored length")
    if symbol_offset != expected_symbol or reloc_offset != expected_reloc or len(raw) != expected_total:
        raise NativeFormatError("OBJ1 table offsets or stored length are invalid")
    body = raw[OBJ1_HEADER_SIZE:]
    if crc16_ccitt_false(body) != struct.unpack_from("<H", raw, 20)[0]:
        raise NativeFormatError("OBJ1 body CRC mismatch")
    header = bytearray(raw[:OBJ1_HEADER_SIZE])
    stored_header_crc = struct.unpack_from("<H", header, 22)[0]
    header[22:24] = b"\0\0"
    if crc16_ccitt_false(bytes(header)) != stored_header_crc:
        raise NativeFormatError("OBJ1 header CRC mismatch")

    text = raw[OBJ1_HEADER_SIZE:symbol_offset]
    symbols: list[ObjSymbol] = []
    names: set[str] = set()
    for index in range(symbol_count):
        offset = symbol_offset + index * OBJ1_SYMBOL_SIZE
        name = _decode_symbol_name(raw[offset:offset + 16])
        value, section, flags = struct.unpack_from("<HBB", raw, offset + 16)
        if name in names:
            raise NativeFormatError(f"duplicate OBJ1 symbol {name!r}")
        names.add(name)
        if section not in {OBJ_SECTION_UNDEF, OBJ_SECTION_TEXT, OBJ_SECTION_BSS, OBJ_SECTION_ABS}:
            raise NativeFormatError("OBJ1 symbol section is invalid")
        if flags & ~OBJ_SYMBOL_GLOBAL:
            raise NativeFormatError("OBJ1 symbol flags are invalid")
        if section == OBJ_SECTION_UNDEF and (value != 0 or not (flags & OBJ_SYMBOL_GLOBAL)):
            raise NativeFormatError("undefined OBJ1 symbol is invalid")
        if section == OBJ_SECTION_TEXT and value > text_size:
            raise NativeFormatError("OBJ1 text symbol is out of range")
        if section == OBJ_SECTION_BSS and value > bss_size:
            raise NativeFormatError("OBJ1 BSS symbol is out of range")
        symbols.append(ObjSymbol(name, value, section, flags))

    relocs: list[ObjReloc] = []
    previous = -2
    for index in range(reloc_count):
        offset = reloc_offset + index * OBJ1_RELOC_SIZE
        word_offset, symbol_index, kind, reserved = struct.unpack_from("<HHBB", raw, offset)
        if kind != OBJ_RELOC_ABS16 or reserved != 0:
            raise NativeFormatError("OBJ1 relocation record is invalid")
        if symbol_index >= symbol_count or word_offset + 2 > text_size or word_offset < previous + 2:
            raise NativeFormatError("OBJ1 relocation range or order is invalid")
        previous = word_offset
        relocs.append(ObjReloc(word_offset, symbol_index, kind))
    return ObjImage(text, bss_size, tuple(symbols), tuple(relocs))


def encode_mex1(mex: MexImage) -> bytes:
    image = bytes(mex.image)
    if not image:
        raise NativeFormatError("MEX1 image must not be empty")
    bss = _u16(mex.bss_size, "MEX1 BSS size")
    _checked_add(len(image), bss, "MEX1 image+BSS")
    entry = _u16(mex.entry_offset, "MEX1 entry offset")
    if entry >= len(image):
        raise NativeFormatError("MEX1 entry offset is outside the image")
    if not MIN_FAST_STACK <= mex.min_stack <= MAX_FAST_STACK:
        raise NativeFormatError("MEX1 minimum stack is outside the native range")
    reloc_bytes = _checked_mul(len(mex.relocs), MEX1_RELOC_SIZE, "MEX1 relocation table")
    reloc_offset = _checked_add(MEX1_HEADER_SIZE, len(image), "MEX1 relocation offset")
    total = _checked_add(reloc_offset, reloc_bytes, "MEX1 stored length")
    previous = -2
    reloc_blob = bytearray()
    for value in mex.relocs:
        offset = _u16(value, "MEX1 relocation offset")
        if offset + 2 > len(image) or offset < previous + 2:
            raise NativeFormatError("MEX1 relocations must be strictly increasing and non-overlapping")
        addend = int.from_bytes(image[offset:offset + 2], "little")
        if addend > len(image) + bss:
            raise NativeFormatError("MEX1 relocation addend is outside image+BSS")
        previous = offset
        reloc_blob.extend(struct.pack("<H", offset))
    body = image + bytes(reloc_blob)
    header = bytearray(MEX1_HEADER_SIZE)
    header[:4] = MEX1_MAGIC
    header[4] = FORMAT_VERSION
    header[5] = 0
    struct.pack_into(
        "<HHHHHHH",
        header,
        6,
        MEX1_HEADER_SIZE,
        len(image),
        bss,
        entry,
        mex.min_stack,
        len(mex.relocs),
        reloc_offset,
    )
    struct.pack_into("<H", header, 20, crc16_ccitt_false(body))
    struct.pack_into("<H", header, 22, 0)
    struct.pack_into("<H", header, 22, crc16_ccitt_false(bytes(header)))
    if total != len(header) + len(body):
        raise AssertionError("MEX1 length accounting error")
    return bytes(header) + body


def decode_mex1(data: bytes) -> MexImage:
    raw = bytes(data)
    if len(raw) < MEX1_HEADER_SIZE or raw[:4] != MEX1_MAGIC:
        raise NativeFormatError("MEX1 header identity is invalid")
    if raw[4] != FORMAT_VERSION or raw[5] != 0:
        raise NativeFormatError("MEX1 version or flags are invalid")
    header_size, image_size, bss_size, entry, min_stack, reloc_count, reloc_offset = struct.unpack_from(
        "<HHHHHHH", raw, 6
    )
    if header_size != MEX1_HEADER_SIZE or image_size == 0:
        raise NativeFormatError("MEX1 header size or image size is invalid")
    _checked_add(image_size, bss_size, "MEX1 image+BSS")
    reloc_bytes = _checked_mul(reloc_count, MEX1_RELOC_SIZE, "MEX1 relocation table")
    expected_offset = _checked_add(MEX1_HEADER_SIZE, image_size, "MEX1 relocation offset")
    expected_total = _checked_add(expected_offset, reloc_bytes, "MEX1 stored length")
    if reloc_offset != expected_offset or len(raw) != expected_total:
        raise NativeFormatError("MEX1 relocation offset or stored length is invalid")
    if entry >= image_size or not MIN_FAST_STACK <= min_stack <= MAX_FAST_STACK:
        raise NativeFormatError("MEX1 entry or stack contract is invalid")
    body = raw[MEX1_HEADER_SIZE:]
    if crc16_ccitt_false(body) != struct.unpack_from("<H", raw, 20)[0]:
        raise NativeFormatError("MEX1 body CRC mismatch")
    header = bytearray(raw[:MEX1_HEADER_SIZE])
    stored_header_crc = struct.unpack_from("<H", header, 22)[0]
    header[22:24] = b"\0\0"
    if crc16_ccitt_false(bytes(header)) != stored_header_crc:
        raise NativeFormatError("MEX1 header CRC mismatch")
    image = raw[MEX1_HEADER_SIZE:reloc_offset]
    relocs: list[int] = []
    previous = -2
    for index in range(reloc_count):
        offset = struct.unpack_from("<H", raw, reloc_offset + 2 * index)[0]
        if offset + 2 > image_size or offset < previous + 2:
            raise NativeFormatError("MEX1 relocation range or order is invalid")
        addend = int.from_bytes(image[offset:offset + 2], "little")
        if addend > image_size + bss_size:
            raise NativeFormatError("MEX1 relocation addend is outside image+BSS")
        previous = offset
        relocs.append(offset)
    return MexImage(image, bss_size, entry, min_stack, tuple(relocs))


def validate_portable_name(name: str) -> bytes:
    try:
        raw = name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise NativeFormatError("M48O name is not ASCII") from exc
    if not 1 <= len(raw) <= 10 or name in {".", ".."} or any(b not in PORTABLE_NAME_BYTES for b in raw):
        raise NativeFormatError("M48O name is not a portable 1..10 byte base name")
    return raw


def encode_m48o_bin(name: str, mex_payload: bytes) -> bytes:
    payload = bytes(mex_payload)
    decode_mex1(payload)
    if len(payload) > MAX_NATIVE_IMAGE:
        raise NativeFormatError("M48O BIN payload exceeds native limit")
    raw_name = validate_portable_name(name)
    header = bytearray(M48O_HEADER_SIZE)
    header[:4] = M48O_MAGIC
    header[4] = FORMAT_VERSION
    header[5] = M48O_TYPE_BIN
    header[6] = 0
    header[7] = M48O_TARGET_BIN
    struct.pack_into("<HHH", header, 8, len(payload), len(payload), M48O_CODEC_RAW)
    struct.pack_into("<H", header, 14, crc16_ccitt_false(payload))
    header[16:26] = raw_name.ljust(10, b"\0")
    header[26:28] = b"\0\0"
    header[28:32] = b"\0\0\0\0"
    struct.pack_into("<H", header, 26, crc16_ccitt_false(bytes(header)))
    return bytes(header) + payload


def decode_m48o_bin(data: bytes) -> TapeBinary:
    raw = bytes(data)
    if len(raw) < M48O_HEADER_SIZE or raw[:4] != M48O_MAGIC:
        raise NativeFormatError("M48O header identity is invalid")
    if raw[4] != FORMAT_VERSION or raw[5] != M48O_TYPE_BIN or raw[6] != 0 or raw[7] != M48O_TARGET_BIN:
        raise NativeFormatError("M48O BIN type, flags, or target are invalid")
    physical, logical, codec = struct.unpack_from("<HHH", raw, 8)
    if codec != M48O_CODEC_RAW or physical != logical or physical > MAX_NATIVE_IMAGE:
        raise NativeFormatError("M48O RAW length or codec is invalid")
    if len(raw) != M48O_HEADER_SIZE + physical or raw[28:32] != b"\0\0\0\0":
        raise NativeFormatError("M48O stored length or reserved bytes are invalid")
    field = raw[16:26]
    try:
        end = field.index(0)
    except ValueError:
        end = len(field)
    if any(field[end:]):
        raise NativeFormatError("M48O name padding is invalid")
    name = field[:end].decode("ascii", errors="strict")
    validate_portable_name(name)
    header = bytearray(raw[:M48O_HEADER_SIZE])
    stored_header_crc = struct.unpack_from("<H", header, 26)[0]
    header[26:28] = b"\0\0"
    if crc16_ccitt_false(bytes(header)) != stored_header_crc:
        raise NativeFormatError("M48O header CRC mismatch")
    payload = raw[M48O_HEADER_SIZE:]
    if crc16_ccitt_false(payload) != struct.unpack_from("<H", raw, 14)[0]:
        raise NativeFormatError("M48O payload CRC mismatch")
    decode_mex1(payload)
    return TapeBinary(name, payload)


def _tap_block(body: bytes) -> bytes:
    framed = bytes((TAP_DATA_FLAG,)) + body
    checksum = 0
    for byte in framed:
        checksum ^= byte
    framed += bytes((checksum,))
    return struct.pack("<H", len(framed)) + framed


def build_bin_tap(name: str, mex_payload: bytes) -> bytes:
    m48o = encode_m48o_bin(name, mex_payload)
    header = m48o[:M48O_HEADER_SIZE]
    payload = m48o[M48O_HEADER_SIZE:]
    out = bytearray(_tap_block(header))
    for offset in range(0, len(payload), TAP_CHUNK_SIZE):
        out.extend(_tap_block(payload[offset:offset + TAP_CHUNK_SIZE]))
    built = bytes(out)
    parsed = parse_bin_tap(built)
    if parsed != TapeBinary(name, bytes(mex_payload)):
        raise NativeFormatError("internal TAP round-trip validation did not match")
    return built


def _read_tap_block(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 2 > len(data):
        raise NativeFormatError("truncated TAP block length")
    size = int.from_bytes(data[offset:offset + 2], "little")
    offset += 2
    if size < 2 or offset + size > len(data):
        raise NativeFormatError("truncated TAP block")
    framed = data[offset:offset + size]
    if framed[0] != TAP_DATA_FLAG:
        raise NativeFormatError("M48O TAP block must use data flag FF")
    checksum = 0
    for byte in framed:
        checksum ^= byte
    if checksum:
        raise NativeFormatError("TAP checksum mismatch")
    return framed[1:-1], offset + size


def parse_bin_tap(data: bytes) -> TapeBinary:
    raw = bytes(data)
    header, offset = _read_tap_block(raw, 0)
    if len(header) != M48O_HEADER_SIZE:
        raise NativeFormatError("M48O TAP header block size is invalid")
    physical = int.from_bytes(header[8:10], "little")
    payload = bytearray()
    left = physical
    while left:
        chunk, offset = _read_tap_block(raw, offset)
        expected = min(TAP_CHUNK_SIZE, left)
        if len(chunk) != expected:
            raise NativeFormatError("M48O TAP payload chunk size is invalid")
        payload.extend(chunk)
        left -= len(chunk)
    if offset != len(raw):
        raise NativeFormatError("M48O TAP has trailing blocks")
    return decode_m48o_bin(header + bytes(payload))
