# Agent comparison results

Generated 2026-11-15 15:46 by `python -m evaluation.comparison`.

## Scenario A: Unit Test Failure After Code Change (critical)

_A developer modified payment validation logic. The build succeeds but two unit tests fail._

Expected category: `unit_test` - Build passed, tests failed, and the failing tests target the recently modified validate_payment() function.

| Agent | Status | Failure category | Category correct | Recommended step | Step relevant | Extra | Time (s) |
|---|---|---|---|---|---|---|---|
| Simple Reflex | ok | unit_test_failure | True | Inspect failing test results and related recent code changes. | True |  | 0.0 |
| Model-Based Reflex | ok | unit_test_failure | True | Correlate failing test cases with recent code changes and prior test status. | True |  | 0.0 |
| Goal-Based | ok | unit_test_failure | True | Inspect failing tests and their error messages. | True | plan of 4 steps | 0.0 |
| Utility-Based | ok | unit_test | True | Inspect failed unit test results | True | utility=0.805 | 0.0 |
| Learning | unavailable | - | None | agents.learning_agent not found (not merged yet) | None |  | 0.0 |
| LLM (Ollama + tools) | unavailable | - | None | agents.llm_agent not found (not merged yet) | None |  | 0.0 |

- Agents run: 4; not compared: Learning, LLM (Ollama + tools)
- Category correct: 4/4; step relevant: 4/4
- Category agreement (majority `unit_test`): 4/4; distinct recommended steps: 4
- Same input to every agent and no agent mutated it: True

### Why the decisions differ

- **Simple Reflex** (Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.) -> `unit_test_failure`, which matches the expected `unit_test`. It recommends: *Inspect failing test results and related recent code changes.*
- **Model-Based Reflex** (Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.) -> `unit_test_failure`, which matches the expected `unit_test`. It recommends: *Correlate failing test cases with recent code changes and prior test status.*
- **Goal-Based** (Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.) -> `unit_test_failure`, which matches the expected `unit_test`. It recommends: *Inspect failing tests and their error messages.*
- **Utility-Based** (Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.) -> `unit_test`, which matches the expected `unit_test`. It recommends: *Inspect failed unit test results*
- **Learning** - not compared (unavailable: agents.learning_agent not found (not merged yet)).
- **LLM (Ollama + tools)** - not compared (unavailable: agents.llm_agent not found (not merged yet)).
- All agents agree on the category; they differ in *how* they reach it and in the specific next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence).

## Scenario B: Dependency Version Unavailable / Incompatible (critical)

_requirements.txt was updated to a library version that does not exist on the package index, so the build cannot resolve dependencies._

Expected category: `dependency` - Build failed at dependency resolution immediately after the pydantic version bump.

| Agent | Status | Failure category | Category correct | Recommended step | Step relevant | Extra | Time (s) |
|---|---|---|---|---|---|---|---|
| Simple Reflex | ok | dependency_or_build_failure | True | Inspect build logs and dependency resolution errors. | True |  | 0.0 |
| Model-Based Reflex | ok | dependency_or_build_failure | True | Compare current build logs and dependency versions with the last successful build. | True |  | 0.0 |
| Goal-Based | ok | dependency_or_build_failure | True | Inspect build logs and dependency resolution evidence. | True | plan of 4 steps | 0.0 |
| Utility-Based | ok | dependency | True | Check dependency versions and compatibility | True | utility=0.834 | 0.0 |
| Learning | unavailable | - | None | agents.learning_agent not found (not merged yet) | None |  | 0.0 |
| LLM (Ollama + tools) | unavailable | - | None | agents.llm_agent not found (not merged yet) | None |  | 0.0 |

- Agents run: 4; not compared: Learning, LLM (Ollama + tools)
- Category correct: 4/4; step relevant: 4/4
- Category agreement (majority `dependency`): 4/4; distinct recommended steps: 4
- Same input to every agent and no agent mutated it: True

### Why the decisions differ

- **Simple Reflex** (Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.) -> `dependency_or_build_failure`, which matches the expected `dependency`. It recommends: *Inspect build logs and dependency resolution errors.*
- **Model-Based Reflex** (Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.) -> `dependency_or_build_failure`, which matches the expected `dependency`. It recommends: *Compare current build logs and dependency versions with the last successful build.*
- **Goal-Based** (Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.) -> `dependency_or_build_failure`, which matches the expected `dependency`. It recommends: *Inspect build logs and dependency resolution evidence.*
- **Utility-Based** (Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.) -> `dependency`, which matches the expected `dependency`. It recommends: *Check dependency versions and compatibility*
- **Learning** - not compared (unavailable: agents.learning_agent not found (not merged yet)).
- **LLM (Ollama + tools)** - not compared (unavailable: agents.llm_agent not found (not merged yet)).
- All agents agree on the category; they differ in *how* they reach it and in the specific next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence).

## Scenario C: Deployment Health Check Failure After Release (critical)

_Build and tests pass and the release is deployed, but the service fails its readiness health checks._

Expected category: `deployment` - Build and tests passed; health checks return 503 and runtime logs show a missing environment variable after a config rename.

| Agent | Status | Failure category | Category correct | Recommended step | Step relevant | Extra | Time (s) |
|---|---|---|---|---|---|---|---|
| Simple Reflex | ok | deployment_health_failure | True | Inspect deployment logs and health-check results. | True |  | 0.0 |
| Model-Based Reflex | ok | deployment_health_failure | True | Compare deployment health checks and runtime configuration with the previous healthy state. | True |  | 0.0 |
| Goal-Based | ok | deployment_health_failure | True | Inspect deployment status and failed health checks. | True | plan of 4 steps | 0.0 |
| Utility-Based | ok | deployment | True | Inspect deployment health-check results | True | utility=0.834 | 0.0 |
| Learning | unavailable | - | None | agents.learning_agent not found (not merged yet) | None |  | 0.0 |
| LLM (Ollama + tools) | unavailable | - | None | agents.llm_agent not found (not merged yet) | None |  | 0.0 |

- Agents run: 4; not compared: Learning, LLM (Ollama + tools)
- Category correct: 4/4; step relevant: 4/4
- Category agreement (majority `deployment`): 4/4; distinct recommended steps: 4
- Same input to every agent and no agent mutated it: True

### Why the decisions differ

- **Simple Reflex** (Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.) -> `deployment_health_failure`, which matches the expected `deployment`. It recommends: *Inspect deployment logs and health-check results.*
- **Model-Based Reflex** (Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.) -> `deployment_health_failure`, which matches the expected `deployment`. It recommends: *Compare deployment health checks and runtime configuration with the previous healthy state.*
- **Goal-Based** (Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.) -> `deployment_health_failure`, which matches the expected `deployment`. It recommends: *Inspect deployment status and failed health checks.*
- **Utility-Based** (Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.) -> `deployment`, which matches the expected `deployment`. It recommends: *Inspect deployment health-check results*
- **Learning** - not compared (unavailable: agents.learning_agent not found (not merged yet)).
- **LLM (Ollama + tools)** - not compared (unavailable: agents.llm_agent not found (not merged yet)).
- All agents agree on the category; they differ in *how* they reach it and in the specific next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence).

## Scenario D: Ambiguous: Test Stage Timed Out With Incomplete Logs (edge)

_The test stage timed out. Logs are truncated, no test report was produced and the recent-change summary is unavailable. The failure type cannot be determined with confidence._

Expected category: `unknown` - Evidence is incomplete; a good agent should avoid over-confident classification and ask for more diagnostics (e.g. full logs, test report, rerun with verbose output).

| Agent | Status | Failure category | Category correct | Recommended step | Step relevant | Extra | Time (s) |
|---|---|---|---|---|---|---|---|
| Simple Reflex | ok | unknown | True | Collect build, test, and deployment statuses. | True |  | 0.0 |
| Model-Based Reflex | ok | unknown | True | Collect missing stage statuses and compare with the previous run. | True |  | 0.0 |
| Goal-Based | ok | unknown | True | Collect missing pipeline status and diagnostic evidence. | True | plan of 2 steps | 0.0 |
| Utility-Based | ok | unknown | True | Collect additional diagnostic evidence | True |  | 0.0 |
| Learning | unavailable | - | None | agents.learning_agent not found (not merged yet) | None |  | 0.0 |
| LLM (Ollama + tools) | unavailable | - | None | agents.llm_agent not found (not merged yet) | None |  | 0.0 |

- Agents run: 4; not compared: Learning, LLM (Ollama + tools)
- Category correct: 4/4; step relevant: 4/4
- Category agreement (majority `unknown`): 4/4; distinct recommended steps: 4
- Same input to every agent and no agent mutated it: True

### Why the decisions differ

- **Simple Reflex** (Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.) -> `unknown`, which matches the expected `unknown`. It recommends: *Collect build, test, and deployment statuses.*
- **Model-Based Reflex** (Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.) -> `unknown`, which matches the expected `unknown`. It recommends: *Collect missing stage statuses and compare with the previous run.*
- **Goal-Based** (Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.) -> `unknown`, which matches the expected `unknown`. It recommends: *Collect missing pipeline status and diagnostic evidence.*
- **Utility-Based** (Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.) -> `unknown`, which matches the expected `unknown`. It recommends: *Collect additional diagnostic evidence*
- **Learning** - not compared (unavailable: agents.learning_agent not found (not merged yet)).
- **LLM (Ollama + tools)** - not compared (unavailable: agents.llm_agent not found (not merged yet)).
- All agents agree on the category; they differ in *how* they reach it and in the specific next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence).

## Scenario E: Normal: Healthy Pipeline (Control Case) (normal)

_All stages pass and health checks succeed. Used as a control to confirm agents do not invent failures._

Expected category: `healthy` - No failure is present; the right recommendation is to continue monitoring.

| Agent | Status | Failure category | Category correct | Recommended step | Step relevant | Extra | Time (s) |
|---|---|---|---|---|---|---|---|
| Simple Reflex | ok | healthy | True | No troubleshooting needed; continue monitoring. | True |  | 0.0 |
| Model-Based Reflex | ok | healthy | True | Continue monitoring the pipeline. | True |  | 0.0 |
| Goal-Based | ok | healthy | True | Continue monitoring future pipeline runs. | True | plan of 1 steps | 0.0 |
| Utility-Based | ok | none | True | Collect additional diagnostic evidence | False |  | 0.0 |
| Learning | unavailable | - | None | agents.learning_agent not found (not merged yet) | None |  | 0.0 |
| LLM (Ollama + tools) | unavailable | - | None | agents.llm_agent not found (not merged yet) | None |  | 0.0 |

- Agents run: 4; not compared: Learning, LLM (Ollama + tools)
- Category correct: 4/4; step relevant: 3/4
- Category agreement (majority `healthy`): 4/4; distinct recommended steps: 4
- Same input to every agent and no agent mutated it: True

### Why the decisions differ

- **Simple Reflex** (Fixed IF-THEN rules on the current pipeline stage statuses only. No memory, goals or scores.) -> `healthy`, which matches the expected `healthy`. It recommends: *No troubleshooting needed; continue monitoring.*
- **Model-Based Reflex** (Keeps an internal model of each pipeline's last observed state and uses state transitions plus recent changes.) -> `healthy`, which matches the expected `healthy`. It recommends: *Continue monitoring the pipeline.*
- **Goal-Based** (Goal = build, tests and deployment all pass. Plans a diagnostic sequence for the earliest unmet prerequisite.) -> `healthy`, which matches the expected `healthy`. It recommends: *Continue monitoring future pipeline runs.*
- **Utility-Based** (Scores candidate actions with U(a) = 0.4P + 0.3E + 0.2S - 0.1C and picks the highest score.) -> `none`, which matches the expected `healthy`. It recommends: *Collect additional diagnostic evidence*
- **Learning** - not compared (unavailable: agents.learning_agent not found (not merged yet)).
- **LLM (Ollama + tools)** - not compared (unavailable: agents.llm_agent not found (not merged yet)).
- All agents agree on the category; they differ in *how* they reach it and in the specific next step (fixed rule vs. remembered state vs. plan vs. utility score vs. history vs. tool evidence).
