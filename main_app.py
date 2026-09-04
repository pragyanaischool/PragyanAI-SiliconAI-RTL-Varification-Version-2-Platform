"""
PragyanAI SiliconAI
===================

Streamlit UI for the Agentic RTL / Verilog Verification Platform.

Pipeline
--------

Specification
      ↓
RTL Analyzer
      ↓
Verification Planner
      ↓
Test Generator
      ↓
Testbench Generator
      ↓
Simulation
      ↓
Failure Analyzer
      ↓
Coverage
      ↓
Red Team
      ↓
Mutation
      ↓
Formal
      ↓
Verification Judge
      ↓
Final Verdict

Run:

    streamlit run main_app.py

Environment:

    GROQ_API_KEY=...

Optional:

    GROQ_MODEL=llama-3.3-70b-versatile
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from config.settings import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RUN_FORMAL,
    DEFAULT_RUN_MUTATION,
    ENABLE_RED_TEAM,
    GROQ_API_KEY,
    GROQ_MODEL,
    MAX_RTL_CHARS,
    MAX_SPEC_CHARS,
    STREAMLIT_PAGE_ICON,
    STREAMLIT_PAGE_TITLE,
    get_settings_summary,
    iverilog_available,
    vvp_available,
)

from graph.workflow import run_workflow


# =============================================================================
# STREAMLIT PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=STREAMLIT_PAGE_TITLE,
    page_icon=STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# APPLICATION PATHS
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parent

EXAMPLES_DIR = (
    ROOT_DIR
    / "examples"
)

SAMPLE_PROJECTS_DIR = (
    EXAMPLES_DIR
    / "sample_projects"
)

RUNTIME_DIR = (
    ROOT_DIR
    / "runtime"
)

RUNS_DIR = (
    RUNTIME_DIR
    / "runs"
)


# =============================================================================
# SESSION STATE
# =============================================================================

DEFAULT_SESSION_VALUES: Dict[str, Any] = {
    "project_name": "custom_rtl",
    "specification": "",
    "rtl_code": "",
    "reference_testbench": "",
    "reference_test_vectors": [],
    "last_state": None,
    "last_run_id": None,
    "verification_started": False,
}


for key, value in DEFAULT_SESSION_VALUES.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def safe_read_text(
    path: Path,
    default: str = "",
) -> str:
    """
    Safely read a UTF-8 text file.
    """

    try:

        if not path.exists():
            return default

        return path.read_text(
            encoding="utf-8"
        )

    except Exception:

        return default


def safe_read_json(
    path: Path,
    default: Any = None,
) -> Any:
    """
    Safely read a JSON file.
    """

    try:

        if not path.exists():
            return default

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            return json.load(handle)

    except Exception:

        return default


def list_sample_projects() -> Dict[str, Path]:
    """
    Discover available sample projects.

    A sample project is considered valid when it contains at least:

        spec.md
        rtl.v
    """

    projects: Dict[str, Path] = {}

    if not SAMPLE_PROJECTS_DIR.exists():
        return projects

    try:

        directories = sorted(
            SAMPLE_PROJECTS_DIR.iterdir(),
            key=lambda item: item.name.lower(),
        )

    except Exception:

        return projects

    for directory in directories:

        if not directory.is_dir():
            continue

        if directory.name.startswith("."):
            continue

        specification_file = (
            directory
            / "spec.md"
        )

        rtl_file = (
            directory
            / "rtl.v"
        )

        if (
            specification_file.exists()
            and rtl_file.exists()
        ):

            projects[
                directory.name
            ] = directory

    return projects


def load_sample_project(
    project_dir: Path,
) -> Dict[str, Any]:
    """
    Load all supported files from a sample project.
    """

    return {
        "name": project_dir.name,

        "specification": safe_read_text(
            project_dir / "spec.md"
        ),

        "rtl": safe_read_text(
            project_dir / "rtl.v"
        ),

        "testbench": safe_read_text(
            project_dir / "testbench.v"
        ),

        "test_vectors": safe_read_json(
            project_dir / "test_vectors.json",
            default=[],
        ),

        "readme": safe_read_text(
            project_dir / "README.md"
        ),
    }


def format_verdict(
    verdict: Any,
) -> str:
    """
    Normalize final verdict.
    """

    if verdict is None:
        return "NOT_RUN"

    text = str(verdict).strip()

    if not text:
        return "NOT_RUN"

    return text.upper()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Convert a value to float safely.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


def render_code(
    code: Any,
    language: str = "text",
) -> None:
    """
    Render source code safely.
    """

    if code is None:
        st.info("No code available.")
        return

    text = str(code)

    if not text.strip():

        st.info("No code available.")
        return

    st.code(
        text,
        language=language,
    )


def render_json(
    value: Any,
) -> None:
    """
    Render arbitrary Python data as JSON.
    """

    if value is None:

        st.info("No data available.")
        return

    try:

        st.json(value)

    except Exception:

        st.code(
            str(value)
        )


def count_items(
    value: Any,
) -> int:
    """
    Return a useful count for lists/dictionaries.
    """

    if isinstance(
        value,
        (list, tuple, set),
    ):

        return len(value)

    if isinstance(
        value,
        dict,
    ):

        return len(value)

    if value is None:
        return 0

    return 1


def get_run_directory_from_state(
    state: Dict[str, Any],
) -> Optional[Path]:
    """
    Get the run directory from VerificationRun.
    """

    verification_run = state.get(
        "verification_run"
    )

    if verification_run is not None:

        run_dir = getattr(
            verification_run,
            "run_dir",
            None,
        )

        if run_dir:

            return Path(
                run_dir
            )

    run_id = state.get(
        "run_id"
    )

    if run_id:

        candidate = (
            RUNS_DIR
            / str(run_id)
        )

        if candidate.exists():
            return candidate

    return None


def read_activity_log(
    run_dir: Optional[Path],
) -> str:
    """
    Read the structured activity log for a run.
    """

    if run_dir is None:
        return ""

    path = (
        run_dir
        / "agent_activity.jsonl"
    )

    if not path.exists():
        return ""

    return safe_read_text(
        path
    )


def read_workflow_log(
    run_dir: Optional[Path],
) -> str:
    """
    Read human-readable workflow log.
    """

    if run_dir is None:
        return ""

    path = (
        run_dir
        / "workflow.log"
    )

    if not path.exists():
        return ""

    return safe_read_text(
        path
    )


def load_manifest(
    run_dir: Optional[Path],
    filename: str,
) -> Dict[str, Any]:
    """
    Load a JSON manifest from a run directory.
    """

    if run_dir is None:
        return {}

    value = safe_read_json(
        run_dir / filename,
        default={},
    )

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


# =============================================================================
# HEADER
# =============================================================================

st.title(
    f"🧪 {APP_NAME}"
)

st.caption(
    f"Agentic RTL / Verilog Verification Platform • v{APP_VERSION}"
)

st.markdown(
    """
### Autonomous Verification Pipeline

**Specification → RTL Analysis → Verification Planning → Test Generation
→ Testbench Generation → Simulation → Failure Analysis → Coverage
→ Red Team → Mutation → Formal → Verification Judge**
"""
)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:

    st.header(
        "⚙️ Verification Configuration"
    )

    # -------------------------------------------------------------------------
    # Sample project
    # -------------------------------------------------------------------------

    sample_projects = list_sample_projects()

    sample_options: List[str] = [
        "Custom RTL"
    ]

    sample_options.extend(
        list(
            sample_projects.keys()
        )
    )

    selected_sample = st.selectbox(
        "Sample Project",
        sample_options,
        key="selected_sample_project",
    )

    if st.button(
        "📦 Load Sample",
        use_container_width=True,
    ):

        if selected_sample == "Custom RTL":

            st.session_state.project_name = (
                "custom_rtl"
            )

            st.session_state.specification = ""
            st.session_state.rtl_code = ""
            st.session_state.reference_testbench = ""
            st.session_state.reference_test_vectors = []

            st.success(
                "Custom RTL mode selected."
            )

        else:

            project_dir = (
                sample_projects[
                    selected_sample
                ]
            )

            sample = load_sample_project(
                project_dir
            )

            st.session_state.project_name = (
                sample["name"]
            )

            st.session_state.specification = (
                sample["specification"]
            )

            st.session_state.rtl_code = (
                sample["rtl"]
            )

            st.session_state.reference_testbench = (
                sample["testbench"]
            )

            st.session_state.reference_test_vectors = (
                sample["test_vectors"]
            )

            st.success(
                f"Loaded sample: {selected_sample}"
            )

    # -------------------------------------------------------------------------
    # Iteration settings
    # -------------------------------------------------------------------------

    st.subheader(
        "Verification Loop"
    )

    max_iterations = st.number_input(
        "Maximum Iterations",
        min_value=1,
        max_value=10,
        value=int(
            DEFAULT_MAX_ITERATIONS
        ),
        step=1,
        help=(
            "Maximum number of verification iterations."
        ),
    )

    # -------------------------------------------------------------------------
    # Optional verification stages
    # -------------------------------------------------------------------------

    st.subheader(
        "Verification Engines"
    )

    run_red_team = st.checkbox(
        "🛡️ Red-Team Testing",
        value=bool(
            ENABLE_RED_TEAM
        ),
    )

    run_mutation = st.checkbox(
        "🧬 Mutation Testing",
        value=bool(
            DEFAULT_RUN_MUTATION
        ),
    )

    run_formal = st.checkbox(
        "🔬 Formal Verification",
        value=bool(
            DEFAULT_RUN_FORMAL
        ),
        help=(
            "Formal backend is optional and disabled by default."
        ),
    )

    # -------------------------------------------------------------------------
    # Tool status
    # -------------------------------------------------------------------------

    st.divider()

    st.subheader(
        "EDA Tool Status"
    )

    if iverilog_available():

        st.success(
            "✓ Icarus Verilog available"
        )

    else:

        st.warning(
            "⚠ Icarus Verilog unavailable"
        )

    if vvp_available():

        st.success(
            "✓ VVP available"
        )

    else:

        st.warning(
            "⚠ VVP unavailable"
        )

    # -------------------------------------------------------------------------
    # LLM status
    # -------------------------------------------------------------------------

    st.subheader(
        "AI Engine"
    )

    if GROQ_API_KEY:

        st.success(
            "✓ Groq API configured"
        )

        st.caption(
            f"Model: {GROQ_MODEL}"
        )

    else:

        st.warning(
            "Groq API key not configured."
        )

        st.caption(
            "The platform can still run deterministic stages "
            "when supported by the installed agents."
        )

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    st.divider()

    if st.button(
        "🔧 Show Configuration",
        use_container_width=True,
    ):

        st.json(
            get_settings_summary()
        )


# =============================================================================
# INPUT SECTION
# =============================================================================

st.header(
    "1️⃣ Verification Input"
)

input_left, input_right = st.columns(
    2
)


with input_left:

    project_name = st.text_input(
        "Project Name",
        value=st.session_state.project_name,
    )

    specification = st.text_area(
        "Functional Specification",
        value=st.session_state.specification,
        height=360,
        max_chars=MAX_SPEC_CHARS,
        placeholder=(
            "Describe the expected behavior of the RTL..."
        ),
    )


with input_right:

    rtl_code = st.text_area(
        "RTL / Verilog Code",
        value=st.session_state.rtl_code,
        height=360,
        max_chars=MAX_RTL_CHARS,
        placeholder=(
            "Paste Verilog/SystemVerilog RTL here..."
        ),
    )


# =============================================================================
# REFERENCE TESTBENCH
# =============================================================================

st.header(
    "2️⃣ Reference Verification Assets"
)

with st.expander(
    "Reference Testbench and Test Vectors",
    expanded=False,
):

    reference_left, reference_right = st.columns(
        2
    )

    with reference_left:

        reference_testbench = st.text_area(
            "Reference Testbench",
            value=st.session_state.reference_testbench,
            height=280,
            placeholder=(
                "Optional reference testbench..."
            ),
        )

    with reference_right:

        reference_vectors_default = json.dumps(
            st.session_state.reference_test_vectors,
            indent=2,
        )

        reference_vectors_text = st.text_area(
            "Reference Test Vectors JSON",
            value=reference_vectors_default,
            height=280,
            placeholder=(
                '[{"name": "reset", "expected": "..."}]'
            ),
        )

        try:

            reference_test_vectors = json.loads(
                reference_vectors_text
            )

            if not isinstance(
                reference_test_vectors,
                list,
            ):

                reference_test_vectors = [
                    reference_test_vectors
                ]

        except Exception:

            reference_test_vectors = []

            st.warning(
                "Reference test vectors JSON is invalid."
            )


# =============================================================================
# INPUT SUMMARY
# =============================================================================

with st.expander(
    "Input Summary"
):

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(
        4
    )

    with summary_col1:

        st.metric(
            "Specification",
            f"{len(specification):,} chars",
        )

    with summary_col2:

        st.metric(
            "RTL",
            f"{len(rtl_code):,} chars",
        )

    with summary_col3:

        st.metric(
            "Reference TB",
            f"{len(reference_testbench):,} chars",
        )

    with summary_col4:

        st.metric(
            "Reference Vectors",
            count_items(
                reference_test_vectors
            ),
        )


# =============================================================================
# START VERIFICATION
# =============================================================================

st.header(
    "3️⃣ Agentic Verification"
)

start_verification = st.button(
    "🚀 START FULL VERIFICATION",
    type="primary",
    use_container_width=True,
)


if start_verification:

    # -------------------------------------------------------------------------
    # Save current input to session.
    # -------------------------------------------------------------------------

    st.session_state.project_name = (
        project_name
    )

    st.session_state.specification = (
        specification
    )

    st.session_state.rtl_code = (
        rtl_code
    )

    st.session_state.reference_testbench = (
        reference_testbench
    )

    st.session_state.reference_test_vectors = (
        reference_test_vectors
    )

    st.session_state.verification_started = True

    # -------------------------------------------------------------------------
    # Validate inputs.
    # -------------------------------------------------------------------------

    if not specification.strip():

        st.error(
            "❌ Functional specification is required."
        )

        st.stop()

    if not rtl_code.strip():

        st.error(
            "❌ RTL / Verilog code is required."
        )

        st.stop()

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    run_metadata = {
        "source": "streamlit",
        "project_name": project_name,
        "rtl_chars": len(rtl_code),
        "specification_chars": len(
            specification
        ),
        "reference_testbench": bool(
            reference_testbench.strip()
        ),
        "reference_test_vectors": count_items(
            reference_test_vectors
        ),
    }

    # -------------------------------------------------------------------------
    # Run workflow.
    # -------------------------------------------------------------------------

    progress_placeholder = st.empty()

    try:

        with st.status(
            "🚀 Starting Agentic RTL Verification...",
            expanded=True,
        ) as verification_status:

            progress_placeholder.info(
                "Creating one verification run and shared logger..."
            )

            verification_status.write(
                "✓ VerificationRun created"
            )

            verification_status.write(
                "✓ Shared ActivityLogger initialized"
            )

            verification_status.write(
                "→ RTL Analyzer"
            )

            state = run_workflow(
                specification=specification,
                rtl_code=rtl_code,
                project_name=project_name,
                reference_testbench=reference_testbench,
                reference_test_vectors=reference_test_vectors,
                max_iterations=int(
                    max_iterations
                ),
                run_mutation=bool(
                    run_mutation
                ),
                run_formal=bool(
                    run_formal
                ),
                run_red_team=bool(
                    run_red_team
                ),
                metadata=run_metadata,
            )

            # ---------------------------------------------------------------
            # Store results.
            # ---------------------------------------------------------------

            st.session_state.last_state = (
                state
            )

            st.session_state.last_run_id = (
                state.get(
                    "run_id"
                )
            )

            verification_status.write(
                "✓ Verification workflow completed"
            )

            verification_status.update(
                label="✅ Verification Completed",
                state="complete",
            )

        progress_placeholder.empty()

    except Exception as exc:

        verification_status.update(
            label="❌ Verification Failed",
            state="error",
        )

        st.error(
            "Verification workflow failed."
        )

        st.exception(
            exc
        )

        st.stop()


# =============================================================================
# RESULT STATE
# =============================================================================

state = st.session_state.last_state


if state is not None:

    # =========================================================================
    # RESULTS HEADER
    # =========================================================================

    st.divider()

    st.header(
        "4️⃣ Verification Results"
    )

    run_id = state.get(
        "run_id",
        "unknown",
    )

    final_verdict = format_verdict(
        state.get(
            "final_verdict",
            state.get(
                "judge_verdict",
                "NOT_RUN",
            ),
        )
    )

    verification_score = safe_float(
        state.get(
            "verification_score",
            0.0,
        )
    )

    coverage_score = safe_float(
        state.get(
            "coverage_score",
            state.get(
                "coverage",
                {},
            ).get(
                "score",
                0.0,
            )
            if isinstance(
                state.get(
                    "coverage",
                    {},
                ),
                dict,
            )
            else 0.0,
        )
    )

    mutation_score = safe_float(
        state.get(
            "mutation_score",
            state.get(
                "mutation_results",
                {},
            ).get(
                "score",
                0.0,
            )
            if isinstance(
                state.get(
                    "mutation_results",
                    {},
                ),
                dict,
            )
            else 0.0,
        )
    )

    confidence = safe_float(
        state.get(
            "confidence",
            0.0,
        )
    )

    # =========================================================================
    # RUN IDENTIFICATION
    # =========================================================================

    st.info(
        f"**Verification Run:** `{run_id}`"
    )

    run_dir = get_run_directory_from_state(
        state
    )

    if run_dir:

        st.caption(
            f"Artifacts: `{run_dir}`"
        )

    # =========================================================================
    # TOP METRICS
    # =========================================================================

    metric1, metric2, metric3, metric4, metric5 = st.columns(
        5
    )

    with metric1:

        st.metric(
            "Final Verdict",
            final_verdict,
        )

    with metric2:

        st.metric(
            "Verification Score",
            f"{verification_score:.1f}%",
        )

    with metric3:

        st.metric(
            "Coverage",
            f"{coverage_score:.1f}%",
        )

    with metric4:

        st.metric(
            "Mutation",
            f"{mutation_score:.1f}%",
        )

    with metric5:

        st.metric(
            "Confidence",
            f"{confidence:.1f}%",
        )

    # =========================================================================
    # AGENT PIPELINE
    # =========================================================================

    st.subheader(
        "Agent Execution Pipeline"
    )

    pipeline = [
        ("🔍", "RTL Analyzer"),
        ("📋", "Planner"),
        ("🧪", "Test Generator"),
        ("🧰", "Testbench"),
        ("▶️", "Simulator"),
        ("💥", "Failure Analyzer"),
        ("📈", "Coverage"),
        ("🛡️", "Red Team"),
        ("🧬", "Mutation"),
        ("🔬", "Formal"),
        ("⚖️", "Judge"),
    ]

    pipeline_columns = st.columns(
        len(pipeline)
    )

    for column, (
        icon,
        name,
    ) in zip(
        pipeline_columns,
        pipeline,
    ):

        with column:

            st.markdown(
                f"### {icon}"
            )

            st.caption(
                name
            )

            st.success(
                "Completed"
            )

    # =========================================================================
    # RTL ANALYSIS
    # =========================================================================

    with st.expander(
        "🔍 RTL Analysis",
        expanded=True,
    ):

        analysis = state.get(
            "rtl_analysis",
            {},
        )

        if analysis:

            render_json(
                analysis
            )

        else:

            st.info(
                "No RTL analysis recorded."
            )

    # =========================================================================
    # VERIFICATION PLAN
    # =========================================================================

    with st.expander(
        "📋 Verification Plan"
    ):

        plan = state.get(
            "verification_plan",
            {},
        )

        render_json(
            plan
        )

        scenarios = state.get(
            "scenarios",
            [],
        )

        if scenarios:

            st.write(
                f"**Scenarios:** {len(scenarios)}"
            )

            for index, scenario in enumerate(
                scenarios,
                start=1,
            ):

                st.write(
                    f"{index}. {scenario}"
                )

    # =========================================================================
    # GENERATED TESTS
    # =========================================================================

    with st.expander(
        "🧪 Generated Tests"
    ):

        tests = state.get(
            "generated_tests",
            [],
        )

        if not tests:

            tests = state.get(
                "test_cases",
                [],
            )

        if tests:

            st.write(
                f"Generated test cases: **{len(tests)}**"
            )

            render_json(
                tests
            )

        else:

            st.info(
                "No generated tests recorded."
            )

    # =========================================================================
    # TESTBENCH
    # =========================================================================

    with st.expander(
        "🧰 Generated Testbench"
    ):

        generated_testbench = state.get(
            "generated_testbench",
            "",
        )

        if not generated_testbench:

            generated_testbench = state.get(
                "testbench_code",
                "",
            )

        if generated_testbench:

            render_code(
                generated_testbench,
                language="verilog",
            )

        else:

            st.info(
                "No generated testbench."
            )

    # =========================================================================
    # SIMULATION
    # =========================================================================

    with st.expander(
        "▶️ Simulation Results"
    ):

        simulation_result = state.get(
            "simulation_result",
            {},
        )

        render_json(
            simulation_result
        )

        simulation_status = state.get(
            "simulation_status",
            "unknown",
        )

        simulation_passed = state.get(
            "simulation_passed",
            False,
        )

        st.write(
            f"**Status:** `{simulation_status}`"
        )

        st.write(
            f"**Passed:** `{simulation_passed}`"
        )

        return_code = state.get(
            "simulation_return_code"
        )

        if return_code is not None:

            st.write(
                f"**Return Code:** `{return_code}`"
            )

        stdout = state.get(
            "simulation_stdout",
            "",
        )

        stderr = state.get(
            "simulation_stderr",
            "",
        )

        if stdout:

            st.subheader(
                "Simulation STDOUT"
            )

            st.code(
                stdout
            )

        if stderr:

            st.subheader(
                "Simulation STDERR"
            )

            st.code(
                stderr
            )

        waveform_file = state.get(
            "waveform_file"
        )

        if waveform_file:

            st.write(
                f"Waveform: `{waveform_file}`"
            )

    # =========================================================================
    # FAILURE ANALYSIS
    # =========================================================================

    with st.expander(
        "💥 Failure Analysis"
    ):

        failure_analysis = state.get(
            "failure_analysis",
            {},
        )

        render_json(
            failure_analysis
        )

        failures = state.get(
            "failures",
            [],
        )

        if failures:

            st.warning(
                f"Detected {len(failures)} failure(s)."
            )

            render_json(
                failures
            )

        root_causes = state.get(
            "root_causes",
            [],
        )

        if root_causes:

            st.subheader(
                "Root Causes"
            )

            for root_cause in root_causes:

                st.write(
                    f"- {root_cause}"
                )

    # =========================================================================
    # COVERAGE
    # =========================================================================

    with st.expander(
        "📈 Coverage Analysis"
    ):

        coverage = state.get(
            "coverage",
            {},
        )

        render_json(
            coverage
        )

        coverage_gaps = state.get(
            "coverage_gaps",
            [],
        )

        if coverage_gaps:

            st.warning(
                "Coverage gaps detected."
            )

            for gap in coverage_gaps:

                st.write(
                    f"- {gap}"
                )

    # =========================================================================
    # RED TEAM
    # =========================================================================

    with st.expander(
        "🛡️ Red-Team Verification"
    ):

        red_team = state.get(
            "red_team_results",
            {},
        )

        render_json(
            red_team
        )

        security_risks = state.get(
            "security_risks",
            [],
        )

        if security_risks:

            st.warning(
                "Potential RTL risks identified:"
            )

            for risk in security_risks:

                st.write(
                    f"- {risk}"
                )

    # =========================================================================
    # MUTATION
    # =========================================================================

    with st.expander(
        "🧬 Mutation Testing"
    ):

        mutation = state.get(
            "mutation_results",
            {},
        )

        render_json(
            mutation
        )

        mutations = state.get(
            "mutations",
            [],
        )

        if mutations:

            st.write(
                f"Mutants generated: {len(mutations)}"
            )

        surviving = state.get(
            "surviving_mutants",
            [],
        )

        if surviving:

            st.warning(
                f"Surviving mutants: {len(surviving)}"
            )

            render_json(
                surviving
            )

    # =========================================================================
    # FORMAL
    # =========================================================================

    with st.expander(
        "🔬 Formal Verification"
    ):

        formal_results = state.get(
            "formal_results",
            {},
        )

        formal_status = state.get(
            "formal_status",
            "unknown",
        )

        st.write(
            f"**Status:** `{formal_status}`"
        )

        render_json(
            formal_results
        )

        counterexamples = state.get(
            "formal_counterexamples",
            [],
        )

        if counterexamples:

            st.warning(
                "Formal counterexamples found."
            )

            render_json(
                counterexamples
            )

    # =========================================================================
    # JUDGE
    # =========================================================================

    with st.expander(
        "⚖️ Verification Judge",
        expanded=True,
    ):

        judge_result = state.get(
            "judge_result",
            {},
        )

        render_json(
            judge_result
        )

        st.divider()

        st.subheader(
            f"Final Verdict: {final_verdict}"
        )

        st.metric(
            "Verification Score",
            f"{verification_score:.1f}%",
        )

    # =========================================================================
    # REPAIR
    # =========================================================================

    with st.expander(
        "🔧 RTL Repair"
    ):

        repair_result = state.get(
            "repair_result",
            {},
        )

        render_json(
            repair_result
        )

        repaired_rtl = state.get(
            "repaired_rtl",
            "",
        )

        repair_applied = state.get(
            "repair_applied",
            False,
        )

        st.write(
            f"**Repair Applied:** `{repair_applied}`"
        )

        if repaired_rtl:

            st.subheader(
                "Repaired RTL"
            )

            render_code(
                repaired_rtl,
                language="verilog",
            )

    # =========================================================================
    # ERRORS
    # =========================================================================

    errors = state.get(
        "errors",
        [],
    )

    if errors:

        with st.expander(
            f"❌ Workflow Errors ({len(errors)})",
            expanded=True,
        ):

            for error in errors:

                st.error(
                    str(error)
                )

    # =========================================================================
    # WARNINGS
    # =========================================================================

    warnings = state.get(
        "warnings",
        [],
    )

    if warnings:

        with st.expander(
            f"⚠️ Workflow Warnings ({len(warnings)})"
        ):

            for warning in warnings:

                st.warning(
                    str(warning)
                )

    # =========================================================================
    # ARTIFACTS
    # =========================================================================

    st.header(
        "5️⃣ Run Artifacts & Observability"
    )

    artifact_tab, activity_tab, workflow_tab, manifest_tab = st.tabs(
        [
            "📦 Artifacts",
            "📊 Agent Activity",
            "📜 Workflow Log",
            "🧾 Manifests",
        ]
    )

    # -------------------------------------------------------------------------
    # ARTIFACT TAB
    # -------------------------------------------------------------------------

    with artifact_tab:

        if run_dir is None:

            st.info(
                "Run artifact directory is not available."
            )

        else:

            st.code(
                str(run_dir)
            )

            artifact_manifest = load_manifest(
                run_dir,
                "artifact_manifest.json",
            )

            artifacts = artifact_manifest.get(
                "artifacts",
                [],
            )

            if artifacts:

                st.write(
                    f"**Registered artifacts:** {len(artifacts)}"
                )

                for artifact in artifacts:

                    relative_path = artifact.get(
                        "path",
                        "",
                    )

                    artifact_type = artifact.get(
                        "artifact_type",
                        "file",
                    )

                    size = artifact.get(
                        "size_bytes",
                        0,
                    )

                    sha256 = artifact.get(
                        "sha256"
                    )

                    st.markdown(
                        f"**{relative_path}**  \n"
                        f"Type: `{artifact_type}` • "
                        f"Size: `{size}` bytes"
                    )

                    if sha256:

                        st.caption(
                            f"SHA-256: `{sha256}`"
                        )

            else:

                st.info(
                    "No registered artifacts."
                )

    # -------------------------------------------------------------------------
    # ACTIVITY TAB
    # -------------------------------------------------------------------------

    with activity_tab:

        activity_log = read_activity_log(
            run_dir
        )

        if activity_log:

            st.code(
                activity_log,
                language="json",
            )

        else:

            st.info(
                "No agent activity log available."
            )

    # -------------------------------------------------------------------------
    # WORKFLOW LOG TAB
    # -------------------------------------------------------------------------

    with workflow_tab:

        workflow_log = read_workflow_log(
            run_dir
        )

        if workflow_log:

            st.code(
                workflow_log
            )

        else:

            st.info(
                "No workflow log available."
            )

    # -------------------------------------------------------------------------
    # MANIFEST TAB
    # -------------------------------------------------------------------------

    with manifest_tab:

        run_manifest = load_manifest(
            run_dir,
            "run_manifest.json",
        )

        artifact_manifest = load_manifest(
            run_dir,
            "artifact_manifest.json",
        )

        st.subheader(
            "Run Manifest"
        )

        render_json(
            run_manifest
        )

        st.subheader(
            "Artifact Manifest"
        )

        render_json(
            artifact_manifest
        )


# =============================================================================
# NO RESULTS STATE
# =============================================================================

else:

    st.divider()

    st.info(
        """
        **No verification run yet.**

        Load one of the sample projects or enter your own:

        1. Functional specification
        2. RTL / Verilog
        3. Optional reference testbench
        4. Optional reference vectors

        Then click **START FULL VERIFICATION**.
        """
    )

    # -------------------------------------------------------------------------
    # Sample project cards
    # -------------------------------------------------------------------------

    if sample_projects:

        st.header(
            "📚 Available Sample Projects"
        )

        sample_columns = st.columns(
            min(
                3,
                len(sample_projects),
            )
        )

        for index, (
            name,
            directory,
        ) in enumerate(
            sample_projects.items()
        ):

            column = sample_columns[
                index
                % len(sample_columns)
            ]

            with column:

                st.subheader(
                    name.replace(
                        "_",
                        " ",
                    ).title()
                )

                readme = safe_read_text(
                    directory
                    / "README.md"
                )

                if readme:

                    # Keep the card concise.
                    preview = readme[:600]

                    st.caption(
                        preview
                    )

                files = []

                for filename in [
                    "spec.md",
                    "rtl.v",
                    "testbench.v",
                    "test_vectors.json",
                ]:

                    if (
                        directory
                        / filename
                    ).exists():

                        files.append(
                            filename
                        )

                if files:

                    st.write(
                        "Files: "
                        + ", ".join(files)
                    )


# =============================================================================
# FOOTER
# =============================================================================

st.divider()

footer_left, footer_right = st.columns(
    2
)

with footer_left:

    st.caption(
        f"{APP_NAME} • v{APP_VERSION}"
    )

with footer_right:

    st.caption(
        "Agentic RTL Verification • AI Test Generation • Simulation • Coverage"
    )
    
