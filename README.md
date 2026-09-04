# PragyanAI SiliconAI — Agentic RTL Verification Platform

An open-source, auditable multi-agent platform for AI-assisted RTL/Verilog verification.

## Verification pipeline

1. RTL Analysis
2. Verification Planning
3. Test Generation
4. Testbench Generation
5. Simulation
6. Failure Analysis
7. Coverage
8. Red Team
9. Mutation
10. Formal (optional; no SymbiYosys dependency)
11. Judge

The platform separates:
- LLM reasoning: analysis, planning, generation, failure reasoning, repair, judgment
- deterministic EDA execution: Icarus Verilog
- orchestration: LangGraph
- observability: per-run JSONL + artifacts
- UI: Streamlit

## Repository

```text
PragyanAI-SiliconAI-Agentic-RTL-Verification/
├── .github/workflows/ci.yml
├── agents/
├── config/
├── core/
├── eda/
├── graph/
├── observability/
├── reports/
├── runtime/runs/.gitkeep
├── examples/
├── tests/
├── main_app.py
├── requirements.txt
├── packages.txt
├── .env.example
├── .gitignore
└── README.md
```

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install Icarus Verilog:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y iverilog

# macOS
brew install icarus-verilog
```

Set Groq:

```bash
export GROQ_API_KEY="your-key"
```

Run:

```bash
streamlit run main_app.py
```

The application also runs without an LLM key in `DEMO_MODE=true`, using deterministic fallback artifacts.

## Verification artifacts

Every run is stored under:

```text
runtime/runs/<run_id>/
```

including:

```text
run_manifest.json
agent_activity.jsonl
workflow.log
01_rtl_analysis/
02_planning/
03_test_generation/
04_testbench/
05_simulation/
06_failure_analysis/
07_coverage/
08_red_team/
09_mutation/
10_formal/
11_judge/
```

Never store API keys or secrets in run artifacts.

## GitHub / Streamlit Cloud

Use `main_app.py` as the Streamlit entry point.

Set `GROQ_API_KEY` in Streamlit Secrets.

`packages.txt` installs Icarus Verilog on Streamlit Cloud.

## Design principles

- Original RTL is never overwritten.
- EDA results are authoritative for compile/simulation.
- Optional formal verification must degrade gracefully.
- Each agent has a structured state contract.
- Every significant activity is logged.
- Generated code and reports are persisted as artifacts.
- No SymbiYosys dependency.
