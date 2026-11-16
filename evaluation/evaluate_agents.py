"""Run reproducible evaluations for Member 2's Utility and Learning agents."""
from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.base_agent import canonical_category  # noqa: E402
from agents.learning_agent import LearningAgent  # noqa: E402
from agents.utility_based import UtilityBasedAgent  # noqa: E402
from evaluation.metrics import (  # noqa: E402
    classification_metric,
    contract_metric,
    evidence_relevance_metric,
    explanation_completeness_metric,
    recommendation_metric,
)
from scenario_loader import (  # noqa: E402
    SCENARIO_FILE,
    agent_input as shared_agent_input,
    expected_for,
    load_scenarios,
    scenario_ids,
)


PRIMARY_SCENARIO_IDS = {"A", "B", "C"}
ROBUSTNESS_SCENARIO_IDS = {"D", "E"}


def _json_safe(value: Any) -> Any:
    """Convert common non-JSON values to serializable equivalents."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(item) for item in value]
        return repr(value)


def _run_agent_case(
    *,
    agent_name: str,
    agent_factory: Callable[[], Any],
    scenario_metadata: dict[str, Any],
    agent_scenario: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    """Run one agent using a deep-copied snapshot from the shared loader."""
    scenario_id = str(scenario_metadata["id"])
    if not isinstance(agent_scenario, dict):
        raise TypeError("Shared scenario loader must return a dictionary for agent input.")
    if "expected" in agent_scenario:
        raise ValueError("Shared scenario loader leaked the evaluator-only 'expected' block.")

    # Keep a local snapshot so the evaluator can verify that the agent did not mutate it.
    scenario_for_agent = deepcopy(agent_scenario)
    before = deepcopy(scenario_for_agent)
    record: dict[str, Any] = {
        "evaluation_id": f"EVAL-{agent_name.split()[0].upper()}-{scenario_id}",
        "agent": agent_name,
        "scenario_id": scenario_id,
        "scenario_name": scenario_metadata.get("name", ""),
        "evaluation_group": "primary" if scenario_id in PRIMARY_SCENARIO_IDS else "robustness",
        "expected_category": canonical_category(expected.get("failure_category")),
        "agent_input_excluded_expected": "expected" not in scenario_for_agent,
    }

    try:
        agent = agent_factory()
        result = agent.decide(scenario_for_agent)
        unchanged = scenario_for_agent == before
        contract = contract_metric(result)

        if isinstance(result, dict):
            classification = classification_metric(
                expected.get("failure_category", "unknown"),
                result.get("failure_category", "unknown"),
            )
            evidence = evidence_relevance_metric(
                scenario_id, result.get("supporting_evidence", [])
            )
            recommendation = recommendation_metric(
                result.get("recommended_step", ""),
                expected.get("acceptable_next_steps", []),
            )
            explanation = explanation_completeness_metric(result)
            record.update({
                "actual_category": classification["actual_category"],
                "classification": classification,
                "evidence_metrics": evidence,
                "recommendation": recommendation,
                "explanation_completeness": explanation,
                "contract": contract,
                "scenario_unchanged": unchanged,
                "agent_output": _json_safe(result),
                "error": None,
            })
        else:
            record.update({
                "actual_category": "unknown",
                "classification": classification_metric(expected.get("failure_category", "unknown"), "unknown"),
                "evidence_metrics": evidence_relevance_metric(scenario_id, []),
                "recommendation": recommendation_metric("", expected.get("acceptable_next_steps", [])),
                "explanation_completeness": explanation_completeness_metric({}),
                "contract": contract,
                "scenario_unchanged": unchanged,
                "agent_output": _json_safe(result),
                "error": "Agent returned a non-dictionary result.",
            })
    except Exception as exc:  # preserve other evaluation cases if one case fails
        record.update({
            "actual_category": "unknown",
            "classification": classification_metric(expected.get("failure_category", "unknown"), "unknown"),
            "evidence_metrics": evidence_relevance_metric(scenario_id, []),
            "recommendation": recommendation_metric("", expected.get("acceptable_next_steps", [])),
            "explanation_completeness": explanation_completeness_metric({}),
            "contract": {"valid": False, "problems": [f"Agent execution failed: {type(exc).__name__}: {exc}"]},
            "scenario_unchanged": scenario_for_agent == before,
            "agent_output": None,
            "error": f"{type(exc).__name__}: {exc}",
        })

    record["evaluation_valid"] = bool(
        record["contract"]["valid"]
        and record["scenario_unchanged"]
        and record["agent_input_excluded_expected"]
        and record["error"] is None
    )
    return record


def _validate_scenario_catalog(scenarios: list[dict[str, Any]]) -> None:
    """Validate evaluation-specific requirements after Karthik's loader validates fixtures."""
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("The shared scenario loader returned no scenarios.")

    seen_ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario at index {index} must be a dictionary.")
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError(f"Scenario at index {index} has an invalid id.")
        if scenario_id in seen_ids:
            raise ValueError(f"Duplicate scenario id: {scenario_id}")
        seen_ids.add(scenario_id)

        expected = scenario.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"Scenario '{scenario_id}' is missing evaluator-only expected data.")
        if not isinstance(expected.get("failure_category"), str):
            raise ValueError(f"Scenario '{scenario_id}' expected.failure_category must be a string.")
        if not isinstance(expected.get("acceptable_next_steps"), list):
            raise ValueError(f"Scenario '{scenario_id}' expected.acceptable_next_steps must be a list.")

def _summarize_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"evaluation_count": 0}

    count = len(records)
    def mean(path: tuple[str, ...]) -> float:
        values: list[float] = []
        for record in records:
            value: Any = record
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "evaluation_count": count,
        "valid_evaluations": sum(bool(row.get("evaluation_valid")) for row in records),
        "classification_accuracy": mean(("classification", "score")),
        "mean_evidence_precision": mean(("evidence_metrics", "precision")),
        "mean_evidence_recall": mean(("evidence_metrics", "recall")),
        "mean_evidence_f1": mean(("evidence_metrics", "f1_score")),
        "recommendation_appropriateness": mean(("recommendation", "score")),
        "mean_explanation_completeness": mean(("explanation_completeness", "percentage")),
    }


def run_learning_before_after(scenario_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Demonstrate feedback learning using an isolated temporary history file.

    The agent-safe snapshot comes directly from Member 4's shared scenario loader.
    """
    agent_scenario = shared_agent_input(scenario_id)
    if "expected" in agent_scenario:
        raise ValueError("Shared scenario loader leaked the evaluator-only 'expected' block.")
    with tempfile.TemporaryDirectory(prefix="member2_learning_eval_") as temp_dir:
        history_path = Path(temp_dir) / "experience_demo.json"
        agent = LearningAgent(experience_file=history_path)

        before_result = agent.decide(deepcopy(agent_scenario))
        before_action = before_result.get("selected_action_id")
        category = canonical_category(expected.get("failure_category"))

        if category not in agent.action_catalog or not before_action:
            return {
                "scenario_id": scenario_id,
                "status": "not_applicable",
                "reason": "Scenario does not select a category-specific learning action.",
            }

        actions = [item["id"] for item in agent.action_catalog[category]]
        alternative = next((action_id for action_id in actions if action_id != before_action), None)
        if alternative is None:
            return {
                "scenario_id": scenario_id,
                "status": "not_applicable",
                "reason": "No alternative action is available for the category.",
            }

        # Controlled simulated feedback: selected action unsuccessful, alternative successful.
        first_feedback = agent.update_experience(category, before_action, False)
        second_feedback = agent.update_experience(category, alternative, True)
        after_result = agent.decide(deepcopy(agent_scenario))
        after_action = after_result.get("selected_action_id")

        persisted = json.loads(history_path.read_text(encoding="utf-8"))
        recommendation = recommendation_metric(
            after_result.get("recommended_step", ""),
            expected.get("acceptable_next_steps", []),
        )

        return {
            "scenario_id": scenario_id,
            "status": "completed",
            "feedback_type": "simulated",
            "experience_file_is_temporary": True,
            "baseline_recommendation": before_result.get("recommended_step"),
            "baseline_action_id": before_action,
            "feedback_events": [
                {"action_id": before_action, "succeeded": False, "update": first_feedback},
                {"action_id": alternative, "succeeded": True, "update": second_feedback},
            ],
            "after_feedback_recommendation": after_result.get("recommended_step"),
            "after_feedback_action_id": after_action,
            "recommendation_changed": before_action != after_action,
            "after_feedback_recommendation_appropriate": recommendation["appropriate"],
            "persisted_experience_snapshot": persisted[category],
        }


def evaluate(
    scenarios_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Execute ten baseline cases and a separate learning feedback demo.

    Scenario loading and answer-key separation are delegated to Member 4's
    public ``scenario_loader`` interface. ``scenarios_path`` is retained for
    compatibility with existing commands/tests, but must point to that shared fixture.
    """
    configured_scenario_path = Path(SCENARIO_FILE).resolve()
    requested_scenario_path = (
        Path(scenarios_path).resolve() if scenarios_path is not None else configured_scenario_path
    )
    if requested_scenario_path != configured_scenario_path:
        raise ValueError(
            "The evaluator uses Member 4's scenario_loader.py, which is configured for "
            f"'{configured_scenario_path}'. Update scenario_loader.py to evaluate a different fixture."
        )

    output_path = (
        Path(output_path) if output_path is not None
        else PROJECT_ROOT / "evaluation" / "results" / "member2_evaluation.json"
    )

    # Load full scenarios for evaluator metadata and answer-key validation.
    # Agents receive separate copies only through shared_agent_input().
    scenarios = load_scenarios()
    _validate_scenario_catalog(scenarios)
    loaded_ids = [str(scenario["id"]) for scenario in scenarios]
    shared_ids = [str(item) for item in scenario_ids()]
    if loaded_ids != shared_ids:
        raise ValueError("scenario_loader.load_scenarios() and scenario_ids() returned inconsistent data.")

    rows: list[dict[str, Any]] = []
    learning_scenario_for_demo: tuple[str, dict[str, Any]] | None = None

    with tempfile.TemporaryDirectory(prefix="member2_baseline_histories_") as temp_dir:
        temp_root = Path(temp_dir)
        for scenario in scenarios:
            scenario_id = str(scenario["id"])
            # Expected values are retrieved separately and never passed to either agent.
            expected = expected_for(scenario_id)

            utility_input = shared_agent_input(scenario_id)
            learning_input = shared_agent_input(scenario_id)
            if (
                utility_input is learning_input
                or utility_input.get("pipeline_status") is learning_input.get("pipeline_status")
                or utility_input.get("test_results") is learning_input.get("test_results")
            ):
                raise RuntimeError(
                    f"Shared loader did not return independent deep copies for scenario {scenario_id}."
                )

            rows.append(_run_agent_case(
                agent_name="Utility-Based Agent",
                agent_factory=UtilityBasedAgent,
                scenario_metadata=scenario,
                agent_scenario=utility_input,
                expected=expected,
            ))

            # Each Learning Agent baseline receives a separate fresh history,
            # preventing feedback or experience leakage across scenarios.
            learning_history = temp_root / f"learning_{scenario_id}.json"
            rows.append(_run_agent_case(
                agent_name="Learning-Based Agent",
                agent_factory=lambda path=learning_history: LearningAgent(experience_file=path),
                scenario_metadata=scenario,
                agent_scenario=learning_input,
                expected=expected,
            ))

            if scenario_id == "A":
                learning_scenario_for_demo = (scenario_id, expected)

    summaries: dict[str, Any] = {}
    for agent_name in ("Utility-Based Agent", "Learning-Based Agent"):
        agent_rows = [row for row in rows if row["agent"] == agent_name]
        summaries[agent_name] = {
            "all_scenarios": _summarize_group(agent_rows),
            "primary_scenarios_A_to_C": _summarize_group(
                [row for row in agent_rows if row["scenario_id"] in PRIMARY_SCENARIO_IDS]
            ),
            "robustness_scenarios_D_to_E": _summarize_group(
                [row for row in agent_rows if row["scenario_id"] in ROBUSTNESS_SCENARIO_IDS]
            ),
        }

    learning_demo = (
        run_learning_before_after(*learning_scenario_for_demo)
        if learning_scenario_for_demo
        else {"status": "not_run", "reason": "Scenario A was not present."}
    )

    payload = {
        "schema_version": "1.0",
        "project": "Intelligent CI/CD Pipeline Failure Assistant",
        "owner": "Member 2",
        "evaluation_metadata": {
            "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "scenario_fixture": str(configured_scenario_path),
            "scenario_loader": "scenario_loader.py (Member 4 shared loader)",
            "learning_baseline_policy": "Fresh zero-count temporary experience file per scenario.",
            "expected_data_policy": "expected_for() is evaluator-only; every agent input is obtained through agent_input().",
        },
        "evaluation_design": {
            "primary_scenarios": sorted(PRIMARY_SCENARIO_IDS),
            "robustness_scenarios": sorted(ROBUSTNESS_SCENARIO_IDS),
            "metrics": [
                "classification_accuracy",
                "evidence_precision_recall_f1",
                "recommendation_appropriateness",
                "explanation_completeness",
                "learning_before_after_feedback",
            ],
            "evidence_reference_policy": (
                "Evaluator-authored scenario-specific logical evidence mapping; aliases are normalized."
            ),
            "recommendation_policy": (
                "Case-insensitive token matching with light suffix normalization against expected.acceptable_next_steps."
            ),
            "explanation_policy": (
                "Four binary checks: meaningful likely cause, informative reasoning, decision rationale, actionable verification checklist."
            ),
        },
        "results": rows,
        "agent_summaries": summaries,
        "learning_before_after_experiment": learning_demo,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_json_safe(payload), indent=2) + "\n", encoding="utf-8")
    return payload

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "evaluation" / "results" / "member2_evaluation.json")
    args = parser.parse_args()

    payload = evaluate(output_path=args.output)
    print("Member 2 evaluation completed.")
    print(f"Evaluations: {len(payload['results'])}")
    for agent_name, summary in payload["agent_summaries"].items():
        print(f"\n{agent_name}")
        print(json.dumps(summary, indent=2))
    demo = payload["learning_before_after_experiment"]
    print("\nLearning before/after experiment:")
    print(json.dumps(demo, indent=2))
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
