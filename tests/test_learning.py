"""
"Automated tests for the shared-schema-compatible Learning Agent.

Owner: Member 2 - Avinash
Project: Intelligent CI/CD Pipeline Failure Assistant

Run:
    python -m pytest tests/test_learning.py -v
"""


import json
from copy import deepcopy
from pathlib import Path

import pytest

from agents.base_agent import REQUIRED_FIELDS, canonical_category, validate_result
from agents.learning_agent import LearningAgent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = PROJECT_ROOT / "data" / "scenarios.json"


@pytest.fixture

def agent(tmp_path):
    """Use an isolated experience file for every test."""
    return LearningAgent(experience_file=tmp_path / "experience.json")


@pytest.fixture(scope="module")
def shared_scenarios():
    """Load Karthik's fixtures and remove grader-only expected blocks."""
    with SCENARIOS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    scenarios = {}
    for source in data["scenarios"]:
        scenario = {key: value for key, value in source.items() if key != "expected"}
        scenarios[scenario["id"]] = scenario
    return scenarios


# --------------------------------------------------
# TEST 1: Missing experience file initialization
# --------------------------------------------------
def test_missing_experience_file_is_initialized(agent):
    assert agent.experience_file.exists()
    assert agent.experience["unit_test"]["inspect_tests"] == {
        "success": 0, "failure": 0
    }
    assert agent.experience["dependency"]["inspect_versions"] == {
        "success": 0, "failure": 0
    }
    assert agent.experience["deployment"]["inspect_health"] == {
        "success": 0, "failure": 0
    }


# --------------------------------------------------
# TEST 2: Laplace-smoothed success-rate calculation
# --------------------------------------------------
@pytest.mark.parametrize(
    ("success", "failure", "expected"),
    [(0, 0, 0.5), (8, 2, 0.75), (0, 3, 0.2), (3, 0, 0.8)],
)
def test_laplace_smoothed_success_rate(success, failure, expected):
    assert LearningAgent.calculate_success_rate(success, failure) == expected


# --------------------------------------------------
# TEST 3: Invalid historical counts are rejected
# --------------------------------------------------
@pytest.mark.parametrize(
    ("success", "failure"),
    [(-1, 0), (0, -1), (True, 0), (0, False), (1.5, 0)],
)
def test_success_rate_rejects_invalid_counts(success, failure):
    with pytest.raises(ValueError):
        LearningAgent.calculate_success_rate(success, failure)


# --------------------------------------------------
# TEST 4: Common and Learning Agent output fields
# --------------------------------------------------
def test_decision_has_common_and_learning_output_fields(agent):
    result = agent.decide({"failure_type": "unit_test"})
    assert set(REQUIRED_FIELDS).issubset(result)
    assert {
        "experience_used", "candidate_scores", "selected_action_id",
        "success_rate", "evidence_relevance", "learning_score",
    }.issubset(result)
    assert result["selected_action_id"] == "inspect_tests"
    assert len(result["candidate_scores"]) == 3
    assert result["experience_used"]["history_weight"] == 0.6
    assert validate_result(result) == []


# --------------------------------------------------
# TEST 5: Evidence relevance favours matching test evidence
# --------------------------------------------------
def test_evidence_relevance_prefers_action_supported_by_test_evidence(agent):
    scenario = {
        "failure_type": "unit_test",
        "test_results": {"status": "failed", "failed": 2, "message": "assertion error"},
    }
    test_score = agent.calculate_evidence_relevance(scenario, "inspect_tests")
    change_score = agent.calculate_evidence_relevance(scenario, "inspect_changes")
    assert test_score["evidence_relevance"] > change_score["evidence_relevance"]
    assert "test_results" in test_score["matched_fields"]


# --------------------------------------------------
# TEST 6: Evidence can change action selection when history is tied
# --------------------------------------------------
def test_evidence_changes_selection_when_history_is_tied(agent):
    scenario = {
        "failure_type": "unit_test",
        "test_results": {"status": "failed", "failed": 2, "message": "assertion error"},
    }
    result = agent.decide(scenario)
    assert result["selected_action_id"] == "inspect_tests"
    assert result["evidence_relevance"] > 0


# --------------------------------------------------
# TEST 7: Successful feedback is persisted
# --------------------------------------------------
def test_success_feedback_is_persisted(agent):
    result = agent.update_experience("unit_test", "inspect_tests", True)
    assert result["success"] == 1
    assert result["failure"] == 0
    saved = json.loads(agent.experience_file.read_text(encoding="utf-8"))
    assert saved["unit_test"]["inspect_tests"] == {"success": 1, "failure": 0}


# --------------------------------------------------
# TEST 8: Unsuccessful feedback is persisted
# --------------------------------------------------
def test_failure_feedback_is_persisted(agent):
    result = agent.update_experience("unit_test", "inspect_tests", False)
    assert result["success"] == 0
    assert result["failure"] == 1
    saved = json.loads(agent.experience_file.read_text(encoding="utf-8"))
    assert saved["unit_test"]["inspect_tests"] == {"success": 0, "failure": 1}


# --------------------------------------------------
# TEST 9: New agent instance reads persisted feedback
# --------------------------------------------------
def test_new_agent_instance_reads_persisted_feedback(agent):
    agent.update_experience("dependency", "inspect_versions", True)
    second_agent = LearningAgent(experience_file=agent.experience_file)
    assert second_agent.experience["dependency"]["inspect_versions"] == {
        "success": 1, "failure": 0
    }


# --------------------------------------------------
# TEST 10: Existing agent instance refreshes persisted history
# --------------------------------------------------
def test_existing_instance_refreshes_history_before_decision(agent):
    second_agent = LearningAgent(experience_file=agent.experience_file)
    agent.update_experience("unit_test", "inspect_changes", True)
    result = second_agent.decide({"failure_type": "unit_test"})
    assert result["experience_used"]["candidates"][1]["success"] == 1


# --------------------------------------------------
# TEST 11: Feedback changes future action selection
# --------------------------------------------------
def test_feedback_can_change_future_action_selection(agent):
    initial = agent.decide({"failure_type": "unit_test"})
    assert initial["selected_action_id"] == "inspect_tests"

    for _ in range(3):
        agent.update_experience("unit_test", "inspect_tests", False)
        agent.update_experience("unit_test", "inspect_changes", True)

    learned = agent.decide({"failure_type": "unit_test"})
    assert learned["selected_action_id"] == "inspect_changes"
    assert learned["success_rate"] == 0.8


# --------------------------------------------------
# TEST 12: Invalid feedback is rejected
# --------------------------------------------------
@pytest.mark.parametrize(
    ("category", "action_id", "succeeded"),
    [
        ("unknown", "inspect_tests", True),
        ("unit_test", "unknown_action", True),
        ("unit_test", "inspect_tests", 1),
        ("unit_test", "inspect_tests", "yes"),
        ([], "inspect_tests", True),
        ("unit_test", [], True),
        (None, "inspect_tests", True),
        ("unit_test", None, True),
        ("healthy", "inspect_tests", True),
    ],
)
def test_invalid_feedback_is_rejected(agent, category, action_id, succeeded):
    with pytest.raises(ValueError):
        agent.update_experience(category, action_id, succeeded)


# --------------------------------------------------
# TEST 13: Feedback categories accept shared category aliases
# --------------------------------------------------
def test_feedback_category_alias_is_normalized(agent):
    result = agent.update_experience("unit_test_failure", "inspect_tests", True)
    assert result["failure_category"] == "unit_test"
    assert agent.experience["unit_test"]["inspect_tests"]["success"] == 1


# --------------------------------------------------
# TEST 14: Invalid scenario input types are rejected
# --------------------------------------------------
@pytest.mark.parametrize("scenario", [None, [], "unit_test", 123])
def test_invalid_scenario_types_are_rejected(agent, scenario):
    with pytest.raises(TypeError):
        agent.decide(scenario)


# --------------------------------------------------
# TEST 15: Missing failure category safely maps to unknown
# --------------------------------------------------
@pytest.mark.parametrize("scenario", [{}, {"failure_type": ""}, {"failure_type": None}])
def test_missing_failure_category_returns_unknown_fallback(agent, scenario):
    result = agent.decide(scenario)
    assert result["failure_category"] == "unknown"
    assert result["selected_action_id"] is None
    assert result["candidate_scores"] == []
    assert result["experience_used"] is None
    assert validate_result(result) == []


# --------------------------------------------------
# TEST 16: Unknown category returns safe fallback
# --------------------------------------------------
def test_unknown_failure_category_returns_safe_fallback(agent):
    result = agent.decide({"failure_type": "unknown"})
    assert result["failure_category"] == "unknown"
    assert result["selected_action_id"] is None
    assert result["candidate_scores"] == []
    assert result["experience_used"] is None
    assert "additional" in result["recommended_step"].lower() or "collect" in result["recommended_step"].lower()
    assert validate_result(result) == []


# --------------------------------------------------
# TEST 17: Healthy category does not recommend troubleshooting
# --------------------------------------------------
def test_healthy_category_does_not_recommend_troubleshooting(agent):
    result = agent.decide({"failure_type": "none"})
    assert result["failure_category"] == "healthy"
    assert result["selected_action_id"] is None
    assert result["candidate_scores"] == []
    assert "no troubleshooting" in result["recommended_step"].lower()
    assert "monitor" in result["recommended_step"].lower()
    assert validate_result(result) == []


# --------------------------------------------------
# TEST 18: Shared canonical category aliases are normalized
# --------------------------------------------------
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("unit_test_failure", "unit_test"),
        ("build_failure", "dependency"),
        ("health_check_failure", "deployment"),
        ("none", "healthy"),
        ("passed", "healthy"),
        ("ambiguous", "unknown"),
        ("insufficient_evidence", "unknown"),
    ],
)
def test_shared_category_aliases_are_normalized(agent, source, expected):
    result = agent.decide({"failure_type": source})
    assert result["failure_category"] == expected


# --------------------------------------------------
# TEST 19: Dependency aliases count as one logical evidence group
# --------------------------------------------------
@pytest.mark.parametrize("dependency_field", ["dependency_info", "dependencies"])
def test_dependency_field_alias_counts_as_one_group(agent, dependency_field):
    scenario = {
        "failure_type": "dependency",
        dependency_field: {
            "status": "unresolved",
            "notes": "pydantic version unavailable on package index",
        },
        "build_logs": "Build failed during dependency version resolution.",
    }
    result = agent.calculate_evidence_relevance(scenario, "inspect_versions")
    assert result["field_coverage"] == 1.0
    assert len(result["matched_field_groups"]) == 2
    assert dependency_field in result["matched_fields"]


# --------------------------------------------------
# TEST 20: Duplicate dependency aliases do not inflate field coverage
# --------------------------------------------------
def test_both_dependency_aliases_count_as_one_field_group(agent):
    shared_value = {"status": "unresolved", "package": "pydantic"}
    scenario = {
        "failure_type": "dependency",
        "dependency_info": shared_value,
        "dependencies": deepcopy(shared_value),
        "build_logs": "Could not find requested package version.",
    }
    result = agent.calculate_evidence_relevance(scenario, "inspect_versions")
    assert result["field_coverage"] == 1.0
    assert len(result["matched_field_groups"]) == 2
    assert result["matched_fields"].count("dependency_info") == 1
    assert result["matched_fields"].count("dependencies") == 1


# --------------------------------------------------
# TEST 21: Dependency information is included in supporting evidence
# --------------------------------------------------
def test_dependency_alias_is_in_supporting_evidence(agent):
    scenario = {
        "failure_type": "dependency",
        "dependencies": {"status": "unresolved", "package": "pydantic"},
    }
    evidence = agent.get_supporting_evidence(scenario)
    assert any("Dependency information (dependencies)" in item for item in evidence)


# --------------------------------------------------
# TEST 22: Deployment logs are recognized as runtime evidence
# --------------------------------------------------
def test_deployment_logs_are_used_by_runtime_log_action(agent):
    scenario = {
        "failure_type": "deployment",
        "deployment_logs": "ERROR: DATABASE_URL environment variable not set; runtime returned 503.",
        "health_checks": {"observed_status": 503},
        "build_logs": "Deployment pipeline completed build and tests.",
    }
    result = agent.calculate_evidence_relevance(scenario, "inspect_runtime_logs")
    assert "deployment_logs" in result["matched_fields"]
    assert len(result["matched_field_groups"]) == 3
    evidence = agent.get_supporting_evidence(scenario)
    assert any("Deployment/runtime logs (deployment_logs)" in item for item in evidence)


# --------------------------------------------------
# TEST 23: runtime_logs remains a supported deployment-log alias
# --------------------------------------------------
def test_runtime_logs_alias_is_supported(agent):
    scenario = {
        "failure_type": "deployment",
        "runtime_logs": "Application runtime error: database connection failed.",
    }
    result = agent.calculate_evidence_relevance(scenario, "inspect_runtime_logs")
    assert "runtime_logs" in result["matched_fields"]
    assert any("runtime_logs" in item for item in agent.get_supporting_evidence(scenario))


# --------------------------------------------------
# TEST 24: Grader-only expected block is excluded from evidence
# --------------------------------------------------
def test_expected_block_is_not_used_or_returned_as_evidence(agent):
    scenario = {
        "failure_type": "unit_test",
        "build_logs": "Two tests failed with assertion errors.",
        "expected": {
            "failure_category": "dependency",
            "acceptable_next_steps": ["check dependency versions"],
        },
    }
    result = agent.decide(scenario)
    serialized_evidence = " ".join(result["supporting_evidence"]).lower()
    assert "acceptable_next_steps" not in serialized_evidence
    assert result["failure_category"] == "unit_test"


# --------------------------------------------------
# TEST 25: Scenario input is not mutated
# --------------------------------------------------
def test_scenario_is_not_mutated(agent, shared_scenarios):
    scenario = deepcopy(shared_scenarios["C"])
    original = deepcopy(scenario)
    agent.decide(scenario)
    assert scenario == original


# --------------------------------------------------
# TEST 26: Atomic persistence leaves no temporary files
# --------------------------------------------------
def test_atomic_save_leaves_no_temporary_files(agent):
    agent.update_experience("unit_test", "inspect_tests", True)
    leftovers = list(agent.experience_file.parent.glob("*.tmp"))
    assert leftovers == []


# --------------------------------------------------
# TEST 27: Corrupt experience JSON is reported
# --------------------------------------------------
def test_corrupt_json_is_reported(tmp_path):
    path = tmp_path / "experience.json"
    path.write_text("{not-valid-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        LearningAgent(experience_file=path)


# --------------------------------------------------
# TEST 28: Invalid persisted experience counts are rejected
# --------------------------------------------------
def test_invalid_experience_counts_are_rejected(tmp_path):
    path = tmp_path / "experience.json"
    agent = LearningAgent(experience_file=path)
    data = agent.experience
    data["unit_test"]["inspect_tests"]["success"] = -1
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="non-negative integer"):
        LearningAgent(experience_file=path)


# --------------------------------------------------
# TEST 29: Shared scenarios A-E satisfy the common output contract
# --------------------------------------------------
@pytest.mark.parametrize(
    ("scenario_id", "expected_category"),
    [
        ("A", "unit_test"),
        ("B", "dependency"),
        ("C", "deployment"),
        ("D", "unknown"),
        ("E", "healthy"),
    ],
)
def test_all_five_shared_scenarios_satisfy_output_contract(
    agent, shared_scenarios, scenario_id, expected_category
):
    result = agent.decide(shared_scenarios[scenario_id])
    assert result["failure_category"] == expected_category
    assert validate_result(result) == []
    assert set(REQUIRED_FIELDS).issubset(result)


# --------------------------------------------------
# TEST 30: Scenario D avoids a speculative action
# --------------------------------------------------
def test_scenario_d_returns_uncertainty_fallback(agent, shared_scenarios):
    result = agent.decide(shared_scenarios["D"])
    assert result["failure_category"] == "unknown"
    assert result["selected_action_id"] is None
    assert result["candidate_scores"] == []
    assert "incomplete" in result["likely_cause"].lower() or "insufficient" in result["likely_cause"].lower()


# --------------------------------------------------
# TEST 31: Scenario E returns a healthy monitoring response
# --------------------------------------------------
def test_scenario_e_returns_healthy_monitoring_response(agent, shared_scenarios):
    result = agent.decide(shared_scenarios["E"])
    assert result["failure_category"] == "healthy"
    assert result["selected_action_id"] is None
    assert "monitor" in result["recommended_step"].lower()


# --------------------------------------------------
# TEST 32: Scenario C uses deployment logs as supporting evidence
# --------------------------------------------------
def test_scenario_c_includes_deployment_logs(agent, shared_scenarios):
    result = agent.decide(shared_scenarios["C"])
    assert result["failure_category"] == "deployment"
    assert any("deployment_logs" in item for item in result["supporting_evidence"])
    runtime_candidate = next(
        item for item in result["candidate_scores"]
        if item["action_id"] == "inspect_runtime_logs"
    )
    assert "deployment_logs" in runtime_candidate["matched_fields"]


# --------------------------------------------------
# TEST 33: Every catalog action has evidence rules
# --------------------------------------------------
def test_every_catalog_action_has_evidence_rules(agent):
    catalog_ids = {
        action["id"]
        for actions in agent.action_catalog.values()
        for action in actions
    }
    assert catalog_ids == set(agent.EVIDENCE_RULES)


# --------------------------------------------------
# TEST 34: Recommendation alone does not update experience
# --------------------------------------------------
def test_recommendation_does_not_update_experience(agent):
    before = deepcopy(agent.experience)
    agent.decide({"failure_type": "unit_test", "test_results": {"failed": 2}})
    after = json.loads(agent.experience_file.read_text(encoding="utf-8"))
    assert after == before


# --------------------------------------------------
# TEST 35: Base category helper and Learning Agent agree
# --------------------------------------------------
@pytest.mark.parametrize(
    ("raw_category", "canonical"),
    [
        ("unit_test", "unit_test"),
        ("dependency", "dependency"),
        ("deployment", "deployment"),
        ("none", "healthy"),
        ("unknown", "unknown"),
    ],
)
def test_learning_agent_uses_shared_canonical_category(
    agent, raw_category, canonical
):
    result = agent.decide({"failure_type": raw_category})
    assert canonical_category(raw_category) == canonical
    assert result["failure_category"] == canonical


# --------------------------------------------------
# TEST 36: Candidate ordering is deterministic for equal scores
# --------------------------------------------------
def test_equal_learning_scores_use_catalog_order(agent):
    result = agent.decide({"failure_type": "unit_test"})
    assert result["selected_action_id"] == agent.action_catalog["unit_test"][0]["id"]
