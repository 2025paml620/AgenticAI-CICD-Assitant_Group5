"""Load all six agents and run them on the same scenario.

Owner: Member 4 (Karthik) - integration.

Design points:
* Every agent gets its own deep copy of the *same* scenario input, so one
  agent cannot change what another agent sees.
* An agent that is missing (not merged yet) or raises an error is reported
  as such; it never crashes the run or the Streamlit UI.
"""
from __future__ import annotations

import copy
import importlib
import inspect
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from agents.base_agent import normalize_result, validate_result
from scenario_loader import agent_input


@dataclass(frozen=True)
class AgentSpec:
    key: str
    display_name: str
    module: str
    class_names: tuple[str, ...]
    mechanism: str
    owner: str
    is_llm: bool = False


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        "simple_reflex", "Simple Reflex", "agents.simple_reflex", ("SimpleReflexAgent",),
        "Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.",
        "Member 1",
    ),
    AgentSpec(
        "model_based", "Model-Based Reflex", "agents.model_based", ("ModelBasedAgent", "ModelBasedReflexAgent"),
        "Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.",
        "Member 1",
    ),
    AgentSpec(
        "goal_based", "Goal-Based", "agents.goal_based", ("GoalBasedAgent",),
        "Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.",
        "Member 1",
    ),
    AgentSpec(
        "utility_based", "Utility-Based", "agents.utility_based", ("UtilityBasedAgent",),
        "Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.",
        "Member 2",
    ),
    AgentSpec(
        "learning", "Learning", "agents.learning_agent", ("LearningAgent",),
        "Uses stored success/failure counts per action (experience) to prefer historically successful steps; updates with feedback.",
        "Member 2",
    ),
    AgentSpec(
        "llm", "LLM (Ollama + tools)", "agents.llm_agent", ("LLMAgent", "LlmAgent", "OllamaLLMAgent", "LLMBasedAgent"),
        "Local Ollama model via LangChain; calls diagnostic tools and grounds its answer in the returned evidence.",
        "Member 3",
        is_llm=True,
    ),
)

SPEC_BY_KEY = {s.key: s for s in AGENT_SPECS}


@dataclass
class AgentRun:
    spec: AgentSpec
    status: str  # "ok" | "invalid" | "error" | "unavailable" | "skipped"
    result: dict[str, Any] | None = None
    error: str | None = None
    problems: list[str] = field(default_factory=list)
    seconds: float = 0.0
    input_unchanged: bool = True


def _find_agent_class(module: Any, spec: AgentSpec) -> type | None:
    for name in spec.class_names:
        cls = getattr(module, name, None)
        if inspect.isclass(cls):
            return cls
    # Fallback: first class defined in that module with a decide() method.
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if cls.__module__ == module.__name__ and callable(getattr(cls, "decide", None)):
            return cls
    return None


def load_agent(spec: AgentSpec, factory_kwargs: dict[str, Any] | None = None) -> tuple[Any | None, str | None]:
    """Import and instantiate one agent. Returns (agent, error_message)."""
    try:
        module = importlib.import_module(spec.module)
    except ModuleNotFoundError as exc:
        if exc.name == spec.module:
            return None, f"{spec.module} not found (not merged yet)"
        return None, f"Import error in {spec.module}: {exc}"
    except Exception as exc:  # noqa: BLE001 - surface any import-time error
        return None, f"Import error in {spec.module}: {exc}"
    cls = _find_agent_class(module, spec)
    if cls is None:
        return None, f"No agent class with decide() found in {spec.module}"
    try:
        return cls(**(factory_kwargs or {})), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not create {cls.__name__}: {exc}"


def load_agents(
    keys: list[str] | None = None,
    factory_kwargs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, tuple[Any | None, str | None]]:
    """Load the requested agents (all by default)."""
    factory_kwargs = factory_kwargs or {}
    selected = [SPEC_BY_KEY[k] for k in keys] if keys else list(AGENT_SPECS)
    return {s.key: load_agent(s, factory_kwargs.get(s.key)) for s in selected}


def run_agent(spec: AgentSpec, agent: Any, scenario: dict[str, Any]) -> AgentRun:
    """Run one agent on its own copy of the scenario and validate the output."""
    own_copy = copy.deepcopy(scenario)
    start = time.perf_counter()
    try:
        raw = agent.decide(own_copy)
    except Exception as exc:  # noqa: BLE001 - one agent must not crash the run
        return AgentRun(
            spec, "error",
            error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}",
            seconds=time.perf_counter() - start,
        )
    seconds = time.perf_counter() - start
    problems = validate_result(raw)
    if not isinstance(raw, dict):
        return AgentRun(spec, "invalid", error="Agent did not return a dict", problems=problems, seconds=seconds)
    if raw.get("status") == "error":
        return AgentRun(spec, "error", result=normalize_result(raw, spec.display_name),
                        error=str(raw.get("reasoning", "Agent reported a diagnostic error")),
                        problems=problems, seconds=seconds, input_unchanged=(own_copy == scenario))
    if spec.is_llm:
        successful = [call for call in raw.get("tool_calls", [])
                      if isinstance(call, dict) and "output" in call and "error" not in call
                      and call.get("args") == {"scenario_id": scenario.get("id")}]
        invoked = {call.get("name") for call in successful if call.get("name")}
        if len(invoked) < 2:
            problems.append("LLM requires at least two distinct successful tool calls for this scenario")
        if set(raw.get("tools_used", [])) != invoked:
            problems.append("tools_used does not match the executed tool trace")
    return AgentRun(
        spec,
        "ok" if not problems else "invalid",
        result=normalize_result(raw, spec.display_name),
        problems=problems,
        seconds=seconds,
        input_unchanged=(own_copy == scenario),
    )


def run_all(
    scenario_id: str,
    agents: dict[str, tuple[Any | None, str | None]] | None = None,
    include: list[str] | None = None,
    on_progress: Callable[[AgentSpec], None] | None = None,
) -> tuple[dict[str, Any], list[AgentRun]]:
    """Run every agent on the same scenario. Returns (shared_input, runs)."""
    shared_input = agent_input(scenario_id)
    agents = agents if agents is not None else load_agents()
    runs: list[AgentRun] = []
    for spec in AGENT_SPECS:
        if spec.key not in agents:
            continue
        if include is not None and spec.key not in include:
            runs.append(AgentRun(spec, "skipped", error="Not selected for this run"))
            continue
        agent, load_error = agents[spec.key]
        if agent is None:
            runs.append(AgentRun(spec, "unavailable", error=load_error))
            continue
        if on_progress:
            on_progress(spec)
        runs.append(run_agent(spec, agent, shared_input))
    return shared_input, runs
