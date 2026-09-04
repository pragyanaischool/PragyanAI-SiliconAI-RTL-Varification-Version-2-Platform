"""Streamlit UI for PragyanAI SiliconAI."""

from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from config.settings import (
    APP_NAME, APP_VERSION, DEFAULT_MAX_ITERATIONS,
    MUTATION_ENABLED_BY_DEFAULT, FORMAL_ENABLED_BY_DEFAULT,
)
from core.state import create_initial_state
from graph.workflow import run_workflow

st.set_page_config(page_title=APP_NAME, page_icon="🔬", layout="wide")

st.title("🔬 PragyanAI SiliconAI")
st.caption(f"Agentic RTL Verification Platform v{APP_VERSION}")

st.markdown(
    "**RTL Analysis • Planning • AI Test Generation • Testbench • Simulation • "
    "Failure Analysis • Coverage • Red Team • Mutation • Formal • Judge**"
)

with st.sidebar:
    st.header("Verification Controls")
    max_iterations = st.number_input("Max iterations", 1, 10, DEFAULT_MAX_ITERATIONS)
    run_mutation = st.checkbox("Run mutation", MUTATION_ENABLED_BY_DEFAULT)
    run_formal = st.checkbox("Run formal", FORMAL_ENABLED_BY_DEFAULT)

rtl = st.text_area(
    "RTL / Verilog",
    height=320,
    value="""module counter(input clk, input reset, output reg [3:0] count);
always @(posedge clk) begin
  if (reset) count <= 0;
  else count <= count + 1;
end
endmodule""",
)

spec = st.text_area("Specification", height=140)

if st.button("🚀 Run Agentic Verification", type="primary"):
    state = create_initial_state(
        rtl_code=rtl,
        specification=spec,
        max_iterations=int(max_iterations),
        run_mutation=run_mutation,
        run_formal=run_formal,
    )
    with st.spinner("Running verification agents..."):
        try:
            result = run_workflow(state)
            st.session_state["result"] = result
        except Exception as exc:
            st.exception(exc)

result = st.session_state.get("result")
if result:
    st.success(f"Final Verdict: {result.get('final_verdict', 'UNKNOWN')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Verification Score", result.get("verification_score", 0))
    c2.metric("Coverage", result.get("coverage", {}).get("score", 0))
    c3.metric("Mutation", result.get("mutation_score", 0))

    st.subheader("Agent Results")
    rows = [
        ("01", "RTL Analysis", bool(result.get("rtl_analysis"))),
        ("02", "Planning", bool(result.get("verification_plan"))),
        ("03", "Test Generation", bool(result.get("generated_tests"))),
        ("04", "Testbench", bool(result.get("testbench"))),
        ("05", "Simulation", bool(result.get("simulation_result"))),
        ("06", "Failure Analysis", bool(result.get("failure_analysis"))),
        ("07", "Coverage", bool(result.get("coverage"))),
        ("08", "Red Team", bool(result.get("red_team_results"))),
        ("09", "Mutation", bool(result.get("mutation_results"))),
        ("10", "Formal", bool(result.get("formal_result"))),
        ("11", "Judge", bool(result.get("judge_result"))),
    ]
    for no, name, done in rows:
        st.write(f"{'✅' if done else '⬜'} **{no} {name}**")

    st.subheader("Run Artifacts")
    if result.get("run_dir"):
        run_dir = Path(result["run_dir"])
        st.code(str(run_dir))
        if run_dir.exists():
            for path in sorted(run_dir.rglob("*")):
                if path.is_file():
                    st.write(f"📄 `{path.relative_to(run_dir)}`")
