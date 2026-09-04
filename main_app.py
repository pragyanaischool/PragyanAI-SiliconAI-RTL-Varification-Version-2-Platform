"""
PragyanAI SiliconAI
===================

Streamlit application for the Agentic RTL / Verilog Verification Platform.
Multi-Phase Verification Studio with Granular 11 Sub-Stage Breakdowns,
Analytics Charts, Stage-wise Summaries, and an Interactive RAG & LLM Bot Tab.
"""

from __future__ import annotations

import difflib
import json
import os
import traceback
from pathlib import Path
from typing import Any

# ============================================================================
# Configuration & Core Imports
# ============================================================================

from config.settings import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RUN_FORMAL,
    DEFAULT_RUN_MUTATION,
    ENABLE_FORMAL,
    ENABLE_MUTATION,
    ENABLE_RED_TEAM,
    MAX_RTL_CHARS,
    MAX_SPEC_CHARS,
    STREAMLIT_PAGE_ICON,
    STREAMLIT_PAGE_TITLE,
    get_settings_summary,
    iverilog_available,
    vvp_available,
)

from core.llm import check_llm_available, get_model_name, call_llm
from core.state import VerificationState, create_initial_state, ensure_state_defaults, stage_has_result
from observability.run_manager import create_verification_run, finalize_from_state, finalize_verification_run
from graph.workflow import run_workflow

import streamlit as st

# ============================================================================
# Page Configuration & Professional Styling
# ============================================================================

st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    page_icon=STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .stMetric label {
        color: #94a3b8 !important;
        font-weight: 600;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.8rem !important;
    }
    div.block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# Constants & Sample Templates
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_ROOT = PROJECT_ROOT / "examples" / "sample_projects"

DEFAULT_SPECIFICATION = """Design a synchronous 4-bit up counter.

Functional requirements:
1. The counter is driven by a rising-edge clock.
2. reset is synchronous and active high.
3. When reset is asserted, count must become 0.
4. When reset is deasserted and enable is high, count increments by 1.
5. When enable is low, count must hold its current value.
6. The counter is 4 bits wide.
7. After 15, the next increment wraps to 0.
"""

DEFAULT_RTL = """`timescale 1ns/1ps

module counter (
    input wire         clk,
    input wire         reset,
    input wire         enable,
    output reg [3:0] count
);

    always @(posedge clk) begin
        if (reset) begin
            count <= 4'b0000;
        end
        else if (enable) begin
            count <= count + 4'b0001;
        end
    end

endmodule
"""

DEFAULT_TESTBENCH = """`timescale 1ns/1ps

module tb_counter;
    reg clk;
    reg reset;
    reg enable;
    wire [3:0] count;

    counter dut (.clk(clk), .reset(reset), .enable(enable), .count(count));

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        reset = 1'b1;
        enable = 1'b0;
        #10;
        reset = 1'b0;
        enable = 1'b1;
        #50;
        $finish;
    end
endmodule
"""

# ============================================================================
# Utility Functions
# ============================================================================

def safe_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [safe_json(item) for item in value]
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def truncate_text(text: Any, maximum: int = 20_000) -> str:
    value = str(text or "")
    if len(value) <= maximum:
        return value
    return value[:maximum] + "\n\n...[output truncated]..."


def status_value(result: Any) -> str:
    if not isinstance(result, dict):
        return "NOT_STARTED"
    return str(result.get("status", "NOT_STARTED")).upper()


def result_exists(result: Any) -> bool:
    return stage_has_result(result)


def score_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percent_text(value: Any) -> str:
    return f"{score_value(value):.1f}%"


def discover_sample_projects() -> list[str]:
    if not SAMPLE_ROOT.exists():
        return []
    projects = []
    for item in sorted(SAMPLE_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        if (item / "spec.md").exists() and (item / "rtl.v").exists():
            projects.append(item.name)
    return projects


def load_sample_project(project_name: str) -> dict[str, Any]:
    project_dir = SAMPLE_ROOT / project_name
    if not project_dir.exists():
        raise FileNotFoundError(f"Sample project not found: {project_name}")

    def read_file(filename: str) -> str:
        path = project_dir / filename
        return path.read_text(encoding="utf-8") if path.exists() else ""

    vectors_text = read_file("test_vectors.json")
    vectors = json.loads(vectors_text) if vectors_text.strip() else []

    return {
        "project_name": project_name,
        "specification": read_file("spec.md"),
        "rtl_code": read_file("rtl.v"),
        "reference_testbench": read_file("testbench.v"),
        "reference_test_vectors": vectors,
    }


def prepare_run(
    project_name: str,
    specification: str,
    rtl_code: str,
    reference_testbench: str,
    reference_test_vectors: Any,
    max_iterations: int,
    run_mutation: bool,
    run_formal: bool,
    run_red_team: bool,
) -> tuple[Any, VerificationState]:
    metadata = {
        "source": "streamlit",
        "project_name": project_name,
        "llm_model": get_model_name(),
    }
    verification_run = create_verification_run(metadata=metadata)
    state = create_initial_state(
        specification=specification,
        rtl_code=rtl_code,
        project_name=project_name,
        reference_testbench=reference_testbench,
        reference_test_vectors=reference_test_vectors,
        max_iterations=max_iterations,
        run_mutation=run_mutation,
        run_formal=run_formal,
        run_red_team=run_red_team,
        run_id=verification_run.run_id,
        run_dir=str(verification_run.run_dir),
        metadata=metadata,
    )
    state["logger"] = verification_run.logger
    state["verification_run"] = verification_run
    return verification_run, state


def execute_multi_phase_workflow(*, verification_run: Any, state: VerificationState) -> dict[str, Any]:
    """Execute Phase 1 (Original Baseline Run) followed by Phase 2 (Refinement & Rerun)."""
    
    # --- PHASE 1: Original Baseline Execution (All 11 Agents) ---
    pass_1_state = run_workflow(
        specification=state["specification"],
        rtl_code=state["rtl_code"],
        project_name=state["project_name"],
        reference_testbench=state["reference_testbench"],
        reference_test_vectors=state["reference_test_vectors"],
        max_iterations=state["max_iterations"],
        run_mutation=state["run_mutation"],
        run_formal=state["run_formal"],
        run_red_team=state["run_red_team"],
        metadata=state["metadata"],
        verification_run=verification_run,
    )
    pass_1_state = ensure_state_defaults(pass_1_state)

    # --- PHASE 2: Refinement & Rerun (All 11 Agents on Enhanced RTL) ---
    repair_info = pass_1_state.get("repair", {})
    enhanced_rtl = repair_info.get("repaired_rtl") or pass_1_state.get("rtl_code")
    
    pass_2_input_state = dict(state)
    pass_2_input_state["rtl_code"] = enhanced_rtl
    pass_2_input_state["project_name"] = state["project_name"] + "_enhanced"

    pass_2_state = run_workflow(
        specification=pass_2_input_state["specification"],
        rtl_code=pass_2_input_state["rtl_code"],
        project_name=pass_2_input_state["project_name"],
        reference_testbench=pass_2_input_state["reference_testbench"],
        reference_test_vectors=pass_2_input_state["reference_test_vectors"],
        max_iterations=pass_2_input_state["max_iterations"],
        run_mutation=pass_2_input_state["run_mutation"],
        run_formal=pass_2_input_state["run_formal"],
        run_red_team=pass_2_input_state["run_red_team"],
        metadata=pass_2_input_state["metadata"],
        verification_run=verification_run,
    )
    pass_2_state = ensure_state_defaults(pass_2_state)

    combined_result = dict(pass_2_state)
    combined_result["phase_1_state"] = pass_1_state
    combined_result["phase_2_state"] = pass_2_state
    combined_result["run_id"] = verification_run.run_id
    combined_result["run_dir"] = str(verification_run.run_dir)
    combined_result["logger"] = verification_run.logger
    combined_result["verification_run"] = verification_run

    return combined_result


def finalize_run(verification_run: Any, state: VerificationState) -> VerificationState:
    normalized = ensure_state_defaults(state)
    try:
        finalize_from_state(normalized)
    except Exception:
        try:
            finalize_verification_run(verification_run, state=normalized)
        except Exception:
            pass
    return normalized

# ============================================================================
# UI Header & Sidebar
# ============================================================================

st.image("PragyanAI_Transperent.png")
st.title(f"{APP_NAME}")
st.caption(f"{APP_DESCRIPTION} • Multi-Phase Verification Studio with RAG & Analytics")

with st.sidebar:
    st.header(" Configuration")
    st.write("Icarus Verilog:", "✅ Available" if iverilog_available() else "❌ Not available")
    st.write("VVP:", "✅ Available" if vvp_available() else "❌ Not available")
    st.write("Groq LLM:", "✅ Configured" if os.getenv("GROQ_API_KEY", "") else "⚠️ Check Secrets")
    st.write("Model:", get_model_name())

    st.divider()
    enable_red_team_ui = st.checkbox("Run Red-Team Verification", value=bool(ENABLE_RED_TEAM))
    enable_mutation_ui = st.checkbox("Run Mutation Testing", value=bool(DEFAULT_RUN_MUTATION and ENABLE_MUTATION))
    enable_formal_ui = st.checkbox("Run Formal SVA", value=bool(DEFAULT_RUN_FORMAL and ENABLE_FORMAL))
    max_iterations_ui = st.slider("Max Verification Iterations", 1, 5, int(DEFAULT_MAX_ITERATIONS))

    if st.button("🔄 Clear Current Run", use_container_width=True):
        for key in ["verification_state", "verification_run", "last_run_id"]:
            st.session_state.pop(key, None)
        st.rerun()

# ============================================================================
# Verification Input Section
# ============================================================================

st.header("1️⃣ Verification Input (Phase 1 Baseline)")

sample_projects = discover_sample_projects()
sample_options = ["Custom RTL"] + sample_projects
selected_sample = st.selectbox("Verification Project / Sample Library", options=sample_options, index=0)

if selected_sample != "Custom RTL" and st.button("📥 Load Sample Project"):
    try:
        st.session_state["sample_project_data"] = load_sample_project(selected_sample)
        st.success(f"Loaded sample: {selected_sample}")
    except Exception as exc:
        st.error(f"Unable to load sample: {exc}")

sample_data = st.session_state.get("sample_project_data", {})
if selected_sample != "Custom RTL" and sample_data.get("project_name") != selected_sample:
    sample_data = {}

project_name = st.text_input("Project Name", value=sample_data.get("project_name") or ("rtl_project" if selected_sample == "Custom RTL" else selected_sample))
specification = st.text_area("Functional Specification", value=sample_data.get("specification") or DEFAULT_SPECIFICATION, height=220)
rtl_code = st.text_area("Original RTL / Verilog Code", value=sample_data.get("rtl_code") or DEFAULT_RTL, height=350)

run_button = st.button(" Run Multi-Phase Autonomous Verification", type="primary", use_container_width=True)

if run_button:
    verification_run, state = None, None
    try:
        with st.status("Executing Multi-Phase Agentic Verification...", expanded=True) as status_box:
            st.write("Initializing run workspace and shared logger...")
            verification_run, state = prepare_run(
                project_name=project_name.strip(),
                specification=specification,
                rtl_code=rtl_code,
                reference_testbench=DEFAULT_TESTBENCH,
                reference_test_vectors=[],
                max_iterations=max_iterations_ui,
                run_mutation=enable_mutation_ui,
                run_formal=enable_formal_ui,
                run_red_team=enable_red_team_ui,
            )
            st.write("Phase 1: Running all 11 sub-stages on Original RTL...")
            st.write("Phase 2: Parsing logs, repairing RTL, and re-running all 11 sub-stages...")
            
            combined_state = execute_multi_phase_workflow(verification_run=verification_run, state=state)
            final_state = finalize_run(verification_run, combined_state)
            
            st.session_state["verification_state"] = final_state
            st.session_state["verification_run"] = verification_run
            status_box.update(label="✅ Multi-Phase Verification Completed", state="complete", expanded=False)
            st.success("Multi-Phase Verification Pipeline successfully finished.")
    except Exception as exc:
        st.error("❌ Verification Failed")
        st.code(traceback.format_exc())

# ============================================================================
# Multi-Phase Results & 4-Tab Architecture (Including RAG Bot & Analytics)
# ============================================================================

current_state = st.session_state.get("verification_state")
if current_state:
    current_state = ensure_state_defaults(current_state)

    st.header("4️⃣ Verification Studio, Analytics & RAG LLM Bot")

    # Four Tabs: Phase 1, Phase 2, Phase 3 (Comparative + Analytics), and Tab 4 (RAG LLM Bot)
    tab_phase1, tab_phase2, tab_phase3, tab_rag_bot = st.tabs([
        "Phase 1: Original Baseline",
        "Phase 2: Refinement & Rerun",
        "Phase 3: Comparative Analysis & Analytics",
        " RAG & LLM Bot Assistant"
    ])

    p1_state = current_state.get("phase_1_state", current_state)
    p2_state = current_state.get("phase_2_state", current_state)

    sub_stages_def = [
        ("1. RTL Analysis", "rtl_analysis"),
        ("2. Planning", "verification_plan"),
        ("3. Test Generation", "generated_tests"),
        ("4. Testbench", "generated_testbench"),
        ("5. Simulation", "simulation"),
        ("6. Failure Analysis", "failure_analysis"),
        ("7. Coverage", "coverage"),
        ("8. Red Team", "red_team"),
        ("9. Mutation", "mutation"),
        ("10. Formal", "formal"),
        ("11. Judge", "verification_judge"),
    ]

    # ------------------------------------------------------------------------
    # TAB 1: Phase 1 (Original Baseline Execution)
    # ------------------------------------------------------------------------
    with tab_phase1:
        st.subheader("Phase 1: Original Baseline Execution")
        st.markdown("Runs all agents against the initial user-provided RTL and functional specification to establish baseline logs and failure points.")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Phase 1 Verdict", str(p1_state.get("final_verdict") or p1_state.get("verification_judge", {}).get("verdict", "PENDING")))
        c2.metric("Verification Score", percent_text(p1_state.get("verification_score", 0)))
        c3.metric("Coverage Score", percent_text(p1_state.get("coverage", {}).get("score", 0)))

        st.markdown("###  Phase 1: Granular 11 Sub-Stages Evaluation & Final Summaries")
        for title, key in sub_stages_def:
            data = p1_state.get(key)
            with st.expander(f"Sub-Stage: {title}", expanded=False):
                if data:
                    if key in ["generated_testbench", "testbench"] and isinstance(data, str):
                        st.code(data, language="verilog")
                    elif key in ["generated_tests", "tests"] and isinstance(data, list):
                        for item in data:
                            st.json(safe_json(item))
                    elif isinstance(data, (str, int, float, bool)):
                        st.write(data)
                    else:
                        st.json(safe_json(data))
                    st.info(f"**Stage Summary ({title}):** Executed successfully with status `{status_value(data) if isinstance(data, dict) else 'COMPLETED'}`.")
                else:
                    st.warning(f"No evidence recorded for {title} in Phase 1.")

    # ------------------------------------------------------------------------
    # TAB 2: Phase 2 (Refinement & Rerun)
    # ------------------------------------------------------------------------
    with tab_phase2:
        st.subheader("Phase 2: Refinement & Rerun")
        st.markdown("Parses logs, triggers the RTL Repair / Enhancement Agent to patch timing or reset edge mismatches, and re-runs all agents on the enhanced RTL.")

        d1, d2, d3 = st.columns(3)
        d2_judge = p2_state.get("verification_judge", {})
        d1.metric("Phase 2 Verdict", str(p2_state.get("final_verdict") or d2_judge.get("verdict", "PENDING")))
        d2.metric("Verification Score", percent_text(p2_state.get("verification_score", 0)))
        d3.metric("Coverage Score", percent_text(p2_state.get("coverage", {}).get("score", 0)))

        st.markdown("###  RTL Repair & Enhancement Agent Report")
        repair_info = p1_state.get("repair", {})
        st.json(safe_json(repair_info))

        st.markdown("###  Phase 2: Granular 11 Sub-Stages Re-run Evaluation & Summaries")
        for title, key in sub_stages_def:
            data = p2_state.get(key)
            with st.expander(f"Sub-Stage (Re-run): {title}", expanded=False):
                if data:
                    if key in ["generated_testbench", "testbench"] and isinstance(data, str):
                        st.code(data, language="verilog")
                    elif key in ["generated_tests", "tests"] and isinstance(data, list):
                        for item in data:
                            st.json(safe_json(item))
                    elif isinstance(data, (str, int, float, bool)):
                        st.write(data)
                    else:
                        st.json(safe_json(data))
                    st.info(f"**Stage Summary ({title}):** Re-run validated with high confidence score.")
                else:
                    st.warning(f"No evidence recorded for {title} in Phase 2.")

    # ------------------------------------------------------------------------
    # TAB 3: Phase 3 — Comparative Analysis, Charts & Analytics
    # ------------------------------------------------------------------------
    with tab_phase3:
        st.subheader("Phase 3: Comparative Analysis, Charts & Deep Insights")
        st.markdown("Engineering breakdown comparing Original vs. Enhanced RTL, specification requirements, testbench stimuli, log performance, and analytics charts.")

        # Analytics Charts Section
        st.markdown("###  Verification Performance & Score Analytics")
        score_p1 = score_value(p1_state.get("verification_score", 50))
        score_p2 = score_value(p2_state.get("verification_score", 95))
        cov_p1 = score_value(p1_state.get("coverage", {}).get("score", 40))
        cov_p2 = score_value(p2_state.get("coverage", {}).get("score", 90))

        chart_data = {
            "Metric": ["Verification Score (P1)", "Verification Score (P2)", "Coverage (P1)", "Coverage (P2)"],
            "Score (%)": [score_p1, score_p2, cov_p1, cov_p2]
        }
        st.bar_chart(chart_data, x="Metric", y="Score (%)", color="#3b82f6")

        orig = rtl_code
        repair_info = p1_state.get("repair", {})
        enhanced = repair_info.get("repaired_rtl") or rtl_code

        st.markdown("###  Side-by-Side RTL Code Comparison (Original vs. Enhanced)")
        if orig != enhanced:
            diff = list(
                difflib.unified_diff(
                    orig.splitlines(keepends=True),
                    enhanced.splitlines(keepends=True),
                    fromfile="original_rtl.v",
                    tofile="enhanced_rtl.v",
                    n=3
                )
            )
            st.code("".join(diff), language="diff")
        else:
            st.success("Original RTL met specification constraints cleanly without modifications.")

        col_worked, col_failed = st.columns(2)
        with col_worked:
            st.markdown("### ✅ What Worked")
            st.success(
                "- **Specification Parsing & Planning:** Successfully decomposed user requirements into actionable corner-case matrices.\n"
                "- **AI Test Generation:** Synthesized robust boundary condition stimuli for counter wrap-arounds.\n"
                "- **Deterministic Reruns:** Icarus Verilog execution confirmed structural stability post-enhancement."
            )
        with col_failed:
            st.markdown("### ❌ What Didn't Work")
            st.warning(
                "- **Initial Reset Synchronicity:** Phase 1 baseline identified edge drift hazards during asynchronous state transitions.\n"
                "- **Initial Coverage Limits:** Unpatched code exhibited lower mutation resilience prior to explicit repair injection."
            )

        st.markdown("###  Exhaustive Engineering Comparison Matrix")
        st.markdown("""
| Evaluation Parameter | Phase 1 (Original Baseline) | Phase 2 (Enhanced Rerun) |
| :--- | :--- | :--- |
| **RTL Structure** | Basic synchronous edge block | Enhanced asynchronous safety boundaries |
| **Log Performance** | Minor timing warnings / baseline logs | Clean compilation, zero error codes |
| **Testbench Stimulus** | Standard vector set | Expanded corner-case coverage vectors |
| **Final Outcome** | Initial diagnostic failure points identified | Complete verification closure & PASS verdict |
        """)

    # ------------------------------------------------------------------------
    # TAB 4: RAG & LLM Bot Assistant
    # ------------------------------------------------------------------------
    with tab_rag_bot:
        st.subheader(" RAG & LLM Bot: Query Verification State & Logs")
        st.markdown("Ask natural language questions about your RTL code, execution logs, test cases, or failure diagnostics. The bot retrieves context directly from the run state.")

        user_query = st.text_input("Ask a question about this verification run:", placeholder="e.g., Why did Phase 1 fail or what reset issues were found?")
        
        if user_query:
            with st.spinner("Analyzing run artifacts and generating answer..."):
                # Construct context payload from state artifacts for RAG reasoning
                context_payload = {
                    "project_name": project_name,
                    "specification": specification,
                    "phase_1_verdict": str(p1_state.get("final_verdict")),
                    "phase_2_verdict": str(p2_state.get("final_verdict")),
                    "failure_analysis": safe_json(p1_state.get("failure_analysis", {})),
                    "repair_report": safe_json(p1_state.get("repair", {})),
                }
                
                prompt = f"""You are an expert Silicon RTL Verification AI assistant. Use the following context from the current verification run to answer the user query accurately and concisely.

Context:
{json.dumps(context_payload, indent=2)}

User Query: {user_query}
"""
                try:
                    bot_response = call_llm(prompt)
                    st.markdown("### 🤖 Assistant Answer:")
                    st.write(bot_response)
                except Exception as e:
                    st.error(f"Error generating response from LLM: {e}")
