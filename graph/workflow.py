"""
PragyanAI SiliconAI
===================

Agentic RTL / Verilog Verification Workflow.

Pipeline
--------

Specification
    ->
RTL Analyzer
    ->
Verification Planner
    ->
Test Generator
    ->
Testbench Generator
    ->
Simulator
    ->
Failure Analyzer
    ->
Coverage
    ->
Red Team
    ->
Mutation
    ->
Formal
    ->
Verification Judge

Design rules
------------

* One verification run per execution.
* One shared ActivityLogger per run.
* All agents receive the same state.
* No agent result should silently become {}.
* Optional stages explicitly return SKIPPED.
* Simulation evidence comes from deterministic tools.
* LLM is not treated as simulation evidence.
* SymbiYosys is not required.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config.settings import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_RUN_FORMAL,
    DEFAULT_RUN_MUTATION,
    ENABLE_FORMAL,
    ENABLE_MUTATION,
    ENABLE_RED_TEAM,
    MAX_ITERATIONS,
)

from core.state import (
    STATUS_COMPLETED,
    STATUS_DEGRADED,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    VerificationState,
    add_error,
    add_warning,
    ensure_state_defaults,
    update_agent_status,
    create_initial_state,
)

from observability.run_manager import (
    create_verification_run,
    finalize_verification_run,
)


# ============================================================================
# Agent imports
# ============================================================================

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

def _create_agents(
    logger: Any = None,
) -> dict[str, Any]:
    """
    Construct all verification agents.

    The logger is passed when supported by the agent constructor.

    Agents should ideally inherit from agents.base.BaseAgent and use
    the shared run logger.
    """

    agents: dict[str, Any] = {}

    constructors = {
        "rtl_analyzer": RTLAnalyzerAgent,
        "verification_planner": VerificationPlannerAgent,
        "test_generator": TestGeneratorAgent,
        "testbench_generator": TestbenchGeneratorAgent,
        "simulator": SimulatorAgent,
        "failure_analyzer": FailureAnalyzerAgent,
        "coverage": CoverageAgent,
        "red_team": RedTeamAgent,
        "mutation": MutationAgent,
        "formal": FormalAgent,
        "verification_judge": VerificationJudgeAgent,
    }

    for name, constructor in constructors.items():

        try:
            agents[name] = constructor(
                logger=logger
            )

        except TypeError:

            # Compatibility with agents whose constructor does not
            # yet accept logger.
            try:
                agents[name] = constructor()

            except Exception as exc:
                raise RuntimeError(
                    f"Unable to create agent '{name}': {exc}"
                ) from exc

        except Exception as exc:

            raise RuntimeError(
                f"Unable to create agent '{name}': {exc}"
            ) from exc

    return agents


# ============================================================================
# Generic agent execution
# ============================================================================

def _execute_agent(
    state: VerificationState,
    agent: Any,
    agent_name: str,
) -> VerificationState:
    """
    Execute one agent against the shared state.

    The agent may either:

        return state

    or:

        return partial_state

    The result is normalized before being returned.
    """

    state = ensure_state_defaults(
        state
    )

    state = update_agent_status(
        state,
        agent_name,
        STATUS_RUNNING,
        message=f"{agent_name} started.",
    )

    try:

        result = agent(
            state
        )

        if result is None:
            raise RuntimeError(
                f"{agent_name} returned None."
            )

        result = ensure_state_defaults(
            result
        )

        # Preserve run-level references.
        if not result.get(
            "run_id"
        ):
            result["run_id"] = state.get(
                "run_id",
                "",
            )

        if not result.get(
            "run_dir"
        ):
            result["run_dir"] = state.get(
                "run_dir",
                "",
            )

        if result.get(
            "logger"
        ) is None:
            result["logger"] = state.get(
                "logger"
            )

        if result.get(
            "verification_run"
        ) is None:
            result["verification_run"] = state.get(
                "verification_run"
            )

        # --------------------------------------------------------------
        # Agent result validation
        # --------------------------------------------------------------

        stage_key = _stage_key_for_agent(
            agent_name
        )

        stage_result = result.get(
            stage_key
        )

        if stage_key == "generated_tests":

            valid_result = bool(
                isinstance(
                    stage_result,
                    list,
                )
                and len(stage_result) > 0
            )

        elif stage_key == "generated_testbench":

            valid_result = bool(
                isinstance(
                    stage_result,
                    str,
                )
                and stage_result.strip()
            )

        else:

            valid_result = bool(
                isinstance(
                    stage_result,
                    dict,
                )
                and len(stage_result) > 0
            )

        # --------------------------------------------------------------
        # Determine status
        # --------------------------------------------------------------

        existing_status = str(
            result.get(
                "agent_status",
                "",
            )
        ).upper()

        if existing_status in {
            STATUS_FAILED,
            "FAIL",
        }:

            final_status = STATUS_FAILED

        elif existing_status == STATUS_SKIPPED:

            final_status = STATUS_SKIPPED

        elif not valid_result:

            final_status = STATUS_DEGRADED

            result = add_warning(
                result,
                (
                    f"{agent_name} completed execution "
                    "but did not produce expected evidence."
                ),
            )

        else:

            final_status = STATUS_COMPLETED

        result = update_agent_status(
            result,
            agent_name,
            final_status,
            message=(
                f"{agent_name} finished with "
                f"status {final_status}."
            ),
            metadata={
                "result_key": stage_key,
                "evidence_present": valid_result,
            },
        )

        return result

    except Exception as exc:

        message = (
            f"{agent_name} failed: {exc}"
        )

        state = add_error(
            state,
            message,
        )

        state = update_agent_status(
            state,
            agent_name,
            STATUS_FAILED,
            message=message,
        )

        return state


# ============================================================================
# State key mapping
# ============================================================================

def _stage_key_for_agent(
    agent_name: str,
) -> str:
    """
    Map an agent name to its canonical state field.
    """

    mapping = {
        "rtl_analyzer": "rtl_analysis",
        "verification_planner": "verification_plan",
        "test_generator": "generated_tests",
        "testbench_generator": "generated_testbench",
        "simulator": "simulation",
        "failure_analyzer": "failure_analysis",
        "coverage": "coverage",
        "red_team": "red_team",
        "mutation": "mutation",
        "formal": "formal",
        "verification_judge": "verification_judge",
    }

    return mapping.get(
        agent_name,
        agent_name,
    )


# ============================================================================
# Optional-stage helpers
# ============================================================================

def _skip_stage(
    state: VerificationState,
    agent_name: str,
    state_key: str,
    reason: str,
) -> VerificationState:
    """
    Explicitly mark an optional stage as skipped.
    """

    state = ensure_state_defaults(
        state
    )

    state[state_key] = {
        "status": STATUS_SKIPPED,
        "reason": reason,
        "source": "workflow",
    }

    state = update_agent_status(
        state,
        agent_name,
        STATUS_SKIPPED,
        message=reason,
    )

    return state


# ============================================================================
# Main workflow
# ============================================================================

def run_workflow(
    specification: str,
    rtl_code: str,
    project_name: str = "rtl_project",
    reference_testbench: str = "",
    reference_test_vectors: Any = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    run_mutation: bool = DEFAULT_RUN_MUTATION,
    run_formal: bool = DEFAULT_RUN_FORMAL,
    run_red_team: bool = ENABLE_RED_TEAM,
    metadata: dict[str, Any] | None = None,
    verification_run: Any = None,
) -> VerificationState:
    """
    Run the complete agentic verification pipeline.

    Important compatibility behavior
    ---------------------------------

    verification_run is OPTIONAL.

    If main_app.py has already created a VerificationRun, it is reused.

    If not, this function creates one.

    This guarantees that there is exactly one shared logger for one
    verification execution.
    """

    # =========================================================================
    # Normalize arguments
    # =========================================================================

    specification = str(
        specification or ""
    )

    rtl_code = str(
        rtl_code or ""
    )

    project_name = str(
        project_name
        or "rtl_project"
    )

    reference_testbench = str(
        reference_testbench or ""
    )

    if reference_test_vectors is None:
        reference_test_vectors = []

    max_iterations = max(
        1,
        min(
            int(
                max_iterations
                or DEFAULT_MAX_ITERATIONS
            ),
            int(
                MAX_ITERATIONS
            ),
        ),
    )

    run_mutation = bool(
        run_mutation
        and ENABLE_MUTATION
    )

    run_formal = bool(
        run_formal
        and ENABLE_FORMAL
    )

    run_red_team = bool(
        run_red_team
        and ENABLE_RED_TEAM
    )

    metadata = deepcopy(
        metadata or {}
    )


    # =========================================================================
    # Validate input
    # =========================================================================

    if not specification.strip():

        raise ValueError(
            "Functional specification is empty."
        )

    if not rtl_code.strip():

        raise ValueError(
            "RTL / Verilog code is empty."
        )


    # =========================================================================
    # Create/reuse verification run
    # =========================================================================

    owns_run = False

    if verification_run is None:

        verification_run = (
            create_verification_run(
                metadata={
                    **metadata,
                    "project_name": project_name,
                    "source": "graph.workflow",
                }
            )
        )

        owns_run = True


    # =========================================================================
    # Create canonical state
    # =========================================================================

    #
    # IMPORTANT:
    #
    # create_initial_state() does NOT receive verification_run.
    #
    # The run object is attached AFTER state creation.
    #
    # This fixes:
    #
    # TypeError:
    # create_initial_state()
    # got an unexpected keyword argument 'verification_run'
    #

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
        run_id=str(
            verification_run.run_id
        ),
        run_dir=str(
            verification_run.run_dir
        ),
        metadata=metadata,
    )

    # -------------------------------------------------------------------------
    # Attach shared run objects AFTER create_initial_state()
    # -------------------------------------------------------------------------

    state["verification_run"] = (
        verification_run
    )

    state["logger"] = (
        verification_run.logger
    )

    state["run_id"] = (
        verification_run.run_id
    )

    state["run_dir"] = str(
        verification_run.run_dir
    )


    # =========================================================================
    # Log initial inputs
    # =========================================================================

    logger = state.get(
        "logger"
    )

    if logger is not None:

        try:

            logger.info(
                "Verification workflow initialized."
            )

            logger.agent_event(
                "workflow",
                "input_received",
                {
                    "project_name": project_name,
                    "specification_characters": len(
                        specification
                    ),
                    "rtl_characters": len(
                        rtl_code
                    ),
                    "reference_testbench_characters": len(
                        reference_testbench
                    ),
                    "max_iterations": max_iterations,
                    "run_mutation": run_mutation,
                    "run_formal": run_formal,
                    "run_red_team": run_red_team,
                },
            )

        except Exception:
            pass


    # =========================================================================
    # Create agents
    # =========================================================================

    agents = _create_agents(
        logger=logger
    )


    # =========================================================================
    # Iteration loop
    # =========================================================================

    for iteration in range(
        1,
        max_iterations + 1,
    ):

        state["current_iteration"] = (
            iteration
        )

        if logger is not None:

            try:

                logger.info(
                    f"Verification iteration {iteration}/{max_iterations}"
                )

            except Exception:
                pass


        # ---------------------------------------------------------------------
        # 1. RTL Analyzer
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["rtl_analyzer"],
            "rtl_analyzer",
        )


        # ---------------------------------------------------------------------
        # 2. Verification Planner
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["verification_planner"],
            "verification_planner",
        )


        # ---------------------------------------------------------------------
        # 3. Test Generator
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["test_generator"],
            "test_generator",
        )


        # ---------------------------------------------------------------------
        # 4. Testbench Generator
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["testbench_generator"],
            "testbench_generator",
        )


        # ---------------------------------------------------------------------
        # 5. Simulator
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["simulator"],
            "simulator",
        )


        # ---------------------------------------------------------------------
        # 6. Failure Analyzer
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["failure_analyzer"],
            "failure_analyzer",
        )


        # ---------------------------------------------------------------------
        # 7. Coverage
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["coverage"],
            "coverage",
        )


        # ---------------------------------------------------------------------
        # 8. Red Team
        # ---------------------------------------------------------------------

        if run_red_team:

            state = _execute_agent(
                state,
                agents["red_team"],
                "red_team",
            )

        else:

            state = _skip_stage(
                state,
                "red_team",
                "red_team",
                "Red-Team verification disabled.",
            )


        # ---------------------------------------------------------------------
        # 9. Mutation
        # ---------------------------------------------------------------------

        if run_mutation:

            state = _execute_agent(
                state,
                agents["mutation"],
                "mutation",
            )

        else:

            state = _skip_stage(
                state,
                "mutation",
                "mutation",
                "Mutation testing disabled.",
            )


        # ---------------------------------------------------------------------
        # 10. Formal
        # ---------------------------------------------------------------------

        if run_formal:

            state = _execute_agent(
                state,
                agents["formal"],
                "formal",
            )

        else:

            state = _skip_stage(
                state,
                "formal",
                "formal",
                "Formal verification disabled.",
            )


        # ---------------------------------------------------------------------
        # 11. Verification Judge
        # ---------------------------------------------------------------------

        state = _execute_agent(
            state,
            agents["verification_judge"],
            "verification_judge",
        )


        # ---------------------------------------------------------------------
        # Check whether another iteration is necessary
        # ---------------------------------------------------------------------

        judge = state.get(
            "verification_judge",
            {},
        )

        if isinstance(
            judge,
            dict,
        ):

            verdict = str(
                judge.get(
                    "verdict",
                    "",
                )
            ).upper()

            score = float(
                judge.get(
                    "verification_score",
                    0,
                )
                or 0
            )

        else:

            verdict = ""
            score = 0.0


        # ---------------------------------------------------------------------
        # Successful verification
        # ---------------------------------------------------------------------

        if verdict in {
            "PASS",
            "PASSED",
        }:

            state["final_verdict"] = (
                "PASS"
            )

            state["verification_score"] = (
                score
            )

            break


        # ---------------------------------------------------------------------
        # No need to iterate beyond configured count
        # ---------------------------------------------------------------------

        if iteration >= max_iterations:

            break


        # ---------------------------------------------------------------------
        # Prepare next iteration
        # ---------------------------------------------------------------------

        if logger is not None:

            try:

                logger.info(
                    "Verification target not yet reached; "
                    "continuing to next iteration."
                )

            except Exception:
                pass


    # =========================================================================
    # Final normalization
    # =========================================================================

    state = ensure_state_defaults(
        state
    )


    # =========================================================================
    # Synchronize final judge values
    # =========================================================================

    judge = state.get(
        "verification_judge",
        {},
    )

    if isinstance(
        judge,
        dict,
    ):

        if judge.get(
            "verdict"
        ):

            state["final_verdict"] = (
                str(
                    judge.get(
                        "verdict"
                    )
                )
            )

        if judge.get(
            "verification_score"
        ) is not None:

            try:

                state["verification_score"] = float(
                    judge.get(
                        "verification_score"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        if judge.get(
            "confidence"
        ) is not None:

            try:

                state["confidence"] = float(
                    judge.get(
                        "confidence"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                pass


    # =========================================================================
    # Final status
    # =========================================================================

    state["current_agent"] = (
        "verification_judge"
    )

    state["current_step"] = (
        "verification_complete"
    )

    if state.get(
        "final_verdict"
    ) == "PASS":

        state["agent_status"] = (
            STATUS_COMPLETED
        )

    elif state.get(
        "errors"
    ):

        state["agent_status"] = (
            STATUS_DEGRADED
        )

    else:

        state["agent_status"] = (
            STATUS_COMPLETED
        )


    # =========================================================================
    # Log final state
    # =========================================================================

    if logger is not None:

        try:

            logger.info(
                "Verification workflow completed."
            )

            logger.agent_event(
                "workflow",
                "verification_completed",
                {
                    "run_id": state.get(
                        "run_id"
                    ),
                    "final_verdict": state.get(
                        "final_verdict"
                    ),
                    "verification_score": state.get(
                        "verification_score"
                    ),
                    "confidence": state.get(
                        "confidence"
                    ),
                    "errors": len(
                        state.get(
                            "errors",
                            []
                        )
                    ),
                    "warnings": len(
                        state.get(
                            "warnings",
                            []
                        )
                    ),
                },
            )

            logger.write_state_snapshot(
                state
            )

        except Exception:
            pass


    # =========================================================================
    # Finalize owned run
    # =========================================================================

    if owns_run:

        try:

            finalize_verification_run(
                verification_run,
                state=state,
                status="COMPLETED",
                final_verdict=state.get(
                    "final_verdict",
                    "NEED_MORE",
                ),
            )

        except Exception:

            # Never destroy a valid verification state merely because
            # final logging failed.
            pass


    return state


# ============================================================================
# Public exports
# ============================================================================

__all__ = [
    "run_workflow",
]

