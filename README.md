# AgenticAI-CICD-Assitant_Group5
An assistant that investigates failed build-and-deployment pipelines. Inspect build logs, test results, dependency information, and recent code changes; recommend the next troubleshooting step without changing code or deploying automatically.

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
timeouts produce an explicit `status: error` / `unknown` result with the partial trace.
All four tools are collected so diagnosis can relate failures to recent changes.
An additional structured model review checks claims, causes, recommendations and
verification against returned evidence and rejects unsupported diagnoses. This
semantic check is probabilistic; review the saved trace alongside the recommendation.

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
