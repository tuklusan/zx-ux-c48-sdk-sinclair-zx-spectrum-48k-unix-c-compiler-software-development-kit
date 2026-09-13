#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
a = root / "usr" / "src" / "ailmzx48"
module = a / "tooling" / "context_reference.py"
test = a / "evaluation" / "test_context_reference.py"
if not module.is_file() or not test.is_file():
    raise SystemExit("context reference files missing")

report = a / "evaluation" / "context-reference-report.json"
subprocess.run(
    [sys.executable, "-B", str(test), "--report", str(report)],
    cwd=root,
    check=True,
)

design_path = a / "AILMZX48-DETAILED-DESIGN.md"
design = design_path.read_text(encoding="utf-8")
if design.count("Revision: 0.19-draft") != 1:
    raise SystemExit("unexpected design revision")
design = design.replace(
    "Revision: 0.19-draft",
    "Revision: 0.20-draft",
    1,
)
marker = "### 8.4 Correction and supersession rule"
if design.count(marker) != 1:
    raise SystemExit("design insertion marker mismatch")
note = (
    "Implementation measurement note (Revision 0.20): a deterministic "
    "host reference for the Candidate-A L0/L1/L2/session-literal context "
    "machinery now exists in `tooling/context_reference.py`. It models "
    "the 896-byte L0 ring and 32-descriptor limit, complete-dialogue "
    "eviction, 48 fixed L1 records, 24 fixed L2 records, saturating ages, "
    "deterministic L1-to-L2 compaction/L2 eviction, four-record bounded "
    "retrieval, generation-checked session literals, and transactional "
    "preflight by clone-and-apply. Host-only descriptor metadata is an "
    "oracle sidecar; the target descriptor remains exactly four bytes. "
    "The retained stress report covers 500 dialogue pairs and 51,000 raw "
    "source-equivalent bytes while all modeled target context capacities "
    "remain fixed. This is a host correctness oracle, not yet proof that "
    "the C48 target implements the same state machine or native memory "
    "layout.\n\n"
)
design = design.replace(marker, note + marker, 1)
design_path.write_text(design, encoding="utf-8", newline="\n")
print("host context reference verified and design updated")
