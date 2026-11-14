"""Simple Reflex Agent for CI/CD pipeline failure diagnosis.

Makes decisions solely from current observations using fixed IF/THEN rules.
No memory, planning, or learned behavior is used.
"""
from __future__ import annotations

from typing import Any


class SimpleReflexAgent:
    """Recommend a troubleshooting step using predefined condition-action rules."""

    name = "Simple Reflex Agent"

    def decide(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Return a diagnostic recommendation for one pipeline scenario."""
        status = scenario.get("pipeline_status", {})
        build = str(status.get("build", scenario.get("build", "unknown"))).lower()
        tests = str(status.get("tests", scenario.get("tests", "unknown"))).lower()
        deployment = str(status.get("deployment", scenario.get("deployment", "unknown"))).lower()

        if build == "failed":
            category = "dependency_or_build_failure"
            evidence = ["Build stage is marked failed."]
            cause = "A build or dependency issue may be blocking the pipeline."
            action = "Inspect build logs and dependency resolution errors."
            checks = ["Confirm required versions are available.", "Rerun the build.", "Verify tests pass after the build."]
            rule = "IF build failed THEN inspect build logs and dependencies."
        elif tests == "failed":
            category = "unit_test_failure"
            evidence = ["Test stage is marked failed."]
            cause = "A test regression or test-environment issue may be present."
            action = "Inspect failing test results and related recent code changes."
            checks = ["Rerun failing tests after the fix.", "Run the full test suite.", "Confirm the pipeline passes."]
            rule = "IF tests failed THEN inspect failing tests."
        elif deployment == "failed":
            category = "deployment_health_failure"
            evidence = ["Deployment stage is marked failed."]
            cause = "A deployment or runtime health issue may be present."
            action = "Inspect deployment logs and health-check results."
            checks = ["Confirm health endpoints respond.", "Review runtime logs.", "Verify deployment health after the fix."]
            rule = "IF deployment failed THEN inspect deployment health evidence."
        elif build == tests == deployment == "passed":
            category = "healthy"
            evidence = ["Build, tests, and deployment are marked passed."]
            cause = "No failure detected in the supplied stage statuses."
            action = "No troubleshooting needed; continue monitoring."
            checks = ["Continue routine monitoring."]
            rule = "IF all stages passed THEN monitor."
        else:
            category = "unknown"
            evidence = ["Insufficient stage status information."]
            cause = "The failure cannot be classified from current status alone."
            action = "Collect build, test, and deployment statuses."
            checks = ["Confirm all pipeline stage statuses are recorded."]
            rule = "ELSE request additional observations."

        return {
            "agent": self.name,
            "failure_category": category,
            "supporting_evidence": evidence,
            "likely_cause": cause,
            "recommended_step": action,
            "reasoning": f"Fixed rule applied: {rule}",
            "verification_checklist": checks,
        }


if __name__ == "__main__":
    sample = {"id": "A", "pipeline_status": {"build": "passed", "tests": "failed", "deployment": "not_started"}}
    from pprint import pprint
    pprint(SimpleReflexAgent().decide(sample))
