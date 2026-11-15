
"""
Unit tests for Utility-Based Agent.

Owner: Member 2 - Avinash
Project: Intelligent CI/CD Pipeline Failure Assistant

Run:
    python -m pytest tests/test_utility.py -v
"""

import pytest

from agents.utility_based import UtilityBasedAgent


@pytest.fixture
def agent():
    """Create a fresh Utility-Based Agent for each test."""
    return UtilityBasedAgent()


@pytest.fixture
def scenarios():
    """Provide three representative CI/CD failure scenarios."""

    return {
        "A": {
            "failure_type": "unit_test",
            "pipeline_status": {
                "build": "passed",
                "tests": "failed",
                "deployment": "not_started"
            },
            "build_logs": "Expected 200 but received 500",
            "test_results": {
                "passed": 18,
                "failed": 2
            },
            "recent_changes": ["Modified payment API"]
        },

        "B": {
            "failure_type": "dependency",
            "pipeline_status": {
                "build": "failed",
                "tests": "not_started",
                "deployment": "not_started"
            },
            "build_logs": "Package version unavailable",
            "dependencies": {
                "status": "failed"
            },
            "recent_changes": ["Updated requirements.txt"]
        },

        "C": {
            "failure_type": "deployment",
            "pipeline_status": {
                "build": "passed",
                "tests": "passed",
                "deployment": "unhealthy"
            },
            "build_logs": "Health endpoint returned HTTP 503",
            "test_results": {
                "passed": 24,
                "failed": 0
            },
            "health_checks": {
                "status": "failed",
                "details": "HTTP 503"
            }
        }
    }


# --------------------------------------------------
# TEST 1: Utility formula calculation
# --------------------------------------------------

def test_calculate_utility(agent):

    action = {
        "success_probability": 0.85,
        "evidence_relevance": 0.95,
        "safety": 1.00,
        "cost": 0.20
    }

    score = agent.calculate_utility(action)

    assert score == pytest.approx(0.805)


# --------------------------------------------------
# TEST 2: Highest utility action selection
# --------------------------------------------------

@pytest.mark.parametrize(
    "scenario_id, expected_action, expected_score",
    [
        ("A", "inspect_tests", 0.805),
        ("B", "inspect_versions", 0.834),
        ("C", "inspect_health", 0.834)
    ]
)
def test_best_action_selection(
    agent,
    scenarios,
    scenario_id,
    expected_action,
    expected_score
):

    result = agent.decide(scenarios[scenario_id])

    assert result["candidate_scores"]

    selected = max(
        result["candidate_scores"],
        key=lambda action: action["utility_score"]
    )

    assert selected["id"] == expected_action

    assert result["recommended_step"] == selected["step"]

    assert result["utility_score"] == pytest.approx(
        expected_score
    )


# --------------------------------------------------
# TEST 3: Correct failure classification
# --------------------------------------------------

@pytest.mark.parametrize(
    "scenario_id, expected_category",
    [
        ("A", "unit_test"),
        ("B", "dependency"),
        ("C", "deployment")
    ]
)
def test_failure_classification(
    agent,
    scenarios,
    scenario_id,
    expected_category
):

    result = agent.decide(scenarios[scenario_id])

    assert result["failure_category"] == expected_category


# --------------------------------------------------
# TEST 4: Common output structure
# --------------------------------------------------

def test_standard_output_structure(agent, scenarios):

    result = agent.decide(scenarios["A"])

    required_fields = [
        "agent",
        "failure_category",
        "supporting_evidence",
        "likely_cause",
        "recommended_step",
        "reasoning",
        "verification_checklist",
        "utility_score",
        "candidate_scores"
    ]

    for field in required_fields:
        assert field in result

    assert result["agent"] == "Utility-Based Agent"
    assert isinstance(result["supporting_evidence"], list)
    assert isinstance(result["candidate_scores"], list)
    assert result["recommended_step"]
    assert result["reasoning"]


# --------------------------------------------------
# TEST 5: All candidate scores must be valid
# --------------------------------------------------

@pytest.mark.parametrize("scenario_id", ["A", "B", "C"])
def test_candidate_scores_are_valid(
    agent,
    scenarios,
    scenario_id
):

    result = agent.decide(scenarios[scenario_id])

    for candidate in result["candidate_scores"]:

        assert -0.1 <= candidate["utility_score"] <= 0.9

        assert candidate["id"]

        assert candidate["step"]


# --------------------------------------------------
# TEST 6: Missing utility parameter
# --------------------------------------------------

def test_missing_utility_parameter(agent):

    invalid_action = {
        "success_probability": 0.85,
        "evidence_relevance": 0.95,
        "safety": 1.0
        # Cost is intentionally missing
    }

    with pytest.raises(ValueError, match="cost"):
        agent.calculate_utility(invalid_action)


# --------------------------------------------------
# TEST 7: Invalid utility parameter values
# --------------------------------------------------

@pytest.mark.parametrize(
    "field, invalid_value",
    [
        ("success_probability", 1.5),
        ("evidence_relevance", -0.2),
        ("safety", 2.0),
        ("cost", -1.0),
        ("cost", True),
        ("safety", "high")
    ]
)
def test_invalid_utility_values(
    agent,
    field,
    invalid_value
):

    action = {
        "success_probability": 0.85,
        "evidence_relevance": 0.95,
        "safety": 1.0,
        "cost": 0.20
    }

    action[field] = invalid_value

    with pytest.raises(ValueError):
        agent.calculate_utility(action)


# --------------------------------------------------
# TEST 8: Unknown failure category
# --------------------------------------------------

def test_unknown_failure_category(agent):

    scenario = {
        "failure_type": "unknown_failure",
        "build_logs": "Unexpected pipeline error"
    }

    result = agent.decide(scenario)

    assert result["failure_category"] == "unknown_failure"

    assert result["recommended_step"] == (
        "Collect additional diagnostic evidence"
    )

    assert result["utility_score"] is None

    assert result["candidate_scores"] == []


# --------------------------------------------------
# TEST 9: Invalid scenario input
# --------------------------------------------------

@pytest.mark.parametrize(
    "invalid_scenario",
    [
        None,
        [],
        "unit_test",
        123
    ]
)
def test_invalid_scenario_input(agent, invalid_scenario):

    with pytest.raises(TypeError):
        agent.decide(invalid_scenario)


# --------------------------------------------------
# TEST 10: Deterministic tie-breaking
# --------------------------------------------------

def test_tie_breaking_uses_catalog_order(agent, monkeypatch):

    actions = [
        {
            "id": "first",
            "step": "First action",
            "success_probability": 0.8,
            "evidence_relevance": 0.8,
            "safety": 1.0,
            "cost": 0.2
        },
        {
            "id": "second",
            "step": "Second action",
            "success_probability": 0.8,
            "evidence_relevance": 0.8,
            "safety": 1.0,
            "cost": 0.2
        }
    ]

    monkeypatch.setitem(
        agent.ACTION_CATALOG,
        "unit_test",
        actions
    )

    result = agent.decide({"failure_type": "unit_test"})

    assert result["recommended_step"] == "First action"
