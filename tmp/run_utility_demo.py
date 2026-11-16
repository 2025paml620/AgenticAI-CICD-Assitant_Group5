
import sys
from pathlib import Path

# Add the project root directory to Python's module search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT))

from agents.utility_based import UtilityBasedAgent

# Temporary test scenarios.
# Replace these with the shared scenarios.json later.

scenarios = {
    "A": {
        "failure_type": "unit_test",
        "pipeline_status": {
            "build": "passed",
            "tests": "failed",
            "deployment": "not_started"
        },
        "build_logs": "Expected 200 but received 500",
        "test_results": {"passed": 18, "failed": 2},
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
        "test_results": {"passed": 24, "failed": 0},
        "health_checks": {
            "status": "failed",
            "details": "HTTP 503"
        }
    }
}

agent = UtilityBasedAgent()

for scenario_id, scenario in scenarios.items():

    print("\n" + "=" * 60)
    print(f"SCENARIO {scenario_id}")
    print("=" * 60)

    result = agent.decide(scenario)

    print("Agent:", result["agent"])
    print("Failure:", result["failure_category"])
    print("Recommended:", result["recommended_step"])
    print("Utility:", result["utility_score"])

    print("\nCandidate scores:")

    for candidate in result["candidate_scores"]:
        print(
            candidate["id"],
            "=>",
            candidate["utility_score"]
        )

    print("\nReasoning:")
    print(result["reasoning"])

    print("\nSupporting evidence:")
    for item in result["supporting_evidence"]:
        print("-", item)
