"""
PragyanAI SiliconAI
===================

Shared verification state.

This module defines the canonical state contract used by every
agent in the verification workflow.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_RUNNING = "RUNNING"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_DEGRADED = "DEGRADED"
STATUS_COMPLETED = "COMPLETED"


AGENT_NAMES = [
    "rtl_analyzer",
    "verification_planner",
    "test_generator",
    "testbench_generator",
    "simulator",
    "failure_analyzer",
    "coverage",
    "red_team",
    "mutation",
    "assertion_agent",
    "verification_judge",
    "repair",
]


# ---------------------------------------------------------------------------
# TypedDict
# ---------------------------------------------------------------------------

class VerificationState(TypedDict, total=False):
    """
    Canonical LangGraph-compatible verification state.

    total=False is intentional because LangGraph nodes may progressively
    populate the state.
    """

    # Run information
    run_id: str
    run_dir: str
    started_at: str
    completed_at: str

    # Project information
    project_name: str
    specification: str
    rtl_code: str
    reference_testbench: str
    reference_test_vectors: Any

    # Configuration
    max_iterations: int
    current_iteration: int

    run_mutation: bool
    run_formal: bool
    run_red_team: bool

    # Agent outputs
    rtl_analysis: dict[str, Any]
    verification_plan: dict[str, Any]
    generated_tests: list[dict[str, Any]]
    generated_testbench: str

    simulation: dict[str, Any]
    failure_analysis: dict[str, Any]
    coverage: dict[str, Any]
    red_team: dict[str, Any]
    mutation: dict[str, Any]
    formal: dict[str, Any]
    verification_judge: dict[str, Any]
    repair: dict[str, Any]

    # Agent execution
    current_agent: str
    current_step: str
    agent_status: str
    agent_history: list[dict[str, Any]]

    # Final result
    final_verdict: str
    verification_score: float
    confidence: float

    # Diagnostics
    errors: list[str]
    warnings: list[str]
    messages: list[str]

    # Runtime / logging
    logger: Any
    verification_run: Any

    # Artifacts
    artifacts: list[dict[str, Any]]

    # Internal metadata
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return a UTC timestamp suitable for JSON serialization."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Empty stage factories
# ---------------------------------------------------------------------------

def empty_rtl_analysis() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "module_name": "",
        "ports": [],
        "parameters": [],
        "clocks": [],
        "resets": [],
        "registers": [],
        "wires": [],
        "always_blocks": [],
        "assignments": [],
        "instances": [],
        "behavioral_summary": "",
        "risks": [],
        "confidence": 0.0,
        "source": "not_run",
    }


def empty_verification_plan() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "objective": "",
        "scenarios": [],
        "corner_cases": [],
        "assertions": [],
        "coverage_goals": [],
        "priority": [],
        "source": "not_run",
    }


def empty_simulation() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "compile_status": "NOT_RUN",
        "simulation_status": "NOT_RUN",
        "exit_code": None,
        "passed": False,
        "tests_total": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "stdout": "",
        "stderr": "",
        "compile_log": "",
        "simulation_log": "",
        "duration_seconds": 0.0,
        "testbench_file": "",
        "rtl_file": "",
        "executable_file": "",
        "error": "",
        "source": "not_run",
    }


def empty_failure_analysis() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "failures": [],
        "root_causes": [],
        "suspected_rtl_locations": [],
        "recommendations": [],
        "severity": "NONE",
        "summary": "",
        "source": "not_run",
    }


def empty_coverage() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "score": 0.0,
        "target": 90.0,
        "scenarios_total": 0,
        "scenarios_covered": 0,
        "scenarios_missed": [],
        "covered": [],
        "uncovered": [],
        "method": "scenario_proxy",
        "source": "not_run",
    }


def empty_red_team() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "scenarios": [],
        "tests_generated": 0,
        "tests_executed": 0,
        "failures_found": 0,
        "issues": [],
        "score": 0.0,
        "source": "not_run",
    }


def empty_mutation() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "mutants_total": 0,
        "mutants_killed": 0,
        "mutants_survived": 0,
        "score": None,
        "target": 80.0,
        "mutants": [],
        "source": "not_run",
    }


def empty_formal() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "backend": "symbiyosys_compatible",
        "properties_checked": 0,
        "properties_proven": 0,
        "properties_failed": 0,
        "assertions": [],
        "score": None,
        "reason": "",
        "source": "not_run",
    }


def empty_judge() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "verification_score": 0.0,
        "target": 90.0,
        "verdict": "NEED_MORE",
        "confidence": 0.0,
        "evidence": {},
        "strengths": [],
        "weaknesses": [],
        "recommendations": [],
        "source": "not_run",
    }


def empty_repair() -> dict[str, Any]:
    return {
        "status": STATUS_NOT_STARTED,
        "repair_attempted": False,
        "repair_applied": False,
        "original_rtl": "",
        "repaired_rtl": "",
        "changes": [],
        "reason": "",
        "source": "not_run",
    }


# ---------------------------------------------------------------------------
# State factory
# ---------------------------------------------------------------------------

def create_initial_state(
    specification: str = "",
    rtl_code: str = "",
    project_name: str = "rtl_project",
    reference_testbench: str = "",
    reference_test_vectors: Any = None,
    max_iterations: int = 2,
    run_mutation: bool = True,
    run_formal: bool = True,
    run_red_team: bool = True,
    run_id: str = "",
    run_dir: str = "",
    metadata: dict[str, Any] | None = None,
) -> VerificationState:
    """Create a fully initialized verification state with physical directory provisioning."""
    if not run_dir:
        default_run_dir = Path("runtime/runs/default_run")
        default_run_dir.mkdir(parents=True, exist_ok=True)
        resolved_run_dir = str(default_run_dir)
    else:
        resolved_run_dir = str(run_dir)
        Path(resolved_run_dir).mkdir(parents=True, exist_ok=True)

    state: VerificationState = {
        "run_id": run_id or "run_default_local",
        "run_dir": resolved_run_dir,
        "started_at": utc_now(),
        "completed_at": "",
        "project_name": project_name or "rtl_project",
        "specification": specification or "",
        "rtl_code": rtl_code or "",
        "reference_testbench": reference_testbench or "",
        "reference_test_vectors": reference_test_vectors if reference_test_vectors is not None else [],
        "max_iterations": max(1, int(max_iterations or 1)),
        "current_iteration": 1,
        "run_mutation": bool(run_mutation),
        "run_formal": bool(run_formal),
        "run_red_team": bool(run_red_team),
        "rtl_analysis": empty_rtl_analysis(),
        "verification_plan": empty_verification_plan(),
        "generated_tests": [],
        "generated_testbench": "",
        "simulation": empty_simulation(),
        "failure_analysis": empty_failure_analysis(),
        "coverage": empty_coverage(),
        "red_team": empty_red_team(),
        "mutation": empty_mutation(),
        "formal": empty_formal(),
        "verification_judge": empty_judge(),
        "repair": empty_repair(),
        "current_agent": "",
        "current_step": "",
        "agent_status": STATUS_NOT_STARTED,
        "agent_history": [],
        "final_verdict": "NEED_MORE",
        "verification_score": 0.0,
        "confidence": 0.0,
        "errors": [],
        "warnings": [],
        "messages": [],
        "logger": None,
        "verification_run": None,
        "artifacts": [],
        "metadata": deepcopy(metadata or {}),
    }

    return state


# ---------------------------------------------------------------------------
# State normalization
# ---------------------------------------------------------------------------

def ensure_state_defaults(
    state: dict[str, Any] | None,
) -> VerificationState:
    """Normalize an existing state, filling missing keys with safe defaults."""
    if state is None:
        return create_initial_state()

    normalized: VerificationState = dict(state)
    defaults = create_initial_state()

    for key, default_value in defaults.items():
        if key not in normalized:
            normalized[key] = deepcopy(default_value)
            continue
        if normalized[key] is None:
            if isinstance(default_value, dict):
                normalized[key] = deepcopy(default_value)
            elif isinstance(default_value, list):
                normalized[key] = []
            elif isinstance(default_value, str):
                normalized[key] = ""

    if not normalized.get("run_dir"):
        default_run_dir = Path("runtime/runs/default_run")
        default_run_dir.mkdir(parents=True, exist_ok=True)
        normalized["run_dir"] = str(default_run_dir)
    else:
        Path(str(normalized["run_dir"])).mkdir(parents=True, exist_ok=True)

    for key in ["errors", "warnings", "messages", "agent_history", "artifacts", "generated_tests"]:
        if not isinstance(normalized.get(key), list):
            normalized[key] = []

    for key in ["rtl_analysis", "verification_plan", "simulation", "failure_analysis", "coverage", "red_team", "mutation", "formal", "verification_judge", "repair", "metadata"]:
        if not isinstance(normalized.get(key), dict):
            normalized[key] = {}

    return normalized


# ---------------------------------------------------------------------------
# Diagnostics & Helpers
# ---------------------------------------------------------------------------

def add_error(state: dict[str, Any], message: str) -> VerificationState:
    normalized = ensure_state_defaults(state)
    text = str(message).strip()
    if text and text not in normalized["errors"]:
        normalized["errors"].append(text)
    return normalized


def add_warning(state: dict[str, Any], message: str) -> VerificationState:
    normalized = ensure_state_defaults(state)
    text = str(message).strip()
    if text and text not in normalized["warnings"]:
        normalized["warnings"].append(text)
    return normalized


def add_message(state: dict[str, Any], message: str) -> VerificationState:
    normalized = ensure_state_defaults(state)
    text = str(message).strip()
    if text:
        normalized["messages"].append(text)
    return normalized


def update_agent_status(
    state: dict[str, Any],
    agent_name: str,
    status: str,
    message: str = "",
    metadata: dict[str, Any] | None = None,
) -> VerificationState:
    normalized = ensure_state_defaults(state)
    now = utc_now()
    normalized["current_agent"] = str(agent_name)
    normalized["current_step"] = str(agent_name)
    normalized["agent_status"] = str(status)

    event = {
        "timestamp": now,
        "agent": str(agent_name),
        "status": str(status),
        "message": str(message or ""),
        "metadata": deepcopy(metadata or {}),
    }
    normalized["agent_history"].append(event)
    return normalized


def stage_has_result(result: Any) -> bool:
    if result is None:
        return False
    if isinstance(result, dict):
        if not result:
            return False
        status = str(result.get("status", "")).upper()
        if status in {STATUS_FAILED, STATUS_FAIL}:
            return False
        return len(result) > 0
    if isinstance(result, list):
        return len(result) > 0
    if isinstance(result, str):
        return bool(result.strip())
    return True


def stage_status(result: Any) -> str:
    if not isinstance(result, dict):
        return STATUS_NOT_STARTED
    return str(result.get("status", STATUS_NOT_STARTED))


def clamp_score(value: Any, minimum: float = 0.0, maximum: float = 100.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = minimum
    return max(minimum, min(maximum, score))


__all__ = [
    "VerificationState",
    "STATUS_NOT_STARTED",
    "STATUS_RUNNING",
    "STATUS_PASS",
    "STATUS_FAIL",
    "STATUS_FAILED",
    "STATUS_SKIPPED",
    "STATUS_DEGRADED",
    "STATUS_COMPLETED",
    "AGENT_NAMES",
    "create_initial_state",
    "ensure_state_defaults",
    "empty_rtl_analysis",
    "empty_verification_plan",
    "empty_simulation",
    "empty_failure_analysis",
    "empty_coverage",
    "empty_red_team",
    "empty_mutation",
    "empty_formal",
    "empty_judge",
    "empty_repair",
    "add_error",
    "add_warning",
    "add_message",
    "update_agent_status",
    "stage_has_result",
    "stage_status",
    "clamp_score",
    "utc_now",
]

