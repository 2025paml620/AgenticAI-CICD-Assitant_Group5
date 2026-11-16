from __future__ import annotations

import copy

import pytest

from evaluation.evaluate_agents import _validate_scenario_catalog
from evaluation.metrics import (
    classification_metric,
    evidence_relevance_metric,
    explanation_completeness_metric,
    recommendation_metric,
)
from scenario_loader import agent_input, expected_for, load_scenarios, scenario_ids


# --------------------------------------------------
# TEST 1: Load all scenarios using Member 4's shared loader
# --------------------------------------------------
def test_load_shared_scenarios():
    scenarios = load_scenarios()
    assert [scenario["id"] for scenario in scenarios] == ["A", "B", "C", "D", "E"]
    assert scenario_ids() == ["A", "B", "C", "D", "E"]
    assert all("expected" in scenario for scenario in scenarios)


# --------------------------------------------------
# TEST 2: Shared agent_input excludes evaluator-only expected data
# --------------------------------------------------
def test_agent_input_excludes_expected_and_expected_for_returns_answer_key():
    scenario = agent_input("A")
    expected = expected_for("A")

    assert "expected" not in scenario
    assert expected["failure_category"] == "unit_test"
    assert "expected" not in scenario


# --------------------------------------------------
# TEST 3: Shared loader returns independent deep copies
# --------------------------------------------------
def test_agent_inputs_are_independent_deep_copies():
    utility_input = agent_input("A")
    learning_input = agent_input("A")
    original_name = learning_input["name"]

    utility_input["name"] = "MODIFIED"
    utility_input["pipeline_status"]["build"] = "MODIFIED"
    utility_input["test_results"]["failed"] = 999

    assert learning_input["name"] == original_name
    assert learning_input["pipeline_status"]["build"] != "MODIFIED"
    assert learning_input["test_results"]["failed"] != 999


# --------------------------------------------------
# TEST 4: Evaluator rejects duplicate scenario IDs
# --------------------------------------------------
def test_evaluator_rejects_duplicate_scenario_ids():
    expected = {"failure_category": "unit_test", "acceptable_next_steps": []}
    scenarios = [
        {"id": "A", "expected": copy.deepcopy(expected)},
        {"id": "A", "expected": copy.deepcopy(expected)},
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        _validate_scenario_catalog(scenarios)


# --------------------------------------------------
# TEST 5: Evaluator validates expected outcome structure
# --------------------------------------------------
def test_evaluator_rejects_invalid_expected_block():
    scenarios = [{"id": "A", "expected": {"failure_category": "unit_test"}}]
    with pytest.raises(ValueError, match="acceptable_next_steps"):
        _validate_scenario_catalog(scenarios)


# --------------------------------------------------
# TEST 6: Canonical classification comparison
# --------------------------------------------------
def test_classification_uses_canonical_categories():
    result = classification_metric("none", "healthy")
    assert result["correct"] is True
    assert result["score"] == 1.0


# --------------------------------------------------
# TEST 7: Evidence aliases are normalized without double counting
# --------------------------------------------------
def test_evidence_aliases_are_normalized():
    result = evidence_relevance_metric(
        "B",
        [
            "Dependency information (dependencies): package x",
            "Additional dependency information (dependency_info): package x",
            "Build logs: missing package",
        ],
    )
    assert "dependencies" in result["predicted_sources"]
    assert result["predicted_sources"].count("dependencies") == 1


# --------------------------------------------------
# TEST 8: Evidence precision, recall and F1 calculations
# --------------------------------------------------
def test_evidence_f1_calculation():
    result = evidence_relevance_metric(
        "A",
        [
            "Pipeline status: tests failed",
            "Build logs: test stage failed",
            "Test results: two failed",
        ],
    )
    assert result["true_positive"] == 3
    assert result["false_positive"] == 0
    assert result["false_negative"] == 1
    assert result["precision"] == 1.0
    assert result["recall"] == 0.75
    assert result["f1_score"] == 0.8571


# --------------------------------------------------
# TEST 9: Empty evidence receives zero precision, recall and F1
# --------------------------------------------------
def test_empty_evidence_scores_zero():
    result = evidence_relevance_metric("A", [])
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1_score"] == 0.0


# --------------------------------------------------
# TEST 10: Acceptable recommendation phrase matching
# --------------------------------------------------
@pytest.mark.parametrize(
    ("recommendation", "acceptable", "expected"),
    [
        ("Inspect failed unit test results", ["failing test", "regression"], True),
        ("Check dependency versions and compatibility", ["version", "package"], True),
        ("No troubleshooting action required; continue monitoring pipeline health", ["no troubleshooting", "monitor"], True),
        ("Restart the server", ["inspect health", "runtime logs"], False),
    ],
)
def test_recommendation_metric(recommendation, acceptable, expected):
    result = recommendation_metric(recommendation, acceptable)
    assert result["appropriate"] is expected


# --------------------------------------------------
# TEST 11: Explanation completeness rubric
# --------------------------------------------------
def test_explanation_completeness_rubric():
    result = explanation_completeness_metric({
        "failure_category": "unit_test",
        "likely_cause": "Possible regression in recently modified payment validation code.",
        "recommended_step": "Inspect failed unit test results",
        "reasoning": "Selected inspect_tests because it achieved the highest utility score of 0.8050.",
        "candidate_scores": [{"id": "inspect_tests"}],
        "verification_checklist": ["Review failed test output and verify the result after the fix."],
    })
    assert result["score"] == 4
    assert result["percentage"] == 1.0


# --------------------------------------------------
# TEST 12: Shared loader's full scenario and agent snapshots stay separate
# --------------------------------------------------
def test_expected_block_is_not_mutable_through_agent_snapshot():
    full_scenario = next(s for s in load_scenarios() if s["id"] == "A")
    expected_before = expected_for("A")
    agent_snapshot = agent_input("A")

    agent_snapshot["name"] = "CHANGED"
    assert full_scenario["name"] != "CHANGED"
    assert expected_for("A") == expected_before
