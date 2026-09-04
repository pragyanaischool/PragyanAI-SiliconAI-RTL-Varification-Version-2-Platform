"""Shared verification state."""

from __future__ import annotations

from typing import Any, TypedDict

class VerificationState(TypedDict, total=False):
    run_id: str
    run_dir: str
    prompt: str
    specification: str
    rtl_code: str
    original_rtl: str
    current_rtl: str
    repaired_rtl: str

    rtl_analysis: dict[str, Any]
    verification_plan: dict[str, Any]
    generated_tests: list[dict[str, Any]]
    testbench: str

    compile_passed: bool
    simulation_passed: bool
    compile_output: str
    simulation_output: str
    simulation_result: dict[str, Any]

    failure_analysis: dict[str, Any]
    coverage: dict[str, Any]
    red_team_results: list[dict[str, Any]]
    mutation_results: list[dict[str, Any]]
    mutation_score: float
    formal_result: dict[str, Any]
    judge_result: dict[str, Any]

    iteration: int
    max_iterations: int
    run_mutation: bool
    run_formal: bool

    current_agent: str
    status: str
    final_verdict: str
    errors: list[str]
    warnings: list[str]

def create_initial_state(
    rtl_code: str,
    specification: str = "",
    prompt: str = "",
    max_iterations: int = 3,
    run_mutation: bool = True,
    run_formal: bool = False,
) -> VerificationState:
    return {
        "prompt": prompt,
        "specification": specification,
        "rtl_code": rtl_code,
        "original_rtl": rtl_code,
        "current_rtl": rtl_code,
        "iteration": 0,
        "max_iterations": max_iterations,
        "run_mutation": run_mutation,
        "run_formal": run_formal,
        "status": "initialized",
        "final_verdict": "UNKNOWN",
        "errors": [],
        "warnings": [],
    }
