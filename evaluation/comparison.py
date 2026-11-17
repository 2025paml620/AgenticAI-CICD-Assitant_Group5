"""Compare the decisions of all six agents on one scenario.

Owner: Member 4 (Karthik) - comparison table and explanation.

Run from the repo root to regenerate the saved test results:

    python -m evaluation.comparison            # all scenarios, LLM included
    python -m evaluation.comparison --no-llm   # skip the Ollama agent
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import canonical_category
from evaluation.runner import AGENT_SPECS, AgentRun, load_agents, run_all
from scenario_loader import expected_for, load_scenario, scenario_ids

RESULTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "test_results"


def step_matches_expected(step: str, expected: dict[str, Any]) -> bool:
    """True if the recommended step mentions at least one acceptable keyword."""
    text = (step or "").lower()
    return any(k.lower() in text for k in expected.get("acceptable_next_steps", []))


def comparison_rows(runs: list[AgentRun], expected: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per agent for the comparison table."""
    rows = []
    for run in runs:
        row: dict[str, Any] = {"Agent": run.spec.display_name, "Status": run.status}
        if run.result:
            r = run.result
            cat = r["canonical_category"]
            row.update({
                "Failure category": r["failure_category"],
                "Canonical": cat,
                "Category correct": cat == expected["failure_category"] if run.status == "ok" else None,
                "Recommended step": r["recommended_step"],
                "Step relevant": step_matches_expected(r["recommended_step"], expected) if run.status == "ok" else None,
                "Evidence items": len(r["supporting_evidence"]),
                "Extra": _extra_summary(r),
                "Time (s)": round(run.seconds, 3),
            })
        else:
            row.update({
                "Failure category": "-", "Canonical": "-", "Category correct": None,
                "Recommended step": run.error or "-", "Step relevant": None,
                "Evidence items": 0, "Extra": "", "Time (s)": round(run.seconds, 3),
            })
        rows.append(row)
    return rows


def _extra_summary(result: dict[str, Any]) -> str:
    parts = []
    if result.get("tools_used"):
        parts.append("tools: " + ", ".join(map(str, result["tools_used"])))
    if result.get("utility_score") is not None:
        parts.append(f"utility={result['utility_score']}")
    if result.get("experience_used"):
        parts.append("experience used")
    if result.get("plan"):
        parts.append(f"plan of {len(result['plan'])} steps")
    return "; ".join(parts)


def summarize(runs: list[AgentRun], expected: dict[str, Any]) -> dict[str, Any]:
    """Aggregate agreement and correctness numbers for one scenario."""
    ok = [r for r in runs if r.result and r.status == "ok"]
    cats = Counter(r.result["canonical_category"] for r in ok)
    steps = {r.result["recommended_step"] for r in ok}
    majority, majority_n = cats.most_common(1)[0] if cats else ("-", 0)
    return {
        "agents_run": len(ok),
        "agents_unavailable": [r.spec.display_name for r in runs if r.status in ("unavailable", "error", "invalid")],
        "category_correct": sum(r.result["canonical_category"] == expected["failure_category"] for r in ok),
        "step_relevant": sum(step_matches_expected(r.result["recommended_step"], expected) for r in ok),
        "majority_category": majority,
        "category_agreement": f"{majority_n}/{len(ok)}" if ok else "0/0",
        "distinct_steps": len(steps),
        "all_inputs_unchanged": all(r.input_unchanged for r in runs),
    }


def explain_differences(runs: list[AgentRun], expected: dict[str, Any]) -> list[str]:
    """Plain-language explanation of why the agents' decisions differ."""
    lines = []
    for run in runs:
        if not run.result or run.status != "ok":
            lines.append(f"**{run.spec.display_name}** - not compared ({run.status}: {run.error}).")
            continue
        r = run.result
        verdict = "matches" if r["canonical_category"] == expected["failure_category"] else "differs from"
        lines.append(
            f"**{run.spec.display_name}** ({run.spec.mechanism}) -> `{r['failure_category']}`, "
            f"which {verdict} the expected `{expected['failure_category']}`. "
            f"It recommends: *{r['recommended_step']}*"
        )
    ok = [r for r in runs if r.result and r.status == "ok"]
    if ok and len({r.result["canonical_category"] for r in ok}) > 1:
        lines.append(
            "Categories disagree: rule/state-driven agents classify from stage statuses, while the "
            "Utility agent depends on the declared `failure_type` and the LLM/Learning agents depend on "
            "the evidence or history available. With incomplete evidence these mechanisms diverge."
        )
    elif ok:
        lines.append(
            "All agents agree on the category; they differ in *how* they reach it and in the specific "
            "next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence)."
        )
    return lines


def to_markdown(scenario_id: str, runs: list[AgentRun]) -> str:
    scenario = load_scenario(scenario_id)
    expected = scenario["expected"]
    rows = comparison_rows(runs, expected)
    summary = summarize(runs, expected)
    cols = ["Agent", "Status", "Failure category", "Category correct", "Recommended step", "Step relevant", "Extra", "Time (s)"]
    out = [
        f"## Scenario {scenario_id}: {scenario['name']} ({scenario.get('scenario_type', '')})",
        "",
        f"_{scenario['description']}_",
        "",
        f"Expected category: `{expected['failure_category']}` - {expected['rationale']}",
        "",
        "| " + " | ".join(cols) + " |",
        "|" + "---|" * len(cols),
    ]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    out += [
        "",
        f"- Agents run: {summary['agents_run']}; not compared: {', '.join(summary['agents_unavailable']) or 'none'}",
        f"- Category correct: {summary['category_correct']}/{summary['agents_run']}; "
        f"step relevant: {summary['step_relevant']}/{summary['agents_run']}",
        f"- Category agreement (majority `{summary['majority_category']}`): {summary['category_agreement']}; "
        f"distinct recommended steps: {summary['distinct_steps']}",
        f"- Same input to every agent and no agent mutated it: {summary['all_inputs_unchanged']}",
        "",
        "### Why the decisions differ",
        "",
    ]
    out += [f"- {line}" for line in explain_differences(runs, expected)]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run all agents on all scenarios and save a comparison report.")
    parser.add_argument("--no-llm", action="store_true", help="Skip the Ollama LLM agent")
    parser.add_argument("--out", default=str(RESULTS_DIR / "comparison_results.md"))
    args = parser.parse_args(argv)

    include = [s.key for s in AGENT_SPECS if not (args.no_llm and s.is_llm)]
    agents = load_agents()
    parts = [
        "# Agent comparison results",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} by `python -m evaluation.comparison"
        f"{' --no-llm' if args.no_llm else ''}`.",
        "",
    ]
    for sid in scenario_ids():
        _, runs = run_all(sid, agents=agents, include=include)
        parts.append(to_markdown(sid, runs))
        print(f"Scenario {sid}: {summarize(runs, expected_for(sid))}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
