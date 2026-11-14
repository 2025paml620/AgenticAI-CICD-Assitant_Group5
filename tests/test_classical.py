"""Small smoke test for the three classical agents."""
from agents.simple_reflex import SimpleReflexAgent
from agents.model_based import ModelBasedAgent
from agents.goal_based import GoalBasedAgent

SCENARIOS = {
    "A": {"id": "A", "pipeline_status": {"build": "passed", "tests": "failed", "deployment": "not_started"}, "recent_changes": ["Modified payment API"]},
    "B": {"id": "B", "pipeline_status": {"build": "failed", "tests": "not_started", "deployment": "not_started"}, "recent_changes": ["Updated requirements.txt"]},
    "C": {"id": "C", "pipeline_status": {"build": "passed", "tests": "passed", "deployment": "failed"}, "recent_changes": ["Changed runtime configuration"]},
}
EXPECTED = {"A": "unit_test_failure", "B": "dependency_or_build_failure", "C": "deployment_health_failure"}
REQUIRED = {"agent", "failure_category", "supporting_evidence", "likely_cause", "recommended_step", "reasoning", "verification_checklist"}


def main():
    for cls in (SimpleReflexAgent, ModelBasedAgent, GoalBasedAgent):
        agent = cls()
        for key, scenario in SCENARIOS.items():
            result = agent.decide(scenario)
            assert REQUIRED <= result.keys(), (cls.__name__, REQUIRED - result.keys())
            assert result["failure_category"] == EXPECTED[key], result
            print(f'{result["agent"]} | {key} | {result["failure_category"]} | {result["recommended_step"]}')
    print("All 9 agent-scenario checks passed.")


if __name__ == "__main__":
    main()
