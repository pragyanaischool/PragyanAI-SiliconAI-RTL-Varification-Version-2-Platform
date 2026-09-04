"""
PragyanAI SiliconAI
===================

Base class for all verification agents.

Every agent automatically records:

- start
- completion
- failure
- duration
- iteration
- metadata
- exception traceback
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from observability.activity_logger import (
    ActivityLogger,
)


class BaseAgent(ABC):
    """
    Common base class for all verification agents.
    """

    name = "base_agent"

    def __init__(
        self,
        logger: ActivityLogger | None = None,
    ) -> None:

        self.logger = logger

    # ------------------------------------------------------------------
    # Agent implementation
    # ------------------------------------------------------------------

    @abstractmethod
    def run(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Implement agent-specific behavior here.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def input_metadata(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return lightweight input metadata.

        Do not log huge RTL contents here.
        Actual artifacts are stored separately.
        """

        rtl = state.get(
            "rtl_code",
            state.get(
                "current_rtl",
                "",
            ),
        )

        specification = state.get(
            "specification",
            "",
        )

        tests = state.get(
            "generated_tests",
            [],
        )

        return {
            "rtl_chars": (
                len(rtl)
                if isinstance(rtl, str)
                else 0
            ),
            "specification_chars": (
                len(specification)
                if isinstance(
                    specification,
                    str,
                )
                else 0
            ),
            "test_count": (
                len(tests)
                if isinstance(
                    tests,
                    list,
                )
                else 0
            ),
            "iteration": state.get(
                "iteration",
                0,
            ),
        }

    def output_metadata(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return lightweight output metadata.
        """

        metadata: dict[str, Any] = {}

        for key in (
            "status",
            "simulation_passed",
            "compile_passed",
            "coverage_percent",
            "mutation_score",
            "verification_score",
            "final_verdict",
            "verdict",
        ):
            if key in result:
                value = result[key]

                if isinstance(
                    value,
                    (str, int, float, bool),
                ):
                    metadata[key] = value

        return metadata

    # ------------------------------------------------------------------
    # Execution wrapper
    # ------------------------------------------------------------------

    def execute(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute the agent with complete lifecycle logging.
        """

        started_at = time.perf_counter()

        iteration = int(
            state.get(
                "iteration",
                0,
            )
            or 0
        )

        agent_name = self.name

        if self.logger:
            self.logger.started(
                agent=agent_name,
                iteration=iteration,
                metadata=self.input_metadata(
                    state
                ),
            )

        # Keep current agent visible in state.
        state["current_agent"] = agent_name
        state["current_step"] = agent_name
        state["agent_status"] = "RUNNING"

        try:

            result = self.run(
                state
            )

            if result is None:
                result = state

            if not isinstance(
                result,
                dict,
            ):
                raise TypeError(
                    f"{agent_name}.run() must return "
                    f"a dictionary, got "
                    f"{type(result).__name__}"
                )

            # Merge the returned state.
            state.update(result)

            state["current_agent"] = agent_name
            state["current_step"] = agent_name
            state["agent_status"] = "COMPLETED"

            duration = (
                time.perf_counter()
                - started_at
            )

            if self.logger:
                self.logger.completed(
                    agent=agent_name,
                    duration_seconds=duration,
                    iteration=iteration,
                    metadata=self.output_metadata(
                        result
                    ),
                )

            return state

        except Exception as exc:

            duration = (
                time.perf_counter()
                - started_at
            )

            state["current_agent"] = agent_name
            state["current_step"] = agent_name
            state["agent_status"] = "FAILED"

            errors = state.setdefault(
                "errors",
                [],
            )

            if isinstance(
                errors,
                list,
            ):
                errors.append(
                    {
                        "agent": agent_name,
                        "error": str(exc),
                    }
                )

            if self.logger:
                self.logger.failed(
                    agent=agent_name,
                    duration_seconds=duration,
                    error=self.logger.exception_text(
                        exc
                    ),
                    iteration=iteration,
                )

            raise
