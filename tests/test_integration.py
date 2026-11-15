"""End-to-end integration tests (Member 4 - Karthik).

Checks the shared scenarios, the common agent contract, that every agent gets
the same input, that one failing/missing agent does not break a run, and that
the comparison report is produced.

Agents not merged yet are skipped, not failed. The LLM agent needs a running
Ollama server, so its test runs only with RUN_LLM_TESTS=1.

    pytest -v tests/test_integration.py
    RUN_LLM_TESTS=1 pytest -v tests/test_integration.py
"""
from __future__ import annotations

import os

import pytest

from agents.base_agent import REQUIRED_FIELDS, canonical_category, validate_result
from evaluation.comparison import comparison_rows, summarize, to_markdown
from evaluation.runner import AGENT_SPECS, AgentSpec, load_agent, run_agent, run_all
from scenario_loader import agent_input, expected_for, load_scenarios, scenario_ids

CLASSICAL = [s for s in AGENT_SPECS if not s.is_llm]
LLM_SPEC = next(s for s in AGENT_SPECS if s.is_llm)
REQUIRED_SCENARIOS = {"A": "unit_test", "B": "dependency", "C": "deployment"}


def _agent_or_skip(spec: AgentSpec):
    agent, err = load_agent(spec)
    if agent is None:
        pytest.skip(f"{spec.display_name} unavailable: {err}")
    return agent


# ------------------------------------------------------------ scenarios
def test_required_scenarios_present():
    ids = scenario_ids()
    for sid, ftype in REQUIRED_SCENARIOS.items():
        assert sid in ids
        assert expected_for(sid)["failure_category"] == ftype


def test_normal_critical_and_edge_cases_covered():
    types = {s["scenario_type"] for s in load_scenarios()}
    assert {"normal", "critical", "edge"} <= types


def test_scenario_status_matches_story():
    a, b, c = (agent_input(x)["pipeline_status"] for x in "ABC")
    assert a == {"build": "passed", "tests": "failed", "deployment": "not_started"}
    assert b["build"] == "failed"
    assert c == {"build": "passed", "tests": "passed", "deployment": "failed"}


def test_agent_input_hides_expected_and_is_a_copy():
    first = agent_input("A")
    assert "expected" not in first
    first["pipeline_status"]["tests"] = "passed"
    assert agent_input("A")["pipeline_status"]["tests"] == "failed"


# ------------------------------------------------------------ contract helpers
@pytest.mark.parametrize("label,canonical", [
    ("unit_test", "unit_test"), ("unit_test_failure", "unit_test"),
    ("dependency_or_build_failure", "dependency"), ("dependency", "dependency"),
    ("deployment_health_failure", "deployment"), ("healthy", "healthy"),
    ("none", "healthy"), (None, "unknown"), ("Dependency version conflict", "dependency"),
])
def test_canonical_category(label, canonical):
    assert canonical_category(label) == canonical


def test_validate_result_flags_missing_fields():
    assert validate_result({"agent": "x"})
    assert validate_result("not a dict")
    good = {f: ["x"] if f in ("supporting_evidence", "verification_checklist") else "x" for f in REQUIRED_FIELDS}
    assert validate_result(good) == []


# ------------------------------------------------------------ classical agents
@pytest.mark.parametrize("spec", CLASSICAL, ids=[s.key for s in CLASSICAL])
@pytest.mark.parametrize("sid", ["A", "B", "C", "D", "E"])
def test_agent_returns_valid_contract(spec, sid):
    agent = _agent_or_skip(spec)
    run = run_agent(spec, agent, agent_input(sid))
    assert run.status == "ok", (run.error, run.problems)
    assert run.input_unchanged, f"{spec.display_name} mutated its input"


@pytest.mark.parametrize("spec", CLASSICAL, ids=[s.key for s in CLASSICAL])
@pytest.mark.parametrize("sid", list(REQUIRED_SCENARIOS))
def test_agent_classifies_required_scenarios(spec, sid):
    agent = _agent_or_skip(spec)
    run = run_agent(spec, agent, agent_input(sid))
    assert run.result["canonical_category"] == REQUIRED_SCENARIOS[sid], run.result


@pytest.mark.parametrize("spec", CLASSICAL, ids=[s.key for s in CLASSICAL])
def test_edge_case_is_not_overconfident(spec):
    """Scenario D has incomplete evidence: agents must not claim a specific known failure."""
    agent = _agent_or_skip(spec)
    run = run_agent(spec, agent, agent_input("D"))
    assert run.result["canonical_category"] in ("unknown", "unit_test"), run.result
    if run.result["canonical_category"] == "unit_test":
        pytest.xfail(f"{spec.display_name} treats a timed-out test stage as a unit-test failure (documented limitation)")


# ------------------------------------------------------------ fairness / robustness
class _SpyAgent:
    def __init__(self, sink):
        self.sink = sink

    def decide(self, scenario):
        self.sink.append(scenario)
        scenario["pipeline_status"]["build"] = "tampered"  # must not leak to other agents
        return {f: [] if f in ("supporting_evidence", "verification_checklist") else "x" for f in REQUIRED_FIELDS}


class _BrokenAgent:
    def decide(self, scenario):
        raise RuntimeError("boom")


def test_all_agents_receive_identical_input():
    seen: list[dict] = []
    agents = {s.key: (_SpyAgent(seen), None) for s in AGENT_SPECS}
    shared, runs = run_all("B", agents=agents)
    assert len(seen) == len(AGENT_SPECS)
    # Each agent tampered with its own copy, yet the next agent still saw the original.
    assert all(s["pipeline_status"]["build"] == "tampered" for s in seen)
    assert shared["pipeline_status"]["build"] == "failed"
    assert all(not r.input_unchanged for r in runs)


def test_failing_or_missing_agent_does_not_break_run():
    agents = {s.key: (_SpyAgent([]), None) for s in AGENT_SPECS}
    agents["learning"] = (None, "not merged yet")
    agents["llm"] = (_BrokenAgent(), None)
    _, runs = run_all("A", agents=agents)
    status = {r.spec.key: r.status for r in runs}
    assert status["learning"] == "unavailable"
    assert status["llm"] == "error" and "boom" in next(r.error for r in runs if r.spec.key == "llm")
    assert status["simple_reflex"] == "ok"


def test_missing_module_reported_cleanly():
    agent, err = load_agent(AgentSpec("x", "X", "agents.does_not_exist", ("X",), "", ""))
    assert agent is None and "not found" in err


# ------------------------------------------------------------ comparison
@pytest.mark.parametrize("sid", scenario_ids())
def test_comparison_report_for_every_scenario(sid):
    _, runs = run_all(sid, include=[s.key for s in CLASSICAL])
    rows = comparison_rows(runs, expected_for(sid))
    assert len(rows) == len(AGENT_SPECS)
    summary = summarize(runs, expected_for(sid))
    assert summary["all_inputs_unchanged"]
    assert f"Scenario {sid}" in to_markdown(sid, runs)


# ------------------------------------------------------------ LLM (optional)
@pytest.mark.skipif(os.environ.get("RUN_LLM_TESTS") != "1", reason="set RUN_LLM_TESTS=1 with Ollama running")
@pytest.mark.parametrize("sid", list(REQUIRED_SCENARIOS))
def test_llm_agent_calls_at_least_two_tools(sid):
    agent = _agent_or_skip(LLM_SPEC)
    run = run_agent(LLM_SPEC, agent, agent_input(sid))
    assert run.status == "ok", (run.error, run.problems)
    assert len(set(run.result.get("tools_used", []))) >= 2, run.result
