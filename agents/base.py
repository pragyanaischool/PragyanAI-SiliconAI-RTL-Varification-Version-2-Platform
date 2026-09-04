"""
PragyanAI SiliconAI
===================

Base class for all verification agents.

Every agent receives the SAME ActivityLogger from LangGraph state.

Agents should NOT instantiate ActivityLogger themselves.
"""

from __future__ import annotations

import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.state import VerificationState
from observability.activity_logger import ActivityLogger


class BaseAgent(ABC):
    """
    Base class for all PragyanAI SiliconAI verification agents.

    Responsibilities
    ----------------

    - Agent lifecycle logging
    - Duration measurement
    - Error handling
    - State updates
    - Artifact directory creation
    - Iteration-aware logging
    """

    name: str = "BaseAgent"

    step_name: str = "verification"

    def __init__(
        self,
        name: Optional[str] = None,
    ) -> None:

        if name:
            self.name = name

    # ========================================================================
    # Logger
    # ========================================================================

    def get_logger(
        self,
        state: VerificationState,
    ) -> Optional[ActivityLogger]:
        """
        Get the shared run-level ActivityLogger.
        """

        logger = state.get(
            "logger"
        )

        if isinstance(
            logger,
            ActivityLogger,
        ):
            return logger

        verification_run = state.get(
            "verification_run"
        )

        if verification_run is not None:

            run_logger = getattr(
                verification_run,
                "logger",
                None,
            )

            if isinstance(
                run_logger,
                ActivityLogger,
            ):
                return run_logger

        return None

    # ========================================================================
    # Main invocation
    # ========================================================================

    def __call__(
        self,
        state: VerificationState,
    ) -> VerificationState:
        """
        Execute one agent with automatic lifecycle logging.
        """

        start_time = time.perf_counter()

        logger = self.get_logger(
            state
        )

        iteration = state.get(
            "iteration",
            0,
        )

        state["current_agent"] = self.name

        state["current_step"] = self.step_name

        state["agent_status"] = "running"

        # --------------------------------------------------------------------
        # Agent start
        # --------------------------------------------------------------------

        if logger:

            logger.started(
                self.name,
                iteration=iteration,
                metadata={
                    "step": self.step_name,
                    "state_keys": sorted(
                        state.keys()
                    ),
                },
            )

        try:

            # ---------------------------------------------------------------
            # Agent implementation
            # ---------------------------------------------------------------

            result = self.run(
                state
            )

            # ---------------------------------------------------------------
            # Support agents that return None.
            # ---------------------------------------------------------------

            if result is None:
                result = state

            # ---------------------------------------------------------------
            # Ensure result is a mutable state dictionary.
            # ---------------------------------------------------------------

            if not isinstance(
                result,
                dict,
            ):
                raise TypeError(
                    f"{self.name}.run() must return a state dict, "
                    f"got {type(result).__name__}"
                )

            state = result

            state["current_agent"] = self.name

            state["current_step"] = self.step_name

            state["agent_status"] = "completed"

            duration = (
                time.perf_counter()
                - start_time
            )

            # ---------------------------------------------------------------
            # Completion logging
            # ---------------------------------------------------------------

            if logger:

                logger.completed(
                    self.name,
                    iteration=iteration,
                    duration_seconds=round(
                        duration,
                        6,
                    ),
                    metadata=self.output_metadata(
                        state
                    ),
                )

            return state

        except Exception as exc:

            duration = (
                time.perf_counter()
                - start_time
            )

            state["agent_status"] = "failed"

            errors = list(
                state.get(
                    "errors",
                    [],
                )
            )

            errors.append(
                f"{self.name}: {exc}"
            )

            state["errors"] = errors

            # ---------------------------------------------------------------
            # Detailed exception logging
            # ---------------------------------------------------------------

            if logger:

                logger.failed(
                    self.name,
                    exc,
                    iteration=iteration,
                    duration_seconds=round(
                        duration,
                        6,
                    ),
                    metadata={
                        "step": self.step_name,
                        "traceback": "".join(
                            traceback.format_exception(
                                type(exc),
                                exc,
                                exc.__traceback__,
                            )
                        ),
                    },
                )

            # Re-raise so LangGraph / workflow can decide how to handle it.
            raise

    # ========================================================================
    # Agent implementation
    # ========================================================================

    @abstractmethod
    def run(
        self,
        state: VerificationState,
    ) -> VerificationState:
        """
        Implement the actual agent logic here.
        """

        raise NotImplementedError

    # ========================================================================
    # Metadata
    # ========================================================================

    def input_metadata(
        self,
        state: VerificationState,
    ) -> Dict[str, Any]:
        """
        Metadata describing agent inputs.

        Override when an agent needs additional information.
        """

        return {
            "project_name": state.get(
                "project_name"
            ),
            "iteration": state.get(
                "iteration",
                0,
            ),
        }

    def output_metadata(
        self,
        state: VerificationState,
    ) -> Dict[str, Any]:
        """
        Metadata describing agent outputs.

        Avoid logging enormous source-code fields here.
        """

        return {
            "current_step": state.get(
                "current_step"
            ),
            "agent_status": state.get(
                "agent_status"
            ),
            "errors": len(
                state.get(
                    "errors",
                    [],
                )
            ),
            "warnings": len(
                state.get(
                    "warnings",
                    [],
                )
            ),
        }

    # ========================================================================
    # Agent artifact helpers
    # ========================================================================

    def artifact_directory(
        self,
        state: VerificationState,
    ):
        """
        Return the artifact directory for this agent.

        The directory sequence is created by the shared logger.
        """

        logger = self.get_logger(
            state
        )

        if logger is None:
            return None

        return logger.agent_dir(
            self.name
        )

    def write_artifact(
        self,
        state: VerificationState,
        relative_path: str,
        content: Any,
        *,
        artifact_type: str = "text",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Write an artifact using the shared run logger.

        `relative_path` is interpreted relative to the run directory.
        """

        logger = self.get_logger(
            state
        )

        if logger is None:
            return None

        return logger.write_text(
            relative_path,
            content,
            artifact_type=artifact_type,
            agent=self.name,
            description=description,
            metadata=metadata,
        )

    def write_json_artifact(
        self,
        state: VerificationState,
        relative_path: str,
        payload: Any,
        *,
        artifact_type: str = "json",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Write a JSON artifact using the shared logger.
        """

        logger = self.get_logger(
            state
        )

        if logger is None:
            return None

        return logger.write_json(
            relative_path,
            payload,
            artifact_type=artifact_type,
            agent=self.name,
            description=description,
            metadata=metadata,
        )

    def write_code_artifact(
        self,
        state: VerificationState,
        relative_path: str,
        code: str,
        *,
        language: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Write a source-code artifact.
        """

        logger = self.get_logger(
            state
        )

        if logger is None:
            return None

        return logger.write_code(
            relative_path,
            code,
            language=language,
            agent=self.name,
            description=description,
            metadata=metadata,
        )

    # ========================================================================
    # Logging helpers
    # ========================================================================

    def info(
        self,
        state: VerificationState,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write an informational event.
        """

        logger = self.get_logger(
            state
        )

        if logger:

            logger.info(
                message,
                agent=self.name,
                iteration=state.get(
                    "iteration",
                    0,
                ),
                metadata=metadata,
            )

    def warning(
        self,
        state: VerificationState,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write a warning event.
        """

        logger = self.get_logger(
            state
        )

        if logger:

            logger.warning(
                message,
                agent=self.name,
                iteration=state.get(
                    "iteration",
                    0,
                ),
                metadata=metadata,
            )

    def error(
        self,
        state: VerificationState,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write an error event.
        """

        logger = self.get_logger(
            state
        )

        if logger:

            logger.error(
                message,
                agent=self.name,
                iteration=state.get(
                    "iteration",
                    0,
                ),
                metadata=metadata,
            )

    def event(
        self,
        state: VerificationState,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write a custom agent event.
        """

        logger = self.get_logger(
            state
        )

        if logger:

            logger.agent_event(
                self.name,
                event_type,
                message,
                iteration=state.get(
                    "iteration",
                    0,
                ),
                metadata=metadata,
            )


__all__ = [
    "BaseAgent",
]
