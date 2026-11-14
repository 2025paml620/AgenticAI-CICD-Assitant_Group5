"""Goal-Based Agent for CI/CD pipeline failure diagnosis.

Builds a safe diagnostic plan toward a healthy pipeline. It chooses actions
based on unmet stage goals and available evidence; it never executes fixes.
"""
from __future__ import annotations

from typing import Any


class GoalBasedAgent:
    """Plan diagnostic steps toward a fully healthy CI/CD pipeline."""

    name = "Goal-Based Agent"
    goal = "Build, tests, and deployment all pass."

    def decide(self, scenario: dict[str, Any]) -> dict[str, Any]:
        status = scenario.get("pipeline_status", {})
        current = {
            stage: str(status.get(stage, scenario.get(stage, "unknown"))).lower()
            for stage in ("build", "tests", "deployment")
        }
        evidence = [f"{stage}={value}" for stage, value in current.items()]
        # The order represents pipeline prerequisites: build -> test -> deploy.
        if current["build"] == "failed":
            category = "dependency_or_build_failure"
            cause = "Build stage is blocking the pipeline goal."
            plan = [
                "Inspect build logs and dependency resolution evidence.",
                "Recommend correcting the identified build or version issue.",
                "Verify the build succeeds.",
                "Verify tests pass before considering deployment readiness.",
            ]
            checks = ["Build passes.", "Tests pass.", "Deployment is verified separately."]
        elif current["tests"] == "failed":
            category = "unit_test_failure"
            cause = "Failing tests prevent safe progression toward deployment readiness."
            plan = [
                "Inspect failing tests and their error messages.",
                "Review relevant recent code changes.",
                "Recommend a targeted fix for the suspected regression.",
                "Verify failing tests and then the full suite pass.",
            ]
            checks = ["Affected tests pass.", "Full test suite passes.", "Build remains successful."]
        elif current["deployment"] == "failed":
            category = "deployment_health_failure"
            cause = "Deployment health is the remaining unmet pipeline goal."
            plan = [
                "Inspect deployment status and failed health checks.",
                "Review runtime logs and configuration changes.",
                "Recommend a safe corrective step for the identified issue.",
                "Verify service health after an authorized fix.",
            ]
            checks = ["Health checks pass.", "Runtime errors are resolved.", "Deployment status is healthy."]
        elif all(value == "passed" for value in current.values()):
            category = "healthy"
            cause = "All pipeline goals are already satisfied."
            plan = ["Continue monitoring future pipeline runs."]
            checks = ["Monitor subsequent runs."]
        else:
            category = "unknown"
            cause = "The observed stages do not establish whether the goal is satisfied."
            plan = ["Collect missing pipeline status and diagnostic evidence.", "Reassess which pipeline goal is unmet."]
            checks = ["All stage statuses are known."]

        return {
            "agent": self.name,
            "failure_category": category,
            "supporting_evidence": evidence,
            "likely_cause": cause,
            "recommended_step": plan[0],
            "reasoning": f"Goal: {self.goal} Selected a diagnostic plan for the earliest unmet prerequisite. No actions are executed.",
            "verification_checklist": checks,
            "plan": plan,
        }


if __name__ == "__main__":
    from pprint import pprint
    sample = {"id": "C", "pipeline_status": {"build": "passed", "tests": "passed", "deployment": "failed"}}
    pprint(GoalBasedAgent().decide(sample))
