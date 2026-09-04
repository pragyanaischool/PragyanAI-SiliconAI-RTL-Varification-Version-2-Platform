"""
PragyanAI SiliconAI
===================

LangGraph verification workflow.

The workflow creates ONE verification run and ONE ActivityLogger.

All agents operate on the same state and therefore share the same
observability context.

Workflow
--------

RTL Analyzer
     ↓
Verification Planner
     ↓
Test Generator
     ↓
Testbench Generator
     ↓
Simulator
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
Judge
     ↓
Finalization
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from config.settings import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RUN_FORMAL,
    DEFAULT_RUN_MUTATION,
    ENABLE_RED_TEAM,
)

from core.state import (
    VerificationState,
    create_initial_state,
)

from observability.run_manager import (
    create_verification_run,
    finalize_from_state,
)

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

from agents.rtl_analyzer import RTLAnalyzerAgent
from agents.verification_planner import VerificationPlannerAgent
from agents.test_generator import TestGeneratorAgent
from agents.testbench_generator import TestbenchGeneratorAgent
from agents.simulator_agent import SimulatorAgent
from agents.failure_analyzer import FailureAnalyzerAgent
from agents.coverage_agent import CoverageAgent
from agents.red_team_agent import RedTeamAgent
from agents.mutation_agent import MutationAgent
from agents.formal_agent import FormalAgent
from agents.verification_judge import VerificationJudgeAgent


# ============================================================================
# Agent construction
# ============================================================================

def build_agents() -> Dict[str, Any]:
    """
    Construct all verification agents.

    Agents do not create loggers here.

    The logger belongs to the verification run, not the agent.
    """

    return {
        "rtl_analyzer": RTLAnalyzerAgent(),

        "verification_planner": VerificationPlannerAgent(),

        "test_generator": TestGeneratorAgent(),

        "testbench_generator": TestbenchGeneratorAgent(),

        "simulator": SimulatorAgent(),

        "failure_analyzer": FailureAnalyzerAgent(),

        "coverage": CoverageAgent(),

        "red_team": RedTeamAgent(),

        "mutation": MutationAgent(),

        "formal": FormalAgent(),

        "judge": VerificationJudgeAgent(),
    }


# ============================================================================
# Simple sequential execution
# ============================================================================

def _execute_agent(
    state: VerificationState,
    agent: Any,
) -> VerificationState:
    """
    Execute one agent.

    The BaseAgent class handles lifecycle logging.
    """

    return agent(
        state
    )


# ============================================================================
# Workflow runner
# ============================================================================

def run_workflow(
    *,
    specification: str,
    rtl_code: str,
    project_name: str = "custom_rtl",
    reference_testbench: str = "",
    reference_test_vectors: Any = None,
    max_iterations: Optional[int] = None,
    run_mutation: Optional[bool] = None,
    run_formal: Optional[bool] = None,
    run_red_team: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> VerificationState:
    """
    Execute the complete verification workflow.

    This function creates exactly ONE VerificationRun.

    Parameters
    ----------
    specification:
        RTL functional specification.

    rtl_code:
        Verilog/SystemVerilog source.

    project_name:
        Human-readable project/sample name.

    reference_testbench:
        Optional reference testbench.

    reference_test_vectors:
        Optional expected test vectors.

    max_iterations:
        Maximum verification iterations.

    run_mutation:
        Whether mutation testing is enabled.

    run_formal:
        Whether formal verification is enabled.

    run_red_team:
        Whether red-team testing is enabled.

    metadata:
        Additional run metadata.
    """

    # ------------------------------------------------------------------------
    # Configuration defaults
    # ------------------------------------------------------------------------

    iterations = (
        max_iterations
        if max_iterations is not None
        else DEFAULT_MAX_ITERATIONS
    )

    mutation_enabled = (
        run_mutation
        if run_mutation is not None
        else DEFAULT_RUN_MUTATION
    )

    formal_enabled = (
        run_formal
        if run_formal is not None
        else DEFAULT_RUN_FORMAL
    )

    red_team_enabled = (
        run_red_team
        if run_red_team is not None
        else ENABLE_RED_TEAM
    )

    # ------------------------------------------------------------------------
    # Create ONE verification run.
    # ------------------------------------------------------------------------

    run_metadata = dict(
        metadata or {}
    )

    run_metadata.update(
        {
            "project_name": project_name,
            "mutation_enabled": mutation_enabled,
            "formal_enabled": formal_enabled,
            "red_team_enabled": red_team_enabled,
            "max_iterations": iterations,
        }
    )

    verification_run = create_verification_run(
        metadata=run_metadata
    )

    # ------------------------------------------------------------------------
    # Create initial state with shared logger.
    # ------------------------------------------------------------------------

    state = create_initial_state(
        specification=specification,
        rtl_code=rtl_code,
        project_name=project_name,
        reference_testbench=reference_testbench,
        reference_test_vectors=reference_test_vectors,
        max_iterations=iterations,
        verification_run=verification_run,
    )

    logger = verification_run.logger

    logger.info(
        "LangGraph verification workflow initialized.",
        metadata={
            "project_name": project_name,
            "run_mutation": mutation_enabled,
            "run_formal": formal_enabled,
            "run_red_team": red_team_enabled,
            "max_iterations": iterations,
        },
    )

    # ------------------------------------------------------------------------
    # Build agents.
    # ------------------------------------------------------------------------

    agents = build_agents()

    try:

        # ====================================================================
        # Main verification flow
        # ====================================================================

        state = _execute_agent(
            state,
            agents["rtl_analyzer"],
        )

        state = _execute_agent(
            state,
            agents["verification_planner"],
        )

        state = _execute_agent(
            state,
            agents["test_generator"],
        )

        state = _execute_agent(
            state,
            agents["testbench_generator"],
        )

        state = _execute_agent(
            state,
            agents["simulator"],
        )

        # ====================================================================
        # Failure analysis
        # ====================================================================

        state = _execute_agent(
            state,
            agents["failure_analyzer"],
        )

        # ====================================================================
        # Coverage
        # ====================================================================

        state = _execute_agent(
            state,
            agents["coverage"],
        )

        # ====================================================================
        # Red team
        # ====================================================================

        if red_team_enabled:

            state = _execute_agent(
                state,
                agents["red_team"],
            )

        else:

            logger.info(
                "Red-team verification disabled."
            )

            state["red_team_results"] = {
                "status": "disabled"
            }

        # ====================================================================
        # Mutation
        # ====================================================================

        if mutation_enabled:

            state = _execute_agent(
                state,
                agents["mutation"],
            )

        else:

            logger.info(
                "Mutation verification disabled."
            )

            state["mutation_results"] = {
                "status": "disabled"
            }

        # ====================================================================
        # Formal
        # ====================================================================

        if formal_enabled:

            state = _execute_agent(
                state,
                agents["formal"],
            )

        else:

            logger.info(
                "Formal verification disabled."
            )

            state["formal_results"] = {
                "status": "disabled"
            }

            state["formal_status"] = "disabled"

        # ====================================================================
        # Judge
        # ====================================================================

        state = _execute_agent(
            state,
            agents["judge"],
        )

        # ====================================================================
        # Final state
        # ====================================================================

        state["agent_status"] = "completed"

        # If judge didn't produce a verdict, derive one.
        if not state.get(
            "final_verdict"
        ):

            state["final_verdict"] = state.get(
                "judge_verdict",
                "INCONCLUSIVE",
            )

        logger.info(
            "Verification workflow completed.",
            metadata={
                "final_verdict": state.get(
                    "final_verdict"
                ),
                "verification_score": state.get(
                    "verification_score",
                    0.0,
                ),
                "coverage_score": state.get(
                    "coverage_score",
                    0.0,
                ),
                "mutation_score": state.get(
                    "mutation_score",
                    0.0,
                ),
            },
        )

        # ====================================================================
        # Finalize one run
        # ====================================================================

        finalize_from_state(
            state,
            run=verification_run,
            close_logger=False,
        )

        return state

    except Exception as exc:

        # --------------------------------------------------------------------
        # Log workflow failure.
        # --------------------------------------------------------------------

        logger.log_exception(
            "workflow_failed",
            exc,
            agent=state.get(
                "current_agent"
            ),
            iteration=state.get(
                "iteration",
                0,
            ),
        )

        state["agent_status"] = "failed"

        # --------------------------------------------------------------------
        # Finalize failed run.
        # --------------------------------------------------------------------

        try:

            finalize_from_state(
                state,
                run=verification_run,
                metadata={
                    "error": str(exc),
                },
                close_logger=False,
            )

        except Exception as finalize_error:

            logger.error(
                "Failed to finalize verification run.",
                metadata={
                    "error": str(
                        finalize_error
                    )
                },
            )

        raise


# ============================================================================
# Convenience wrapper
# ============================================================================

def run_verification(
    specification: str,
    rtl_code: str,
    **kwargs: Any,
) -> VerificationState:
    """
    Backward-compatible convenience wrapper.

    Example:

        state = run_verification(
            specification=spec,
            rtl_code=rtl,
        )
    """

    return run_workflow(
        specification=specification,
        rtl_code=rtl_code,
        **kwargs,
    )


__all__ = [
    "build_agents",
    "run_workflow",
    "run_verification",
]

