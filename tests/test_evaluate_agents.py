from __future__ import annotations

import json
from pathlib import Path

from evaluation.evaluate_agents import evaluate
from scenario_loader import SCENARIO_FILE


SCENARIOS_PATH = Path(SCENARIO_FILE)


# --------------------------------------------------
# TEST 1: Orchestrator runs ten agent-scenario evaluations
# --------------------------------------------------
def test_evaluator_runs_ten_cases_and_validates_contracts(tmp_path):
    output_path = tmp_path / "results.json"
    payload = evaluate(SCENARIOS_PATH, output_path)

    assert len(payload["results"]) == 10
    assert all(row["evaluation_valid"] for row in payload["results"])
    assert all(row["agent_input_excluded_expected"] for row in payload["results"])
    assert output_path.is_file()

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(saved["results"]) == 10
    assert saved["evaluation_metadata"]["scenario_loader"] == "scenario_loader.py (Member 4 shared loader)"
    assert all(row["scenario_unchanged"] for row in saved["results"])


# --------------------------------------------------
# TEST 2: Each baseline Learning Agent case is isolated
# --------------------------------------------------
def test_learning_baselines_are_configured_as_fresh_histories(tmp_path):
    output_path = tmp_path / "results.json"
    payload = evaluate(SCENARIOS_PATH, output_path)
    learning_rows = [
        row for row in payload["results"]
        if row["agent"] == "Learning-Based Agent"
    ]
    assert len(learning_rows) == 5
    assert all(row["evaluation_valid"] for row in learning_rows)
    assert "Fresh zero-count temporary experience file per scenario" in payload[
        "evaluation_metadata"
    ]["learning_baseline_policy"]


# --------------------------------------------------
# TEST 3: Learning before/after experiment uses simulated feedback
# --------------------------------------------------
def test_learning_experiment_changes_recommendation_without_real_history(tmp_path):
    payload = evaluate(SCENARIOS_PATH, tmp_path / "results.json")
    experiment = payload["learning_before_after_experiment"]

    assert experiment["status"] == "completed"
    assert experiment["feedback_type"] == "simulated"
    assert experiment["experience_file_is_temporary"] is True
    assert experiment["recommendation_changed"] is True
    assert experiment["after_feedback_recommendation_appropriate"] is True
    assert experiment["baseline_action_id"] == "inspect_tests"
    assert experiment["after_feedback_action_id"] == "inspect_changes"


# --------------------------------------------------
# TEST 4: Evaluator summarizes primary and robustness scenarios separately
# --------------------------------------------------
def test_evaluator_separates_primary_and_robustness_summaries(tmp_path):
    payload = evaluate(SCENARIOS_PATH, tmp_path / "results.json")

    for agent_name, summary in payload["agent_summaries"].items():
        assert summary["primary_scenarios_A_to_C"]["evaluation_count"] == 3
        assert summary["robustness_scenarios_D_to_E"]["evaluation_count"] == 2
        assert summary["all_scenarios"]["evaluation_count"] == 5
        assert summary["all_scenarios"]["valid_evaluations"] == 5


# --------------------------------------------------
# TEST 5: Evaluator requires the shared loader's configured scenario fixture
# --------------------------------------------------
def test_evaluator_rejects_unconfigured_scenario_path(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="scenario_loader.py"):
        evaluate(tmp_path / "other_scenarios.json", tmp_path / "results.json")
