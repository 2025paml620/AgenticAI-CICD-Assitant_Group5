# Member 2 — Evaluation Report

**Project:** Intelligent CI/CD Pipeline Failure Assistant  
**Owner:** Member 2 — Avinash  
**Report status:** Finalized — shared-loader migration and local Windows evaluation verified  
**Evaluation date:** 15 November 2026  
**Scenario source:** Member 4's `scenario_loader.py` and `data/scenarios.json`

## 1. Objective

Evaluate the Utility-Based Agent and Learning Agent using the shared CI/CD scenarios supplied by Member 4. The evaluation measures failure classification correctness, evidence relevance, recommendation appropriateness and explanation completeness. Learning behaviour is evaluated separately through controlled simulated feedback.

The primary assessment covers the three required failure scenarios (A, B and C). Scenarios D and E are included as additional ambiguous/edge and healthy/control checks.

## 2. Evaluation inputs, package layout and safeguards

### 2.1 Inputs

- Shared scenario loader: root-level `scenario_loader.py` (provided by Member 4).
- Scenario fixture: `data/scenarios.json` (Scenarios A–E).
- Shared interface: `agents/base_agent.py`.
- Utility-Based Agent: `agents/utility_based.py`.
- Learning Agent: `agents/learning_agent.py`.
- Learning history: `data/experience.json` (not modified by baseline evaluation or the controlled learning experiment).

### 2.2 Evaluation package layout

```text
scenario_loader.py                 # Shared loader supplied by Member 4

evaluation/
    metrics.py
    evaluate_agents.py
    results/
        member2_evaluation.json

tests/
    test_evaluation.py
    test_evaluate_agents.py

docs/
    evaluation.md
```

The evaluator uses the shared loader rather than maintaining a second scenario adapter. The relevant public functions are:

- `load_scenarios()` — returns full scenario copies, including evaluator-only `expected` data.
- `scenario_ids()` — returns the configured scenario identifiers.
- `agent_input(scenario_id)` — returns a deep-copied scenario with `expected` removed.
- `expected_for(scenario_id)` — returns the answer-key block for evaluator use only.

The earlier evaluator-side `evaluation/scenario_adapter.py` has been removed. Scenario loading and answer-key separation now use Member 4's shared implementation.

### 2.3 Safeguards and fairness

- The evaluator obtains expected outcomes using `expected_for()` and never passes them to an agent.
- Each agent receives a separate deep copy obtained through `agent_input()` for the same scenario.
- The evaluator checks that the scenario input remains unchanged after each decision.
- Agent outputs are checked using `validate_result()` from `agents/base_agent.py`.
- Failure categories are compared after normalization using `canonical_category()`.
- Every Learning Agent baseline case uses a fresh zero-count temporary experience file. Baseline cases do not share learned feedback.
- The before/after learning experiment uses a separate temporary history file.
- The project's real `data/experience.json` is not modified by the evaluator.
- Agent errors and contract-validation problems are retained in the JSON results rather than silently discarded.
- The evaluator reads the configured scenario fixture through `scenario_loader.py`; a separate `--scenarios` override is not provided. An optional `--output` argument can change the results JSON destination.

## 3. Evaluation matrix

| Evaluation group | Scenarios | Agents | Executions |
|---|---|---|---:|
| Primary | A, B, C | Utility-Based, Learning | 6 |
| Robustness/control | D, E | Utility-Based, Learning | 4 |
| **Total** | **A–E** | **2 agents** | **10** |

## 4. Metric definitions

### 4.1 Failure classification correctness

The agent's `failure_category` and the scenario's `expected.failure_category` are normalized using `canonical_category()` from `agents/base_agent.py`.

`classification score = 1` when the canonical categories match; otherwise `0`.

Accuracy is the mean of this binary score. Primary scenarios A–C and robustness/control scenarios D–E are summarized separately.

### 4.2 Evidence relevance

The evaluator compares normalized logical evidence sources in the agent's `supporting_evidence` against a scenario-specific reference mapping maintained in `evaluation/metrics.py`.

- `Precision = TP / (TP + FP)`
- `Recall = TP / (TP + FN)`
- `F1 = 2 × Precision × Recall / (Precision + Recall)`

Aliases are normalized: `dependencies` and `dependency_info` count as one logical source; `deployment_logs` and `runtime_logs` count as one logical source.

The reference mapping is an evaluator-authored rubric derived from scenario details and rationale. It is a judgement-based reference, not a field supplied directly by the scenario fixture. The raw expected sources, predicted sources and TP/FP/FN counts are retained per evaluation for auditability.

Aggregate precision, recall and F1 in this report are **macro-averages of the per-scenario metric values**. They are not calculated by pooling all TP/FP/FN counts into one micro-average.

### 4.3 Recommendation appropriateness

The evaluator compares `recommended_step` with `expected.acceptable_next_steps`. Matching is case-insensitive, token-based and applies light suffix normalization for simple variants such as `failed`/`failing` and `log`/`logs`.

A recommendation is marked appropriate when every token in at least one acceptable phrase is present in the recommendation after normalization. The matched acceptable phrases are retained in the JSON result.

This deterministic text-based rubric supports repeatable checks. It does not prove that a recommendation would resolve a real production incident; semantic review remains useful.

### 4.4 Explanation completeness

A four-point rubric assigns one point for each check:

1. A meaningful `likely_cause` is present.
2. Informative `reasoning` is present.
3. The reasoning contains a decision rationale (selected action/score/evidence/history, or an appropriate fallback rationale for healthy/unknown scenarios).
4. A non-empty, actionable `verification_checklist` is present.

The percentage is `score / 4 × 100`. This measures observable structure and rationale completeness, not the full semantic correctness of the explanation.

### 4.5 Learning before/after feedback

A separate Scenario A experiment starts with zero-count experience, records the baseline recommendation, supplies simulated unsuccessful feedback for the selected action and simulated successful feedback for an alternative action, and records the next recommendation and persisted temporary history.

A recommendation change is reported separately from recommendation appropriateness. Simulated feedback is not represented as production incident history.

## 5. Actual evaluation results — local Windows project run

The evaluator was executed from the Windows project repository after migrating to Member 4's shared `scenario_loader.py`.

**Execution environment:**

| Parameter | Actual value |
|---|---|
| Operating system | Windows 11 |
| Python | 3.12.9 |
| Pytest | 9.2.0 |
| Scenario fixture | `data/scenarios.json`, accessed through root `scenario_loader.py` |
| Evaluations executed | 10 |
| Agent output contracts valid | 10/10 |
| Scenario inputs unchanged | 10/10 |
| Agent execution errors | 0 |

The evaluator command was:

```powershell
python -m evaluation.evaluate_agents
```

The command completed successfully and wrote results to `evaluation/results/member2_evaluation.json`.

### 5.1 Summary by agent — all five scenarios

| Agent | Cases | Classification accuracy | Mean evidence precision | Mean evidence recall | Mean evidence F1 | Recommendation appropriateness | Explanation completeness |
|---|---:|---:|---:|---:|---:|---:|---:|
| Utility-Based | 5 | 100.00% | 83.43% | 100.00% | 90.68% | 100.00% | 100.00% |
| Learning-Based | 5 | 100.00% | 83.43% | 100.00% | 90.68% | 100.00% | 100.00% |

### 5.2 Primary and robustness results

| Agent | Group | Cases | Classification accuracy | Mean evidence precision | Mean evidence recall | Mean evidence F1 | Recommendation appropriateness | Explanation completeness |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Utility-Based | Primary A–C | 3 | 100.00% | 81.90% | 100.00% | 90.03% | 100.00% | 100.00% |
| Utility-Based | Robustness D–E | 2 | 100.00% | 85.72% | 100.00% | 91.66% | 100.00% | 100.00% |
| Learning-Based | Primary A–C | 3 | 100.00% | 81.90% | 100.00% | 90.03% | 100.00% | 100.00% |
| Learning-Based | Robustness D–E | 2 | 100.00% | 85.72% | 100.00% | 91.66% | 100.00% | 100.00% |

### 5.3 Per-scenario results

Both agents produced the same baseline metric values for each scenario in this run. Per-scenario evidence scores were:

| Scenario | Expected category | Evidence precision | Evidence recall | Evidence F1 | Classification | Recommendation | Explanation |
|---|---|---:|---:|---:|---|---|---|
| A | `unit_test` | 80.00% | 100.00% | 88.89% | Correct | Appropriate | 100.00% |
| B | `dependency` | 80.00% | 100.00% | 88.89% | Correct | Appropriate | 100.00% |
| C | `deployment` | 85.71% | 100.00% | 92.31% | Correct | Appropriate | 100.00% |
| D | `unknown` | 100.00% | 100.00% | 100.00% | Correct | Appropriate | 100.00% |
| E | `healthy` | 71.43% | 100.00% | 83.33% | Correct | Appropriate | 100.00% |

### 5.4 Actual recommendations

| Scenario | Agent | Canonical category | Recommended next step |
|---|---|---|---|
| A | Utility-Based Agent | `unit_test` | Inspect failed unit test results |
| A | Learning-Based Agent | `unit_test` | Inspect failed unit test results |
| B | Utility-Based Agent | `dependency` | Check dependency versions and compatibility |
| B | Learning-Based Agent | `dependency` | Check dependency versions and compatibility |
| C | Utility-Based Agent | `deployment` | Inspect deployment health-check results |
| C | Learning-Based Agent | `deployment` | Inspect deployment health-check results |
| D | Utility-Based Agent | `unknown` | Collect complete pipeline logs and diagnostic reports, then rerun the affected pipeline stage with sufficient logging. |
| D | Learning-Based Agent | `unknown` | Collect complete pipeline logs and the missing diagnostic report, then rerun the affected stage with sufficient logging. |
| E | Utility-Based Agent | `healthy` | No troubleshooting action required; continue monitoring pipeline health. |
| E | Learning-Based Agent | `healthy` | No troubleshooting action required; continue monitoring pipeline health. |

### 5.5 Observations and interpretation

- Both agents classified all five scenarios correctly and produced contract-valid outputs for all ten runs.
- Both agents achieved 100% recommendation appropriateness under the documented acceptable-phrase matching rubric.
- Both agents received 100% explanation-completeness scores under the four-check structural rubric.
- Mean evidence recall was 100%, indicating that every source in the evaluator's scenario-specific evidence reference was included by the agents.
- Mean evidence precision was 83.43%; therefore some returned evidence sources were not part of the evaluator's manually defined relevant-source set for a given scenario. The JSON preserves the false-positive sources so the team can inspect them.
- The two agents have identical baseline aggregate metrics in this run. They also select the same recommendations for A, B and C under zero-history Learning Agent baselines. This is an observation about the current fixtures, evidence extraction and baseline prior; it does not mean the two decision algorithms are equivalent.
- The evaluator's evidence mapping and recommendation phrase matching are transparent, deterministic rubrics. They should not be interpreted as independent human judgement or production success measurements.

## 6. Learning before/after experiment

A separate controlled experiment was executed for Scenario A.

| Stage | Action | Feedback | Persisted counts after update |
|---|---|---|---|
| Baseline | `inspect_tests` | None | `inspect_tests`: 0 success / 0 failure |
| Feedback 1 | `inspect_tests` | Simulated unsuccessful | `inspect_tests`: 0 success / 1 failure |
| Feedback 2 | `inspect_changes` | Simulated successful | `inspect_changes`: 1 success / 0 failure |
| After feedback | `inspect_changes` | Recommendation changed | Selected action: `inspect_changes` |

**Recorded experiment results:**

- Scenario: A
- Feedback type: simulated
- Baseline action: `inspect_tests` — Inspect failed unit test results
- After-feedback action: `inspect_changes` — Review recently modified code
- Recommendation changed: Yes
- After-feedback recommendation appropriate: Yes
- Experience file: Temporary; the project's `data/experience.json` was not modified.

The experiment demonstrates that explicit feedback updates persistent experience and can change a subsequent recommendation. It does not establish real-world incident-resolution performance.

## 7. Automated test results

### 7.1 Evaluation-specific tests

Command:

```powershell
python -m pytest tests/test_evaluation.py tests/test_evaluate_agents.py -v
```

Actual Windows terminal summary after shared-loader migration:

```text
collected 20 items

20 passed, 1 warning in 0.49s
```

These 20 tests cover shared scenario loading, expected-data separation, independent deep copies, duplicate scenario IDs, expected-block validation, canonical category handling, evidence aliases and F1, recommendation matching, explanation scoring, expected-data isolation, ten-case evaluation execution, fresh Learning Agent baselines, learning feedback behaviour, primary/robustness summaries and evaluator configuration.

### 7.2 Complete Member 2 test suite

Command:

```powershell
python -m pytest -v
```

Actual Windows terminal summary after shared-loader migration:

```text
collected 129 items

129 passed, 1 warning in 2.27s
```

| Test suite | Executions | Passed | Failed |
|---|---:|---:|---:|
| Utility-Based Agent | 38 | 38 | 0 |
| Learning Agent | 71 | 71 | 0 |
| Evaluation framework | 20 | 20 | 0 |
| **Total** | **129** | **129** | **0** |

The combined run reported one non-blocking AnyIO pytest-plugin deprecation warning concerning the `CallSpec2` alias. It did not affect test execution.

### 7.3 Evaluation execution

Command:

```powershell
python -m evaluation.evaluate_agents
```

Actual console result:

```text
Member 2 evaluation completed.
Evaluations: 10
```

The run completed five scenarios for each agent and printed the per-agent summaries and the before/after learning experiment. Results were saved to:

```text
evaluation/results/member2_evaluation.json
```

The JSON records evaluation metadata, the shared scenario loader, the primary and robustness group summaries, individual agent outputs, contract checks, evidence metric components and the learning experiment.

## 8. Limitations and future improvements

- The five scenarios are synthetic fixtures, not production pipeline incidents.
- The evidence reference mapping is manually defined from scenario content and rationale. It should be reviewed if scenario fixtures change.
- Evidence precision is below 100% because the agents currently include some populated but scenario-irrelevant evidence fields. The recorded false positives can guide more selective evidence collection in a future change.
- Recommendation appropriateness uses deterministic phrase matching. It cannot fully assess semantic quality or prove that an action resolves a real incident.
- Explanation completeness measures four observable response properties; human review is still useful for semantic correctness.
- Both agents returned the same supporting evidence sources in this baseline run, so their evidence metrics are equal. More discriminating scenarios or more selective evidence extraction may reveal differences.
- Learning baseline evaluations begin with zero-count temporary histories. The separate learning experiment uses simulated feedback; no production feedback dataset is available.
- Results should not be generalized beyond the five supplied fixtures.

## 9. Reproduction and usage instructions

The root-level `scenario_loader.py` is the authoritative shared loader and reads `data/scenarios.json`. Do not maintain a separate evaluator-side scenario adapter.

Run evaluator-specific tests:

```powershell
python -m pytest tests/test_evaluation.py tests/test_evaluate_agents.py -v
```

Run the evaluation:

```powershell
python -m evaluation.evaluate_agents
```

To change only the results destination, use the evaluator's supported `--output` option:

```powershell
python -m evaluation.evaluate_agents --output evaluation/results/member2_evaluation.json
```

Run the complete Member 2 test suite:

```powershell
python -m pytest -v
```

The evaluator writes raw outputs and metric details to `evaluation/results/member2_evaluation.json`. The shared loader supplies scenario copies to agents through `agent_input()` and retains answer-key access through `expected_for()` for evaluator use only.

### 9.1 Documentation consolidation

The separate root-level `README_EVALUATION.md` was originally generated as a package quick-start guide. Its useful content—package structure, execution commands, evaluation safeguards and metric overview—has been incorporated into this report. To avoid maintaining duplicate instructions, `docs/evaluation.md` is the single evaluation reference; the separate `README_EVALUATION.md` file is no longer required and can be removed from the repository after this report is copied into place.

### 9.2 Evaluation safeguards at a glance

- `expected` is evaluator-only and is removed from agent input by `scenario_loader.agent_input()`.
- Agents receive independent deep copies of the same scenario.
- Learning baselines use fresh temporary experience files.
- The feedback experiment uses a separate temporary experience file.
- The actual project experience history is not overwritten by evaluation.
- Raw recommendations, metric components, contract results and errors are stored in JSON.

## 10. Conclusion

After migrating to Member 4's shared `scenario_loader.py`, the local Windows evaluation completed ten agent-scenario executions: six primary cases across A–C and four robustness/control cases across D–E. All ten outputs passed the shared output contract, the scenarios remained unchanged, and no agent execution errors were recorded.

Both agents achieved 100% classification accuracy, recommendation appropriateness and explanation completeness under the documented evaluation rubrics. Mean evidence F1 was 90.68%. The controlled Scenario A experiment demonstrated a recommendation change after simulated feedback. The evaluation-specific test suite passed all 20 tests, and the complete Member 2 test suite passed all 129 tests.

These results complete the initial Member 2 evaluation deliverable for the supplied synthetic fixtures. Full group integration, Streamlit end-to-end validation and any additional scenario coverage remain team-level activities.
