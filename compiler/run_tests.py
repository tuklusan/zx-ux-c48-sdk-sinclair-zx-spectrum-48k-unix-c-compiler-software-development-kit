#!/usr/bin/env python3
# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations
import unittest
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
