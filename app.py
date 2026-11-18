"""Streamlit dashboard for the Intelligent CI/CD Pipeline Failure Assistant.

Owner: Member 4 (Karthik) - UI and integration.

Run from the repo root:
    streamlit run app.py
"""
from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

from evaluation.comparison import comparison_rows, explain_differences, summarize
from evaluation.runner import AGENT_SPECS, load_agents, run_all
from scenario_loader import agent_input, expected_for, load_scenarios

st.set_page_config(page_title="CI/CD Failure Assistant", page_icon="🛠️", layout="wide")

STATUS_ICON = {"passed": "✅", "failed": "❌", "not_started": "⏸️", "timed_out": "⏱️", "unknown": "❔"}
SCENARIOS = {s["id"]: s for s in load_scenarios()}


# ---------------------------------------------------------------- state
def get_agents(model: str) -> dict:
    """Agents are kept in the session so stateful agents (model-based memory,
    learning history) persist across runs until the user resets them."""
    if st.session_state.get("agents_model") != model or "agents" not in st.session_state:
        st.session_state["agents"] = load_agents(factory_kwargs={"llm": {"model_name": model}})
        st.session_state["agents_model"] = model
    return st.session_state["agents"]


def reset_agents() -> None:
    for key in ("agents", "agents_model", "results", "matrix", "auto_ran"):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🛠️ CI/CD Failure Assistant")
st.sidebar.caption("Advisory only - agents recommend steps; they never change code or deploy.")

# Optional URL params, e.g. ?scenario=B&run=1 (handy for demos and screenshots).
url_scenario = str(st.query_params.get("scenario", "")).upper()
scenario_id = st.sidebar.radio(
    "Select a scenario",
    list(SCENARIOS),
    index=list(SCENARIOS).index(url_scenario) if url_scenario in SCENARIOS else 0,
    format_func=lambda sid: f"{sid} - {SCENARIOS[sid]['name']} [{SCENARIOS[sid].get('scenario_type', '')}]",
)

st.sidebar.subheader("Agents")
selected = [
    spec.key for spec in AGENT_SPECS
    if st.sidebar.checkbox(spec.display_name, value=True, key=f"use_{spec.key}", help=spec.mechanism)
]
model = st.sidebar.text_input("Ollama model (LLM agent)", value=os.environ.get("OLLAMA_MODEL", "qwen3:4b"))
st.sidebar.button("Reset agents (clear memory)", on_click=reset_agents)

agents = get_agents(model)
with st.sidebar.expander("Agent availability"):
    for spec in AGENT_SPECS:
        agent, err = agents.get(spec.key, (None, "not loaded"))
        st.write(f"{'🟢' if agent else '🔴'} **{spec.display_name}** ({spec.owner})")
        if err:
            st.caption(err)

# ---------------------------------------------------------------- scenario
scenario = SCENARIOS[scenario_id]
st.title(f"Scenario {scenario_id}: {scenario['name']}")
st.write(scenario["description"])

st.markdown(
    "**Pipeline status:** "
    + " → ".join(
        f"{stage.title()} {STATUS_ICON.get(v, '❔')} `{v}`"
        for stage, v in ((s, scenario["pipeline_status"].get(s, "unknown")) for s in ("build", "tests", "deployment"))
    )
    + f" · **Pipeline:** `{scenario.get('pipeline_id', '-')}` · **Run:** `{scenario.get('run_id', '-')}`"
    + f" · **Branch:** `{scenario.get('branch', '-')}`"
)

tab_logs, tab_tests, tab_deps, tab_changes, tab_health, tab_raw = st.tabs(
    ["Build logs", "Test results", "Dependencies", "Recent changes", "Health checks", "Agent input (JSON)"]
)
with tab_logs:
    st.code(scenario["build_logs"] or "(no logs)", language="text")
    if scenario.get("deployment_logs"):
        st.caption("Deployment / runtime logs")
        st.code(scenario["deployment_logs"], language="text")
with tab_tests:
    tr = scenario["test_results"]
    st.write({k: v for k, v in tr.items() if k != "failed_tests"})
    if tr.get("failed_tests"):
        st.dataframe(pd.DataFrame(tr["failed_tests"]), hide_index=True, use_container_width=True)
with tab_deps:
    deps = scenario["dependencies"]
    st.write(f"Status: **{deps.get('status')}** - {deps.get('notes', '')}")
    if deps.get("changed"):
        st.dataframe(pd.DataFrame(deps["changed"]), hide_index=True, use_container_width=True)
with tab_changes:
    if scenario["recent_changes"]:
        for change in scenario["recent_changes"]:
            st.write(f"- {change}")
    else:
        st.warning("No recent-change information available.")
with tab_health:
    st.write(scenario["health_checks"] or "No health-check data (deployment not reached or not recorded).")
with tab_raw:
    st.caption("Exactly this dictionary (a fresh copy each) is passed to every agent's decide(). "
               "The expected answer is removed so no agent can see it.")
    st.json(agent_input(scenario_id), expanded=False)

# ---------------------------------------------------------------- run
st.divider()
run_clicked = st.button("▶️ Run all selected agents", type="primary")
auto_run = st.query_params.get("run") == "1" and st.session_state.get("auto_ran") != scenario_id
if run_clicked or auto_run:
    st.session_state["auto_ran"] = scenario_id
    progress = st.status("Running agents...", expanded=False)
    _, runs = run_all(
        scenario_id, agents=agents, include=selected,
        on_progress=lambda spec: progress.write(f"Running {spec.display_name}..."),
    )
    progress.update(label="Agents finished", state="complete")
    st.session_state["results"] = {"scenario_id": scenario_id, "runs": runs}

results = st.session_state.get("results")
if not results or results["scenario_id"] != scenario_id:
    st.info("Select agents and click **Run all selected agents** to compare their decisions.")
    st.stop()

runs = results["runs"]
expected = expected_for(scenario_id)
summary = summarize(runs, expected)

st.header("Comparison")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Agents compared", summary["agents_run"])
m2.metric("Category correct", f"{summary['category_correct']}/{summary['agents_run']}")
m3.metric("Category agreement", summary["category_agreement"], summary["majority_category"], delta_color="off")
m4.metric("Distinct next steps", summary["distinct_steps"])
st.caption(f"Expected category: `{expected['failure_category']}` - {expected['rationale']}")
if not summary["all_inputs_unchanged"]:
    st.warning("At least one agent modified its input copy.")

df = pd.DataFrame(comparison_rows(runs, expected))
st.dataframe(df, hide_index=True, use_container_width=True)

with st.expander("Why do the decisions differ?", expanded=True):
    for line in explain_differences(runs, expected):
        st.markdown(f"- {line}")

# ---------------------------------------------------------------- details
st.header("Agent decisions and reasoning")
for run in runs:
    label = f"{run.spec.display_name} - {run.status}"
    if run.result:
        label += f" - {run.result['failure_category']}"
    with st.expander(label, expanded=run.status != "skipped"):
        st.caption(f"Mechanism: {run.spec.mechanism} · Owner: {run.spec.owner} · {run.seconds:.3f}s")
        if not run.result:
            (st.info if run.status in ("skipped", "unavailable") else st.error)(run.error or run.status)
            continue
        r = run.result
        if run.problems:
            st.warning("Output contract issues: " + "; ".join(run.problems))
        if run.error:
            st.error(run.error)
        left, right = st.columns(2)
        with left:
            st.markdown(f"**Failure category:** `{r['failure_category']}` (canonical `{r['canonical_category']}`)")
            st.markdown(f"**Likely cause:** {r['likely_cause']}")
            st.markdown(f"**Recommended next step:** {r['recommended_step']}")
            st.markdown(f"**Reasoning:** {r['reasoning']}")
        with right:
            st.markdown("**Supporting evidence**")
            for item in r["supporting_evidence"] or ["(none provided)"]:
                st.markdown(f"- {item}")
            st.markdown("**Post-fix verification checklist**")
            for item in r["verification_checklist"]:
                st.checkbox(item, key=f"chk_{run.spec.key}_{item}")
        if r.get("plan"):
            st.markdown("**Plan:** " + " → ".join(r["plan"]))
        if r.get("candidate_scores"):
            st.markdown("**Utility scores of candidate actions**")
            st.dataframe(
                pd.DataFrame(r["candidate_scores"]).sort_values("utility_score", ascending=False),
                hide_index=True, use_container_width=True,
            )
        if r.get("experience_used"):
            st.markdown("**Experience used**")
            st.json(r["experience_used"], expanded=False)
        if r.get("tools_used") or r.get("tool_calls"):
            st.markdown("**LLM tool-call evidence**")
            st.caption(f"Model: {r.get('model', model)} · Actual tool calls: {len(r.get('tool_calls', []))}")
            if r.get("tools_used"):
                st.write("Tools called: " + ", ".join(map(str, r["tools_used"])))
            if r.get("grounding_review"):
                st.write("Grounding review: " + ("passed" if r["grounding_review"].get("supported") else "rejected"))
            st.download_button("Download LLM diagnosis and full trace", json.dumps(r, indent=2, default=str),
                               file_name=f"llm_scenario_{scenario_id}.json", mime="application/json",
                               key=f"download_{run.spec.key}_{scenario_id}")
            with st.expander("Executed tools and returned evidence", expanded=False):
                for call in r.get("tool_calls") or []:
                    st.json(call, expanded=False)

        # Simulated feedback for the Learning agent (if it exposes record_outcome).
        agent_obj = agents.get(run.spec.key, (None, None))[0]
        if run.spec.key == "learning" and callable(getattr(agent_obj, "record_outcome", None)):
            st.markdown("**Simulated feedback** (clearly labelled as simulated, for demonstration)")
            c1, c2 = st.columns(2)
            for col, success in ((c1, True), (c2, False)):
                if col.button(f"Record simulated {'success' if success else 'failure'}", key=f"fb_{success}"):
                    try:
                        agent_obj.record_outcome(scenario.get("failure_type"), r.get("action_id") or r["recommended_step"], success)
                        st.success("Experience updated - rerun the agents to see the effect.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not record feedback: {exc}")

st.divider()
st.caption("Scenario data is simulated. Agents are advisory: no code is changed and nothing is deployed.")
