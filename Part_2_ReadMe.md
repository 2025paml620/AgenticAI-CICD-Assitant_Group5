# Member 2 — Utility-Based Agent, Learning Agent & Evaluation

**Project:** Intelligent CI/CD Pipeline Failure Assistant  
**Group:** Group 5  
**Owner:** Avinash  
**Git Branch:** `2025paml613_Avinash`  
**Status:** In Progress

---

## 1. Scope and Responsibilities

Member 2 is responsible for implementing:

1. Utility-Based Agent
2. Learning Agent
3. Experience history and persistence
4. Evaluation metrics and results
5. Unit tests for the Utility-Based and Learning Agents

The implementation must follow the shared architecture and input/output contract agreed by the group.

## 2. Project Structure Owned by Member 2

```text
agents/
    utility_based.py
    learning_agent.py

data/
    experience.json

evaluation/
    evaluate_agents.py

tests/
    test_utility.py
    test_learning.py

docs/
    evaluation.md

Part_2_ReadMe.md
```

## 3. Shared Project Requirements

All six agents must receive the same selected scenario data.

Required scenarios:

- Scenario A: Unit tests fail after a code change.
- Scenario B: Build fails because a dependency/version is unavailable or incompatible.
- Scenario C: Tests pass, but deployment health checks fail after release.

All agents must return the agreed common output fields:

- agent
- failure_category
- supporting_evidence
- likely_cause
- recommended_step
- reasoning
- verification_checklist

Additional fields specific to Member 2:

- utility_score
- candidate_scores
- experience_used

## 4. Utility-Based Agent

### 4.1 Objective

Evaluate multiple troubleshooting actions and recommend the action with the highest utility score.

### 4.2 Utility Formula

U(a) = 0.4P + 0.3E + 0.2S - 0.1C

Where:

- P = Estimated probability of resolving the issue
- E = Relevance of available evidence
- S = Safety of the diagnostic action
- C = Cost of performing the action

All input values are normalized between 0 and 1.

### 4.3 Implementation Decisions

- Maintain separate candidate actions for unit-test, dependency and deployment failures.
- Calculate the utility score for every applicable action.
- Select the action with the highest utility.
- Resolve ties deterministically using candidate order.
- Return the score of every candidate for transparency.
- Include supporting scenario evidence in the output.
- Do not execute code modifications or deployments.

### 4.4 Assumptions and Limitations

The initial success probabilities, evidence relevance, safety and cost values are illustrative estimates for simulated scenarios. They are not measured production statistics.

The first implementation uses predefined scores to establish a reproducible baseline.

---

## 5. Learning Agent

**Status:** Pending implementation.

Planned approach:

- Maintain experience counts by failure category and diagnostic action.
- Track successful and unsuccessful troubleshooting outcomes.
- Calculate historical success rates.
- Select actions based on available experience.
- Update history only after explicit feedback is provided.
- Persist experience in `data/experience.json`.
- Demonstrate recommendations before and after feedback.

The agent must not treat its own recommendation as a successful outcome.

---

## 6. Experience History

**Status:** Pending implementation.

The experience data will use JSON format.

Planned structure:

```json
{
  "unit_test": {
    "inspect_tests": {
      "success": 8,
      "failure": 2
    }
  }
}
```

The complete structure will include applicable actions for all three failure categories.

---

## 7. Evaluation Strategy

**Status:** Pending implementation.

Two agents will be evaluated across three scenarios, resulting in six primary agent-scenario test cases.

Planned metrics:

1. Failure classification correctness
2. Evidence relevance
3. Recommendation appropriateness
4. Explanation completeness
5. Learning before/after feedback

All evaluation results must come from actual execution. No fabricated performance scores will be reported.

---

## 8. Alignment Required from Other Members

### Member 1 — Classical Agents

- Confirm the agreed failure category names.
- Confirm how their three agents represent scenario evidence.
- Ensure output compatibility with the common agent contract.

### Member 3 — LLM Agent

- Confirm diagnostic action/tool naming where shared.
- Ensure evidence and failure categories remain consistent.
- Coordinate evaluation of evidence-grounded LLM recommendations.

### Member 4 — Integration and UI

- Share `agents/base_agent.py` and its interface once available.
- Share `data/scenarios.json` and confirm its exact field names.
- Confirm how the Streamlit runner invokes each agent.
- Confirm how optional fields such as `utility_score` and `experience_used` will be displayed.
- Coordinate the Learning Agent feedback mechanism in the UI.

These are pending coordination items, not blockers for the initial independent implementation.

---

## 9. Development and Git Workflow

Current branch: `2025paml613_Avinash`

Development will take place independently on this branch.

Planned commits:

- Implement Utility-Based Agent
- Add Utility-Based Agent tests
- Implement Learning Agent
- Add experience persistence
- Add Learning Agent tests
- Implement evaluation metrics
- Add evaluation documentation

All completed changes will be pushed to the existing branch and submitted through a pull request for review and merging into `main`.

---

## 10. Development Progress

| Component | Status |
|-----------|--------|
| Member 2 folder structure | Completed |
| Utility-Based Agent implementation | Completed |
| Utility-Based Agent manual execution (3 scenarios) | Completed |
| Utility-Based Agent automated tests (24 test cases) | Completed — 24 Passed |
| Learning Agent | Pending |
| Experience history and JSON persistence | Pending |
| Learning Agent automated tests | Pending |
| Evaluation framework | Pending |
| Evaluation metrics and results | Pending |
| Evaluation documentation (`docs/evaluation.md`) | Pending |
| Group integration | Pending |

---

## 11. Technical Decision Log

| Decision | Rationale |
|---|---|
| Use Python dictionaries for scenario input | Simple shared data contract |
| Use predefined utility candidate actions | Reproducible baseline |
| Normalize scores to 0–1 | Consistent utility calculations |
| Return all candidate scores | Explainable decisions |
| Use JSON for experience history | Simple persistent storage |
| Accept explicit feedback for learning | Prevent false learning outcomes |
| Use a common agent output schema | Easier integration with Streamlit |

---

## 12. Utility-Based Agent — Initial Execution Results

**Implementation status:** Successfully executed.

### 12.1 Execution Environment

- Python implementation: `agents/utility_based.py`
- Demonstration script: `tmp/run_utility_demo.py`
- Execution command: `python tmp/run_utility_demo.py`
- Scenarios tested: A, B and C

### 12.2 Execution Results

| Scenario | Selected Action | Utility Score |
|---|---|---:|
| A — Unit Test Failure | Inspect failed unit test results | 0.805 |
| B — Dependency Failure | Check dependency versions and compatibility | 0.834 |
| C — Deployment Health Failure | Inspect deployment health-check results | 0.834 |

### 12.3 Observations

**Scenario A:** The agent selected inspection of failed unit tests because this action achieved the highest utility score. The scenario showed that the build passed but two unit tests failed.

**Scenario B:** The agent selected dependency version and compatibility inspection. This was the highest-scoring action for the dependency resolution failure.

**Scenario C:** The agent selected deployment health-check inspection because the application passed its tests but returned HTTP 503 after deployment.

### 12.4 Validation Summary

- Three scenarios successfully processed.
- Nine candidate actions evaluated.
- Highest utility action selected in all three scenarios.
- Supporting evidence returned.
- Reasoning and candidate scores returned.
- Common agent response structure maintained.

### 12.5 Current Limitations

- Utility parameters are illustrative estimates.
- Utility values are predefined in the action catalog.
- In a real-world CI/CD troubleshooting platform, we would derive these values from operational data, historical incidents, monitoring systems, and engineering policies.
- Evidence relevance is not yet dynamically calculated.
- The agent recommends actions but does not execute fixes.
- Real-world CI/CD integration is outside the current implementation.

### 12.6 Next Steps

1. Implement automated utility calculation tests.
2. Validate missing and invalid inputs.
3. Implement the Learning Agent.
4. Add persistent experience history.
5. Demonstrate learning before and after feedback.
6. Evaluate both Member 2 agents across all three scenarios.

## 13. Utility-Based Agent — Automated Testing

### 13.1 Testing Framework and Environment

- Framework: pytest
- Python version: 3.12.9
- Pytest version: 9.2.0
- Test file: `tests/test_utility.py`
- Execution environment: Windows
- Execution command:

```powershell
python -m pytest tests/test_utility.py -v
```

### 13.2 Test Coverage

| Test ID | Test Description | Executions | Result |
|---|---|---:|---|
| UT-01 | Utility formula calculation | 1 | PASS |
| UT-02 | Best action selection | 3 | PASS |
| UT-03 | Failure classification | 3 | PASS |
| UT-04 | Standard output structure | 1 | PASS |
| UT-05 | Candidate score validation | 3 | PASS |
| UT-06 | Missing utility parameter | 1 | PASS |
| UT-07 | Invalid utility values | 6 | PASS |
| UT-08 | Unknown failure category | 1 | PASS |
| UT-09 | Invalid scenario input | 4 | PASS |
| UT-10 | Deterministic tie-breaking | 1 | PASS |
| **Total** | **10 test functions** | **24** | **ALL PASS** |

Note: Parameterized tests generate multiple individual executions from a single test function.

### 13.3 Actual Execution Results

Command:

```powershell
python -m pytest tests/test_utility.py -v
```

Actual terminal summary:

```text
collected 24 items

24 passed, 1 warning in 0.07s
```

### 13.4 Execution Analysis

All 24 individual test cases passed successfully.

The results confirm:

1. Correct mathematical utility calculation.
2. Correct highest-scoring action selection for all three scenarios.
3. Consistent failure category handling.
4. Compliance with the common agent output structure.
5. Valid candidate utility score ranges.
6. Proper handling of missing and invalid utility parameters.
7. Graceful handling of unsupported failure categories.
8. Rejection of invalid scenario input types.
9. Deterministic tie-breaking between equal-scoring actions.

### 13.5 Warning Observation

One non-blocking deprecation warning was reported by the installed AnyIO pytest plugin.

The warning concerns the deprecated `CallSpec2` alias and does not affect the successful execution of the Utility-Based Agent tests.

No test failures were reported.

### 13.6 Testing Summary

| Metric | Actual Result |
|---|---:|
| Test functions | 10 |
| Individual test executions | 24 |
| Passed | 24 |
| Failed | 0 |
| Warnings | 1 |
| Execution time | 0.07 seconds |

Automated test success rate: 100%.

### 13.7 Current Development Status

| Activity | Status |
|---|---|
| Utility-Based Agent implementation | Completed |
| Manual execution for three scenarios | Successful |
| Utility formula validation | Successful |
| Automated test implementation | Completed |
| Automated test execution | 24 passed |
| Learning Agent | Pending |
| Experience history | Pending |
| Evaluation framework | Pending |


**Document maintenance:** This document will be updated as implementation progresses, design decisions change, tests are executed and integration dependencies are resolved.
