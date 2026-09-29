# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
COMPILER=ROOT/"compiler"
sys.path.insert(0,str(COMPILER))
import check_license_headers as headers
import c48srctap

class LicenseHeaderPolicyTests(unittest.TestCase):
    def test_canonical_python_and_launcher_forms(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"x.py").write_text(headers._expected("x.py")+"x = 1\n",encoding="utf-8")
            (root/"c48").write_text("#!/bin/sh\n"+headers._expected("c48")+"exit 0\n",encoding="utf-8")
            self.assertEqual(headers.check_tree(root),[])
    def test_legacy_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"x.py").write_text("# Copyright (c) 2026 SANYALnet Labs.\nprint(1)\n",encoding="utf-8")
            self.assertTrue(any("canonical header" in e for e in headers.check_tree(root)))
    def test_unknown_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"x.weird").write_text("x",encoding="utf-8")
            self.assertTrue(any("unclassified" in e for e in headers.check_tree(root)))
    def test_office_exemptions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for suffix in headers.OFFICE_SUFFIXES:(root/("x"+suffix)).write_bytes(b"x")
            self.assertEqual(headers.check_tree(root),[])
    def test_pinned_paths_are_narrow(self):
        self.assertEqual(headers.classify("usr/src/examples/hello.c"),"pinned")
        self.assertEqual(headers.classify("usr/src/examples/new-file.c"),"header")
    def test_c48_header_reconstructs_and_compiles(self):
        parts=headers.C_HEADER.splitlines(); self.assertTrue(all(len(line.encode("utf-8"))<=64 for line in parts))
        self.assertEqual(parts[0][3:]+" "+parts[1][3:],headers.LINE1)
        self.assertEqual(parts[3][3:]+" "+parts[4][3:],headers.LINE2)
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"header.c"; out=Path(td)/"header.c48b"
            src.write_text(headers.C_HEADER+"int main(void) { return 0; }\n",encoding="utf-8")
            cp=subprocess.run([sys.executable,"-B",str(COMPILER/"c48.py"),str(src),"-o",str(out)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr); self.assertTrue(out.is_file())
    def test_source_tape_canonical_header_exception_is_narrow(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.c"; good=headers.C_HEADER.encode("utf-8")+b"int main(void) { return 0; }\n"
            c48srctap._validate_source_text(p,good)
            with self.assertRaises(c48srctap.SourceTapeError): c48srctap._validate_source_text(p,b"// x \xc2\xa9\nint main(void) { return 0; }\n")
            with self.assertRaises(c48srctap.SourceTapeError): c48srctap._validate_source_text(p,headers.C_HEADER.encode("utf-8")+"int x=1; // ©\n".encode("utf-8"))
    def test_generic_policy_hook_requires_external_context(self):
        spec=importlib.util.spec_from_file_location("policy",COMPILER/"check_project_banned_words.py"); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module)
        with self.assertRaises(module.PolicyContextUnavailable): module.check_tree(ROOT)
        cp=subprocess.run([sys.executable,"-B",str(COMPILER/"check_project_banned_words.py")],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.assertNotEqual(cp.returncode,0)
        self.assertIn("policy context unavailable",cp.stderr)

if __name__=="__main__": unittest.main()
