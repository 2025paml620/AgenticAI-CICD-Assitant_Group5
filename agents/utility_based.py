"""
Utility-Based Agent
Project: Intelligent CI/CD Pipeline Failure Assistant
Owner: Avinash (Member 2)

The agent ranks safe, read-only diagnostic actions using a weighted utility
function. It follows the shared scenario and output conventions defined by
Member 4's ``base_agent.py``.

The agent is advisory only: it never modifies source code or deploys software.
"""
from __future__ import annotations

from typing import Any

from agents.base_agent import canonical_category


class UtilityBasedAgent:
    """Recommend the highest-utility diagnostic action for a CI/CD scenario."""

    agent_name = "Utility-Based Agent"

    # Utility formula weights. Keep aligned with the documented project plan.
    SUCCESS_WEIGHT = 0.4
    EVIDENCE_WEIGHT = 0.3
    SAFETY_WEIGHT = 0.2
    COST_WEIGHT = 0.1

    # Candidate values are illustrative estimates, not measured probabilities.
    # Action IDs and descriptions are retained from the original implementation
    # so that the Learning Agent can share this catalog.
    ACTION_CATALOG: dict[str, list[dict[str, Any]]] = {
        "unit_test": [
            {
                "id": "inspect_tests",
                "step": "Inspect failed unit test results",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.20,
            },
            {
                "id": "inspect_changes",
                "step": "Review recently modified code",
                "success_probability": 0.80,
                "evidence_relevance": 0.90,
                "safety": 1.00,
                "cost": 0.25,
            },
            {
                "id": "inspect_pipeline",
                "step": "Investigate the complete pipeline",
                "success_probability": 0.60,
                "evidence_relevance": 0.65,
                "safety": 1.00,
                "cost": 0.70,
            },
        ],
        "dependency": [
            {
                "id": "inspect_versions",
                "step": "Check dependency versions and compatibility",
                "success_probability": 0.90,
                "evidence_relevance": 0.98,
                "safety": 1.00,
                "cost": 0.20,
            },
            {
                "id": "inspect_build_logs",
                "step": "Inspect dependency resolution build logs",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.20,
            },
            {
                "id": "inspect_package_index",
                "step": "Check package registry availability",
                "success_probability": 0.75,
                "evidence_relevance": 0.85,
                "safety": 1.00,
                "cost": 0.30,
            },
        ],
        "deployment": [
            {
                "id": "inspect_health",
                "step": "Inspect deployment health-check results",
                "success_probability": 0.90,
                "evidence_relevance": 0.98,
                "safety": 1.00,
                "cost": 0.20,
            },
            {
                "id": "inspect_runtime_logs",
                "step": "Inspect application runtime logs",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.25,
            },
            {
                "id": "inspect_deployment_changes",
                "step": "Review recent deployment configuration changes",
                "success_probability": 0.80,
                "evidence_relevance": 0.90,
                "safety": 1.00,
                "cost": 0.30,
            },
        ],
    }

    def __init__(self) -> None:
        """Initialize a stateless Utility-Based Agent."""

    def calculate_utility(self, action: dict[str, Any]) -> float:
        """Calculate ``U(a) = 0.4P + 0.3E + 0.2S - 0.1C``.

        Each utility parameter must be a real numeric value in [0, 1].
        Boolean values are rejected even though ``bool`` subclasses ``int``.
        """
        if not isinstance(action, dict):
            raise TypeError("action must be a dictionary")

        required_fields = (
            "success_probability",
            "evidence_relevance",
            "safety",
            "cost",
        )

        for field in required_fields:
            if field not in action:
                raise ValueError(f"Missing utility parameter: {field}")

            value = action[field]
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 1
            ):
                raise ValueError(f"{field} must be a number between 0 and 1")

        score = (
            self.SUCCESS_WEIGHT * action["success_probability"]
            + self.EVIDENCE_WEIGHT * action["evidence_relevance"]
            + self.SAFETY_WEIGHT * action["safety"]
            - self.COST_WEIGHT * action["cost"]
        )
        return round(score, 4)

    @staticmethod
    def _is_present(value: Any) -> bool:
        """Return True for non-empty evidence values, including numeric zero."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (dict, list, tuple, set)):
            return bool(value)
        return True

    @staticmethod
    def _format_evidence(label: str, value: Any) -> str:
        """Format one evidence item for the common output contract."""
        return f"{label}: {value}"

    def get_supporting_evidence(self, scenario: dict[str, Any]) -> list[str]:
        """Extract available evidence using the shared scenario field names.

        ``dependencies`` and ``dependency_info`` are treated as aliases for the
        same logical information. ``deployment_logs`` and ``runtime_logs`` are
        handled similarly. The grader-only ``expected`` field is never read.
        """
        evidence: list[str] = []

        standard_fields = (
            ("Pipeline status", "pipeline_status"),
            ("Build logs", "build_logs"),
            ("Test results", "test_results"),
            ("Recent changes", "recent_changes"),
            ("Health checks", "health_checks"),
        )
        for label, field in standard_fields:
            value = scenario.get(field)
            if self._is_present(value):
                evidence.append(self._format_evidence(label, value))

        # Dependency aliases: include each supplied value once, not as separate
        # logical fields when both happen to be present.
        dependency_values: list[Any] = []
        for field in ("dependency_info", "dependencies"):
            value = scenario.get(field)
            if self._is_present(value) and value not in dependency_values:
                dependency_values.append(value)
        if dependency_values:
            evidence.append(
                self._format_evidence("Dependency information", dependency_values[0])
            )
            if len(dependency_values) > 1:
                evidence.append(
                    self._format_evidence(
                        "Additional dependency information", dependency_values[1]
                    )
                )

        # Karthik's fixture uses deployment_logs. runtime_logs is accepted as
        # a compatibility alias for any existing callers.
        deployment_values: list[Any] = []
        for field in ("deployment_logs", "runtime_logs"):
            value = scenario.get(field)
            if self._is_present(value) and value not in deployment_values:
                deployment_values.append(value)
        if deployment_values:
            evidence.append(
                self._format_evidence("Deployment/runtime logs", deployment_values[0])
            )
            if len(deployment_values) > 1:
                evidence.append(
                    self._format_evidence(
                        "Additional deployment/runtime logs", deployment_values[1]
                    )
                )

        # Deliberately do not include scenario['expected']; it is grader-only.
        return evidence

    def _fallback_result(
        self, failure_category: str, evidence: list[str]
    ) -> dict[str, Any]:
        """Return a safe response for unknown or healthy scenarios."""
        if failure_category == "healthy":
            return {
                "agent": self.agent_name,
                "failure_category": "healthy",
                "supporting_evidence": evidence,
                "likely_cause": "No pipeline failure is indicated by the supplied scenario.",
                "recommended_step": (
                    "No troubleshooting action required; continue monitoring pipeline health."
                ),
                "reasoning": (
                    "The shared category is healthy, so no failure-specific diagnostic "
                    "action should be recommended."
                ),
                "verification_checklist": [
                    "Confirm that build, tests and deployment stages passed.",
                    "Confirm that the deployment health check is successful.",
                    "Continue normal pipeline monitoring.",
                ],
                "utility_score": None,
                "candidate_scores": [],
            }

        return {
            "agent": self.agent_name,
            "failure_category": "unknown",
            "supporting_evidence": evidence,
            "likely_cause": (
                "The available evidence is insufficient to determine the failure cause."
            ),
            "recommended_step": (
                "Collect complete pipeline logs and diagnostic reports, then rerun "
                "the affected pipeline stage with sufficient logging."
            ),
            "reasoning": (
                "The failure category is unknown or unsupported. Avoiding a speculative "
                "diagnosis is safer than selecting a category-specific action."
            ),
            "verification_checklist": [
                "Retrieve complete, untruncated pipeline logs.",
                "Collect the missing test report or stage-specific diagnostic output.",
                "Confirm the stage status and rerun with verbose logging if appropriate.",
            ],
            "utility_score": None,
            "candidate_scores": [],
        }

    def decide(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Evaluate the supplied scenario and return the common agent schema.

        The method is read-only: it does not mutate the scenario or inspect the
        grader-only ``expected`` field.
        """
        if not isinstance(scenario, dict):
            raise TypeError("Scenario must be a dictionary")

        raw_category = scenario.get("failure_type")
        failure_category = canonical_category(raw_category)
        evidence = self.get_supporting_evidence(scenario)

        if failure_category not in self.ACTION_CATALOG:
            return self._fallback_result(failure_category, evidence)

        candidates = self.ACTION_CATALOG[failure_category]
        scored_actions: list[dict[str, Any]] = []
        for action in candidates:
            score = self.calculate_utility(action)
            scored_actions.append({**action, "utility_score": score})

        # max() preserves catalog order when scores tie.
        best_action = max(
            scored_actions, key=lambda action: action["utility_score"]
        )

        likely_causes = {
            "unit_test": "Possible regression in recently modified code.",
            "dependency": "Possible unavailable or incompatible dependency version.",
            "deployment": "Possible runtime or deployment configuration issue.",
        }

        return {
            "agent": self.agent_name,
            "failure_category": failure_category,
            "supporting_evidence": evidence,
            "likely_cause": likely_causes[failure_category],
            "recommended_step": best_action["step"],
            "reasoning": (
                f"Selected {best_action['id']} because it achieved the highest "
                f"utility score of {best_action['utility_score']:.4f}. The decision "
                "considers estimated success probability, evidence relevance, safety "
                "and troubleshooting cost."
            ),
            "verification_checklist": [
                "Review the diagnostic findings.",
                "Apply an appropriate fix through the normal development process.",
                "Rerun the affected pipeline stage.",
                "Confirm the complete pipeline is healthy.",
            ],
            "utility_score": best_action["utility_score"],
            "candidate_scores": scored_actions,
        }
