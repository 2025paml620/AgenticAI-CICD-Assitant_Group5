"""Load the shared CI/CD scenarios.

Owner: Member 4 (Karthik) - shared scenario data.

Use ``agent_input(scenario_id)`` to get the exact input every agent receives.
It is a deep copy with the ``expected`` (answer-key) block removed, so no
agent - including the LLM tools - can see the expected answer.
"""
from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SCENARIO_FILE = Path(__file__).resolve().parent / "data" / "scenarios.json"

REQUIRED_SCENARIO_FIELDS = (
    "id",
    "name",
    "failure_type",
    "pipeline_status",
    "build_logs",
    "test_results",
    "dependencies",
    "recent_changes",
    "health_checks",
    "expected",
)


@lru_cache(maxsize=1)
def _load_raw(path: str = str(SCENARIO_FILE)) -> tuple[dict[str, Any], ...]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    scenarios = data["scenarios"]
    for s in scenarios:
        missing = [f for f in REQUIRED_SCENARIO_FIELDS if f not in s]
        if missing:
            raise ValueError(f"Scenario {s.get('id')} is missing fields: {missing}")
    return tuple(scenarios)


def load_scenarios() -> list[dict[str, Any]]:
    """Return all scenarios (deep copies, including the ``expected`` block)."""
    return copy.deepcopy(list(_load_raw()))


def scenario_ids() -> list[str]:
    return [s["id"] for s in _load_raw()]


def load_scenario(scenario_id: str) -> dict[str, Any]:
    """Return one full scenario (including ``expected``) by id, e.g. ``"A"``."""
    for s in _load_raw():
        if s["id"].upper() == str(scenario_id).strip().upper():
            return copy.deepcopy(s)
    raise KeyError(f"Unknown scenario id: {scenario_id!r}. Known: {scenario_ids()}")


def agent_input(scenario_id: str) -> dict[str, Any]:
    """Return the scenario as agents should see it (no ``expected`` block)."""
    scenario = load_scenario(scenario_id)
    scenario.pop("expected", None)
    return scenario


def expected_for(scenario_id: str) -> dict[str, Any]:
    """Return the answer key used only for evaluation/comparison."""
    return load_scenario(scenario_id)["expected"]
