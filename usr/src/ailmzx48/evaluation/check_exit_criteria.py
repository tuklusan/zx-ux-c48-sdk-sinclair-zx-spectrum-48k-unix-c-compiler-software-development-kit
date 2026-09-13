#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AILM = ROOT / "usr" / "src" / "ailmzx48"
REQUESTS = AILM / "training" / "requests"
CONVERSATIONS = AILM / "conversations"
DEFAULT_CRITERIA = AILM / "training" / "exit-criteria.json"
DEFAULT_STATUS = AILM / "training" / "goal-status.json"


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def ratio(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{name} must be numeric")
    out = float(value)
    if out < 0.0 or out > 1.0:
        raise RuntimeError(f"{name} must be in 0..1")
    return out


def integer(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RuntimeError(f"{name} must be an integer >= {minimum}")
    return value


def request_index() -> tuple[dict[str, list[dict]], list[int]]:
    by_scenario: dict[str, list[dict]] = {}
    pending: list[int] = []
    for path in sorted(REQUESTS.glob("iter-*.json")):
        request = load_json(path)
        iteration = integer(request.get("iteration"), f"{path}: iteration", 1)
        scenario = request.get("scenario")
        if not isinstance(scenario, str) or not scenario:
            raise RuntimeError(f"{path}: scenario must be a non-empty string")
        record = {
            "iteration": iteration,
            "request": path,
            "scenario": scenario,
        }
        out_dir = CONVERSATIONS / f"iter-{iteration:04d}"
        score_path = out_dir / "score.json"
        if score_path.is_file():
            record["score"] = load_json(score_path)
            record["score_path"] = score_path
        else:
            pending.append(iteration)
        by_scenario.setdefault(scenario, []).append(record)
    return by_scenario, pending


def evaluate_record(
    record: dict,
    gates: dict,
    min_turns: int,
) -> tuple[bool, list[str], dict]:
    score = record.get("score")
    if score is None:
        return False, ["retained score evidence is missing"], {}

    failures: list[str] = []
    turns = integer(score.get("turns"), "score.turns")
    if turns < min_turns:
        failures.append(f"turns {turns} < required {min_turns}")

    actual_ratio = ratio(score.get("keyword_ratio"), "score.keyword_ratio")
    minimum_ratio = ratio(gates.get("min_keyword_ratio"), "min_keyword_ratio")
    if actual_ratio < minimum_ratio:
        failures.append(
            f"keyword_ratio {actual_ratio:.6f} < required {minimum_ratio:.6f}"
        )

    if bool(gates.get("require_clean_exit", True)) and not bool(score.get("clean_exit")):
        failures.append("clean_exit is false")

    max_losses = integer(
        gates.get("max_literal_reference_losses", 0),
        "max_literal_reference_losses",
    )
    losses = integer(score.get("literal_reference_losses", 0), "literal_reference_losses")
    if losses > max_losses:
        failures.append(
            f"literal_reference_losses {losses} > allowed {max_losses}"
        )

    limit = integer(score.get("vm_step_limit"), "vm_step_limit", 1)
    steps = integer(score.get("vm_steps"), "vm_steps")
    utilization = steps / limit
    max_utilization = ratio(
        gates.get("max_vm_step_utilization"),
        "max_vm_step_utilization",
    )
    if utilization > max_utilization:
        failures.append(
            f"vm_step_utilization {utilization:.6f} > allowed {max_utilization:.6f}"
        )

    evidence = {
        "iteration": record["iteration"],
        "turns": turns,
        "keyword_ratio": actual_ratio,
        "clean_exit": bool(score.get("clean_exit")),
        "literal_reference_losses": losses,
        "vm_steps": steps,
        "vm_step_limit": limit,
        "vm_step_utilization": utilization,
    }
    return not failures, failures, evidence


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA)
    ap.add_argument("--write-status", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--assert-achieved", action="store_true")
    ns = ap.parse_args()

    criteria = load_json(ns.criteria)
    if criteria.get("schema") != 1:
        raise RuntimeError("unsupported exit-criteria schema")
    gates = criteria.get("global_gates")
    if not isinstance(gates, dict):
        raise RuntimeError("global_gates must be an object")
    required = criteria.get("required_qualification_scenarios")
    if not isinstance(required, list) or not required:
        raise RuntimeError("required_qualification_scenarios must be a non-empty list")

    by_scenario, pending = request_index()
    results: list[dict] = []
    achieved_iterations: dict[str, int] = {}

    for item in required:
        if not isinstance(item, dict):
            raise RuntimeError("qualification scenario entry must be an object")
        scenario = item.get("scenario")
        goal = item.get("goal")
        min_turns = integer(item.get("min_turns"), f"{scenario}: min_turns", 1)
        if not isinstance(scenario, str) or not scenario:
            raise RuntimeError("qualification scenario must be a non-empty string")
        if not isinstance(goal, str) or not goal:
            raise RuntimeError(f"{scenario}: goal must be a non-empty string")

        candidates = by_scenario.get(scenario, [])
        best: dict | None = None
        candidate_failures: list[dict] = []
        for record in candidates:
            ok, failures, evidence = evaluate_record(record, gates, min_turns)
            if ok:
                if best is None or record["iteration"] > best["iteration"]:
                    best = {"iteration": record["iteration"], "evidence": evidence}
            else:
                candidate_failures.append({
                    "iteration": record["iteration"],
                    "failures": failures,
                })
        satisfied = best is not None
        result = {
            "scenario": scenario,
            "goal": goal,
            "satisfied": satisfied,
            "min_turns": min_turns,
        }
        if best is not None:
            result["iteration"] = best["iteration"]
            result["evidence"] = best["evidence"]
            achieved_iterations[scenario] = best["iteration"]
        elif candidate_failures:
            result["candidate_failures"] = candidate_failures
        else:
            result["reason"] = "no retained request/evidence for this scenario"
        results.append(result)

    stability = criteria.get("final_stability_tail")
    if not isinstance(stability, dict):
        raise RuntimeError("final_stability_tail must be an object")
    tail_scenarios = stability.get("required_scenarios")
    if not isinstance(tail_scenarios, list) or not tail_scenarios:
        raise RuntimeError("final_stability_tail.required_scenarios must be non-empty")
    tail_iterations = [achieved_iterations.get(name) for name in tail_scenarios]
    tail_satisfied = all(value is not None for value in tail_iterations)
    tail_reason = None
    if tail_satisfied and bool(stability.get("require_consecutive_iteration_numbers")):
        ints = [int(value) for value in tail_iterations if value is not None]
        tail_satisfied = ints == list(range(ints[0], ints[0] + len(ints)))
        if not tail_satisfied:
            tail_reason = "final regression scenarios are not consecutive retained iterations"
    elif not tail_satisfied:
        tail_reason = "one or more final regression scenarios are not yet satisfied"

    no_pending_required = bool(criteria.get("require_no_pending_requests", True))
    pending_satisfied = (not pending) if no_pending_required else True

    qualifications_satisfied = all(item["satisfied"] for item in results)
    achieved = qualifications_satisfied and tail_satisfied and pending_satisfied
    completion_token = criteria.get("completion_token", "GOALS_ACHIEVED")
    pending_token = criteria.get("pending_token", "GOALS_PENDING")
    status_token = completion_token if achieved else pending_token

    unmet = [item["scenario"] for item in results if not item["satisfied"]]
    status = {
        "schema": 1,
        "criteria_schema": criteria["schema"],
        "status": status_token,
        "goals_achieved": achieved,
        "qualification_scenarios": results,
        "unmet_scenarios": unmet,
        "final_stability_tail": {
            "satisfied": tail_satisfied,
            "scenarios": tail_scenarios,
            "iterations": tail_iterations,
            "reason": tail_reason,
        },
        "pending_iterations": pending,
        "no_pending_requests_satisfied": pending_satisfied,
        "next_action": (
            "Report goals achieved; do not invent another iteration."
            if achieved
            else (
                f"Pursue unmet scenario {unmet[0]}."
                if unmet
                else "Resolve pending iteration requests and re-evaluate."
            )
        ),
    }

    ns.write_status.parent.mkdir(parents=True, exist_ok=True)
    ns.write_status.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, sort_keys=True))

    if ns.assert_achieved and not achieved:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
