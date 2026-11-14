"""Model-Based Reflex Agent for CI/CD pipeline failure diagnosis.

Maintains an internal state per pipeline, remembers previous observations,
and uses transitions and recent change evidence to refine its recommendation.
"""
from __future__ import annotations

from typing import Any


class ModelBasedAgent:
    """Use current and remembered pipeline state to select diagnostic actions."""

    name = "Model-Based Reflex Agent"

    def __init__(self) -> None:
        self._state_by_pipeline: dict[str, dict[str, str]] = {}

    def reset(self) -> None:
        """Clear remembered pipeline state (useful for independent tests)."""
        self._state_by_pipeline.clear()

    def decide(self, scenario: dict[str, Any]) -> dict[str, Any]:
        pipeline_id = str(scenario.get("pipeline_id", scenario.get("id", "default")))
        status = scenario.get("pipeline_status", {})
        current = {
            stage: str(status.get(stage, scenario.get(stage, "unknown"))).lower()
            for stage in ("build", "tests", "deployment")
        }
        previous = self._state_by_pipeline.get(pipeline_id)
        changes = scenario.get("recent_changes", scenario.get("recent_change", []))
        if isinstance(changes, str):
            changes = [changes] if changes else []
        changes = [str(change) for change in changes]

        evidence = [f"Current {stage} status: {value}." for stage, value in current.items()]
        if previous is not None:
            transitions = [
                f"{stage}: {previous[stage]} -> {current[stage]}"
                for stage in current if previous[stage] != current[stage]
            ]
            evidence.extend(transitions or ["Pipeline status is unchanged from the previous observation."])
        if changes:
            evidence.append("Recent changes: " + "; ".join(changes))

        if current["build"] == "failed":
            category = "dependency_or_build_failure"
            cause = "Build failure; recent dependency or configuration changes may be relevant."
            action = "Compare current build logs and dependency versions with the last successful build."
            checks = ["Validate dependency compatibility.", "Rerun the build.", "Rerun tests after a successful build."]
        elif current["tests"] == "failed":
            category = "unit_test_failure"
            cause = "Test failure; a recent code change may have introduced a regression."
            action = "Correlate failing test cases with recent code changes and prior test status."
            checks = ["Rerun affected tests.", "Run the full test suite.", "Confirm the failure no longer occurs."]
        elif current["deployment"] == "failed":
            category = "deployment_health_failure"
            cause = "Deployment failed despite earlier stages; runtime or configuration issues may be relevant."
            action = "Compare deployment health checks and runtime configuration with the previous healthy state."
            checks = ["Review health endpoint responses.", "Check runtime configuration.", "Verify health after the fix."]
        elif all(value == "passed" for value in current.values()):
            category = "healthy"
            cause = "All observed stages passed."
            action = "Continue monitoring the pipeline."
            checks = ["Monitor subsequent pipeline runs."]
        else:
            category = "unknown"
            cause = "Current and remembered state do not identify a failure."
            action = "Collect missing stage statuses and compare with the previous run."
            checks = ["Capture missing stage results."]

        if previous is None:
            memory_note = "No previous observation was stored for this pipeline."
        else:
            changed = [stage for stage in current if current[stage] != previous[stage]]
            memory_note = (
                "State transition detected in: " + ", ".join(changed) + "."
                if changed else "Remembered state matches the current observation."
            )
        self._state_by_pipeline[pipeline_id] = current.copy()
        return {
            "agent": self.name,
            "failure_category": category,
            "supporting_evidence": evidence,
            "likely_cause": cause,
            "recommended_step": action,
            "reasoning": memory_note + " The recommendation uses current pipeline state and change context.",
            "verification_checklist": checks,
        }


if __name__ == "__main__":
    from pprint import pprint
    agent = ModelBasedAgent()
    sample = {"id": "A", "pipeline_status": {"build": "passed", "tests": "failed", "deployment": "not_started"}, "recent_changes": ["Modified payment API"]}
    pprint(agent.decide(sample))
    pprint(agent.decide(sample))
