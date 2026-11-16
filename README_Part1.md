# Member 1 Contribution — Classical Decision-Making Agents

**Project:** Intelligent CI/CD Pipeline Failure Assistant  
**Repository:** `AgenticAI-CICD-Assistant_Group5`  
**Member 1:** Shubhra Shrivastava  
**Responsibility:** Classical AI agents, unit tests, and shared-scenario integration testing  
**Status:** Three agent modules implemented; Member 1 unit tests have shown passing results locally. Member 4 integration-test execution and full Streamlit verification require confirmation from the local test output.

## 1. Project context and objective

The project investigates simulated CI/CD failures and recommends the next safe troubleshooting step. Member 1 implements **three distinct classical agents** that inspect the same pipeline scenario but use different decision-making methods. All agents are advisory only: they **do not change code, run fixes, or deploy software**.

## 2. Files and ownership

| File | Contribution |
|---|---|
| `agents/simple_reflex.py` | Stateless, fixed condition–action rules for pipeline stage failures. |
| `agents/model_based.py` | Remembers previous observations by pipeline, identifies unchanged states/transitions, and supports reset. |
| `agents/goal_based.py` | Recommends a safe diagnostic plan to reach a healthy build → test → deployment state. |
| `tests/test_classical.py` | Independent unit tests for the three agents (10 test methods). |
| `tests/test_integration.py` | **Member 4-owned** integration tests reused by Member 1 to validate shared scenarios, scenario loading, and (where implemented) runner integration. Member 1 did not create a separate integration-test file. |
| `docs/README_Member1.md` | This contribution and testing guide (recommended repository destination). |

**Shared dependencies (Member 4):** `data/scenarios.json`, `scenario_loader.py`, `evaluation/runner.py`, `evaluation/comparison.py`, and `app.py`. These are **not** Member 1's deliverables.

## 3. Implementation summary

### 3.1 Simple Reflex Agent

- Reads the current pipeline stage statuses, supporting nested `pipeline_status` and top-level stage fields.
- Uses fixed IF–THEN rules and stage priority (build before tests before deployment).
- Classifies unit-test, dependency/build, deployment, healthy, or unknown situations.
- Returns a diagnostic recommendation and explanation based on current evidence only.
- **No memory, learning, or planning** is performed.

### 3.2 Model-Based Reflex Agent

- Maintains an in-memory observation history indexed by `pipeline_id` (or scenario `id`).
- Compares current and previous stage statuses, distinguishing first observation, unchanged status, and state transition.
- Uses recent-change context when available.
- Provides `reset()` to clear in-memory state for a new test/demo.
- **Limitation:** State is not persistent across process restarts and does not learn from outcome feedback.

### 3.3 Goal-Based Agent

- Uses the target state: build, tests, and deployment all pass.
- Chooses a safe, predefined troubleshooting plan for the earliest unmet stage.
- Returns a `plan` list and uses its first step as `recommended_step`.
- Adds verification steps; plans are recommendations, not executable automation.
- **Limitation:** The agent does not perform general-purpose search or automatic remediation.

## 4. Shared input and output contract

All three agents implement:

```python
result = agent.decide(scenario_dict)
```

Example input (a simplified representation of Member 4's scenario schema):

```python
scenario = {
    "id": "A",
    "pipeline_id": "payments-service",
    "pipeline_status": {
        "build": "passed",
        "tests": "failed",
        "deployment": "not_started"
    },
    "recent_changes": ["Modified payment validation logic"]
}
```

Common result fields:

- `agent` — name of the decision-making agent
- `failure_category` — agent-specific category string
- `supporting_evidence` — evidence items used in diagnosis
- `likely_cause` — likely reason for the failure
- `recommended_step` — first recommended troubleshooting action
- `reasoning` — explanation of the decision
- `verification_checklist` — post-fix checks to recommend
- `plan` — extra list returned by the Goal-Based Agent

The input scenario should not be modified by the agent.

### Category normalization for Member 4's evaluation

| Member 1 category | Canonical shared category |
|---|---|
| `unit_test_failure` | `unit_test` |
| `dependency_or_build_failure` | `dependency` |
| `deployment_health_failure` | `deployment` |
| `unknown` | `unknown` |
| `healthy` | `healthy` |

The additional Member 1 integration test explicitly maps these categories. **Confirm the same mapping in `evaluation/runner.py` before claiming full dashboard integration.**

## 5. Shared scenarios covered

Member 4's `data/scenarios.json` defines five simulated cases:

| ID | Scenario | Expected canonical category | Why it matters |
|---|---|---|---|
| A | Unit tests fail after code change | `unit_test` | Detect a regression after a successful build. |
| B | Dependency/version unavailable | `dependency` | Diagnose build-stage dependency resolution failure. |
| C | Deployment health checks fail | `deployment` | Identify a runtime/health-check issue after successful tests. |
| D | Test stage times out with incomplete logs | `unknown` | Avoid unsupported certainty when evidence is missing. |
| E | Healthy pipeline | `healthy` | Ensure agents do not invent a failure. |

The first three are required project failure cases; D is an edge case and E is a normal control case.

## 6. Testing strategy

### 6.1 Unit testing — Member 1 agent behavior

`tests/test_classical.py` checks:

1. Classification across five pipeline conditions for each agent.
2. Required output fields and types.
3. Input immutability.
4. Support for flat stage-status fields.
5. Build failure priority.
6. Model-Based Agent memory for repeated observations.
7. State transition detection.
8. Isolation of state across pipeline IDs.
9. Memory reset.
10. Safe, nonempty Goal-Based troubleshooting plans.

From the **repository root**, run:

```powershell
python -m unittest discover -s tests -p "test_classical.py" -v
```

### 6.2 Integration testing using Member 4's existing file

**Actual file used:** `tests/test_integration.py` (created and maintained by Member 4). Member 1 did **not** use or add `test_member1_integration.py`.

The visible portion of Member 4's test file checks:

- Required shared scenario IDs and expected failure categories.
- Presence of normal, critical, and edge-case scenarios.
- Correct pipeline statuses for scenarios A, B, and C.
- Removal of the `expected` answer from the agent input and isolation of the input copy.

Other integration tests may be present in that file; consult the complete local file and pytest output for the full test count and coverage. Passing this file alone does **not** prove that all three Member 1 agents are integrated into the runner unless tests explicitly exercise them.

From the repository root, run:

```powershell
python -m pytest tests/test_integration.py -v
```

### 6.3 Run unit and integration tests together

```powershell
python -m pytest tests/test_classical.py tests/test_integration.py -v
```

To run every repository test:

```powershell
python -m pytest tests/ -v
```

If needed, install pytest with `python -m pip install pytest`.

### 6.4 Validation evidence and status

- **Unit testing:** The provided VS Code screenshot shows Member 1's `test_classical.py` methods reporting `ok` for the visible cases. The complete final test summary should be saved as evidence.
- **Integration testing:** Member 4's `test_integration.py` has been copied into the local repository, but no complete pytest execution result was provided for that file. Its passing status and test count are **not yet confirmed**.
- **Agent–scenario coverage:** The target is 3 classical agents × 5 shared scenarios = **15 classifications**. Confirm these through the runner or an explicit test before reporting 15/15 as passed.
- **End-to-end UI:** Streamlit execution and screenshots remain pending verification.

Do not report the earlier **16-test isolated result** as the outcome of this repository: it involved a different, additional integration-test file that was not used here.

## 7. Manual runner and Streamlit integration checklist — pending local verification

1. Pull the merged Member 4 changes after committing your own work.
2. Confirm `data/scenarios.json`, `scenario_loader.py`, `evaluation/runner.py`, `evaluation/comparison.py`, and `app.py` exist.
3. Verify `evaluation/runner.py` loads all three Member 1 agents and normalizes their categories correctly.
4. Run `tests/test_classical.py` and Member 4's `tests/test_integration.py`, and save the actual pytest summary.
5. Start the app from the project root:

   ```powershell
   python -m streamlit run app.py
   ```

6. In the sidebar, select **only** Simple Reflex, Model-Based Reflex, and Goal-Based agents.
7. Run scenarios **A, B, C, D, E** and inspect the comparison table, category, evidence, reasoning, recommended next step, and verification checklist.
8. Repeat one scenario to demonstrate Model-Based memory, then use **Reset agents (clear memory)** and verify fresh state.
9. Capture terminal test output and UI screenshots in `docs/screenshots/member1/`.
10. Record any integration errors and coordinate fixes with Member 4 before marking full integration complete.

The app also supports LLM and learning agents, but their implementation and testing belong to other members.

## 8. Git workflow

```powershell
git status
git branch --show-current
git add agents/simple_reflex.py agents/model_based.py agents/goal_based.py
git add tests/test_classical.py
git add docs/README_Part1.md
git commit -m "test: document and validate Member 1 classical agents"
```

## 9. Contribution summary

**Shubhra Shrivastava (Member 1)** I have implemented and documented three classical decision-making agents: Simple Reflex, Model-Based Reflex, and Goal-Based. The modules expose a consistent `decide(scenario)` interface, return evidence-based advisory recommendations, and demonstrate distinct decision mechanisms. Member 1 unit-test cases have shown passing output locally, while Member 4's existing `tests/test_integration.py` is the shared integration-test suite. The next milestone is to run that suite, verify all three agents through the merged runner and Streamlit dashboard, and capture final test results and screenshots.
