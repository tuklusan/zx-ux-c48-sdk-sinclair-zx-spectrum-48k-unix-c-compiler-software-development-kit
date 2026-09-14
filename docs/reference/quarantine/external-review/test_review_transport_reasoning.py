#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
# This file is governed by the SANYALnet Labs Non-Commercial License in the root LICENSE file.
"""Deterministic transport/reasoning/lock tests for the ZX-UX external review gate."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from tools.reviewer import review_gate as rg
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.reviewer import legacy_bootstrap_gate as lbg


class Response:
    def __init__(self, body: bytes, status: int = 200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}
    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def read(self): return self.body
    def getcode(self): return self.status


def completion(value, *, finish_reason="stop", reasoning="PRIVATE-REASONING-SENTINEL") -> bytes:
    return json.dumps({
        "choices": [{"finish_reason": finish_reason, "message": {
            "content": json.dumps(value), "reasoning_content": reasoning,
        }}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 13},
    }).encode()


class ReviewTransportReasoningTests(unittest.TestCase):
    def setUp(self):
        self.old_cadence = rg.MIN_REVIEW_REQUEST_CADENCE_SECONDS
        rg.MIN_REVIEW_REQUEST_CADENCE_SECONDS = 0
    def tearDown(self):
        rg.MIN_REVIEW_REQUEST_CADENCE_SECONDS = self.old_cadence

    def capture_one(self, model=rg.PRIMARY_MODEL, phase="CODE-DISCOVERY"):
        captures = []
        def opener(request, timeout):
            captures.append(json.loads(request.data.decode()))
            return Response(completion({"ok": True}))
        telemetry = rg.Telemetry("CODE", "test")
        client = rg.CodeReviewerClient(key="secret", opener=opener, model=model)
        result = client.request(
            "system", "user", telemetry, thinking="enabled", reasoning_effort="high",
            phase=phase, deadline=None, starting_model=model, allow_failover=False, max_attempts=1,
        )
        return result, captures, telemetry

    def test_embedded_self_tests_pass(self):
        self.assertEqual(rg.run_self_tests()["status"], "PASS")

    def test_super_serialized_wire_payload(self):
        _, captures, telemetry = self.capture_one(rg.PRIMARY_MODEL)
        payload = captures[0]
        self.assertEqual(payload["reasoning_effort"], "high")
        self.assertEqual(payload["reasoning_budget"], rg.REASONING_BUDGET_TOKENS)
        self.assertNotIn("chat_template_kwargs", payload)
        self.assertEqual(telemetry.api_call_records[0]["reasoning_effort"], "high")

    def test_lightning_serialized_wire_payload(self):
        _, captures, telemetry = self.capture_one(rg.FALLBACK_MODEL)
        payload = captures[0]
        self.assertNotIn("reasoning_effort", payload)
        self.assertEqual(payload["reasoning_budget"], rg.REASONING_BUDGET_TOKENS)
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": True})
        self.assertTrue(telemetry.api_call_records[0]["enable_thinking"])

    def test_substantive_markers_reject_disabled_reasoning(self):
        for marker in rg.REASONING_REQUIRED_PHASE_MARKERS:
            with self.subTest(marker=marker), self.assertRaises(rg.ConfigurationError):
                rg.CodeReviewerClient(key="secret", opener=lambda *_a, **_k: None).request(
                    "s", "u", rg.Telemetry("CODE", "test"), thinking="disabled", reasoning_effort=None,
                    phase=marker, deadline=None, max_attempts=1,
                )

    def test_404_retry_delay_matches_workflow(self):
        self.assertEqual(rg.RETRY_DELAY_404_SECONDS, 4)

    def test_async_status_poll_floor_matches_workflow(self):
        self.assertGreaterEqual(rg.ASYNC_POLL_INTERVAL_SECONDS, 30.0)

    def test_bootstrap_line_slice_preserves_line_endings(self):
        self.assertEqual(lbg.line_slice_content("a\nb\n", 1, 1), "a\n\n")

    def test_reasoning_content_is_not_persisted(self):
        result, _, telemetry = self.capture_one()
        self.assertNotIn("PRIVATE-REASONING-SENTINEL", rg.canonical_json(result))
        self.assertNotIn("PRIVATE-REASONING-SENTINEL", rg.canonical_json(telemetry.api_call_records))

    def test_schema_failure_reaudits_packet_before_retry(self):
        class Client:
            def __init__(self):
                self.calls = 0

            def request(self, *_args, **_kwargs):
                self.calls += 1
                return {} if self.calls == 1 else {"ok": True}

        client = Client()
        audits = []
        result = rg.request_validated(
            client, "system", "user", rg.Telemetry("CODE", "audit"),
            lambda value: value.get("ok") is True, "TEST",
            packet_audit=lambda: audits.append("audited"),
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(client.calls, 2)
        self.assertEqual(audits, ["audited"])

    def test_failed_packet_reaudit_blocks_schema_retry(self):
        class Client:
            calls = 0

            def request(self, *_args, **_kwargs):
                self.calls += 1
                return {}

        client = Client()
        with self.assertRaises(rg.ReviewError):
            rg.request_validated(
                client, "system", "user", rg.Telemetry("CODE", "audit-fail"),
                lambda value: value.get("ok") is True, "TEST",
                packet_audit=lambda: (_ for _ in ()).throw(
                    rg.ReviewError("REVIEW_PACKET_REAUDIT_FAILED")
                ),
            )
        self.assertEqual(client.calls, 1)

    def test_output_error_reaudits_packet_before_propagating(self):
        audits = []

        class Client:
            def request(self, *_args, **_kwargs):
                raise rg.OutputError("malformed response")

        with self.assertRaises(rg.OutputError):
            rg.request_validated(
                Client(), "system", "user", rg.Telemetry("CODE", "output-error"),
                lambda value: True, "TEST",
                packet_audit=lambda: audits.append("audited"),
            )
        self.assertEqual(audits, ["audited"])

    def test_202_polls_same_invocation_without_duplicate_post(self):
        request_id = "123e4567-e89b-12d3-a456-426614174000"
        seen = []
        polls = 0
        def opener(request, timeout):
            nonlocal polls
            seen.append((request.full_url, request.method))
            if request.method == "POST":
                return Response(json.dumps({"requestId": request_id}).encode(), 202)
            polls += 1
            if polls == 1:
                return Response(json.dumps({"requestId": request_id}).encode(), 202)
            return Response(completion({"status": "done"}), 200)
        telemetry = rg.Telemetry("CODE", "async")
        client = rg.CodeReviewerClient(key="secret", opener=opener)
        with patch.object(rg.time, "sleep", lambda _delay: None):
            result = client.request("s", "u", telemetry, phase="CODE-DISCOVERY", deadline=None,
                                    allow_failover=False, max_attempts=1)
        self.assertEqual(result, {"status": "done"})
        self.assertEqual(sum(method == "POST" for _, method in seen), 1)
        self.assertEqual(sum(method == "GET" for _, method in seen), 2)
        self.assertEqual(telemetry.calls, 1)
        self.assertEqual(telemetry.async_poll_count, 2)

    def test_resource_failure_uses_resource_class_and_alternates(self):
        captures = []
        responses = [Response(completion({}, finish_reason="insufficient_system_resource")),
                     Response(completion({"ok": True}))]
        def opener(request, timeout):
            captures.append(json.loads(request.data.decode()))
            return responses[len(captures)-1]
        telemetry = rg.Telemetry("CODE", "resource")
        with patch.object(rg.time, "sleep", lambda _delay: None):
            result = rg.CodeReviewerClient(key="secret", opener=opener).request(
                "s", "u", telemetry, phase="CODE-DISCOVERY", deadline=None, max_attempts=2)
        self.assertEqual(result, {"ok": True})
        self.assertEqual([item["model"] for item in captures], [rg.PRIMARY_MODEL, rg.FALLBACK_MODEL])
        self.assertEqual(telemetry.api_call_records[0]["failure_class"], "resource")

    def test_new_logical_call_restarts_primary(self):
        models = []
        sequence = [404, "PASS", "PASS"]
        def opener(request, timeout):
            models.append(json.loads(request.data.decode())["model"])
            item = sequence[len(models)-1]
            if item == 404:
                raise urllib.error.HTTPError(request.full_url, 404, "route", {}, None)
            return Response(completion({"verdict": item}))
        client = rg.CodeReviewerClient(key="secret", opener=opener)
        with patch.object(rg.time, "sleep", lambda _delay: None):
            client.request("s", "u", rg.Telemetry("CODE", "a"), phase="CODE-DISCOVERY", deadline=None)
            client.request("s", "u", rg.Telemetry("CODE", "b"), phase="CODE-DISCOVERY", deadline=None,
                           max_attempts=1)
        self.assertEqual(models, [rg.PRIMARY_MODEL, rg.FALLBACK_MODEL, rg.PRIMARY_MODEL])

    def test_global_lock_blocks_second_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rg.acquire_review_lock(root, "snap-a", "CODE", "CR-A", 7200)
            with self.assertRaises(rg.ReviewError):
                rg.acquire_review_lock(root, "snap-b", "CODE", "CR-B", 7200)

    def test_live_lock_is_not_stale_due_to_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active-review-global.json"
            path.write_text("{}", encoding="utf-8")
            record = {"process_id": os.getpid(), "process_identity": rg.process_identity(os.getpid()),
                      "started_epoch": time.time() - 999999, "deadline_seconds": 1, "status": "RUNNING"}
            self.assertFalse(rg.active_review_is_stale(record, path, time.time()))

    def test_pid_reuse_identity_mismatch_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active-review-global.json"
            path.write_text("{}", encoding="utf-8")
            record = {"process_id": 123, "process_identity": "old", "started_epoch": time.time(),
                      "deadline_seconds": 7200, "status": "RUNNING"}
            with patch.object(rg, "process_is_active", return_value=True), \
                 patch.object(rg, "process_identity", return_value="new"):
                self.assertTrue(rg.active_review_is_stale(record, path, time.time()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
