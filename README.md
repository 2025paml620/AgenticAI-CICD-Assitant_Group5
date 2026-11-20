# AgenticAI-CICD-Assitant_Group5

**Intelligent CI/CD Pipeline Failure Assistant** - Agentic AI (S2-25_PCAMZG519), Assignment 1 set-2, Group 5.

An assistant that investigates failed build-and-deployment pipelines. It inspects build logs, test results,
dependency information and recent code changes, then recommends the next troubleshooting step **without changing
code or deploying automatically**.

Six agents receive the *same* scenario and their decisions are compared side by side in a Streamlit dashboard:

| # | Agent | Decision mechanism | File | Owner |
|---|---|---|---|---|
| 1 | Simple Reflex | Fixed IF-THEN rules on current stage statuses | `agents/simple_reflex.py` | Member 1 |
| 2 | Model-Based Reflex | Remembers each pipeline's last state; uses transitions + recent changes | `agents/model_based.py` | Member 1 |
| 3 | Goal-Based | Plans diagnostic steps toward the goal "build, tests and deployment pass" | `agents/goal_based.py` | Member 1 |
| 4 | Utility-Based | Scores actions with `U(a) = 0.4P + 0.3E + 0.2S - 0.1C`, picks the max | `agents/utility_based.py` | Member 2 (Avinash) |
| 5 | Learning | Uses/updates success-failure counts per action (`data/experience.json`) | `agents/learning_agent.py` | Member 2 (Avinash) |
| 6 | LLM | Local Ollama model via LangChain, calls >= 2 diagnostic tools, grounds answer in tool output | `agents/llm_agent.py`, `tools/pipeline_tools.py` | Member 3 |

Every agent returns: failure category, supporting evidence, likely cause, recommended next step, reasoning and a
post-fix verification checklist.

## Architecture

```text
data/scenarios.json ──► scenario_loader.agent_input(id)  (deep copy, answer key removed)
                                   │
                    evaluation/runner.run_all()  ── same input, own copy per agent,
                                   │                errors/missing agents isolated
     ┌──────────┬──────────┬───────┴──┬───────────┬──────────┬────────────┐
  Simple     Model-     Goal-     Utility-    Learning     LLM (Ollama +
  Reflex     Based      Based     Based                    LangChain tools)
     └──────────┴──────────┴───────┬──┴───────────┴──────────┴────────────┘
                                   ▼
             agents/base_agent  (contract check + category normalisation)
                                   ▼
          evaluation/comparison (table, agreement, why-they-differ) ──► app.py (Streamlit)
                                                                    └─► docs/test_results/
```

```text
app.py                      Streamlit dashboard                         (Member 4)
scenario_loader.py          load scenarios; agent_input() hides answers (Member 4)
agents/base_agent.py        common contract, validation, categories     (Member 4)
agents/*.py                 the six agents                              (Members 1-3)
tools/pipeline_tools.py     LLM tools                                   (Member 3)
data/scenarios.json         shared scenarios A-E                        (Member 4)
data/experience.json        learning history                            (Member 2)
evaluation/runner.py        load + run all agents safely                (Member 4)
evaluation/comparison.py    comparison table/report (CLI)               (Member 4)
evaluation/evaluate_agents.py  evaluation metrics                       (Member 2)
tests/test_integration.py   end-to-end tests                            (Member 4)
scripts/capture_screenshots.py  dashboard screenshots                   (Member 4)
docs/screenshots/, docs/test_results/
```

## Scenarios

All scenarios live in `data/scenarios.json` with the same fields: `pipeline_status`, `build_logs`,
`test_results`, `dependencies`, `recent_changes`, `health_checks`, `deployment_logs`, plus an `expected` answer key
that is **removed before the data reaches any agent** (so the LLM tools cannot read it either).

| ID | Type | Scenario | Pipeline status | Expected category |
|---|---|---|---|---|
| A | critical | Unit tests fail after a change to `validate_payment()` | build ✅ tests ❌ deploy ⏸ | `unit_test` |
| B | critical | `pydantic==3.9.1` does not exist on the package index | build ❌ | `dependency` |
| C | critical | Deployed, but `/health` returns 503 (renamed env var) | build ✅ tests ✅ deploy ❌ | `deployment` |
| D | edge | Test stage timed out, logs truncated, no change info | build ✅ tests ⏱ | `unknown` (ask for more evidence) |
| E | normal | Healthy pipeline (control case) | all ✅ | `healthy` |

Scenario data is simulated for the demo; it is not taken from a real pipeline.

## Common agent interface

```python
class MyAgent:
    def decide(self, scenario: dict) -> dict:
        return {
            "agent": "My Agent",
            "failure_category": "unit_test",          # any label; mapped by canonical_category()
            "supporting_evidence": ["..."],
            "likely_cause": "...",
            "recommended_step": "...",
            "reasoning": "...",
            "verification_checklist": ["..."],
            # optional: tools_used, tool_calls (LLM); utility_score, candidate_scores (Utility);
            #           experience_used (Learning); plan (Goal-Based)
        }
```

The runner finds each agent class by name (`SimpleReflexAgent`, `ModelBasedAgent`, `GoalBasedAgent`,
`UtilityBasedAgent`, `LearningAgent`, `LLMAgent`) or, failing that, the first class in the module with a `decide()`
method. The LLM agent is created with `model=<name>` if its constructor accepts it (the UI also sets the
`OLLAMA_MODEL` environment variable). If the Learning agent exposes `record_outcome(failure_type, action, success)`,
the UI shows buttons to record **simulated** feedback.

## Setup

Python 3.10+ is required.

```bash
git clone https://github.com/2025paml620/AgenticAI-CICD-Assitant_Group5.git
cd AgenticAI-CICD-Assitant_Group5
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Ollama (for the LLM agent)

```bash
# install from https://ollama.com, then:
ollama pull qwen3:4b               # or any tool-calling model that fits your RAM
ollama serve                       # if it is not already running as a service
ollama list
```

## Run

### Windows / PowerShell quick start

Run from the repository folder. These commands use the project interpreter
directly, so virtual-environment activation is not required:

```powershell
cd C:\Users\amgka\workspace\Bits\Electives\agentic_ai
# Create the environment only if .venv does not already exist:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c constraints-windows.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Leave that terminal running and open **http://127.0.0.1:8501** in your browser.
Stop the server with Ctrl+C. If port 8501 is occupied, use `--server.port 8502`
and open http://127.0.0.1:8502 instead.

Test the flow in two steps:

1. Uncheck **LLM (Ollama + tools)**, choose scenario A, and click
   **Run all selected agents**. Check the comparison and agent decisions.
2. Start the Ollama application, run `ollama list` in another terminal, and
   run `ollama pull qwen3:4b` if the model is missing. Check the LLM agent again,
   enter `qwen3:4b` as the model, and rerun. Repeat for B and C. Expected categories
   are `unit_test`, `dependency`, and `deployment`. Expand the LLM decision and
   **Executed tools and returned evidence** to inspect actual calls; use
   **Download LLM diagnosis and full trace** to save the evidence.

If Ollama is not responding, run `ollama serve` in a separate terminal. If it
reports the address is already in use, Ollama is already serving.

Troubleshooting:

- **`streamlit` is not recognized / module not found:** use the full
  `.\.venv\Scripts\python.exe -m streamlit` command above and install requirements
  with that same interpreter. In PyCharm, select `.venv\Scripts\python.exe`.
- **NumPy/Pandas/PyArrow DLL import failure:** first stop every old Streamlit
  terminal with Ctrl+C and restart the app. A server started before package changes
  may retain old imports. Check fresh imports with
  `.\.venv\Scripts\python.exe -c "import pyarrow.compute, pandas; print('Imports OK')"`.
  The Windows constraints select the versions
  verified for this project. Repair the installation with
  `.\.venv\Scripts\python.exe -m pip install --force-reinstall -r requirements.txt -c constraints-windows.txt`.
  Windows previously blocked a binary from a newer NumPy wheel on this machine.
  If the fresh import still reports an Application Control block, retain the
  traceback and consult the device administrator; do not disable the policy.
- **Blank page / only a heading:** open the local URL above and check the terminal
  running Streamlit for its traceback. Start `app.py` with `-m streamlit run`,
  rather than running it as a plain Python script.
- **LLM error:** inspect the red error and partial tool trace. Confirm the model
  name matches `ollama list`, then reset agents and rerun. A failed diagnosis is
  reported as an error rather than counted as a successful comparison.

Verify locally:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_integration.py -q
# Optional: real Ollama acceptance for A, B and C (can take several minutes):
$env:RUN_LLM_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_integration.py -k llm_agent_calls -v
Remove-Item Env:RUN_LLM_TESTS
```

### Other environments

```bash
streamlit run app.py
```

1. Pick a scenario (A-E) in the sidebar and tick the agents to compare.
2. Click **Run all selected agents**.
3. Read the summary metrics, the comparison table, *Why do the decisions differ?*, and each agent's
   evidence, reasoning, checklist, utility scores, experience and LLM tool calls.

`http://localhost:8501/?scenario=C&run=1` opens scenario C and runs it straight away.
**Reset agents** clears the Model-Based agent's memory and reloads all agents.

Regenerate the comparison report in `docs/test_results/comparison_results.md`:

```bash
python -m evaluation.comparison            # with the LLM (Ollama must be running)
python -m evaluation.comparison --no-llm   # classical agents only
```

## Tests

```bash
pytest -v                                         # all tests; LLM test skipped
RUN_LLM_TESTS=1 pytest -v tests/test_integration.py   # also checks the LLM calls >= 2 tools
```

`tests/test_integration.py` checks that:
- scenarios A, B, C exist with the right expected category, and normal/critical/edge cases are covered;
- the answer key is hidden from agents and each agent gets its own copy of the same input;
- every classical agent returns the full output contract on all five scenarios and classifies A-C correctly;
- the edge case D is not classified with false confidence;
- a missing or crashing agent is reported but does not break the run or the UI;
- a comparison report can be produced for every scenario.

Agents that are not merged yet are **skipped**, not failed.

## Results

Saved in `docs/test_results/`: `comparison_results.md` (agent x scenario table and explanations) and
`pytest_integration.txt`. Screenshots per scenario are in `docs/screenshots/scenario_[A-E].png`.

> The current results and screenshots were generated with Members 1 and 2's branches merged
> (Simple Reflex, Model-Based, Goal-Based, Utility-Based). Learning and LLM show as *unavailable*. Re-run
> `python -m evaluation.comparison` and `scripts/capture_screenshots.py` after all branches are merged.

### Why the decisions differ (summary)

- **Simple Reflex** looks only at stage statuses, so its evidence is minimal ("tests failed") and its step is generic.
- **Model-Based** uses the same statuses but adds remembered state and recent changes, so on a repeat run it reports
  transitions, and its step points to comparing with the last good state.
- **Goal-Based** finds the earliest unmet goal (build → tests → deploy) and returns a multi-step plan.
- **Utility-Based** trusts the declared `failure_type` and picks the highest-scoring action from a catalogue; on the
  healthy case E it falls back to "collect more evidence" because there is no catalogue entry for a healthy run.
- **Learning** prefers the action with the best historical success rate, so its choice can change after feedback.
- **LLM** reads the actual logs/tests/changes through tools, so it can cite specifics (e.g. `pydantic==3.9.1`,
  `DATABASE_URL`) that the rule-based agents never look at.

## Member 3 — 2025paml617 (Abijith)

The local LLM agent implements `decide(scenario)` and the shared agent result
contract. Four read-only tools retrieve fixture evidence through `scenario_loader`;
the evaluator answer key and `failure_type` labels are never exposed to the model.
Pipeline status includes health checks/runtime logs; build logs include dependencies.

### Setup (PowerShell, Python 3.10+)

Install [Ollama for Windows](https://ollama.com/download/windows), then:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-llm.txt
ollama pull qwen3:4b
# Start `ollama serve` if the Ollama application is not already serving.
.\.venv\Scripts\python.exe -m agents.llm_agent --scenarios A B C --output evaluation/results/member3_live.json
.\.venv\Scripts\python.exe -m unittest tests.test_llm -v
```

Use `--model llama3.1:8b` or `OLLAMA_MODEL` to select another installed tool-capable
model. Choose a model that fits available RAM/VRAM; CPU execution may take longer.
The default HTTP timeout is 120 seconds per request; generation is capped at 2,048
tokens with a 16,384-token context. The loop has at most six rounds and eight calls
per round. Citation schemas constrain quotes and IDs to returned evidence; invalid
pairings get at most two correction attempts. Category choices are constrained by
observed pipeline stages. The live run checks compatibility by requiring actual
successful invocations of all four tools, rather than trusting registration alone.

### Output and validation

Results include failure category, supporting evidence, likely cause, recommended
step, reasoning, and a post-fix verification checklist. `tool_calls` records actual
model-requested names, arguments, IDs, returned evidence and errors; `tools_used`
contains only successfully executed tools. Structured answers must cite exact
returned evidence from at least two distinct tools (JSON projections are checked
against the returned keys and values). Stage/category contradictions,
fabricated citations, malformed output, missing evidence, unavailable models and
timeouts produce an explicit `status: error` / `unknown` result with the partial trace,
and a `recommended_step` that matches the cause (Ollama unreachable or model missing,
model without structured output or tool calling, or output that failed validation).
All four tools are collected so diagnosis can relate failures to recent changes. A
repeated call to a tool that already succeeded is answered from its first result and
is not added to the trace again.
An additional structured model review checks claims, causes, recommendations and
verification against returned evidence. This semantic check is probabilistic, so it
does not discard a diagnosis that already passed the citation and stage checks: the
result carries `verified: true` when the review confirms it, and `verified: false`
plus a `grounding_warning` (shown in the dashboard) when the review rejects it or
fails. Review the saved trace alongside an unverified recommendation.

Only fixture reads are exposed to the model. Recommendations are advisory; the
agent cannot run shell commands, modify code, or deploy. The optional CLI output
path writes a local report outside the model's tool interface.

Tests use scripted model responses for deterministic error-path coverage. To run
real local model acceptance for scenarios A/B/C:

```powershell
$env:RUN_OLLAMA_TESTS = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_llm -v
```

API references: [ChatOllama tool binding](https://reference.langchain.com/python/langchain-ollama/chat_models/ChatOllama/bind_tools).

### Recorded acceptance

The checked-in `evaluation/results/member3_live.json` contains real local
`qwen3:4b` runs: A = `unit_test` (8 calls), B = `dependency` (8 calls), and
C = `deployment` (5 calls). Every case invoked all four tools and passed citation,
stage consistency and semantic grounding checks. Counts include repeated calls
actually requested by the model. These are captured runs; model output can vary.
Automated regression validation: 152 tests passed, 1 opt-in live test skipped,
and 44 subtests passed. The live CLI acceptance above was executed separately.

## Known limitations

- Scenarios are simulated JSON fixtures, not a live CI system (GitHub Actions, Jenkins, etc.).
- Utility weights and probabilities are design assumptions, not measured success rates.
- "Step relevant" in the comparison is a keyword check against acceptable steps, not a human judgement.
- The classical agents mostly rely on stage statuses, so they classify A-C the same way; the differences are in
  evidence depth and next step rather than category.
- LLM output depends on the local model; small models can call the wrong tool or format the answer badly, and the
  runner reports that as an error or contract issue instead of hiding it.
- Learning feedback in the demo is simulated and labelled as such.

## Team contributions

| Member             | Branch                | Responsibility |
|--------------------|-----------------------|---|
| Member 1 - Shubhra | `2025paml620_Shubhra` | Simple Reflex, Model-Based Reflex, Goal-Based agents + tests |
| Member 2 - Avinash | `2025paml613_Avinash` | Utility-Based and Learning agents, experience data, evaluation |
| Member 3 - Abijith | `2025paml617_Abijith` | Ollama LLM agent, LangChain tools, LLM tests |
| Member 4 - Karthik | `2025paml541_Karthik` | Shared scenarios, common interface, runner, Streamlit UI, comparison, integration tests, README, screenshots |
