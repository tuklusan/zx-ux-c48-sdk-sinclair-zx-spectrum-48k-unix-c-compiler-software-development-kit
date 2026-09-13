from pathlib import Path

path = Path("usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md")
text = path.read_text(encoding="utf-8")

text = text.replace("Revision: 0.10-draft", "Revision: 0.11-draft", 1)
text = text.replace(
    "Revision 0.10 retains it as a corrected benchmark baseline",
    "Revision 0.11 retains it as a corrected benchmark baseline",
    1,
)
text = text.replace(
    "Revision 0.10 keeps conceptual target interfaces deliberately within",
    "Revision 0.11 keeps conceptual target interfaces deliberately within",
    1,
)
text = text.replace(
    "## 23. Open design questions after Revision 0.10",
    "## 23. Open design questions after Revision 0.11",
    1,
)

needle = """### 18.2 Required final proof sequence

Before user documentation claims an exact command sequence, the native implementation must prove the following on a 48K configuration:
"""
replacement = """### 18.2 Operator Build Overview

The release operator has two conceptual build paths. Both begin from an exact accepted source/model identity and both must preserve the same runtime interfaces, memory limits, provenance records and release gates.

For the **host/SDK build**, the operator starts from a clean repository `main` plus an admitted, content-addressed corpus/provenance snapshot. Deterministic host tooling builds the resident vocabulary/topic/semantic maps, bounded hot LM tables, cold A48M knowledge object(s), interface identity and model manifest. The repository C48 toolchain then compiles/links `ailmzx48.c` with the candidate heap/stack settings and produces the SDK runnable artifact plus the native executable/model payloads intended for packaging. Host format tests, active SDK conversations, model/interface checks, `MANIFEST.sha256`, `git diff --check` and the complete SDK release verifier must all pass before those identities are eligible for a release tape.

For the **native-on-ZX-UX build**, model training is not repeated on the Spectrum. The operator boots canonical ZX-UX, loads the source/development tape containing the native C48 toolchain, `ailmzx48` source and already-generated accepted model resources, compiles the source to the canonical native object form, links the MEX1 image with measured heap/stack settings, verifies the resulting executable/model objects using documented target facilities, and saves the accepted runtime objects to cassette. Build-only source/tool/intermediate RAM objects are then reclaimed through supported ZX-UX semantics before runtime memory proof. Host and native builds must use the same frozen source/model/interface contracts; byte-identical executables are claimed only if measurement proves them, otherwise retained hashes plus behavioral/native verification identify each accepted build.

Packaging is the final operator step, not an inference step: the accepted prebuilt executable and required model resource(s) form the runtime/distribution tape, while source, native build inputs and development tools belong on the source/development tape. Exact M48O order, target object names and final commands remain subject to the proof sequence below rather than being invented here.

### 18.3 Independent Installation Overview

Ordinary installation/use starts from a clean 48K-compatible machine that can boot the canonical ZX-UX system tape and from an accepted `ailmzx48` runtime/distribution tape. The user does **not** need the C48 compiler, source/development tape, host SDK, training corpus or model-building tools merely to install and run the released program.

The runtime tape contains the prebuilt MEX1 executable plus every required cold-model/resource object and the release identity information needed by the documented verification flow. After boot, the user enters the normal ZX-UX shell session, scans/loads or directly executes the runtime objects only through the cassette/object operations actually provided by ZX-UX, and verifies the loaded objects with documented tape/object metadata checks. The normal launch path must leave the required model object(s) resident in the form expected by `ailmzx48`; launch-time A48M length/interface/integrity validation remains mandatory before model records can influence an answer. Exact target names, directories, commands and tape ordering are deliberately deferred until native proof freezes them.

A successful launch presents the normal startup conversation. Entering exact `q` at a normal input prompt terminates the program cleanly and returns control according to the proven ZX-UX launch path; no hidden daemon or background model service remains resident. Process allocations, stack and open-description/decoder state are released by normal close/exit semantics.

"Uninstall" on ZX-UX primarily means reclaiming the volatile runtime objects after `ailmzx48` has exited and all relevant handles are closed. Mutable executable/model RAM objects are removed only through supported object-removal semantics; pinned/system resources are never treated as application files. Removing RAM objects does not erase their cassette copies, because cassette is sequential persistent media rather than an in-place deletable filesystem. A distribution tape that should no longer contain `ailmzx48` is replaced/recreated without those objects rather than being described as having an in-place uninstall operation. Memory/extent evidence after reclaim must show that the application's arena allocations are actually gone.

### 18.4 Required final proof sequence

Before user documentation claims an exact command sequence, the native implementation must prove the following on a 48K configuration:
"""
if needle not in text:
    raise SystemExit("section 18.2 anchor not found")
text = text.replace(needle, replacement, 1)
text = text.replace(
    "### 18.3 Compiler/linker lifetime question",
    "### 18.5 Compiler/linker lifetime question",
    1,
)
text = text.replace(
    "### 18.4 Reboot fallback",
    "### 18.6 Reboot fallback",
    1,
)

checks = [
    "Revision: 0.11-draft",
    "### 18.2 Operator Build Overview",
    "### 18.3 Independent Installation Overview",
    "### 18.4 Required final proof sequence",
    "### 18.5 Compiler/linker lifetime question",
    "### 18.6 Reboot fallback",
    "The user does **not** need the C48 compiler",
    "Removing RAM objects does not erase their cassette copies",
]
for item in checks:
    if text.count(item) != 1:
        raise SystemExit(f"postcondition failed for {item!r}: {text.count(item)}")
if "Revision 0.10" in text or "after Revision 0.10" in text:
    raise SystemExit("stale Revision 0.10 reference remains")

path.write_text(text, encoding="utf-8", newline="\n")
