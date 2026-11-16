"""Transparent evaluation metrics for the Member 2 CI/CD agents."""
from __future__ import annotations

import re
from typing import Any

from agents.base_agent import canonical_category, validate_result


# Evaluator-owned reference mapping derived from the scenario descriptions and
# rationales. This is independent of the agent's own evidence selection rules.
EXPECTED_EVIDENCE_FIELDS: dict[str, set[str]] = {
    "A": {"pipeline_status", "build_logs", "test_results", "recent_changes"},
    "B": {"pipeline_status", "build_logs", "dependencies", "recent_changes"},
    "C": {
        "pipeline_status", "build_logs", "test_results", "health_checks",
        "deployment_logs", "recent_changes",
    },
    "D": {"pipeline_status", "build_logs", "test_results", "dependencies"},
    "E": {
        "pipeline_status", "build_logs", "test_results", "health_checks",
        "deployment_logs",
    },
}

# Public output labels are normalized to logical scenario evidence fields.
_EVIDENCE_LABELS: tuple[tuple[str, str], ...] = (
    ("pipeline status", "pipeline_status"),
    ("build logs", "build_logs"),
    ("test results", "test_results"),
    ("dependency information", "dependencies"),
    ("recent changes", "recent_changes"),
    ("health checks", "health_checks"),
    ("deployment/runtime logs", "deployment_logs"),
    ("deployment logs", "deployment_logs"),
    ("runtime logs", "deployment_logs"),
)


def _round(value: float) -> float:
    return round(float(value), 4)


def classification_metric(expected_category: str, actual_category: str) -> dict[str, Any]:
    """Compare categories after applying the group's canonical normalizer."""
    expected = canonical_category(expected_category)
    actual = canonical_category(actual_category)
    correct = expected == actual
    return {
        "expected_category": expected,
        "actual_category": actual,
        "correct": correct,
        "score": 1.0 if correct else 0.0,
    }


def extract_evidence_sources(supporting_evidence: Any) -> set[str]:
    """Map supporting_evidence labels to normalized logical source names."""
    if not isinstance(supporting_evidence, list):
        return set()

    extracted: set[str] = set()
    for item in supporting_evidence:
        if not isinstance(item, str):
            continue
        label = item.split(":", 1)[0].strip().lower()
        # Agent outputs may annotate the source field in parentheses, e.g.
        # "Dependency information (dependencies)".
        label = re.sub(r"\s*\([^)]*\)\s*", " ", label).strip()
        label = re.sub(r"^additional\s+", "", label)
        for display_label, canonical_field in _EVIDENCE_LABELS:
            if label == display_label:
                extracted.add(canonical_field)
                break
    return extracted


def evidence_relevance_metric(
    scenario_id: str, supporting_evidence: Any
) -> dict[str, Any]:
    """Calculate evidence precision, recall and F1 against evaluator references.

    Alias fields are normalized: dependencies/dependency_info count as one,
    and deployment_logs/runtime_logs count as one.
    """
    expected = EXPECTED_EVIDENCE_FIELDS.get(scenario_id)
    if expected is None:
        raise ValueError(f"No evidence reference mapping for scenario: {scenario_id}")

    predicted = extract_evidence_sources(supporting_evidence)
    true_positive = len(expected & predicted)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "expected_sources": sorted(expected),
        "predicted_sources": sorted(predicted),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": _round(precision),
        "recall": _round(recall),
        "f1_score": _round(f1),
    }


def _stem_token(token: str) -> str:
    """Apply a deliberately small suffix normalizer for phrase matching."""
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
        if len(token) > 2 and token[-1] == token[-2]:
            token = token[:-1]
    elif len(token) > 4 and token.endswith("ied"):
        token = token[:-3] + "y"
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    return [_stem_token(token) for token in re.findall(r"[a-z0-9]+", text.lower())]


def _acceptable_phrase_matches(recommendation: str, phrase: str) -> bool:
    recommendation_tokens = set(_tokens(recommendation))
    phrase_tokens = _tokens(phrase)
    if not phrase_tokens:
        return False
    # Require each meaningful phrase token to be present after light stemming.
    # This supports simple variants such as failing/failed and log/logs.
    return all(token in recommendation_tokens for token in phrase_tokens)


def recommendation_metric(recommendation: Any, acceptable_next_steps: Any) -> dict[str, Any]:
    """Check whether recommendation matches at least one evaluator-approved phrase."""
    recommendation_text = recommendation if isinstance(recommendation, str) else ""
    accepted = acceptable_next_steps if isinstance(acceptable_next_steps, list) else []
    matched = [
        phrase for phrase in accepted
        if isinstance(phrase, str) and _acceptable_phrase_matches(recommendation_text, phrase)
    ]
    appropriate = bool(matched)
    return {
        "appropriate": appropriate,
        "score": 1.0 if appropriate else 0.0,
        "matched_acceptable_steps": matched,
        "acceptable_next_steps": accepted,
    }


def explanation_completeness_metric(result: dict[str, Any]) -> dict[str, Any]:
    """Score four observable explanation components (0-4 and percentage)."""
    likely_cause = result.get("likely_cause")
    reasoning = result.get("reasoning")
    recommended_step = result.get("recommended_step")
    checklist = result.get("verification_checklist")
    candidates = result.get("candidate_scores")
    category = canonical_category(result.get("failure_category"))

    cause_ok = isinstance(likely_cause, str) and len(likely_cause.strip()) >= 15 and likely_cause.strip().lower() != "not provided"
    reasoning_ok = isinstance(reasoning, str) and len(reasoning.strip()) >= 20

    if isinstance(candidates, list) and candidates:
        decision_ok = bool(
            isinstance(reasoning, str)
            and (
                any(
                    isinstance(candidate, dict)
                    and isinstance(candidate.get("id", candidate.get("action_id")), str)
                    and candidate.get("id", candidate.get("action_id")) in reasoning
                    for candidate in candidates
                )
                or "score" in reasoning.lower()
                or "evidence" in reasoning.lower()
                or "historical" in reasoning.lower()
            )
        )
    else:
        decision_ok = isinstance(reasoning, str) and any(
            term in reasoning.lower()
            for term in ("unknown", "insufficient", "incomplete", "healthy", "monitor", "no failure", "additional evidence")
        )

    checklist_ok = (
        isinstance(checklist, list)
        and any(isinstance(item, str) and len(item.strip()) >= 12 for item in checklist)
    )

    checks = {
        "likely_cause_explained": bool(cause_ok),
        "reasoning_provided": bool(reasoning_ok),
        "decision_rationale_present": bool(decision_ok),
        "verification_checklist_actionable": bool(checklist_ok),
    }
    score = sum(checks.values())
    return {
        "checks": checks,
        "score": score,
        "maximum_score": 4,
        "percentage": _round(score / 4),
    }


def contract_metric(result: Any) -> dict[str, Any]:
    """Validate mandatory shared output fields using Member 4's helper."""
    problems = validate_result(result)
    return {"valid": not problems, "problems": problems}


def average_metric(records: list[dict[str, Any]], path: tuple[str, ...]) -> float | None:
    """Return mean of a numeric nested result field, ignoring failed records."""
    values: list[float] = []
    for record in records:
        value: Any = record
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return _round(sum(values) / len(values)) if values else None
