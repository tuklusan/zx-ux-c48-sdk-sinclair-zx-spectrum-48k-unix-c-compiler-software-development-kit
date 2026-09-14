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
"""Deterministic tests for alternating hosted-review availability."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_gate  # noqa: E402


class Response:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def semantic(verdict: str = "PASS") -> bytes:
    return json.dumps({
        "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"verdict": verdict})
        }}]
    }).encode()


def exercise(sequence):
    calls = []

    def opener(request, timeout):
        payload = json.loads(request.data.decode())
        calls.append(payload["model"])
        item = sequence[len(calls) - 1]
        if item == 404:
            raise urllib.error.HTTPError(request.full_url, 404, "route unavailable", {}, None)
        if item == 401:
            raise urllib.error.HTTPError(request.full_url, 401, "not authorized", {}, None)
        return Response(semantic(item))

    telemetry = review_gate.Telemetry("CODE", "test")
    client = review_gate.CodeReviewerClient(key="secret", opener=opener)
    sleeps = []
    original_sleep = review_gate.time.sleep
    original_cadence = review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS
    review_gate.time.sleep = sleeps.append
    review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS = 0
    try:
        value = client.request("system", "user", telemetry, deadline=None)
    finally:
        review_gate.time.sleep = original_sleep
        review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS = original_cadence
    return value, calls, sleeps, telemetry


sequence = [404] * review_gate.MIN_ALTERNATING_AVAILABILITY_ATTEMPTS
# This direct adapter trace records every dispatch without admitting a verdict.
calls = []
telemetry = review_gate.Telemetry("CODE", "test")
def exhausted_opener(request, timeout):
    calls.append(json.loads(request.data.decode())["model"])
    raise urllib.error.HTTPError(request.full_url, 404, "route unavailable", {}, None)
client = review_gate.CodeReviewerClient(key="secret", opener=exhausted_opener)
original_sleep = review_gate.time.sleep
original_cadence = review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS
review_gate.time.sleep = lambda _delay: None
review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS = 0
try:
    client.request("system", "user", telemetry, deadline=None)
except review_gate.ReviewError:
    pass
finally:
    review_gate.time.sleep = original_sleep
    review_gate.MIN_REVIEW_REQUEST_CADENCE_SECONDS = original_cadence
expected = [review_gate.PRIMARY_MODEL if i % 2 == 0 else review_gate.FALLBACK_MODEL
            for i in range(review_gate.MIN_ALTERNATING_AVAILABILITY_ATTEMPTS)]
assert calls == expected
assert len(telemetry.api_call_records) == review_gate.MIN_ALTERNATING_AVAILABILITY_ATTEMPTS
assert [record["model"] for record in telemetry.api_call_records] == expected
assert telemetry.api_call_records[0]["previous_failure_class"] is None
assert telemetry.api_call_records[1]["previous_failure_class"] == "404"

for stop_at in (0, 1, 7, 24):
    sequence = [404] * stop_at + ["PASS"]
    value, calls, _, _ = exercise(sequence)
    assert value["verdict"] == "PASS"
    assert len(calls) == stop_at + 1
    assert calls[-1] == (review_gate.PRIMARY_MODEL if stop_at % 2 == 0 else review_gate.FALLBACK_MODEL)

_, calls, _, _ = exercise(["FAIL", 404])
assert len(calls) == 1

try:
    exercise([401])
except review_gate.ConfigurationError:
    pass
else:
    raise AssertionError("permanent authorization failure retried")

first, first_calls, _, _ = exercise([404, "PASS"])
second, second_calls, _, _ = exercise(["PASS"])
assert first["verdict"] == "PASS" and second["verdict"] == "PASS"
assert first_calls[1] == review_gate.FALLBACK_MODEL
assert second_calls == [review_gate.PRIMARY_MODEL]

schema_calls = []
def schema_opener(request, timeout):
    schema_calls.append(json.loads(request.data.decode())["model"])
    return Response(b"{}" if len(schema_calls) == 1 else semantic("PASS"))
schema_client = review_gate.CodeReviewerClient(key="secret", opener=schema_opener)
schema_telemetry = review_gate.Telemetry("CODE", "schema")
schema_value = review_gate.request_validated(
    schema_client, "system", "user", schema_telemetry,
    lambda value: value.get("verdict") == "PASS", "SCHEMA-REPAIR"
)
assert schema_value["verdict"] == "PASS"
assert schema_calls == [review_gate.PRIMARY_MODEL, review_gate.PRIMARY_MODEL]

print("review availability policy tests: PASS")
