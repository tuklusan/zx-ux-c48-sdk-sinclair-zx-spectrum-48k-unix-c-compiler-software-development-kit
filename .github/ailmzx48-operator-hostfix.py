from pathlib import Path

path = Path("usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md")
text = path.read_text(encoding="utf-8")
old = """For the **host/SDK build**, the operator starts from a clean repository `main` plus an admitted, content-addressed corpus/provenance snapshot. Deterministic host tooling builds the resident vocabulary/topic/semantic maps, bounded hot LM tables, cold A48M knowledge object(s), interface identity and model manifest. The repository C48 toolchain then compiles/links `ailmzx48.c` with the candidate heap/stack settings and produces the SDK runnable artifact plus the native executable/model payloads intended for packaging. Host format tests, active SDK conversations, model/interface checks, `MANIFEST.sha256`, `git diff --check` and the complete SDK release verifier must all pass before those identities are eligible for a release tape.
"""
new = """For the **host/SDK build**, the operator starts from a clean repository `main` plus an admitted, content-addressed corpus/provenance snapshot. Deterministic host tooling builds the resident vocabulary/topic/semantic maps, bounded hot LM tables, cold A48M knowledge object(s), interface identity and model manifest. The portable repository C48 toolchain compiles `ailmzx48.c` into the deterministic SDK C48B1/VM form and produces the runnable SDK artifact under the project `usr/bin/ailmzx48` release path. That host artifact is explicitly not OBJ1, MEX1 or Z80 machine code. Host tooling also emits the accepted model resources/manifests that feed native packaging. Host format tests, active SDK conversations, model/interface checks, `MANIFEST.sha256`, `git diff --check` and the complete SDK release verifier must all pass before those identities can feed the native release build.
"""
if text.count(old) != 1:
    raise SystemExit(f"host build paragraph count={text.count(old)}")
text = text.replace(old, new, 1)
old2 = """Packaging is the final operator step, not an inference step: the accepted prebuilt executable and required model resource(s) form the runtime/distribution tape, while source, native build inputs and development tools belong on the source/development tape. Exact M48O order, target object names and final commands remain subject to the proof sequence below rather than being invented here.
"""
new2 = """Packaging is the final operator step, not an inference step: the accepted native MEX1 executable from the native build path and the required accepted model resource(s) form the runtime/distribution tape, while source, native build inputs and development tools belong on the source/development tape. The SDK C48B1 artifact remains a host/SDK deliverable and is never mislabeled as a Spectrum executable. Exact M48O order, target object names and final commands remain subject to the proof sequence below rather than being invented here.
"""
if text.count(old2) != 1:
    raise SystemExit(f"packaging paragraph count={text.count(old2)}")
text = text.replace(old2, new2, 1)
for item in (
    "That host artifact is explicitly not OBJ1, MEX1 or Z80 machine code.",
    "the accepted native MEX1 executable from the native build path",
    "The SDK C48B1 artifact remains a host/SDK deliverable",
):
    if text.count(item) != 1:
        raise SystemExit(f"postcondition failed: {item!r}")
path.write_text(text, encoding="utf-8", newline="\n")
