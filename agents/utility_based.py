
"""
Utility-Based Agent
Project: Intelligent CI/CD Pipeline Failure Assistant
Owner: Member 2 - Avinash

Purpose:
Evaluate possible troubleshooting actions using a utility
function and recommend the action with the highest score.

The agent is advisory only. It does not modify code or deploy.
"""

from typing import Any, Dict, List


class UtilityBasedAgent:
    """
    Selects the most useful diagnostic action based on
    estimated success probability, evidence relevance,
    safety and troubleshooting cost.
    """

    # Utility formula weights
    SUCCESS_WEIGHT = 0.4
    EVIDENCE_WEIGHT = 0.3
    SAFETY_WEIGHT = 0.2
    COST_WEIGHT = 0.1

    # Candidate actions for each failure category.
    # Values are illustrative estimates, not measured probabilities.
    ACTION_CATALOG = {
        "unit_test": [
            {
                "id": "inspect_tests",
                "step": "Inspect failed unit test results",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.20
            },
            {
                "id": "inspect_changes",
                "step": "Review recently modified code",
                "success_probability": 0.80,
                "evidence_relevance": 0.90,
                "safety": 1.00,
                "cost": 0.25
            },
            {
                "id": "inspect_pipeline",
                "step": "Investigate the complete pipeline",
                "success_probability": 0.60,
                "evidence_relevance": 0.65,
                "safety": 1.00,
                "cost": 0.70
            }
        ],

        "dependency": [
            {
                "id": "inspect_versions",
                "step": "Check dependency versions and compatibility",
                "success_probability": 0.90,
                "evidence_relevance": 0.98,
                "safety": 1.00,
                "cost": 0.20
            },
            {
                "id": "inspect_build_logs",
                "step": "Inspect dependency resolution build logs",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.20
            },
            {
                "id": "inspect_package_index",
                "step": "Check package registry availability",
                "success_probability": 0.75,
                "evidence_relevance": 0.85,
                "safety": 1.00,
                "cost": 0.30
            }
        ],

        "deployment": [
            {
                "id": "inspect_health",
                "step": "Inspect deployment health-check results",
                "success_probability": 0.90,
                "evidence_relevance": 0.98,
                "safety": 1.00,
                "cost": 0.20
            },
            {
                "id": "inspect_runtime_logs",
                "step": "Inspect application runtime logs",
                "success_probability": 0.85,
                "evidence_relevance": 0.95,
                "safety": 1.00,
                "cost": 0.25
            },
            {
                "id": "inspect_deployment_changes",
                "step": "Review recent deployment configuration changes",
                "success_probability": 0.80,
                "evidence_relevance": 0.90,
                "safety": 1.00,
                "cost": 0.30
            }
        ]
    }

    def __init__(self):
        """Initialize the Utility-Based Agent."""
        self.agent_name = "Utility-Based Agent"

    def calculate_utility(self, action: Dict[str, Any]) -> float:
        """
        Calculate the utility score of an action.

        Formula:
        U(a) = 0.4P + 0.3E + 0.2S - 0.1C
        """

        required_fields = [
            "success_probability",
            "evidence_relevance",
            "safety",
            "cost"
        ]

        for field in required_fields:
            if field not in action:
                raise ValueError(
                    f"Missing utility parameter: {field}"
                )

            value = action[field]

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 1
            ):
                raise ValueError(
                    f"{field} must be a number between 0 and 1"
                )

        score = (
            self.SUCCESS_WEIGHT * action["success_probability"]
            + self.EVIDENCE_WEIGHT * action["evidence_relevance"]
            + self.SAFETY_WEIGHT * action["safety"]
            - self.COST_WEIGHT * action["cost"]
        )

        return round(score, 4)

    def get_supporting_evidence(
        self, scenario: Dict[str, Any]
    ) -> List[str]:
        """Extract evidence relevant to the selected scenario."""

        evidence = []

        pipeline = scenario.get("pipeline_status", {})

        if pipeline:
            evidence.append(f"Pipeline status: {pipeline}")

        if scenario.get("build_logs"):
            evidence.append(
                f"Build logs: {scenario['build_logs']}"
            )

        if scenario.get("test_results"):
            evidence.append(
                f"Test results: {scenario['test_results']}"
            )

        if scenario.get("dependencies"):
            evidence.append(
                f"Dependency information: {scenario['dependencies']}"
            )

        if scenario.get("recent_changes"):
            evidence.append(
                f"Recent changes: {scenario['recent_changes']}"
            )

        if scenario.get("health_checks"):
            evidence.append(
                f"Health checks: {scenario['health_checks']}"
            )

        return evidence

    def decide(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate available actions and return the best recommendation.

        Input:
            Shared CI/CD scenario dictionary.

        Output:
            Standardized agent response.
        """

        if not isinstance(scenario, dict):
            raise TypeError("Scenario must be a dictionary")

        failure_category = scenario.get("failure_type")

        if failure_category not in self.ACTION_CATALOG:
            return {
                "agent": self.agent_name,
                "failure_category": failure_category or "unknown",
                "supporting_evidence": [],
                "likely_cause": "Insufficient or unsupported failure information",
                "recommended_step": "Collect additional diagnostic evidence",
                "reasoning": "No applicable utility action was found.",
                "verification_checklist": [
                    "Confirm pipeline status",
                    "Collect relevant logs and diagnostic information"
                ],
                "utility_score": None,
                "candidate_scores": []
            }

        # Retrieve applicable actions.
        candidates = self.ACTION_CATALOG[failure_category]

        # Calculate utility for every candidate.
        scored_actions = []

        for action in candidates:
            score = self.calculate_utility(action)

            scored_actions.append({
                **action,
                "utility_score": score
            })

        # Select highest utility.
        # Original catalog order resolves equal-score ties.
        best_action = max(
            scored_actions,
            key=lambda action: action["utility_score"]
        )

        evidence = self.get_supporting_evidence(scenario)

        # Determine likely cause without claiming certainty.
        likely_causes = {
            "unit_test": "Possible regression in recently modified code",
            "dependency": "Possible unavailable or incompatible dependency version",
            "deployment": "Possible runtime or deployment configuration issue"
        }

        return {
            "agent": self.agent_name,
            "failure_category": failure_category,
            "supporting_evidence": evidence,
            "likely_cause": likely_causes[failure_category],
            "recommended_step": best_action["step"],
            "reasoning": (
                f"Selected {best_action['id']} because it achieved "
                f"the highest utility score of "
                f"{best_action['utility_score']:.4f}. "
                "The decision considers estimated success probability, "
                "evidence relevance, safety and troubleshooting cost."
            ),
            "verification_checklist": [
                "Review the diagnostic findings",
                "Apply an appropriate fix through the normal development process",
                "Rerun the affected pipeline stage",
                "Confirm the complete pipeline is healthy"
            ],
            "utility_score": best_action["utility_score"],
            "candidate_scores": scored_actions
        }
