"""
Learning Agent
Project: Intelligent CI/CD Pipeline Failure Assistant
Owner: Avinash (Member 2)

Experience-based CI/CD troubleshooting agent.

The Learning Agent follows Member 4's shared scenario/output contract. It
ranks applicable diagnostic actions using persisted historical outcomes and
scenario evidence. It only updates experience after explicit feedback and
never modifies source code or deploys software.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from agents.base_agent import canonical_category
from agents.utility_based import UtilityBasedAgent


class LearningAgent:
    """Select diagnostic actions using persisted experience and evidence."""

    # These weights are implementation choices, not assignment-mandated values.
    # The resulting score is for ranking actions, not a calibrated probability.
    HISTORY_WEIGHT = 0.60
    EVIDENCE_WEIGHT = 0.40
    agent_name = "Learning-Based Agent"

    # Each item in field_groups is one logical evidence group. Multiple field
    # names inside a group are aliases, so dependencies/dependency_info count
    # as one logical source rather than two separate sources.
    EVIDENCE_RULES: dict[str, dict[str, Any]] = {
        "inspect_tests": {
            "field_groups": (("test_results",), ("build_logs",)),
            "keywords": (
                "test", "tests", "failed", "failure", "assert",
                "traceback", "error",
            ),
        },
        "inspect_changes": {
            "field_groups": (("recent_changes",), ("test_results",)),
            "keywords": (
                "change", "changed", "modified", "updated", "commit",
                "regression", "function",
            ),
        },
        "inspect_pipeline": {
            "field_groups": (("pipeline_status",),),
            "keywords": (
                "overall pipeline", "stage transition", "multiple stages",
                "pipeline orchestration", "unknown stage", "cross-stage failure",
            ),
        },
        "inspect_versions": {
            "field_groups": (
                ("dependency_info", "dependencies"),
                ("build_logs",),
            ),
            "keywords": (
                "version", "versions", "dependency", "dependencies",
                "incompatible", "requirements", "package", "resolution",
            ),
        },
        "inspect_build_logs": {
            "field_groups": (("build_logs",), ("pipeline_status",)),
            "keywords": (
                "build", "failed", "failure", "error", "install",
                "resolve", "dependency",
            ),
        },
        "inspect_package_index": {
            "field_groups": (
                ("dependency_info", "dependencies"),
                ("build_logs",),
            ),
            "keywords": (
                "registry", "index", "package", "unavailable", "not found",
                "repository", "package index",
            ),
        },
        "inspect_health": {
            "field_groups": (("health_checks",), ("pipeline_status",)),
            "keywords": (
                "health", "unhealthy", "503", "readiness", "liveness",
                "endpoint", "failed",
            ),
        },
        "inspect_runtime_logs": {
            "field_groups": (
                ("deployment_logs", "runtime_logs"),
                ("build_logs",),
                ("health_checks",),
            ),
            "keywords": (
                "exception", "traceback", "timeout", "runtime", "crash", "error",
            ),
        },
        "inspect_deployment_changes": {
            "field_groups": (("recent_changes",), ("health_checks",)),
            "keywords": (
                "deployment", "config", "configuration", "manifest",
                "environment", "release", "changed",
            ),
        },
    }

    # Output evidence aliases are grouped so duplicate values are not displayed
    # twice. The expected/grader-only block is deliberately excluded.
    EVIDENCE_FIELD_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("Pipeline status", ("pipeline_status",)),
        ("Build logs", ("build_logs",)),
        ("Test results", ("test_results",)),
        ("Dependency information", ("dependency_info", "dependencies")),
        ("Recent changes", ("recent_changes",)),
        ("Health checks", ("health_checks",)),
        ("Deployment/runtime logs", ("deployment_logs", "runtime_logs")),
    )

    def __init__(self, experience_file: str | Path | None = None):
        project_root = Path(__file__).resolve().parent.parent
        self.experience_file = (
            Path(experience_file)
            if experience_file is not None
            else project_root / "data" / "experience.json"
        )
        self.action_catalog = UtilityBasedAgent.ACTION_CATALOG

        catalog_action_ids = {
            action["id"]
            for actions in self.action_catalog.values()
            for action in actions
        }
        missing_rules = catalog_action_ids.difference(self.EVIDENCE_RULES)
        if missing_rules:
            raise ValueError(
                "Evidence rules are missing for action IDs: "
                + ", ".join(sorted(missing_rules))
            )

        self.experience = self.load_experience()

    @staticmethod
    def _has_value(value: Any) -> bool:
        """Return True when a field contains useful, non-empty evidence."""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in {"", "none", "null", "n/a", "unknown"}
        if isinstance(value, dict):
            return any(LearningAgent._has_value(item) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(LearningAgent._has_value(item) for item in value)
        # Numeric zero is meaningful evidence (e.g. zero failed tests).
        return True

    def _create_empty_experience(self) -> dict[str, dict[str, dict[str, int]]]:
        """Create zero-count history for every action in the shared catalog."""
        return {
            category: {
                action["id"]: {"success": 0, "failure": 0}
                for action in actions
            }
            for category, actions in self.action_catalog.items()
        }

    def _validate_experience(self, experience: Any) -> None:
        """Validate the persisted category/action structure and outcome counts."""
        if not isinstance(experience, dict):
            raise ValueError("Experience data must be a JSON object.")

        for category, actions in self.action_catalog.items():
            category_data = experience.get(category)
            if not isinstance(category_data, dict):
                raise ValueError(f"Missing or invalid experience category: {category}")

            for action in actions:
                action_id = action["id"]
                counts = category_data.get(action_id)
                if not isinstance(counts, dict):
                    raise ValueError(
                        f"Missing or invalid experience for action '{action_id}'."
                    )
                for outcome in ("success", "failure"):
                    count = counts.get(outcome)
                    if type(count) is not int or count < 0:
                        raise ValueError(
                            f"'{outcome}' count for '{action_id}' must be "
                            "a non-negative integer."
                        )

    def _write_experience(self, experience: dict) -> None:
        """Persist using a same-directory temporary file and atomic replace."""
        self._validate_experience(experience)
        self.experience_file.parent.mkdir(parents=True, exist_ok=True)
        temp_name: str | None = None
        try:
            file_descriptor, temp_name = tempfile.mkstemp(
                prefix=f"{self.experience_file.name}.",
                suffix=".tmp",
                dir=str(self.experience_file.parent),
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
                json.dump(experience, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            # Same-directory replacement is atomic on the same filesystem.
            os.replace(temp_name, self.experience_file)
            temp_name = None
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def load_experience(self) -> dict:
        """Load validated history or create an empty history file when absent."""
        if not self.experience_file.exists():
            experience = self._create_empty_experience()
            self._write_experience(experience)
            return experience

        try:
            with self.experience_file.open("r", encoding="utf-8") as file:
                experience = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in experience file: {self.experience_file}"
            ) from exc

        self._validate_experience(experience)
        return experience

    def save_experience(self) -> None:
        """Save the current in-memory history after validating its structure."""
        self._write_experience(self.experience)

    @staticmethod
    def calculate_success_rate(success: int, failure: int) -> float:
        """Calculate Laplace-smoothed rate: (success + 1)/(success + failure + 2)."""
        if type(success) is not int or success < 0:
            raise ValueError("success must be a non-negative integer.")
        if type(failure) is not int or failure < 0:
            raise ValueError("failure must be a non-negative integer.")
        return round((success + 1) / (success + failure + 2), 4)

    def update_experience(
        self,
        failure_category: str,
        action_id: str,
        succeeded: bool,
    ) -> dict:
        """Apply explicit feedback and atomically persist the resulting counts."""
        if not isinstance(failure_category, str) or not failure_category.strip():
            raise ValueError("failure_category must be a non-empty string.")
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id must be a non-empty string.")
        if type(succeeded) is not bool:
            raise ValueError("succeeded must be a boolean value.")

        canonical = canonical_category(failure_category)
        if canonical not in self.action_catalog:
            raise ValueError(
                f"Unsupported failure category for learning feedback: {failure_category}"
            )

        action_id = action_id.strip()
        valid_action_ids = {
            action["id"] for action in self.action_catalog[canonical]
        }
        if action_id not in valid_action_ids:
            raise ValueError(f"Unknown action '{action_id}' for '{canonical}'.")

        # Refresh first so this instance does not overwrite newer persisted data.
        current_experience = self.load_experience()
        updated_experience = deepcopy(current_experience)
        counts = updated_experience[canonical][action_id]
        counts["success" if succeeded else "failure"] += 1

        # Update in-memory state only after the atomic disk write succeeds.
        self._write_experience(updated_experience)
        self.experience = updated_experience

        return {
            "failure_category": canonical,
            "action_id": action_id,
            "success": counts["success"],
            "failure": counts["failure"],
            "success_rate": self.calculate_success_rate(
                counts["success"], counts["failure"]
            ),
        }

    @staticmethod
    def _flatten_for_matching(value: Any) -> str:
        """Convert nested evidence to searchable lowercase text."""
        try:
            return json.dumps(value, sort_keys=True, default=str).lower()
        except (TypeError, ValueError):
            return str(value).lower()

    def calculate_evidence_relevance(self, scenario: dict, action_id: str) -> dict:
        """Score evidence using logical field coverage and keyword coverage.

        Alternative names within a field group (e.g. ``dependencies`` and
        ``dependency_info``) count as one logical evidence source.
        Relevance = 0.60 * field-group coverage + 0.40 * keyword coverage.
        """
        if not isinstance(scenario, dict):
            raise TypeError("scenario must be a dictionary")
        if action_id not in self.EVIDENCE_RULES:
            raise ValueError(f"No evidence rules defined for action: {action_id}")

        rules = self.EVIDENCE_RULES[action_id]
        matched_fields: list[str] = []
        matched_field_groups: list[list[str]] = []
        relevant_text_parts: list[str] = []

        for field_group in rules["field_groups"]:
            matching_fields = [
                field
                for field in field_group
                if field in scenario and self._has_value(scenario[field])
            ]
            if matching_fields:
                matched_field_groups.append(matching_fields)
                matched_fields.extend(matching_fields)
                # If aliases are both present, both are useful evidence; they
                # still contribute only one unit to logical field coverage.
                relevant_text_parts.extend(
                    self._flatten_for_matching(scenario[field])
                    for field in matching_fields
                )

        relevant_text = " ".join(relevant_text_parts)
        matched_keywords = [
            keyword
            for keyword in rules["keywords"]
            if re.search(
                rf"(?<![\w]){re.escape(keyword.lower())}(?![\w])",
                relevant_text,
            )
        ]

        total_groups = len(rules["field_groups"])
        field_coverage = (
            len(matched_field_groups) / total_groups if total_groups else 0.0
        )
        total_keywords = len(rules["keywords"])
        keyword_coverage = (
            len(matched_keywords) / total_keywords if total_keywords else 0.0
        )
        relevance = round(0.60 * field_coverage + 0.40 * keyword_coverage, 4)

        return {
            "evidence_relevance": relevance,
            "matched_fields": matched_fields,
            "matched_field_groups": matched_field_groups,
            "matched_keywords": matched_keywords,
            "field_coverage": round(field_coverage, 4),
            "keyword_coverage": round(keyword_coverage, 4),
        }

    def get_supporting_evidence(self, scenario: dict) -> list[str]:
        """Extract populated shared-schema evidence; never expose ``expected``."""
        evidence: list[str] = []
        for label, aliases in self.EVIDENCE_FIELD_GROUPS:
            included_values: list[tuple[str, Any]] = []
            for field in aliases:
                value = scenario.get(field)
                if self._has_value(value) and not any(
                    value == prior_value for _, prior_value in included_values
                ):
                    included_values.append((field, value))

            for index, (field, value) in enumerate(included_values):
                display_label = label if index == 0 else f"Additional {label.lower()}"
                evidence.append(f"{display_label} ({field}): {value}")

        return evidence

    def _fallback_result(self, failure_category: str, evidence: list[str]) -> dict:
        """Return a safe, contract-compliant answer for unknown/healthy scenarios."""
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
                    "The shared scenario category is healthy, so no failure-specific "
                    "diagnostic action should be selected."
                ),
                "verification_checklist": [
                    "Confirm that build, tests and deployment stages passed.",
                    "Confirm that deployment health checks are successful.",
                    "Continue normal pipeline monitoring.",
                ],
                "selected_action_id": None,
                "success_rate": None,
                "evidence_relevance": None,
                "learning_score": None,
                "candidate_scores": [],
                "experience_used": None,
            }

        return {
            "agent": self.agent_name,
            "failure_category": "unknown",
            "supporting_evidence": evidence,
            "likely_cause": (
                "The available evidence is incomplete or insufficient to determine "
                "the failure cause confidently."
            ),
            "recommended_step": (
                "Collect complete pipeline logs and the missing diagnostic report, "
                "then rerun the affected stage with sufficient logging."
            ),
            "reasoning": (
                "The failure category is unknown or could not be normalized to a "
                "supported category. The agent avoids a speculative diagnosis and "
                "requests additional evidence."
            ),
            "verification_checklist": [
                "Retrieve complete, untruncated pipeline logs.",
                "Collect missing test reports or stage-specific diagnostic output.",
                "Confirm the stage status and rerun with verbose logging if appropriate.",
            ],
            "selected_action_id": None,
            "success_rate": None,
            "evidence_relevance": None,
            "learning_score": None,
            "candidate_scores": [],
            "experience_used": None,
        }

    def decide(self, scenario: dict) -> dict:
        """Return a recommendation that satisfies the shared agent output schema.

        Missing/ambiguous categories map to ``unknown``; aliases are normalized
        through Member 4's ``canonical_category`` helper. The input is read-only.
        """
        if not isinstance(scenario, dict):
            raise TypeError("scenario must be a dictionary")

        raw_category = scenario.get("failure_type", scenario.get("failure_category"))
        failure_category = canonical_category(raw_category)

        # Refresh before each decision so feedback written by another instance
        # is visible immediately.
        self.experience = self.load_experience()
        supporting_evidence = self.get_supporting_evidence(scenario)

        if failure_category not in self.action_catalog:
            return self._fallback_result(failure_category, supporting_evidence)

        candidates: list[dict[str, Any]] = []
        for action in self.action_catalog[failure_category]:
            action_id = action["id"]
            counts = self.experience[failure_category][action_id]
            success_rate = self.calculate_success_rate(
                counts["success"], counts["failure"]
            )
            evidence_result = self.calculate_evidence_relevance(scenario, action_id)
            evidence_relevance = evidence_result["evidence_relevance"]
            learning_score = round(
                self.HISTORY_WEIGHT * success_rate
                + self.EVIDENCE_WEIGHT * evidence_relevance,
                4,
            )

            candidates.append({
                "action_id": action_id,
                "recommended_step": action["step"],
                "success": counts["success"],
                "failure": counts["failure"],
                "success_rate": success_rate,
                "evidence_relevance": evidence_relevance,
                "learning_score": learning_score,
                "matched_fields": evidence_result["matched_fields"],
                "matched_field_groups": evidence_result["matched_field_groups"],
                "matched_keywords": evidence_result["matched_keywords"],
            })

        # Stable tie handling: first action in the shared catalog wins.
        best_action = max(candidates, key=lambda candidate: candidate["learning_score"])
        selected_id = best_action["action_id"]
        likely_cause = scenario.get("likely_cause") or (
            "The underlying cause is not established; the recommendation is based "
            "on the available evidence and historical troubleshooting outcomes."
        )
        reasoning = (
            f"Selected '{selected_id}' with a learning score of "
            f"{best_action['learning_score']:.4f}. The score combines its "
            f"Laplace-smoothed historical success rate "
            f"({best_action['success_rate']:.4f}, weight {self.HISTORY_WEIGHT:.0%}) "
            f"and scenario evidence relevance "
            f"({best_action['evidence_relevance']:.4f}, weight {self.EVIDENCE_WEIGHT:.0%})."
        )

        experience_used = {
            "selection_formula": (
                "learning_score = 0.60 * smoothed_success_rate "
                "+ 0.40 * evidence_relevance"
            ),
            "history_weight": self.HISTORY_WEIGHT,
            "evidence_weight": self.EVIDENCE_WEIGHT,
            "candidates": [
                {
                    "action_id": candidate["action_id"],
                    "success": candidate["success"],
                    "failure": candidate["failure"],
                    "smoothed_success_rate": candidate["success_rate"],
                }
                for candidate in candidates
            ],
        }

        return {
            "agent": self.agent_name,
            "failure_category": failure_category,
            "supporting_evidence": supporting_evidence,
            "likely_cause": str(likely_cause),
            "recommended_step": best_action["recommended_step"],
            "reasoning": reasoning,
            "verification_checklist": [
                "Execute the recommended diagnostic action.",
                "Verify whether the diagnostic action achieved its intended outcome.",
                "Provide explicit success or failure feedback to update experience.",
            ],
            "selected_action_id": selected_id,
            "success_rate": best_action["success_rate"],
            "evidence_relevance": best_action["evidence_relevance"],
            "learning_score": best_action["learning_score"],
            "candidate_scores": candidates,
            "experience_used": experience_used,
        }
