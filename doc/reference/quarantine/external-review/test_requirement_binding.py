#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.reviewer.review_gate import (
    API_URL,
    IMPLEMENTATION_REQUIREMENT_SOURCE,
    UNIVERSAL_REQUIREMENT_SOURCE,
    ReviewError,
    authority_receipt_fields,
    aggregate_requirement_coverage,
    build_authority_binding,
    code_packet,
    decision_schema_valid,
    discovery_schema_valid,
    exact_step_section,
    load_cr_scope,
    requirement_coverage_valid,
    requirement_records,
    review_scope_paths,
    stable_prefix,
)


ROOT = Path(__file__).resolve().parents[2]
REQUIREMENT_PATHS = [
    "v1/docs/01-ZX-UX-ARCHITECTURE-REV11.md",
    IMPLEMENTATION_REQUIREMENT_SOURCE,
    UNIVERSAL_REQUIREMENT_SOURCE,
    "v1/docs/active-cr.md",
]


class RequirementBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requirements = requirement_records(ROOT, REQUIREMENT_PATHS)

    def binding_for(self, cr, active=None):
        if active is None:
            active = False
        scope = load_cr_scope(ROOT, cr, None, require_active=active)
        return scope, build_authority_binding(ROOT, scope, self.requirements)

    def test_reviewer_endpoint_is_exact(self):
        self.assertEqual(API_URL, "https://integrate.api.nvidia.com/v1/chat/completions")

    def test_p003_exact_authority_is_bound(self):
        scope, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.03", False)
        step = binding["implementation_authority"]
        source = next(item for item in self.requirements if item["source"] == IMPLEMENTATION_REQUIREMENT_SOURCE)
        expected = exact_step_section(source["content"], "P0.03")
        self.assertEqual(scope["implementation_step"], "P0.03")
        self.assertEqual(step, expected)
        self.assertIn(expected["content"], stable_prefix("CODE", "snapshot", scope, self.requirements, "packet", binding))

    def test_other_step_uses_same_generic_extractor(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        self.assertEqual(binding["implementation_step"], "P0.04")
        self.assertEqual(binding["implementation_authority"]["normative_requirements"][0]["id"], "P0.04-R01")

    def test_packet_contains_binding_and_exact_step_text(self):
        scope, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        with patch("tools.reviewer.review_gate.validate_code_snapshot",
                   return_value=("3caa51df9320cf3540cceb12bff08e5f6638eb98",
                                 "e963267ac28381c4648e89acdde9d36485cfdd62")):
            packet = code_packet(ROOT, "3caa51df9320cf3540cceb12bff08e5f6638eb98",
                                 "e963267ac28381c4648e89acdde9d36485cfdd62", binding)
        record = dict(packet.records)["authority-binding.json"]
        self.assertEqual(json.loads(record), binding)
        self.assertEqual(packet.authority_binding["implementation_step"], scope["implementation_step"])

    def test_scoped_code_packet_excludes_unrelated_changed_files(self):
        scope = {
            "private_scope": {
                "content": json.dumps({
                    "purpose": "Review only the P0.05 wrapper and proof implementation.",
                    "paths": [
                        "v1/src/kernel/rom_services.asm",
                        "v1/src/kernel/interrupt.asm",
                    ],
                })
            }
        }
        paths = review_scope_paths(scope)
        self.assertEqual(paths, ["v1/src/kernel/interrupt.asm", "v1/src/kernel/rom_services.asm"])
        with patch("tools.reviewer.review_gate.validate_code_snapshot",
                   return_value=("0f9529a61a8fdc8420bb1913606c995f68f11ce7",
                                 "f383909a22e7e1781c6f1062bafd9eab63eb1ead")):
            packet = code_packet(ROOT, "0f9529a61a8fdc8420bb1913606c995f68f11ce7",
                                 "f383909a22e7e1781c6f1062bafd9eab63eb1ead",
                                 scope_paths=paths)
        self.assertEqual(
            {item["head_path"] for item in packet.manifest},
            {"v1/src/kernel/interrupt.asm", "v1/src/kernel/rom_services.asm"},
        )
        self.assertNotIn("tools/reviewer/review_gate.py", packet.records[0][1])
        self.assertEqual(json.loads(dict(packet.records)["review-scope.json"])["paths"], paths)

    def test_scoped_code_packet_keeps_unchanged_direct_context(self):
        paths = ["v1/src/boot/entry.asm", "v1/tests/emulator/p003_proof.py"]
        with patch("tools.reviewer.review_gate.validate_code_snapshot",
                   return_value=("e28845222b4160e99b24d82c061eef682eed25a2",
                                 "af70fe7794b0c2c512e9b62cba9d1d66135053d7")):
            packet = code_packet(ROOT, "e28845222b4160e99b24d82c061eef682eed25a2",
                                 "af70fe7794b0c2c512e9b62cba9d1d66135053d7",
                                 scope_paths=paths)
        entries = {item["head_path"]: item for item in packet.manifest}
        self.assertIn("v1/src/boot/entry.asm", entries)
        self.assertTrue(entries["v1/src/boot/entry.asm"]["context_only"])

    def test_private_code_scope_requires_purpose_and_paths(self):
        for payload in ({"purpose": "", "paths": ["v1/src/kernel/interrupt.asm"]},
                        {"purpose": "P0.05", "paths": []},
                        {"purpose": "P0.05", "paths": ["../outside.py"]}):
            with self.subTest(payload=payload), self.assertRaises(ReviewError):
                review_scope_paths({"private_scope": {"content": json.dumps(payload)}})

    def test_inconclusive_coverage_requires_bounded_context_request(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        ids = {item["id"] for item in binding["implementation_authority"]["normative_requirements"]}
        coverage = [{"requirement_id": identifier, "status": "PASS", "implementation_location": "x:1",
                     "proof": "observed", "falsification": "challenged"} for identifier in sorted(ids)]
        coverage[0]["status"] = "INCONCLUSIVE"
        self.assertFalse(requirement_coverage_valid({"requirement_coverage": coverage}, ids))
        coverage[0]["context_requests"] = [{"type": "PATH", "path": "v1/src/kernel/im2.asm",
                                            "symbol": "zx48_im2_init"}]
        self.assertTrue(requirement_coverage_valid({"requirement_coverage": coverage}, ids))

    def test_prefix_uses_bound_architecture_sections_not_whole_file(self):
        scope, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.05")
        prefix = stable_prefix("CODE", "snapshot", scope, self.requirements, "packet", binding)
        architecture = next(item for item in self.requirements
                             if item["source"] == "v1/docs/01-ZX-UX-ARCHITECTURE-REV11.md")
        self.assertNotIn(architecture["content"], prefix)
        universal = next(item for item in self.requirements
                         if item["source"] == UNIVERSAL_REQUIREMENT_SOURCE)
        self.assertNotIn(universal["content"], prefix)
        self.assertIn('"content_scope":"exact universal authority remains hash-bound; only the harness protocol is transmitted"', prefix)
        for section in binding["architecture_authorities"]:
            self.assertIn(json.dumps(section["content"], ensure_ascii=False), prefix)

    def test_missing_step_is_rejected(self):
        scope, _ = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        scope.pop("implementation_step")
        with self.assertRaises(ReviewError):
            build_authority_binding(ROOT, scope, self.requirements)

    def test_unknown_step_is_rejected(self):
        scope, _ = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        scope["implementation_step"] = "P0.99"
        with self.assertRaises(ReviewError):
            build_authority_binding(ROOT, scope, self.requirements)

    def test_duplicate_or_malformed_step_section_is_rejected(self):
        source = next(item for item in self.requirements if item["source"] == IMPLEMENTATION_REQUIREMENT_SOURCE)
        with self.assertRaises(ReviewError):
            exact_step_section(source["content"] + "\n## P0.04 - duplicate\n1. duplicate\n", "P0.04")

    def test_coverage_requires_every_requirement(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        ids = {item["id"] for item in binding["implementation_authority"]["normative_requirements"]}
        complete = {"requirement_coverage": [
            {"requirement_id": identifier, "status": "PASS", "implementation_location": "x:1",
             "proof": "observed", "falsification": "challenged"} for identifier in sorted(ids)
        ]}
        self.assertTrue(requirement_coverage_valid(complete, ids))
        incomplete = json.loads(json.dumps(complete))
        incomplete["requirement_coverage"].pop()
        self.assertFalse(requirement_coverage_valid(incomplete, ids))

    def test_failed_requirement_cannot_be_clear_coverage(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        ids = {item["id"] for item in binding["implementation_authority"]["normative_requirements"]}
        failed = {"requirement_coverage": [
            {"requirement_id": identifier, "status": "FAIL" if identifier.endswith("01") else "PASS",
             "implementation_location": "x:1", "proof": "observed", "falsification": "challenged"}
            for identifier in sorted(ids)
        ]}
        self.assertTrue(requirement_coverage_valid(failed, ids))
        self.assertNotEqual({item["status"] for item in failed["requirement_coverage"]}, {"PASS"})

    def test_discovery_and_falsification_schemas_require_coverage(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        ids = {item["id"] for item in binding["implementation_authority"]["normative_requirements"]}
        coverage = [{"requirement_id": identifier, "status": "PASS", "implementation_location": "x:1",
                     "proof": "observed", "falsification": "challenged"} for identifier in sorted(ids)]
        discovery = {"review_complete": True, "pass": "CODE-DISCOVERY", "candidates": [],
                     "uncertainties": [], "requirement_coverage": coverage}
        self.assertTrue(discovery_schema_valid(discovery, "CODE-DISCOVERY", ids))
        discovery.pop("requirement_coverage")
        self.assertFalse(discovery_schema_valid(discovery, "CODE-DISCOVERY", ids))
        decision = {"review_complete": True, "decisions": [], "new_candidates": [],
                    "requirement_coverage": coverage}
        self.assertTrue(decision_schema_valid(decision, set(), ids))
        decision["requirement_coverage"] = coverage[:-1]
        self.assertFalse(decision_schema_valid(decision, set(), ids))

    def test_sharded_discovery_coverage_aggregates_fail_closed(self):
        ids = {"P0.11-R01", "P0.11-R02"}
        row = lambda identifier, status="PASS": {
            "requirement_id": identifier,
            "status": status,
            "implementation_location": "v1/tests/emulator/p011_proof.py:1",
            "proof": "observed",
            "falsification": "challenged",
        }
        partial = {"requirement_coverage": [row("P0.11-R01")]}
        self.assertTrue(requirement_coverage_valid(partial, ids, exact=False))
        self.assertFalse(requirement_coverage_valid(partial, ids))
        self.assertTrue(requirement_coverage_valid({"requirement_coverage": []}, ids, exact=False))
        self.assertFalse(requirement_coverage_valid({"requirement_coverage": []}, ids))
        self.assertIsNone(aggregate_requirement_coverage(partial["requirement_coverage"], ids))
        complete = aggregate_requirement_coverage(
            [row("P0.11-R01"), row("P0.11-R02"), row("P0.11-R01", "INCONCLUSIVE")], ids
        )
        self.assertEqual([item["status"] for item in complete], ["INCONCLUSIVE", "PASS"])
        self.assertIsNone(aggregate_requirement_coverage([row("P0.11-R01"), row("UNKNOWN")], ids))

    def test_partial_discovery_schema_does_not_fabricate_coverage(self):
        ids = {"P0.11-R01", "P0.11-R02"}
        value = {
            "review_complete": True,
            "pass": "CODE-DISCOVERY",
            "candidates": [],
            "uncertainties": [],
            "requirement_coverage": [{
                "requirement_id": "P0.11-R01",
                "status": "PASS",
                "implementation_location": "v1/tests/emulator/p011_proof.py:1",
                "proof": "observed",
                "falsification": "challenged",
            }],
        }
        self.assertTrue(discovery_schema_valid(value, "CODE-DISCOVERY", ids, complete_coverage=False))
        self.assertFalse(discovery_schema_valid(value, "CODE-DISCOVERY", ids))
        value["requirement_coverage"][0]["requirement_id"] = "UNKNOWN"
        self.assertFalse(discovery_schema_valid(value, "CODE-DISCOVERY", ids, complete_coverage=False))

    def test_receipt_projection_contains_authority_hashes(self):
        _, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        receipt = authority_receipt_fields(binding)
        self.assertEqual(receipt["implementation_step"], "P0.04")
        self.assertTrue(receipt["implementation_authority"]["section_sha256"])
        self.assertTrue(receipt["architecture_authorities"])
        self.assertTrue(receipt["change_request_authority"]["record_sha256"])

    def test_changed_authority_changes_receipt_identity(self):
        scope, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        mutated_requirements = [dict(item) for item in self.requirements]
        implementation = next(item for item in mutated_requirements
                              if item["source"] == IMPLEMENTATION_REQUIREMENT_SOURCE)
        implementation["content"] += "\n"
        changed_binding = build_authority_binding(ROOT, scope, mutated_requirements)
        self.assertNotEqual(
            authority_receipt_fields(binding)["implementation_authority"],
            authority_receipt_fields(changed_binding)["implementation_authority"],
        )

    def test_changed_scope_changes_receipt_identity(self):
        scope, binding = self.binding_for("CR-ZXUX-QA-REMEDIATION-P0.04")
        changed_scope = dict(scope)
        changed_scope["record_content"] += "\n"
        changed_scope["record_sha256"] = "0" * 64
        changed_binding = build_authority_binding(ROOT, changed_scope, self.requirements)
        self.assertNotEqual(
            authority_receipt_fields(binding)["change_request_authority"],
            authority_receipt_fields(changed_binding)["change_request_authority"],
        )


if __name__ == "__main__":
    unittest.main()
