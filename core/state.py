"""
PragyanAI SiliconAI
===================

Shared LangGraph state for Agentic RTL / Verilog Verification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from observability.run_manager import VerificationRun


class VerificationState(TypedDict, total=False):
    """
    Complete state passed between verification agents.

    The most important fields for observability are:

        run_id
        verification_run
        logger

    All agents in one verification run must use the same logger.
    """

    # ========================================================================
    # Run / observability
    # ========================================================================

    run_id: str

    verification_run: VerificationRun

    logger: Any

    run_metadata: Dict[str, Any]

    started_at: str

    current_agent: str

    current_step: str

    agent_status: str

    iteration: int

    max_iterations: int

    # ========================================================================
    # User input
    # ========================================================================

    project_name: str

    specification: str

    rtl_code: str

    reference_testbench: str

    reference_test_vectors: Any

    # ========================================================================
    # RTL analysis
    # ========================================================================

    rtl_analysis: Dict[str, Any]

    module_name: str

    ports: List[Dict[str, Any]]

    clocks: List[str]

    resets: List[str]

    registers: List[str]

    parameters: List[str]

    inferred_behavior: List[str]

    rtl_risks: List[str]

    # ========================================================================
    # Verification planning
    # ========================================================================

    verification_plan: Dict[str, Any]

    scenarios: List[Dict[str, Any]]

    coverage_goals: List[str]

    corner_cases: List[str]

    # ========================================================================
    # Test generation
    # ========================================================================

    generated_tests: List[Dict[str, Any]]

    test_cases: List[Dict[str, Any]]

    test_generation_notes: str

    # ========================================================================
    # Testbench
    # ========================================================================

    generated_testbench: str

    testbench_code: str

    testbench_status: str

    # ========================================================================
    # Simulation
    # ========================================================================

    simulation_result: Dict[str, Any]

    simulation_status: str

    simulation_passed: bool

    simulation_return_code: Optional[int]

    simulation_stdout: str

    simulation_stderr: str

    waveform_file: Optional[str]

    # ========================================================================
    # Failure analysis
    # ========================================================================

    failures: List[Dict[str, Any]]

    failure_analysis: Dict[str, Any]

    root_causes: List[str]

    bug_locations: List[Dict[str, Any]]

    # ========================================================================
    # Coverage
    # ========================================================================

    coverage: Dict[str, Any]

    coverage_score: float

    coverage_gaps: List[str]

    # ========================================================================
    # Red team
    # ========================================================================

    red_team_results: Dict[str, Any]

    adversarial_tests: List[Dict[str, Any]]

    security_risks: List[str]

    # ========================================================================
    # Mutation
    # ========================================================================

    mutation_results: Dict[str, Any]

    mutations: List[Dict[str, Any]]

    mutation_score: float

    surviving_mutants: List[Dict[str, Any]]

    # ========================================================================
    # Formal
    # ========================================================================

    formal_results: Dict[str, Any]

    formal_status: str

    formal_counterexamples: List[Dict[str, Any]]

    # ========================================================================
    # Repair
    # ========================================================================

    repaired_rtl: str

    repair_result: Dict[str, Any]

    repair_applied: bool

    # ========================================================================
    # Judge
    # ========================================================================

    judge_result: Dict[str, Any]

    judge_verdict: str

    final_verdict: str

    verification_score: float

    confidence: float

    # ========================================================================
    # Iterative verification
    # ========================================================================

    retry_required: bool

    next_action: str

    convergence_status: str

    # ========================================================================
    # Artifacts / reporting
    # ========================================================================

    artifact_manifest: Dict[str, Any]

    report: Dict[str, Any]

    report_text: str

    errors: List[str]

    warnings: List[str]


def create_initial_state(
    *,
    specification: str = "",
    rtl_code: str = "",
    project_name: str = "custom_rtl",
    reference_testbench: str = "",
    reference_test_vectors: Any = None,
    max_iterations: Optional[int] = None,
    verification_run: Optional[VerificationRun] = None,
) -> VerificationState:
    """
    Create the initial LangGraph state.

    If verification_run is supplied, its logger is automatically placed
    into the state and reused by every agent.
    """

    state: VerificationState = {
        "run_id": "",
        "run_metadata": {},
        "started_at": "",

        "current_agent": "",
        "current_step": "",
        "agent_status": "created",

        "iteration": 0,
        "max_iterations": (
            max_iterations
            if max_iterations is not None
            else 3
        ),

        "project_name": project_name,

        "specification": specification,
        "rtl_code": rtl_code,

        "reference_testbench": reference_testbench,
        "reference_test_vectors": reference_test_vectors,

        "rtl_analysis": {},
        "module_name": "",
        "ports": [],
        "clocks": [],
        "resets": [],
        "registers": [],
        "parameters": [],
        "inferred_behavior": [],
        "rtl_risks": [],

        "verification_plan": {},
        "scenarios": [],
        "coverage_goals": [],
        "corner_cases": [],

        "generated_tests": [],
        "test_cases": [],
        "test_generation_notes": "",

        "generated_testbench": "",
        "testbench_code": "",
        "testbench_status": "not_started",

        "simulation_result": {},
        "simulation_status": "not_started",
        "simulation_passed": False,
        "simulation_return_code": None,
        "simulation_stdout": "",
        "simulation_stderr": "",
        "waveform_file": None,

        "failures": [],
        "failure_analysis": {},
        "root_causes": [],
        "bug_locations": [],

        "coverage": {},
        "coverage_score": 0.0,
        "coverage_gaps": [],

        "red_team_results": {},
        "adversarial_tests": [],
        "security_risks": [],

        "mutation_results": {},
        "mutations": [],
        "mutation_score": 0.0,
        "surviving_mutants": [],

        "formal_results": {},
        "formal_status": "not_run",
        "formal_counterexamples": [],

        "repaired_rtl": "",
        "repair_result": {},
        "repair_applied": False,

        "judge_result": {},
        "judge_verdict": "NOT_RUN",
        "final_verdict": "NOT_RUN",

        "verification_score": 0.0,
        "confidence": 0.0,

        "retry_required": False,
        "next_action": "",
        "convergence_status": "not_started",

        "artifact_manifest": {},
        "report": {},
        "report_text": "",

        "errors": [],
        "warnings": [],
    }

    if verification_run is not None:

        state["verification_run"] = verification_run

        state["logger"] = verification_run.logger

        state["run_id"] = verification_run.run_id

        state["run_metadata"] = dict(
            verification_run.metadata
        )

        state["started_at"] = (
            verification_run.started_at
        )

        state["agent_status"] = "running"

    return state


def get_logger(
    state: VerificationState,
) -> Any:
    """
    Return the shared run-level logger.

    This helper prevents agents from accidentally constructing their
    own logger.
    """

    logger = state.get(
        "logger"
    )

    if logger is None:

        verification_run = state.get(
            "verification_run"
        )

        if verification_run is not None:
            return verification_run.logger

    return logger


def get_verification_run(
    state: VerificationState,
) -> Optional[VerificationRun]:
    """
    Return the shared VerificationRun object.
    """

    run = state.get(
        "verification_run"
    )

    if isinstance(
        run,
        VerificationRun,
    ):
        return run

    return None


def add_error(
    state: VerificationState,
    message: str,
) -> VerificationState:
    """
    Add an error to workflow state.
    """

    errors = list(
        state.get(
            "errors",
            [],
        )
    )

    errors.append(
        str(message)
    )

    state["errors"] = errors

    return state


def add_warning(
    state: VerificationState,
    message: str,
) -> VerificationState:
    """
    Add a warning to workflow state.
    """

    warnings = list(
        state.get(
            "warnings",
            [],
        )
    )

    warnings.append(
        str(message)
    )

    state["warnings"] = warnings

    return state


__all__ = [
    "VerificationState",
    "create_initial_state",
    "get_logger",
    "get_verification_run",
    "add_error",
    "add_warning",
]

