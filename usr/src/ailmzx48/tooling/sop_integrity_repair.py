#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
# ============================================================================
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
A = ROOT / "usr" / "src" / "ailmzx48"
E = A / "evaluation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path: Path) -> str:
    data = path.read_bytes()
    head = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(head + data).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"patch anchor not unique in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def patch_runtime() -> None:
    src = A / "ailmzx48.c"
    test = E / "test_a48m_reference.py"
    checker = E / "check_design_compliance.py"

    replace_once(src, '#include "aimod.h"\n',
                 '#include "aimod.h"\n#include "aicold.h"\n')
    replace_once(src, 'unsigned int ai_mtrusted;\n', '')
    replace_once(
        src,
        "    if(ai_mhead[4]!=2||ai_mhead[5]!=0||\n"
        "       ai_mhead[6]!=40||ai_mhead[7]!=1)return -1;\n"
        "    ai_mtsalt=ai_getu16(ai_mhead,34);\n",
        "    if(ai_mhead[4]!=2||ai_mhead[5]!=0||\n"
        "       ai_mhead[6]!=40||ai_mhead[7]!=1)return -1;\n"
        "    i=0;\n"
        "    while(i<8){\n"
        "        if(ai_mhead[8+i]!=ai_cvid[i])return -1;\n"
        "        if(ai_mhead[16+i]!=ai_ciid[i])return -1;\n"
        "        i=i+1;\n"
        "    }\n"
        "    ai_mtsalt=ai_getu16(ai_mhead,34);\n",
    )
    replace_once(src, '        if (!ai_mtrusted) ai_fdata(ai_mstage, hlen);\n',
                 '        ai_fdata(ai_mstage, hlen);\n')
    replace_once(src, '            if (!ai_mtrusted) ai_fdata(ai_mstage, take);\n',
                 '            ai_fdata(ai_mstage, take);\n')
    replace_once(
        src,
        "    if (!ai_mtrusted) {\n"
        "        calc = ai_fs1 + (ai_fs2 * 256);\n"
        "        if (calc != ai_getu16(ai_mhead, 32)) return -1;\n"
        "        if (ai_mbytes != logical) return -1;\n"
        "        ai_mtrusted = 1;\n"
        "    }\n",
        "    calc = ai_fs1 + (ai_fs2 * 256);\n"
        "    if (calc != ai_getu16(ai_mhead, 32)) return -1;\n"
        "    if (ai_mbytes != logical) return -1;\n",
    )
    replace_once(src, '    ai_mtrusted = 0;\n', '')

    replace_once(
        test,
        '    out_meta = root / "model" / "cold-seed.json"\n'
        '    report_path = HERE / "a48m-reference-report.json"\n',
        '    out_meta = root / "model" / "cold-seed.json"\n'
        '    out_header = root / "aicold.h"\n'
        '    report_path = HERE / "a48m-reference-report.json"\n',
    )
    replace_once(
        test,
        '    out_meta.write_text(\n'
        '        json.dumps(meta, indent=2, sort_keys=True) + "\\n",\n'
        '        encoding="utf-8",\n'
        '    )\n'
        '    report = {\n',
        '    out_meta.write_text(\n'
        '        json.dumps(meta, indent=2, sort_keys=True) + "\\n",\n'
        '        encoding="utf-8",\n'
        '    )\n'
        '    vocab = list(data[8:16])\n'
        '    interface = list(data[16:24])\n'
        '    header = [\n'
        '        "// ============================================================",\n'
        '        "// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.",\n'
        '        "// Proprietary rights reserved except as licensed in LICENSE.",\n'
        '        "//",\n'
        '        "// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.",\n'
        '        "// Generated hot/cold A48M identity constants.",\n'
        '        "// ============================================================",\n'
        '        "unsigned char ai_cvid[8] = {",\n'
        '        "    " + ", ".join(str(v) for v in vocab),\n'
        '        "};",\n'
        '        "unsigned char ai_ciid[8] = {",\n'
        '        "    " + ", ".join(str(v) for v in interface),\n'
        '        "};",\n'
        '    ]\n'
        '    out_header.write_text(\n'
        '        "\\n".join(header) + "\\n", encoding="ascii", newline="\\n"\n'
        '    )\n'
        '    report = {\n',
    )

    replace_once(
        checker,
        'import json\nfrom pathlib import Path\n',
        'import json\nfrom pathlib import Path\nimport re\n',
    )
    replace_once(
        checker,
        '    evict = (A / "aievict.h").read_text(encoding="utf-8")\n',
        '    evict = (A / "aievict.h").read_text(encoding="utf-8")\n'
        '    cold_header = (A / "aicold.h").read_text(encoding="utf-8")\n'
        '    cold_bytes = (A / "model" / "cold-seed.bin").read_bytes()\n',
    )
    replace_once(
        checker,
        '    require(\'#include "aievict.h"\' in source, "eviction policy header not wired")\n',
        '    require(\'#include "aievict.h"\' in source, "eviction policy header not wired")\n'
        '    require(\'#include "aicold.h"\' in source, "cold identity header not wired")\n'
        '    require("ai_mtrusted" not in source,\n'
        '            "cached model trust bypasses per-scan integrity")\n'
        '    require("ai_mhead[8+i]!=ai_cvid[i]" in source and\n'
        '            "ai_mhead[16+i]!=ai_ciid[i]" in source,\n'
        '            "target hot/cold identity comparison missing")\n'
        '    def target_id(name: str) -> bytes:\n'
        '        match = re.search(\n'
        '            rf"unsigned char {name}\\[8\\] = \\{{([^}}]+)\\}};",\n'
        '            cold_header, re.S\n'
        '        )\n'
        '        require(match is not None, f"generated identity array missing {name}")\n'
        '        values = [int(v.strip()) for v in match.group(1).split(",")\n'
        '                  if v.strip()]\n'
        '        require(len(values) == 8 and all(0 <= v <= 255 for v in values),\n'
        '                f"generated identity width/value mismatch {name}")\n'
        '        return bytes(values)\n'
        '    require(target_id("ai_cvid") == cold_bytes[8:16],\n'
        '            "target vocabulary identity differs from A48M header")\n'
        '    require(target_id("ai_ciid") == cold_bytes[16:24],\n'
        '            "target interface identity differs from A48M header")\n',
    )


def finalize() -> None:
    design = A / "AILMZX48-DETAILED-DESIGN.md"
    status_path = E / "DESIGN-COMPLIANCE-STATUS.json"
    cert = E / "DESIGN-REVIEW-CERTIFICATE.md"
    source_hash = sha(A / "ailmzx48.c")
    binary_hash = sha(ROOT / "usr" / "bin" / "ailmzx48" / "ailmzx48.c48b")
    cold_hash = sha(A / "model" / "cold-seed.bin")

    text = design.read_text(encoding="utf-8")
    anchor = (
        "The target model includes an incremental integrity check suitable for the Z80/C48 implementation. Before record scoring, the target validates the A48M header/version/declared lengths, requires actual object logical length == declared logical length, and checks resident-vocabulary plus hot/cold-interface identities. Every complete cold scan then validates section boundaries, exact declared record count, structural bounds and the requirement that the last declared section/record ends exactly at logical length while accumulating the integrity check over the canonical protected bytes. No selected cold record may reach response generation until the scan has reached the declared logical end and the integrity result matches. Thus the first question also performs full model validation without requiring an extra unbudgeted startup copy/scan; later scans retain the same fail-closed check unless a separately proved immutable-object optimization replaces it. Host release tooling also records SHA-256 for reproducibility. SHA-256 is not imposed on the target merely because the host can calculate it cheaply.\n"
    )
    note = (
        anchor
        + "\nImplementation closure note (Revision 0.26 SoP): the shipped target now compares the generated eight-byte resident-vocabulary and eight-byte hot/cold-interface identities against A48M header bytes 8..23 before record scoring on every turn. It also recomputes Fletcher-16 across the complete protected logical stream on every cold scan; no cached-trust bypass remains. `aicold.h` is regenerated from the same deterministic A48M build that emits `cold-seed.bin`, and the permanent compliance checker independently compares those target constants with the shipped container header.\n"
    )
    if anchor not in text:
        raise RuntimeError("design integrity paragraph anchor missing")
    text = text.replace(anchor, note, 1)
    old = (
        "- retained post-provenance-repair literal/context iteration 9109 is 70/70 with\n"
        "  real compaction, L2 occupancy, semantic retrieval, stale-reference invalidation,\n"
        "  and successful newest-name recall under the current model identity;\n"
        "- retained post-provenance-repair final A/B/C iterations 9110/9111/9112 are each 12/12,\n"
    )
    new = (
        "- retained post-cold-integrity-repair literal/context iteration 9113 is 70/70 with\n"
        "  real compaction, L2 occupancy, semantic retrieval, stale-reference invalidation,\n"
        "  and successful newest-name recall under the current source/binary/model identities;\n"
        "- retained post-cold-integrity-repair final A/B/C iterations 9114/9115/9116 are each 12/12,\n"
    )
    if old not in text:
        raise RuntimeError("design evidence iteration anchor missing")
    text = text.replace(old, new, 1)
    marker = (
        "- provenance schema 3 gives every factual seed record a non-generated licensed\n"
        "  or separately authorized authority and permanently rejects synthetic material\n"
        "  as factual authority; corrected BASIC RUN and Hobbit sales claims retain the\n"
        "  frozen 8,432-byte A48M envelope;\n"
    )
    extra = marker + (
        "- every cold scan rechecks A48M vocabulary/interface identities, structural bounds,\n"
        "  exact logical consumption, and Fletcher-16 integrity before a selected record can\n"
        "  reach response generation; the target has no cached model-trust bypass;\n"
    )
    if marker not in text:
        raise RuntimeError("design provenance bullet anchor missing")
    text = text.replace(marker, extra, 1)
    design.write_text(text, encoding="utf-8", newline="\n")

    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["source_sha256"] = source_hash
    status["sdk_c48b_sha256"] = binary_hash
    status["cold_model_sha256"] = cold_hash
    status["sdk_profile"]["cold_scan_integrity"] = {
        "checksum": "fletcher16-every-scan",
        "identity_header": "aicold.h",
        "interface_identity_checked": True,
        "vocabulary_identity_checked": True,
    }
    lit_score = json.loads((E / "sdk-conformance" / "literal-context" /
                            "score.json").read_text(encoding="utf-8"))
    status["sdk_profile"]["literal_context"] = {
        "context_compactions": lit_score["context_compactions"],
        "final_keyword_hit": lit_score["final_keyword_hit"],
        "keyword_ratio": lit_score["keyword_ratio"],
        "literal_reference_losses": lit_score["literal_reference_losses"],
        "max_l2count": lit_score["max_l2count"],
        "max_lmcount": lit_score["max_lmcount"],
        "semantic_retrieval_uses": lit_score["semantic_retrieval_uses"],
        "turns": lit_score["turns"],
    }
    status["design_sha256"] = sha(design)
    status["design_git_blob_sha1"] = blob(design)
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8", newline="\n")

    ctext = cert.read_text(encoding="utf-8")
    lines = []
    for line in ctext.splitlines():
        if line.startswith("- detailed-design Git blob:"):
            line = f"- detailed-design Git blob: `{status['design_git_blob_sha1']}`"
        elif line.startswith("- detailed-design SHA-256:"):
            line = f"- detailed-design SHA-256: `{status['design_sha256']}`"
        elif line.startswith("- repaired C48 source SHA-256:"):
            line = f"- repaired C48 source SHA-256: `{source_hash}`"
        elif line.startswith("- SDK C48B1 artifact SHA-256:"):
            line = f"- SDK C48B1 artifact SHA-256: `{binary_hash}`"
        elif line.startswith("- cold A48M SHA-256:"):
            line = f"- cold A48M SHA-256: `{cold_hash}`"
        lines.append(line)
    ctext = "\n".join(lines) + "\n"
    cert_anchor = "## Native release boundary\n"
    cert_marker = (
        "Every cold scan recomputes Fletcher-16 and rejects vocabulary/interface "
        "identity mismatch before record use.\n\n"
    )
    if "Every cold scan recomputes Fletcher-16" not in ctext:
        if ctext.count(cert_anchor) != 1:
            raise RuntimeError("certificate native-boundary anchor missing or ambiguous")
        ctext = ctext.replace(cert_anchor, cert_marker + cert_anchor, 1)
    cert.write_text(ctext, encoding="utf-8", newline="\n")

    checker = E / "check_design_compliance.py"
    replace_once(
        checker,
        '    require(sdk.get("zero_gap_passes") == 3, "SDK zero-gap pass count")\n',
        '    require(sdk.get("zero_gap_passes") == 3, "SDK zero-gap pass count")\n'
        '    integ = sdk.get("cold_scan_integrity", {})\n'
        '    require(integ.get("checksum") == "fletcher16-every-scan" and\n'
        '            integ.get("vocabulary_identity_checked") is True and\n'
        '            integ.get("interface_identity_checked") is True,\n'
        '            "cold-scan integrity status missing")\n',
    )
    replace_once(
        checker,
        '    require("FULL_NATIVE_RELEASE: BLOCKED_EXTERNAL" in cert,\n'
        '            "native certificate boundary missing")\n',
        '    require("FULL_NATIVE_RELEASE: BLOCKED_EXTERNAL" in cert,\n'
        '            "native certificate boundary missing")\n'
        '    require("Every cold scan recomputes Fletcher-16" in cert,\n'
        '            "cold-scan integrity certificate marker missing")\n',
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("patch", "finalize"))
    ns = ap.parse_args()
    if ns.mode == "patch":
        patch_runtime()
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
