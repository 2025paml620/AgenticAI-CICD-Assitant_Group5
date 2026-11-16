"""Common agent interface for the CI/CD Pipeline Failure Assistant.

Owner: Member 4 (Karthik) - integration.

Every agent (five classical + one LLM) implements the same contract:

    decide(scenario: dict) -> dict

The input is one scenario from ``data/scenarios.json`` with the grader-only
``expected`` block removed (see ``scenario_loader.agent_input``).

The output must contain the fields in ``REQUIRED_FIELDS``. Agents may add
extra fields such as ``tools_used`` (LLM), ``utility_score`` (Utility) or
``experience_used`` (Learning); the UI shows them when present.

Agents are advisory only: they recommend the next troubleshooting step and
must never modify code or trigger a deployment.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

REQUIRED_FIELDS: tuple[str, ...] = (
    "agent",
    "failure_category",
    "supporting_evidence",
    "likely_cause",
    "recommended_step",
    "reasoning",
    "verification_checklist",
)

OPTIONAL_FIELDS: tuple[str, ...] = (
    "tools_used",        # LLM agent: names of tools actually called
    "tool_calls",        # LLM agent: tool call trace (name, args, output)
    "utility_score",     # Utility agent: score of the chosen action
    "candidate_scores",  # Utility agent: all scored actions
    "experience_used",   # Learning agent: success/failure counts consulted
    "plan",              # Goal-based agent: planned diagnostic sequence
)

# Canonical failure categories used for comparison. Agents written by
# different members use slightly different labels, so they are mapped here.
CANONICAL_CATEGORIES = ("unit_test", "dependency", "deployment", "healthy", "unknown")

_CATEGORY_ALIASES: dict[str, str] = {
    "unit_test": "unit_test",
    "unit_test_failure": "unit_test",
    "unit_test_regression": "unit_test",
    "test_failure": "unit_test",
    "tests": "unit_test",
    "dependency": "dependency",
    "dependency_failure": "dependency",
    "dependency_or_build_failure": "dependency",
    "dependency_incompatibility": "dependency",
    "build_failure": "dependency",
    "build": "dependency",
    "deployment": "deployment",
    "deployment_failure": "deployment",
    "deployment_health_failure": "deployment",
    "health_check_failure": "deployment",
    "healthy": "healthy",
    "none": "healthy",
    "no_failure": "healthy",
    "passed": "healthy",
    "unknown": "unknown",
    "ambiguous": "unknown",
    "insufficient_evidence": "unknown",
}


def canonical_category(label: Any) -> str:
    """Map an agent's failure label onto one of ``CANONICAL_CATEGORIES``."""
    if label is None:
        return "unknown"
    key = str(label).strip().lower().replace("-", "_").replace(" ", "_")
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    # Fall back to keyword matching for free-text labels (e.g. from the LLM).
    if "depend" in key or "version" in key or "build" in key:
        return "dependency"
    if "test" in key:
        return "unit_test"
    if "deploy" in key or "health" in key or "runtime" in key:
        return "deployment"
    if "healthy" in key or "success" in key:
        return "healthy"
    return "unknown"


def validate_result(result: Any) -> list[str]:
    """Return a list of contract problems with an agent result (empty = valid)."""
    if not isinstance(result, dict):
        return [f"result must be a dict, got {type(result).__name__}"]
    problems = [f"missing field '{f}'" for f in REQUIRED_FIELDS if f not in result]
    for list_field in ("supporting_evidence", "verification_checklist"):
        if list_field in result and not isinstance(result[list_field], list):
            problems.append(f"'{list_field}' must be a list")
    for text_field in ("agent", "recommended_step", "reasoning"):
        if text_field in result and not str(result[text_field]).strip():
            problems.append(f"'{text_field}' must not be empty")
    return problems


def normalize_result(result: dict[str, Any], agent_name: str) -> dict[str, Any]:
    """Fill missing fields with safe defaults so the UI can always render."""
    out = dict(result)
    out.setdefault("agent", agent_name)
    out.setdefault("failure_category", "unknown")
    out.setdefault("likely_cause", "Not provided")
    out.setdefault("recommended_step", "Not provided")
    out.setdefault("reasoning", "Not provided")
    for list_field in ("supporting_evidence", "verification_checklist"):
        value = out.get(list_field, [])
        if value is None:
            value = []
        elif not isinstance(value, list):
            value = [value]
        out[list_field] = [str(v) for v in value]
    out["canonical_category"] = canonical_category(out["failure_category"])
    return out


class BaseAgent(ABC):
    """Optional base class. Agents only need a ``decide`` method (duck typing)."""

    name: str = "Base Agent"

    @abstractmethod
    def decide(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Return a recommendation dict containing ``REQUIRED_FIELDS``."""

    def reset(self) -> None:  # pragma: no cover - default no-op
        """Clear any internal state (memory, history). Optional."""
