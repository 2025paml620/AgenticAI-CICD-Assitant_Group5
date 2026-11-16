"""
Unit and shared-contract tests for Utility-Based Agent.

Owner: Member 2 - Avinash
Project: Intelligent CI/CD Pipeline Failure Assistant

Run:
    python -m pytest tests/test_utility.py -v
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agents.base_agent import REQUIRED_FIELDS, canonical_category, validate_result
from agents.utility_based import UtilityBasedAgent


@pytest.fixture
def agent() -> UtilityBasedAgent:
    return UtilityBasedAgent()


@pytest.fixture(scope="module")
def scenarios() -> list[dict]:
    scenario_path = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"
    payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    # Simulate scenario_loader.agent_input: the grader-only expected block is
    # removed before the scenario is supplied to any agent.
    return [
        {key: value for key, value in scenario.items() if key != "expected"}
        for scenario in payload["scenarios"]
    ]


# --------------------------------------------------
# TEST 1: Utility formula calculation
# --------------------------------------------------
def test_calculate_utility(agent):
    action = {
        "success_probability": 0.85,
        "evidence_relevance": 0.95,
        "safety": 1.0,
        "cost": 0.2,
    }
    assert agent.calculate_utility(action) == 0.805


# --------------------------------------------------
# TEST 2: Best action selection for primary scenarios
# --------------------------------------------------
@pytest.mark.parametrize(
    ("scenario_id", "category", "action_id"),
    [
        ("A", "unit_test", "inspect_tests"),
        ("B", "dependency", "inspect_versions"),
        ("C", "deployment", "inspect_health"),
    ],
)
def test_best_action_selection_for_primary_scenarios(agent, scenarios, scenario_id, category, action_id):
    scenario = next(item for item in scenarios if item["id"] == scenario_id)
    result = agent.decide(scenario)
    assert result["failure_category"] == category
    assert result["candidate_scores"]
    assert max(result["candidate_scores"], key=lambda row: row["utility_score"])["id"] == action_id
    assert result["recommended_step"] == next(
        action["step"] for action in agent.ACTION_CATALOG[category]
        if action["id"] == action_id
    )


# --------------------------------------------------
# TEST 3: Failure category normalization
# --------------------------------------------------
@pytest.mark.parametrize(
    ("failure_type", "expected"),
    [
        ("unit_test", "unit_test"),
        ("dependency", "dependency"),
        ("deployment", "deployment"),
        ("none", "healthy"),
        ("healthy", "healthy"),
        ("unknown", "unknown"),
        ("ambiguous", "unknown"),
    ],
)
def test_failure_category_normalization(agent, failure_type, expected):
    result = agent.decide({"failure_type": failure_type})
    assert result["failure_category"] == expected
    assert canonical_category(result["failure_category"]) == expected


# --------------------------------------------------
# TEST 4: Standard output structure
# --------------------------------------------------
def test_standard_output_structure(agent, scenarios):
    result = agent.decide(scenarios[0])
    assert set(REQUIRED_FIELDS).issubset(result)
    assert not validate_result(result)


# --------------------------------------------------
# TEST 5: Candidate utility scores are within the theoretical range
# --------------------------------------------------
@pytest.mark.parametrize("scenario_id", ["A", "B", "C"])
def test_candidate_scores_are_within_theoretical_utility_range(agent, scenarios, scenario_id):
    scenario = next(item for item in scenarios if item["id"] == scenario_id)
    result = agent.decide(scenario)
    # Formula range: minimum -0.1, maximum 0.9.
    assert all(-0.1 <= item["utility_score"] <= 0.9 for item in result["candidate_scores"])


# --------------------------------------------------
# TEST 6: Missing utility parameter validation
# --------------------------------------------------
def test_missing_utility_parameter(agent):
    with pytest.raises(ValueError, match="Missing utility parameter"):
        agent.calculate_utility({"success_probability": 0.8})


# --------------------------------------------------
# TEST 7: Invalid utility values are rejected
# --------------------------------------------------
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("success_probability", 1.5),
        ("evidence_relevance", -0.2),
        ("safety", 2),
        ("cost", -1),
        ("cost", True),
        ("safety", "high"),
    ],
)
def test_invalid_utility_values(agent, field, value):
    action = {
        "success_probability": 0.8,
        "evidence_relevance": 0.8,
        "safety": 1.0,
        "cost": 0.2,
    }
    action[field] = value
    with pytest.raises(ValueError):
        agent.calculate_utility(action)


# --------------------------------------------------
# TEST 8: Unknown scenario returns safe fallback
# --------------------------------------------------
def test_unknown_scenario_returns_safe_fallback(agent, scenarios):
    scenario = next(item for item in scenarios if item["id"] == "D")
    result = agent.decide(scenario)
    assert result["failure_category"] == "unknown"
    assert result["utility_score"] is None
    assert result["candidate_scores"] == []
    assert "complete pipeline logs" in result["recommended_step"].lower()
    assert not validate_result(result)


# --------------------------------------------------
# TEST 9: Healthy scenario does not recommend troubleshooting
# --------------------------------------------------
def test_healthy_scenario_does_not_recommend_troubleshooting(agent, scenarios):
    scenario = next(item for item in scenarios if item["id"] == "E")
    result = agent.decide(scenario)
    assert result["failure_category"] == "healthy"
    assert result["utility_score"] is None
    assert result["candidate_scores"] == []
    assert "no troubleshooting action" in result["recommended_step"].lower()
    assert not validate_result(result)


# --------------------------------------------------
# TEST 10: Invalid scenario input is rejected
# --------------------------------------------------
@pytest.mark.parametrize("invalid_scenario", [None, [], "unit_test", 123])
def test_invalid_scenario_input(agent, invalid_scenario):
    with pytest.raises(TypeError, match="Scenario must be a dictionary"):
        agent.decide(invalid_scenario)


# --------------------------------------------------
# TEST 11: dependency_info alias is supported
# --------------------------------------------------
def test_dependency_info_alias_is_supported(agent):
    scenario = {
        "failure_type": "dependency",
        "dependency_info": {"package": "pydantic", "status": "unavailable"},
        "build_logs": "Could not find a matching distribution for pydantic.",
    }
    evidence = agent.get_supporting_evidence(scenario)
    assert any("Dependency information" in item for item in evidence)


# --------------------------------------------------
# TEST 12: dependencies field from shared fixtures is supported
# --------------------------------------------------
def test_dependencies_field_from_shared_fixtures_is_supported(agent, scenarios):
    scenario = next(item for item in scenarios if item["id"] == "B")
    evidence = agent.get_supporting_evidence(scenario)
    dependency_items = [item for item in evidence if "Dependency information" in item]
    assert len(dependency_items) == 1
    assert "pydantic" in dependency_items[0]


# --------------------------------------------------
# TEST 13: Dependency aliases do not duplicate identical evidence
# --------------------------------------------------
def test_both_dependency_aliases_do_not_duplicate_identical_evidence(agent):
    shared_value = {"package": "pydantic", "status": "unavailable"}
    evidence = agent.get_supporting_evidence({
        "failure_type": "dependency",
        "dependency_info": shared_value,
        "dependencies": shared_value,
    })
    assert len([item for item in evidence if "Dependency information" in item]) == 1


# --------------------------------------------------
# TEST 14: Deployment logs are included in supporting evidence
# --------------------------------------------------
def test_deployment_logs_are_included_in_supporting_evidence(agent, scenarios):
    scenario = next(item for item in scenarios if item["id"] == "C")
    evidence = agent.get_supporting_evidence(scenario)
    deployment_items = [item for item in evidence if "Deployment/runtime logs" in item]
    assert len(deployment_items) == 1
    assert "DATABASE_URL" in deployment_items[0]


# --------------------------------------------------
# TEST 15: runtime_logs alias is supported
# --------------------------------------------------
def test_runtime_logs_alias_is_supported(agent):
    evidence = agent.get_supporting_evidence({
        "failure_type": "deployment",
        "runtime_logs": "Application returned HTTP 503.",
    })
    assert any("Application returned HTTP 503" in item for item in evidence)


# --------------------------------------------------
# TEST 16: Grader-only expected block is not used as evidence
# --------------------------------------------------
def test_expected_block_is_not_returned_as_supporting_evidence(agent, scenarios):
    scenario = copy.deepcopy(scenarios[0])
    scenario["expected"] = {"failure_category": "secret-grader-value"}
    result = agent.decide(scenario)
    assert all("secret-grader-value" not in item for item in result["supporting_evidence"])


# --------------------------------------------------
# TEST 17: Input scenario is not mutated
# --------------------------------------------------
def test_scenario_is_not_mutated(agent, scenarios):
    scenario = copy.deepcopy(scenarios[2])
    before = copy.deepcopy(scenario)
    agent.decide(scenario)
    assert scenario == before


# --------------------------------------------------
# TEST 18: Equal utility scores use catalog-order tie-breaking
# --------------------------------------------------
def test_tie_breaking_uses_catalog_order(agent, monkeypatch):
    actions = [
        {
            "id": "first", "step": "First action",
            "success_probability": 0.8, "evidence_relevance": 0.8,
            "safety": 1.0, "cost": 0.2,
        },
        {
            "id": "second", "step": "Second action",
            "success_probability": 0.8, "evidence_relevance": 0.8,
            "safety": 1.0, "cost": 0.2,
        },
    ]
    monkeypatch.setitem(agent.ACTION_CATALOG, "unit_test", actions)
    result = agent.decide({"failure_type": "unit_test"})
    assert result["recommended_step"] == "First action"


# --------------------------------------------------
# TEST 19: Empty and missing evidence are handled safely
# --------------------------------------------------
def test_empty_and_missing_evidence_are_handled(agent):
    result = agent.decide({"failure_type": "unit_test"})
    assert result["supporting_evidence"] == []
    assert result["recommended_step"] == "Inspect failed unit test results"


# --------------------------------------------------
# TEST 20: All five shared scenarios satisfy output contract
# --------------------------------------------------
def test_all_five_shared_scenarios_satisfy_output_contract(agent, scenarios):
    assert [item["id"] for item in scenarios] == ["A", "B", "C", "D", "E"]
    for scenario in scenarios:
        result = agent.decide(scenario)
        assert not validate_result(result), (scenario["id"], validate_result(result))
