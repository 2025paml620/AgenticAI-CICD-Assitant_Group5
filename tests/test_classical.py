"""
Member 1 : Shubhra Shrivastava
Member 1: tests/test_classical.py
Automated tests for three classical CI/CD agents.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_classical.py' -v

"""
import copy
import unittest

from agents.simple_reflex import SimpleReflexAgent
from agents.model_based import ModelBasedAgent
from agents.goal_based import GoalBasedAgent


SCENARIOS = {
    "A": {
        "id": "A", "pipeline_id": "pipeline-A",
        "pipeline_status": {"build": "passed", "tests": "failed", "deployment": "not_started"},
        "recent_changes": ["Modified payment API"],
    },
    "B": {
        "id": "B", "pipeline_id": "pipeline-B",
        "pipeline_status": {"build": "failed", "tests": "not_started", "deployment": "not_started"},
        "recent_changes": ["Updated requirements.txt"],
    },
    "C": {
        "id": "C", "pipeline_id": "pipeline-C",
        "pipeline_status": {"build": "passed", "tests": "passed", "deployment": "failed"},
        "recent_changes": ["Changed runtime configuration"],
    },
    "HEALTHY": {
        "id": "HEALTHY", "pipeline_id": "pipeline-healthy",
        "pipeline_status": {"build": "passed", "tests": "passed", "deployment": "passed"},
    },
    "UNKNOWN": {"id": "UNKNOWN", "pipeline_id": "pipeline-unknown", "pipeline_status": {}},
}

EXPECTED_CATEGORIES = {
    "A": "unit_test_failure",
    "B": "dependency_or_build_failure",
    "C": "deployment_health_failure",
    "HEALTHY": "healthy",
    "UNKNOWN": "unknown",
}

REQUIRED_FIELDS = {
    "agent", "failure_category", "supporting_evidence", "likely_cause",
    "recommended_step", "reasoning", "verification_checklist",
}

AGENT_CLASSES = (SimpleReflexAgent, ModelBasedAgent, GoalBasedAgent)


class TestClassicalAgents(unittest.TestCase):
    def test_all_agents_classify_scenarios(self):
        """All agents must classify the same five scenarios consistently."""
        for agent_class in AGENT_CLASSES:
            for scenario_id, expected in EXPECTED_CATEGORIES.items():
                with self.subTest(agent=agent_class.__name__, scenario=scenario_id):
                    agent = agent_class()  # fresh state for each independent case
                    result = agent.decide(copy.deepcopy(SCENARIOS[scenario_id]))
                    self.assertEqual(result["failure_category"], expected)

    def test_output_contract(self):
        """Every agent must return a usable, consistently typed result."""
        for agent_class in AGENT_CLASSES:
            for scenario_id in SCENARIOS:
                with self.subTest(agent=agent_class.__name__, scenario=scenario_id):
                    result = agent_class().decide(copy.deepcopy(SCENARIOS[scenario_id]))
                    self.assertIsInstance(result, dict)
                    self.assertTrue(REQUIRED_FIELDS.issubset(result), REQUIRED_FIELDS - result.keys())
                    for field in ("agent", "failure_category", "likely_cause", "recommended_step", "reasoning"):
                        self.assertIsInstance(result[field], str)
                        self.assertTrue(result[field].strip(), f"Empty field: {field}")
                    for field in ("supporting_evidence", "verification_checklist"):
                        self.assertIsInstance(result[field], list)
                        self.assertTrue(result[field], f"Empty list: {field}")
                        self.assertTrue(all(isinstance(item, str) and item.strip() for item in result[field]))

    def test_does_not_mutate_input(self):
        """The agents should never change the shared scenario dictionary."""
        for agent_class in AGENT_CLASSES:
            with self.subTest(agent=agent_class.__name__):
                scenario = copy.deepcopy(SCENARIOS["A"])
                original = copy.deepcopy(scenario)
                agent_class().decide(scenario)
                self.assertEqual(scenario, original)

    def test_flat_status_format_supported(self):
        """Member 4 may initially supply top-level stage statuses."""
        flat = {"id": "flat-A", "build": "passed", "tests": "failed", "deployment": "not_started"}
        for agent_class in AGENT_CLASSES:
            with self.subTest(agent=agent_class.__name__):
                result = agent_class().decide(copy.deepcopy(flat))
                self.assertEqual(result["failure_category"], "unit_test_failure")

    def test_model_based_remembers_same_pipeline(self):
        agent = ModelBasedAgent()
        scenario = copy.deepcopy(SCENARIOS["A"])
        first = agent.decide(scenario)
        second = agent.decide(scenario)
        self.assertIn("No previous observation", first["reasoning"])
        self.assertIn("matches the current observation", second["reasoning"])

    def test_model_based_detects_transition(self):
        agent = ModelBasedAgent()
        before = copy.deepcopy(SCENARIOS["A"])
        after = copy.deepcopy(before)
        after["pipeline_status"]["tests"] = "passed"
        agent.decide(before)
        result = agent.decide(after)
        self.assertIn("tests", result["reasoning"])
        self.assertTrue(any("tests: failed -> passed" in item for item in result["supporting_evidence"]))

    def test_model_based_keeps_pipelines_separate(self):
        agent = ModelBasedAgent()
        agent.decide(copy.deepcopy(SCENARIOS["A"]))
        result = agent.decide(copy.deepcopy(SCENARIOS["B"]))
        self.assertIn("No previous observation", result["reasoning"])

    def test_model_based_reset(self):
        agent = ModelBasedAgent()
        agent.decide(copy.deepcopy(SCENARIOS["A"]))
        agent.reset()
        result = agent.decide(copy.deepcopy(SCENARIOS["A"]))
        self.assertIn("No previous observation", result["reasoning"])

    def test_goal_based_plan_is_safe_and_nonempty(self):
        agent = GoalBasedAgent()
        for scenario_id in SCENARIOS:
            with self.subTest(scenario=scenario_id):
                result = agent.decide(copy.deepcopy(SCENARIOS[scenario_id]))
                self.assertIsInstance(result.get("plan"), list)
                self.assertTrue(result["plan"])
                self.assertEqual(result["recommended_step"], result["plan"][0])
                self.assertIn("No actions are executed", result["reasoning"])

    def test_build_failure_has_priority(self):
        """An upstream build failure should be diagnosed before later stages."""
        scenario = {
            "id": "multi-failure",
            "pipeline_status": {"build": "failed", "tests": "failed", "deployment": "failed"},
        }
        for agent_class in AGENT_CLASSES:
            with self.subTest(agent=agent_class.__name__):
                result = agent_class().decide(copy.deepcopy(scenario))
                self.assertEqual(result["failure_category"], "dependency_or_build_failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
