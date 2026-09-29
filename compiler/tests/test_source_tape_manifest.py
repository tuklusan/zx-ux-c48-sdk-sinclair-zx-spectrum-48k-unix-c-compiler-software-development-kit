# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
COMPILER = ROOT / "compiler"
sys.path.insert(0, str(COMPILER))

import c48srctap

MANIFEST = COMPILER / "source_tape_manifest.json"


class LockedSourceTapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
        cls.tapes = cls.manifest["tapes"]

    def test_locked_manifest_has_57_unique_tapes(self):
        self.assertEqual(self.manifest["schema"], 1)
        self.assertEqual(self.manifest["target"], "USERHOME")
        self.assertEqual(self.manifest["tape_count"], 57)
        outputs = [item["output"] for item in self.tapes]
        self.assertEqual(len(outputs), 57)
        self.assertEqual(len(set(outputs)), 57)
        self.assertFalse(any("ailmzx48" in output for output in outputs))

    def test_locked_tapes_cover_compiled_corpus_except_large_app(self):
        expected = set()
        for path in (ROOT / "usr" / "bin").rglob("*.c48b"):
            rel = path.relative_to(ROOT).as_posix()
            if "/ailmzx48/" in "/" + rel:
                continue
            expected.add(rel[:-5] + ".src.tap")
        actual = {item["output"] for item in self.tapes}
        self.assertEqual(actual, expected)

    def test_no_unlocked_source_tapes(self):
        tracked = {item["output"] for item in self.tapes}
        present = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "usr" / "bin").rglob("*.src.tap")
        }
        self.assertEqual(present, tracked)

    def test_frozen_tapes_match_sources_and_generator(self):
        for item in self.tapes:
            source_args = [
                str(ROOT / source["path"])
                for source in item["sources"]
            ]
            overrides = []
            for source, path in zip(item["sources"], source_args):
                if Path(path).name != source["name"]:
                    overrides.append([path, source["name"]])
            specs = c48srctap.collect_sources(source_args, overrides)
            rebuilt = c48srctap.build_tape(specs)
            frozen = (ROOT / item["output"]).read_bytes()
            self.assertEqual(frozen, rebuilt, item["output"])
            decoded = c48srctap.parse_tape(frozen)
            self.assertEqual(
                [obj.name for obj in decoded],
                [source["name"] for source in item["sources"]],
                item["output"],
            )
            self.assertEqual(
                [obj.payload for obj in decoded],
                [
                    (ROOT / source["path"]).read_bytes()
                    for source in item["sources"]
                ],
                item["output"],
            )
            self.assertTrue(
                all(
                    obj.target == c48srctap.TARGET_USERHOME
                    for obj in decoded
                ),
                item["output"],
            )


if __name__ == "__main__":
    unittest.main()
