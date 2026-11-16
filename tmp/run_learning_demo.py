"""Controlled Learning Agent demonstration using a temporary history file.

All feedback in this script is SIMULATED for demonstration; it is not production data.
"""
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.learning_agent import LearningAgent

SCENARIOS = {
    "A": {
        "failure_type": "unit_test",
        "pipeline_status": {"build": "passed", "tests": "failed", "deployment": "not_started"},
        "build_logs": "Build completed. Unit test failed with an assertion error.",
        "test_results": {"passed": 18, "failed": 2, "details": "assertion error in payment API test"},
        "recent_changes": "Modified payment API validation function.",
    },
    "B": {
        "failure_type": "dependency",
        "pipeline_status": {"build": "failed", "tests": "not_started", "deployment": "not_started"},
        "build_logs": "Build failed while resolving dependency version; package version unavailable.",
        "dependency_info": {"package": "example-lib", "requested_version": "4.2", "status": "unavailable"},
    },
    "C": {
        "failure_type": "deployment",
        "pipeline_status": {"build": "passed", "tests": "passed", "deployment": "unhealthy"},
        "health_checks": {"endpoint": "/health", "status": 503, "result": "failed"},
        "runtime_logs": "Application returned HTTP 503 after release.",
        "recent_changes": "Updated deployment configuration and environment variables.",
    },
}


def main():
    # Temporary directory prevents this demonstration from changing the project's
    # data/experience.json file.
    with tempfile.TemporaryDirectory(prefix="learning-agent-demo-") as temp_dir:
        experience_path = Path(temp_dir) / "experience.json"
        agent = LearningAgent(experience_file=experience_path)

        print("=== BEFORE FEEDBACK ===")
        for scenario_id, scenario in SCENARIOS.items():
            result = agent.decide(scenario)
            print(json.dumps({
                "scenario": scenario_id,
                "selected_action_id": result["selected_action_id"],
                "recommended_step": result["recommended_step"],
                "success_rate": result["success_rate"],
                "evidence_relevance": result["evidence_relevance"],
                "learning_score": result["learning_score"],
            }, indent=2))

        # Controlled SIMULATED feedback for Scenario A.
        agent.update_experience("unit_test", "inspect_tests", False)
        agent.update_experience("unit_test", "inspect_changes", True)

        print("=== AFTER SIMULATED FEEDBACK (Scenario A) ===")
        result = agent.decide(SCENARIOS["A"])
        print(json.dumps({
            "scenario": "A",
            "selected_action_id": result["selected_action_id"],
            "recommended_step": result["recommended_step"],
            "success_rate": result["success_rate"],
            "evidence_relevance": result["evidence_relevance"],
            "learning_score": result["learning_score"],
            "candidate_scores": result["candidate_scores"],
        }, indent=2))

        print("=== PERSISTED EXPERIENCE (TEMPORARY FILE) ===")
        print(experience_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
