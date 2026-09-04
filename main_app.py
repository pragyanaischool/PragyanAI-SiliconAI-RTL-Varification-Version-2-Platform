"""
PragyanAI SiliconAI
Agentic RTL / Verilog Verification Platform
================================================

Streamlit entry point.

Features
--------
- Custom RTL verification
- Sample project loader
- Specification + RTL + reference testbench
- Agentic verification workflow
- Simulation
- Coverage
- Red-team testing
- Mutation testing
- Optional formal stage
- Verification judge
- Run artifact browser
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# ---------------------------------------------------------------------
# Application imports
# ---------------------------------------------------------------------

from config.settings import (  # noqa: E402
    APP_NAME,
    APP_VERSION,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RUN_FORMAL,
    DEFAULT_RUN_MUTATION,
)

from core.state import create_initial_state  # noqa: E402
from graph.workflow import run_workflow  # noqa: E402


# ---------------------------------------------------------------------
# Streamlit configuration
# ---------------------------------------------------------------------

st.set_page_config(
    page_title=f"{APP_NAME} | Agentic RTL Verification",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

SAMPLE_ROOT = ROOT_DIR / "examples" / "sample_projects"
CATALOG_FILE = SAMPLE_ROOT / "catalog.json"


# ---------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------

st.markdown(
    """
<style>
.main-title {
    font-size: 2.25rem;
    font-weight: 800;
    margin-bottom: 0.15rem;
}

.subtitle {
    color: #666;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin-top: 1rem;
}

.metric-card {
    padding: 1rem;
    border-radius: 0.75rem;
    border: 1px solid rgba(128,128,128,0.25);
}

.agent-success {
    padding: 0.5rem 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 0.35rem;
}

.small-text {
    font-size: 0.85rem;
    color: #777;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Sample-project helpers
# ---------------------------------------------------------------------


@st.cache_data
def load_sample_catalog() -> dict[str, Any]:
    """
    Load examples/sample_projects/catalog.json.

    Returns an empty dictionary if the catalog does not exist or
    contains invalid JSON.
    """
    if not CATALOG_FILE.exists():
        return {}

    try:
        with CATALOG_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        return data if isinstance(data, dict) else {}

    except (OSError, json.JSONDecodeError):
        return {}


def get_sample_projects() -> list[dict[str, Any]]:
    """
    Return normalized sample project records from catalog.json.
    """
    catalog = load_sample_catalog()

    projects = catalog.get("projects", [])

    if not isinstance(projects, list):
        return []

    normalized: list[dict[str, Any]] = []

    for project in projects:
        if not isinstance(project, dict):
            continue

        project_id = str(project.get("id", "")).strip()

        if not project_id:
            continue

        normalized.append(project)

    return normalized


def sample_project_path(project_id: str) -> Path:
    """Return the directory for a sample project."""
    return SAMPLE_ROOT / project_id


def read_sample_file(
    project_id: str,
    filename: str,
) -> str:
    """
    Read one file from a sample project.

    Returns an empty string when the file is unavailable.
    """
    path = sample_project_path(project_id) / filename

    if not path.exists():
        return ""

    try:
        return path.read_text(encoding="utf-8")

    except OSError:
        return ""


def load_sample_project(project: dict[str, Any]) -> dict[str, str]:
    """
    Load specification, RTL, reference testbench and test vectors
    from a sample project.
    """
    project_id = str(project.get("id", "")).strip()

    files = project.get("files", {})

    if not isinstance(files, dict):
        files = {}

    specification_file = str(
        files.get("specification", "spec.md")
    )

    rtl_file = str(
        files.get("rtl", "rtl.v")
    )

    testbench_file = str(
        files.get("testbench", "testbench.v")
    )

    vectors_file = str(
        files.get("test_vectors", "test_vectors.json")
    )

    return {
        "id": project_id,
        "name": str(project.get("name", project_id)),
        "description": str(project.get("description", "")),
        "specification": read_sample_file(
            project_id,
            specification_file,
        ),
        "rtl": read_sample_file(
            project_id,
            rtl_file,
        ),
        "testbench": read_sample_file(
            project_id,
            testbench_file,
        ),
        "test_vectors": read_sample_file(
            project_id,
            vectors_file,
        ),
    }


# ---------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------


def initialize_session_state() -> None:
    """Initialize Streamlit session state."""
    defaults: dict[str, Any] = {
        "specification": "",
        "rtl_code": "",
        "reference_testbench": "",
        "test_vectors": "",
        "selected_sample": "Custom RTL",
        "last_result": None,
        "last_run_dir": None,
        "last_run_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_sample_project(project: dict[str, str]) -> None:
    """Put sample-project contents into the Streamlit session."""
    st.session_state.specification = project.get(
        "specification",
        "",
    )

    st.session_state.rtl_code = project.get(
        "rtl",
        "",
    )

    st.session_state.reference_testbench = project.get(
        "testbench",
        "",
    )

    st.session_state.test_vectors = project.get(
        "test_vectors",
        "",
    )

    st.session_state.selected_sample = project.get(
        "name",
        project.get("id", "Sample"),
    )


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------


def render_header() -> None:
    st.markdown(
        f"""
        <div class="main-title">
            🔬 {APP_NAME}
        </div>

        <div class="subtitle">
            Autonomous Agentic RTL / Verilog Verification Platform
            &nbsp;•&nbsp; Version {APP_VERSION}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------


def render_sidebar() -> dict[str, Any]:
    """
    Render configuration sidebar and return run configuration.
    """

    st.sidebar.header("⚙️ Verification Setup")

    # -------------------------------------------------------------
    # Sample projects
    # -------------------------------------------------------------

    st.sidebar.subheader("📦 Sample Projects")

    projects = get_sample_projects()

    sample_names = ["Custom RTL"]

    project_by_name: dict[str, dict[str, Any]] = {}

    for project in projects:
        name = str(
            project.get(
                "name",
                project.get("id", "Sample"),
            )
        )

        sample_names.append(name)
        project_by_name[name] = project

    current_sample = st.session_state.get(
        "selected_sample",
        "Custom RTL",
    )

    if current_sample not in sample_names:
        current_sample = "Custom RTL"

    selected_sample = st.sidebar.selectbox(
        "Choose a sample",
        sample_names,
        index=sample_names.index(current_sample),
        help=(
            "Load a ready-to-run specification, RTL, "
            "reference testbench and test vectors."
        ),
    )

    if selected_sample != "Custom RTL":
        selected_project = project_by_name.get(
            selected_sample
        )

        if selected_project:
            description = selected_project.get(
                "description",
                "",
            )

            if description:
                st.sidebar.caption(description)

            if st.sidebar.button(
                "📥 Load Sample Project",
                use_container_width=True,
            ):
                sample = load_sample_project(
                    selected_project
                )

                apply_sample_project(sample)

                st.sidebar.success(
                    f"Loaded {sample['name']}"
                )

                st.rerun()

    else:
        st.sidebar.caption(
            "Enter your own specification and RTL below."
        )

    st.sidebar.divider()

    # -------------------------------------------------------------
    # Workflow settings
    # -------------------------------------------------------------

    st.sidebar.subheader("🧠 Agentic Workflow")

    max_iterations = st.sidebar.slider(
        "Maximum Verification Iterations",
        min_value=1,
        max_value=10,
        value=int(DEFAULT_MAX_ITERATIONS),
        step=1,
        help=(
            "Controls how many repair / regeneration "
            "cycles the verification workflow may perform."
        ),
    )

    run_mutation = st.sidebar.checkbox(
        "🧬 Enable Mutation Testing",
        value=bool(DEFAULT_RUN_MUTATION),
        help=(
            "Create mutated RTL versions and check "
            "whether the generated verification detects them."
        ),
    )

    run_formal = st.sidebar.checkbox(
        "📐 Enable Formal Stage",
        value=bool(DEFAULT_RUN_FORMAL),
        help=(
            "Run the optional formal verification stage. "
            "No SymbiYosys dependency is required."
        ),
    )

    st.sidebar.divider()

    st.sidebar.subheader("🎯 Verification Targets")

    coverage_target = st.sidebar.number_input(
        "Coverage Target (%)",
        min_value=1,
        max_value=100,
        value=95,
        step=1,
    )

    mutation_target = st.sidebar.number_input(
        "Mutation Target (%)",
        min_value=1,
        max_value=100,
        value=90,
        step=1,
    )

    st.sidebar.divider()

    # -------------------------------------------------------------
    # Information
    # -------------------------------------------------------------

    with st.sidebar.expander("ℹ️ Verification Pipeline"):
        st.markdown(
            """
            1. RTL Analysis  
            2. Verification Planning  
            3. AI Test Generation  
            4. Testbench Generation  
            5. RTL Simulation  
            6. Failure Analysis  
            7. Coverage Analysis  
            8. Red-Team Verification  
            9. Mutation Testing  
            10. Formal Verification  
            11. Verification Judge
            """
        )

    return {
        "max_iterations": max_iterations,
        "run_mutation": run_mutation,
        "run_formal": run_formal,
        "coverage_target": coverage_target,
        "mutation_target": mutation_target,
    }


# ---------------------------------------------------------------------
# Input editor
# ---------------------------------------------------------------------


def render_input_editor() -> tuple[str, str]:
    """
    Render specification and RTL input areas.

    Returns
    -------
    specification, rtl_code
    """

    st.markdown(
        '<div class="section-title">1. Design Specification</div>',
        unsafe_allow_html=True,
    )

    specification = st.text_area(
        "Specification",
        key="specification",
        height=220,
        placeholder=(
            "Describe the required hardware behavior here...\n\n"
            "Example:\n"
            "- 4-bit synchronous counter\n"
            "- Reset clears count to zero\n"
            "- Enable increments count\n"
            "- Counter rolls over from 15 to 0"
        ),
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="section-title">2. RTL / Verilog</div>',
        unsafe_allow_html=True,
    )

    rtl_code = st.text_area(
        "RTL Code",
        key="rtl_code",
        height=360,
        placeholder=(
            "Paste Verilog/SystemVerilog RTL here..."
        ),
        label_visibility="collapsed",
    )

    return specification, rtl_code


# ---------------------------------------------------------------------
# Reference testbench viewer
# ---------------------------------------------------------------------


def render_reference_testbench() -> None:
    """Display reference testbench and test vectors if loaded."""

    reference_testbench = st.session_state.get(
        "reference_testbench",
        "",
    )

    test_vectors = st.session_state.get(
        "test_vectors",
        "",
    )

    if not reference_testbench and not test_vectors:
        return

    st.markdown(
        '<div class="section-title">3. Reference Verification Assets</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(
        [
            "🧪 Reference Testbench",
            "📋 Test Vectors",
        ]
    )

    with tab1:
        if reference_testbench:
            st.code(
                reference_testbench,
                language="verilog",
            )
        else:
            st.info(
                "No reference testbench supplied."
            )

    with tab2:
        if test_vectors:
            try:
                parsed = json.loads(test_vectors)

                st.json(parsed)

            except json.JSONDecodeError:
                st.code(
                    test_vectors,
                    language="json",
                )
        else:
            st.info(
                "No reference test vectors supplied."
            )


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------


def get_nested(
    data: Any,
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve nested dictionary values.
    """
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def numeric_value(value: Any) -> float:
    """Convert a value to float where possible."""
    try:
        return float(value)

    except (TypeError, ValueError):
        return 0.0


def render_result_metrics(state: dict[str, Any]) -> None:
    """Display verification metrics."""

    coverage = get_nested(
        state,
        "coverage",
        "coverage_percent",
        default=state.get(
            "coverage_percent",
            0,
        ),
    )

    mutation = state.get(
        "mutation_score",
        0,
    )

    score = state.get(
        "verification_score",
        0,
    )

    formal = state.get(
        "formal_result",
        {},
    )

    simulation_passed = state.get(
        "simulation_passed",
        False,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Verification Score",
            f"{numeric_value(score):.1f}%",
        )

    with col2:
        st.metric(
            "Coverage",
            f"{numeric_value(coverage):.1f}%",
        )

    with col3:
        st.metric(
            "Mutation Score",
            f"{numeric_value(mutation):.1f}%",
        )

    with col4:
        formal_status = "N/A"

        if isinstance(formal, dict):
            formal_status = str(
                formal.get(
                    "status",
                    "N/A",
                )
            )

        st.metric(
            "Formal",
            formal_status,
        )

    st.write("")

    if simulation_passed:
        st.success(
            "✅ RTL simulation completed successfully."
        )
    else:
        st.warning(
            "⚠️ RTL simulation did not complete successfully."
        )


# ---------------------------------------------------------------------
# Agent activity
# ---------------------------------------------------------------------


def render_agent_activity(state: dict[str, Any]) -> None:
    """Display agent execution information."""

    st.markdown(
        '<div class="section-title">Agent Activity</div>',
        unsafe_allow_html=True,
    )

    activity = state.get(
        "agent_activity",
        state.get(
            "agent_log",
            [],
        ),
    )

    if not activity:
        st.info(
            "No agent activity data available."
        )
        return

    if isinstance(activity, dict):
        activity = [
            {
                "agent": key,
                "result": value,
            }
            for key, value in activity.items()
        ]

    if not isinstance(activity, list):
        st.json(activity)
        return

    for item in activity:
        if not isinstance(item, dict):
            continue

        agent_name = item.get(
            "agent",
            item.get(
                "name",
                "Agent",
            ),
        )

        status = str(
            item.get(
                "status",
                "completed",
            )
        ).upper()

        duration = item.get(
            "duration_seconds",
            item.get(
                "duration",
                "",
            ),
        )

        if status in {
            "COMPLETED",
            "SUCCESS",
            "OK",
        }:
            icon = "✅"

        elif status in {
            "FAILED",
            "ERROR",
        }:
            icon = "❌"

        else:
            icon = "ℹ️"

        duration_text = ""

        if duration != "":
            try:
                duration_text = (
                    f" — {float(duration):.2f}s"
                )
            except (TypeError, ValueError):
                duration_text = ""

        st.markdown(
            f"""
            <div class="agent-success">
                {icon} <b>{agent_name}</b>
                <span class="small-text">
                    {status}{duration_text}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------
# Failure / diagnosis
# ---------------------------------------------------------------------


def render_failure_analysis(
    state: dict[str, Any],
) -> None:
    """Display failure analysis when available."""

    failure = state.get(
        "failure_analysis"
    )

    if not failure:
        return

    st.markdown(
        '<div class="section-title">Failure Analysis</div>',
        unsafe_allow_html=True,
    )

    if isinstance(failure, dict):
        failure_type = failure.get(
            "failure_type",
            failure.get(
                "type",
                "UNKNOWN",
            ),
        )

        root_cause = failure.get(
            "root_cause",
            failure.get(
                "summary",
                "Unknown",
            ),
        )

        evidence = failure.get(
            "evidence",
            "",
        )

        recommended_action = failure.get(
            "recommended_action",
            failure.get(
                "recommendation",
                "",
            ),
        )

        st.write(
            f"**Failure Type:** {failure_type}"
        )

        st.write(
            f"**Root Cause:** {root_cause}"
        )

        if evidence:
            st.write(
                f"**Evidence:** {evidence}"
            )

        if recommended_action:
            st.write(
                f"**Recommended Action:** "
                f"{recommended_action}"
            )

    else:
        st.code(
            str(failure)
        )


# ---------------------------------------------------------------------
# Generated artifacts
# ---------------------------------------------------------------------


def render_generated_artifacts(
    state: dict[str, Any],
) -> None:
    """Display important generated verification artifacts."""

    st.markdown(
        '<div class="section-title">Generated Verification Artifacts</div>',
        unsafe_allow_html=True,
    )

    rtl_analysis = state.get(
        "rtl_analysis"
    )

    verification_plan = state.get(
        "verification_plan"
    )

    generated_tests = state.get(
        "generated_tests",
        [],
    )

    testbench = state.get(
        "testbench",
        "",
    )

    repaired_rtl = state.get(
        "repaired_rtl",
        "",
    )

    tabs = st.tabs(
        [
            "🔍 RTL Analysis",
            "📝 Verification Plan",
            "🧪 Generated Tests",
            "🧰 Generated Testbench",
            "🔧 Repaired RTL",
        ]
    )

    with tabs[0]:
        if rtl_analysis:
            if isinstance(rtl_analysis, dict):
                st.json(rtl_analysis)
            else:
                st.code(str(rtl_analysis))
        else:
            st.info("No RTL analysis available.")

    with tabs[1]:
        if verification_plan:
            if isinstance(verification_plan, dict):
                st.json(verification_plan)
            else:
                st.code(str(verification_plan))
        else:
            st.info(
                "No verification plan available."
            )

    with tabs[2]:
        if generated_tests:
            if isinstance(generated_tests, list):
                for index, test in enumerate(
                    generated_tests,
                    start=1,
                ):
                    with st.expander(
                        f"Test {index}"
                    ):
                        if isinstance(test, dict):
                            st.json(test)
                        else:
                            st.code(str(test))
            else:
                st.json(generated_tests)
        else:
            st.info(
                "No generated tests available."
            )

    with tabs[3]:
        if testbench:
            st.code(
                testbench,
                language="verilog",
            )
        else:
            st.info(
                "No generated testbench available."
            )

    with tabs[4]:
        if repaired_rtl:
            st.code(
                repaired_rtl,
                language="verilog",
            )
        else:
            st.info(
                "No repaired RTL was generated."
            )


# ---------------------------------------------------------------------
# Simulation output
# ---------------------------------------------------------------------


def render_simulation_output(
    state: dict[str, Any],
) -> None:
    """Display compiler and simulation output."""

    compile_output = state.get(
        "compile_output",
        "",
    )

    compile_error = state.get(
        "compile_error",
        "",
    )

    simulation_output = state.get(
        "simulation_output",
        state.get(
            "run_output",
            "",
        ),
    )

    simulation_error = state.get(
        "simulation_error",
        "",
    )

    st.markdown(
        '<div class="section-title">Simulation Results</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Compile",
            "Simulation",
            "Errors",
        ]
    )

    with tab1:
        if compile_output:
            st.code(
                compile_output,
                language="text",
            )
        else:
            st.info(
                "No compiler output available."
            )

    with tab2:
        if simulation_output:
            st.code(
                simulation_output,
                language="text",
            )
        else:
            st.info(
                "No simulation output available."
            )

    with tab3:
        if compile_error or simulation_error:
            if compile_error:
                st.error(
                    f"Compile Error:\n\n{compile_error}"
                )

            if simulation_error:
                st.error(
                    f"Simulation Error:\n\n"
                    f"{simulation_error}"
                )
        else:
            st.success(
                "No simulation errors reported."
            )


# ---------------------------------------------------------------------
# Coverage / red team / mutation / formal
# ---------------------------------------------------------------------


def render_verification_evidence(
    state: dict[str, Any],
) -> None:
    """Display advanced verification evidence."""

    coverage = state.get(
        "coverage"
    )

    red_team = state.get(
        "red_team_results",
        state.get(
            "red_team_scenarios"
        ),
    )

    mutation = state.get(
        "mutation_results",
        state.get(
            "mutation_report"
        ),
    )

    formal = state.get(
        "formal_result",
        state.get(
            "formal_results"
        ),
    )

    tabs = st.tabs(
        [
            "📊 Coverage",
            "🛡️ Red Team",
            "🧬 Mutation",
            "📐 Formal",
        ]
    )

    with tabs[0]:
        if coverage:
            if isinstance(coverage, dict):
                st.json(coverage)
            else:
                st.code(str(coverage))
        else:
            st.info(
                "No coverage evidence available."
            )

    with tabs[1]:
        if red_team:
            if isinstance(red_team, dict):
                st.json(red_team)

            elif isinstance(red_team, list):
                for index, scenario in enumerate(
                    red_team,
                    start=1,
                ):
                    with st.expander(
                        f"Red-Team Scenario {index}"
                    ):
                        if isinstance(
                            scenario,
                            dict,
                        ):
                            st.json(scenario)
                        else:
                            st.write(scenario)

            else:
                st.code(str(red_team))
        else:
            st.info(
                "No red-team results available."
            )

    with tabs[2]:
        if mutation:
            if isinstance(mutation, dict):
                st.json(mutation)

            elif isinstance(mutation, list):
                for index, item in enumerate(
                    mutation,
                    start=1,
                ):
                    with st.expander(
                        f"Mutation {index}"
                    ):
                        if isinstance(
                            item,
                            dict,
                        ):
                            st.json(item)
                        else:
                            st.write(item)

            else:
                st.code(str(mutation))
        else:
            st.info(
                "Mutation testing was not executed."
            )

    with tabs[3]:
        if formal:
            if isinstance(formal, dict):
                st.json(formal)
            else:
                st.code(str(formal))
        else:
            st.info(
                "Formal verification was not executed."
            )


# ---------------------------------------------------------------------
# Artifact directory
# ---------------------------------------------------------------------


def render_artifact_browser(
    state: dict[str, Any],
) -> None:
    """Show files produced by the current verification run."""

    run_dir = state.get(
        "run_dir"
    )

    if not run_dir:
        return

    path = Path(str(run_dir))

    if not path.exists():
        return

    st.markdown(
        '<div class="section-title">📁 Run Artifacts</div>',
        unsafe_allow_html=True,
    )

    files = sorted(
        [
            p
            for p in path.rglob("*")
            if p.is_file()
        ]
    )

    if not files:
        st.info(
            "No run artifacts were created."
        )
        return

    st.caption(
        f"Run directory: `{path}`"
    )

    for file_path in files:
        relative = file_path.relative_to(path)

        with st.expander(
            str(relative)
        ):
            suffix = file_path.suffix.lower()

            try:
                if suffix in {
                    ".json",
                    ".jsonl",
                }:
                    content = file_path.read_text(
                        encoding="utf-8"
                    )

                    if suffix == ".json":
                        try:
                            st.json(
                                json.loads(content)
                            )
                        except json.JSONDecodeError:
                            st.code(content)
                    else:
                        st.code(
                            content,
                            language="text",
                        )

                elif suffix in {
                    ".v",
                    ".sv",
                    ".vh",
                    ".svh",
                }:
                    st.code(
                        file_path.read_text(
                            encoding="utf-8"
                        ),
                        language="verilog",
                    )

                else:
                    st.code(
                        file_path.read_text(
                            encoding="utf-8"
                        ),
                        language="text",
                    )

            except (OSError, UnicodeDecodeError):
                st.warning(
                    "Unable to display this artifact."
                )


# ---------------------------------------------------------------------
# Main verification execution
# ---------------------------------------------------------------------


def execute_verification(
    specification: str,
    rtl_code: str,
    configuration: dict[str, Any],
) -> None:
    """Create state and execute the LangGraph workflow."""

    if not specification.strip():
        st.error(
            "Please provide a design specification."
        )
        return

    if not rtl_code.strip():
        st.error(
            "Please provide RTL / Verilog code."
        )
        return

    state = create_initial_state(
        specification=specification,
        rtl_code=rtl_code,
        max_iterations=int(
            configuration["max_iterations"]
        ),
        run_mutation=bool(
            configuration["run_mutation"]
        ),
        run_formal=bool(
            configuration["run_formal"]
        ),
    )

    # Store UI targets in state so downstream agents can use them.
    state["coverage_target"] = int(
        configuration["coverage_target"]
    )

    state["mutation_target"] = int(
        configuration["mutation_target"]
    )

    # -------------------------------------------------------------
    # Run workflow
    # -------------------------------------------------------------

    progress = st.progress(
        0,
        text="Starting agentic verification...",
    )

    try:
        result = run_workflow(
            state
        )

        progress.progress(
            100,
            text="Verification workflow completed.",
        )

        st.session_state.last_result = result
        st.session_state.last_run_dir = result.get(
            "run_dir"
        )
        st.session_state.last_run_id = result.get(
            "run_id"
        )

        st.success(
            "Agentic RTL verification completed."
        )

        st.rerun()

    except Exception as exc:
        progress.empty()

        st.error(
            "Verification workflow failed."
        )

        with st.expander(
            "Show technical error"
        ):
            st.exception(exc)


# ---------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------


def render_results() -> None:
    """Render the most recent verification result."""

    result = st.session_state.get(
        "last_result"
    )

    if not result:
        return

    st.divider()

    st.header("🏁 Verification Results")

    verdict = str(
        result.get(
            "final_verdict",
            result.get(
                "verdict",
                "UNKNOWN",
            ),
        )
    ).upper()

    if verdict == "PASS":
        st.success(
            "🎉 VERIFICATION PASSED"
        )

    elif verdict in {
        "FAIL",
        "FAILED",
    }:
        st.error(
            "❌ VERIFICATION FAILED"
        )

    elif verdict in {
        "NEED_MORE",
        "NEED MORE",
    }:
        st.warning(
            "⚠️ MORE VERIFICATION REQUIRED"
        )

    else:
        st.info(
            f"Verification verdict: {verdict}"
        )

    render_result_metrics(
        result
    )

    if result.get("run_id"):
        st.caption(
            f"Run ID: `{result['run_id']}`"
        )

    # -------------------------------------------------------------
    # Result tabs
    # -------------------------------------------------------------

    result_tabs = st.tabs(
        [
            "🤖 Agent Activity",
            "🔬 Evidence",
            "🧪 Simulation",
            "🧠 Generated Artifacts",
            "📁 Files",
        ]
    )

    with result_tabs[0]:
        render_agent_activity(
            result
        )

    with result_tabs[1]:
        render_failure_analysis(
            result
        )

        render_verification_evidence(
            result
        )

    with result_tabs[2]:
        render_simulation_output(
            result
        )

    with result_tabs[3]:
        render_generated_artifacts(
            result
        )

    with result_tabs[4]:
        render_artifact_browser(
            result
        )


# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------


def render_footer() -> None:
    st.divider()

    st.caption(
        "PragyanAI SiliconAI — Agentic RTL / Verilog "
        "Verification Platform"
    )

    st.caption(
        "Open-source verification workflow using "
        "AI-assisted planning, test generation, "
        "simulation, coverage, red-team, mutation "
        "and verification judging."
    )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


def main() -> None:
    """Main Streamlit application."""

    initialize_session_state()

    render_header()

    configuration = render_sidebar()

    # -------------------------------------------------------------
    # Introduction
    # -------------------------------------------------------------

    st.info(
        """
        **How it works:** Provide a hardware specification and RTL.
        The platform analyzes the design, creates a verification plan,
        generates tests and a testbench, runs simulation, analyzes
        failures, evaluates coverage, performs adversarial testing,
        optionally performs mutation/formal checks, and produces a
        final verification judgment.
        """
    )

    # -------------------------------------------------------------
    # Main input area
    # -------------------------------------------------------------

    specification, rtl_code = render_input_editor()

    render_reference_testbench()

    # -------------------------------------------------------------
    # Run controls
    # -------------------------------------------------------------

    st.divider()

    col1, col2, col3 = st.columns(
        [2, 1, 1]
    )

    with col1:
        run_clicked = st.button(
            "🚀 RUN AGENTIC RTL VERIFICATION",
            type="primary",
            use_container_width=True,
        )

    with col2:
        if st.button(
            "🗑️ Clear",
            use_container_width=True,
        ):
            st.session_state.specification = ""
            st.session_state.rtl_code = ""
            st.session_state.reference_testbench = ""
            st.session_state.test_vectors = ""
            st.session_state.selected_sample = "Custom RTL"
            st.session_state.last_result = None
            st.session_state.last_run_dir = None
            st.session_state.last_run_id = None

            st.rerun()

    with col3:
        if st.session_state.get("last_run_id"):
            st.metric(
                "Last Run",
                str(
                    st.session_state.last_run_id
                )[-8:],
            )

    # -------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------

    if run_clicked:
        execute_verification(
            specification,
            rtl_code,
            configuration,
        )

    # -------------------------------------------------------------
    # Previous results
    # -------------------------------------------------------------

    render_results()

    render_footer()


# ---------------------------------------------------------------------
# Application entry
# ---------------------------------------------------------------------

if __name__ == "__main__":
    main()
