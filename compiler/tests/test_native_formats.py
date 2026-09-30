# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import unittest

from c48.native_format import (
    MAX_NATIVE_IMAGE,
    MEX1_HEADER_SIZE,
    NativeFormatError,
    OBJ_SECTION_BSS,
    OBJ_SECTION_TEXT,
    ObjImage,
    ObjReloc,
    ObjSymbol,
    MexImage,
    build_bin_tap,
    decode_mex1,
    decode_obj1,
    encode_mex1,
    encode_obj1,
    parse_bin_tap,
)


class NativeFormatTests(unittest.TestCase):
    def test_obj1_round_trip_with_relocation(self) -> None:
        obj = ObjImage(
            b"\x21\x00\x00\xc9",
            2,
            (
                ObjSymbol("main", 0, OBJ_SECTION_TEXT),
                ObjSymbol("slot", 0, OBJ_SECTION_BSS),
            ),
            (ObjReloc(1, 1),),
        )
        raw = encode_obj1(obj)
        self.assertEqual(decode_obj1(raw), obj)
        self.assertEqual(encode_obj1(decode_obj1(raw)), raw)

    def test_obj1_rejects_overlap_and_bad_crc(self) -> None:
        symbols = (ObjSymbol("main", 0, OBJ_SECTION_TEXT),)
        with self.assertRaises(NativeFormatError):
            encode_obj1(
                ObjImage(
                    b"\x00\x00\x00",
                    0,
                    symbols,
                    (ObjReloc(0, 0), ObjReloc(1, 0)),
                )
            )
        raw = bytearray(encode_obj1(ObjImage(b"\xc9", 0, symbols, ())))
        raw[-1] ^= 1
        with self.assertRaises(NativeFormatError):
            decode_obj1(bytes(raw))

    def test_mex1_round_trip(self) -> None:
        mex = MexImage(b"\x21\x03\x00\xc9", 0, 0, 256, (1,))
        raw = encode_mex1(mex)
        self.assertEqual(decode_mex1(raw), mex)
        self.assertEqual(len(raw), MEX1_HEADER_SIZE + len(mex.image) + 2)

    def test_mex1_widened_bounds(self) -> None:
        with self.assertRaises(NativeFormatError):
            encode_mex1(MexImage(b"\x00" * MAX_NATIVE_IMAGE, 1, 0, 256, ()))
        with self.assertRaises(NativeFormatError):
            encode_mex1(MexImage(b"\xc9", 0, 1, 256, ()))

    def test_mex1_independent_native_ceilings(self) -> None:
        stored_limit = encode_mex1(MexImage(b"\xc9" + b"\0" * (32744 - 1), 0, 0, 256, ()))
        self.assertEqual(len(stored_limit), 32768)
        with self.assertRaises(NativeFormatError):
            encode_mex1(MexImage(b"\xc9" + b"\0" * 32744, 0, 0, 256, ()))
        memory_limit = encode_mex1(MexImage(b"\xc9", 32767, 0, 256, ()))
        self.assertLess(len(memory_limit), 32768)
        with self.assertRaises(NativeFormatError):
            encode_mex1(MexImage(b"\xc9", 32768, 0, 256, ()))

    def test_bin_tap_round_trip(self) -> None:
        mex = encode_mex1(MexImage(b"\xc9", 0, 0, 256, ()))
        tap = build_bin_tap("HELLO", mex)
        parsed = parse_bin_tap(tap)
        self.assertEqual(parsed.name, "HELLO")
        self.assertEqual(parsed.payload, mex)

    def test_bin_tap_rejects_bad_name_and_checksum(self) -> None:
        mex = encode_mex1(MexImage(b"\xc9", 0, 0, 256, ()))
        with self.assertRaises(NativeFormatError):
            build_bin_tap("../bad", mex)
        tap = bytearray(build_bin_tap("OK", mex))
        tap[-1] ^= 1
        with self.assertRaises(NativeFormatError):
            parse_bin_tap(bytes(tap))


if __name__ == "__main__":
    unittest.main()
