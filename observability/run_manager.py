"""
PragyanAI SiliconAI
===================

Verification Run Manager
------------------------

This module manages the lifecycle of one complete RTL / Verilog
verification run.

Architecture
------------

One user verification request creates exactly one:

    VerificationRun
          |
          +-- run_id
          |
          +-- run_dir
          |
          +-- ActivityLogger
          |
          +-- run metadata
          |
          +-- artifacts
          |
          +-- agent activity
          |
          +-- workflow logs
          |
          +-- final verdict

The SAME ActivityLogger instance should be passed through the complete
LangGraph workflow.

Example
-------

    from observability.run_manager import (
        create_verification_run,
        finalize_from_state,
    )

    run = create_verification_run(
        metadata={
            "project": "counter_4bit",
            "source": "streamlit",
        }
    )

    logger = run.logger

    state = {
        "run_id": run.run_id,
        "logger": logger,
    }

    # Execute LangGraph workflow...

    finalize_from_state(state)

Expected directory
------------------

runtime/
└── runs/
    └── <run_id>/
        ├── run_manifest.json
        ├── artifact_manifest.json
        ├── agent_activity.jsonl
        ├── workflow.log
        │
        ├── 01_rtl_analysis/
        ├── 02_planning/
        ├── 03_test_generation/
        ├── 04_testbench_generation/
        ├── 05_simulation/
        ├── 06_failure_analysis/
        ├── 07_coverage/
        ├── 08_red_team/
        ├── 09_mutation/
        ├── 10_formal/
        └── 11_judge/

Important
---------

This module does NOT create a package called "logging".

Use:

    observability.activity_logger

instead of:

    logging.activity_logger

This prevents collisions with Python's standard-library logging module.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from config.settings import (
    LOG_ROOT,
    RUNTIME_ROOT,
    RUN_ROOT,
)

from observability.activity_logger import (
    ActivityLogger,
    safe_json_value,
    utc_now,
)


# ============================================================================
# Run ID
# ============================================================================

def create_run_id(
    prefix: str = "run",
) -> str:
    """
    Create a unique verification run ID.

    Example:

        run_20260904T082530_7f31c4a2

    The timestamp makes the directory human-readable while the UUID
    fragment provides uniqueness.
    """

    timestamp = utc_now()

    # Example:
    #
    # 2026-09-04T08:25:30.123456+00:00
    #
    # becomes:
    #
    # 20260904T082530

    timestamp_text = re.sub(
        r"[^0-9]",
        "",
        timestamp,
    )[:15]

    unique = uuid.uuid4().hex[:8]

    clean_prefix = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(prefix).strip() or "run",
    )

    return (
        f"{clean_prefix}_"
        f"{timestamp_text}_"
        f"{unique}"
    )


# ============================================================================
# Verification Run
# ============================================================================

@dataclass
class VerificationRun:
    """
    Represents one complete RTL verification execution.

    Attributes
    ----------
    run_id:
        Unique identifier for this verification run.

    run_dir:
        Filesystem directory containing all run artifacts.

    logger:
        ONE ActivityLogger shared by all agents in this run.

    started_at:
        UTC timestamp at run creation.

    metadata:
        Metadata supplied by the caller.

    status:
        Current lifecycle state.

    final_verdict:
        Final judge verdict, if available.
    """

    run_id: str

    run_dir: Path

    logger: ActivityLogger

    started_at: str

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    status: str = "created"

    final_verdict: Optional[str] = None

    # ------------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------------

    def mark_running(self) -> None:
        """
        Mark this run as running.
        """

        self.status = "running"

        self.logger.run_started(
            metadata=self.metadata
        )

    def mark_completed(
        self,
        verdict: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark this run as successfully completed.
        """

        self.status = "completed"

        if verdict is not None:
            self.final_verdict = str(verdict)

        self.logger.run_completed(
            verdict=self.final_verdict,
            metadata=metadata,
        )

    def mark_failed(
        self,
        error: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark this run as failed.
        """

        self.status = "failed"

        self.logger.run_failed(
            error,
            metadata=metadata,
        )

    def close(self) -> None:
        """
        Close the underlying ActivityLogger.
        """

        self.logger.close()


# ============================================================================
# Directory helpers
# ============================================================================

def _resolve_run_root() -> Path:
    """
    Resolve the configured run root.

    The preferred configuration is:

        RUN_ROOT

    If unavailable, fall back to:

        RUNTIME_ROOT / "runs"

    Finally fall back to:

        runtime/runs
    """

    try:
        configured = RUN_ROOT

    except NameError:
        configured = None

    if configured:
        return Path(configured)

    try:
        runtime_root = RUNTIME_ROOT

    except NameError:
        runtime_root = None

    if runtime_root:
        return Path(runtime_root) / "runs"

    return Path("runtime") / "runs"


def _resolve_log_root() -> Path:
    """
    Resolve the configured logging root.

    LOG_ROOT is used as a compatibility fallback for deployments that
    configure logs separately from run artifacts.
    """

    try:
        configured = LOG_ROOT

    except NameError:
        configured = None

    if configured:
        return Path(configured)

    return _resolve_run_root()


def _ensure_run_directories(
    run_dir: Path,
) -> None:
    """
    Create the run directory and common artifact directories.
    """

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # These directories make the artifact layout predictable.
    common_directories = [
        "state_snapshots",
        "01_rtl_analysis",
        "02_planning",
        "03_test_generation",
        "04_testbench_generation",
        "05_simulation",
        "06_failure_analysis",
        "07_coverage",
        "08_red_team",
        "09_mutation",
        "10_formal",
        "11_judge",
    ]

    for directory in common_directories:

        (
            run_dir / directory
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================================
# Create verification run
# ============================================================================

def create_verification_run(
    metadata: Optional[Mapping[str, Any]] = None,
    *,
    run_id: Optional[str] = None,
    prefix: str = "run",
    mark_running: bool = True,
) -> VerificationRun:
    """
    Create exactly ONE verification run and ONE shared logger.

    Parameters
    ----------
    metadata:
        Optional run metadata.

    run_id:
        Optional explicit run ID. Normally leave this as None.

    prefix:
        Prefix for generated run IDs.

    mark_running:
        If True, immediately log run_started.

    Returns
    -------
    VerificationRun
        A run object containing the shared logger.

    Example
    -------

        run = create_verification_run(
            metadata={
                "project": "counter_4bit",
                "user_action": "verify",
            }
        )

        logger = run.logger

        state = {
            "run_id": run.run_id,
            "logger": logger,
        }
    """

    final_run_id = (
        str(run_id)
        if run_id
        else create_run_id(prefix)
    )

    metadata_dict = dict(
        metadata or {}
    )

    run_root = _resolve_run_root()

    run_dir = (
        run_root / final_run_id
    )

    _ensure_run_directories(
        run_dir
    )

    # ------------------------------------------------------------------------
    # Store environment information.
    # ------------------------------------------------------------------------

    enriched_metadata = dict(
        metadata_dict
    )

    enriched_metadata.setdefault(
        "platform",
        "PragyanAI SiliconAI",
    )

    enriched_metadata.setdefault(
        "run_id",
        final_run_id,
    )

    enriched_metadata.setdefault(
        "process_id",
        os.getpid(),
    )

    enriched_metadata.setdefault(
        "run_root",
        str(run_root),
    )

    enriched_metadata.setdefault(
        "log_root",
        str(_resolve_log_root()),
    )

    # ------------------------------------------------------------------------
    # IMPORTANT:
    #
    # Exactly ONE ActivityLogger is created here.
    #
    # Do not create ActivityLogger inside individual agents.
    # ------------------------------------------------------------------------

    logger = ActivityLogger(
        run_id=final_run_id,
        run_dir=run_dir,
        metadata=enriched_metadata,
    )

    run = VerificationRun(
        run_id=final_run_id,
        run_dir=run_dir,
        logger=logger,
        started_at=utc_now(),
        metadata=enriched_metadata,
        status="created",
    )

    if mark_running:
        run.mark_running()

    return run


# ============================================================================
# Finalize verification run
# ============================================================================

def finalize_verification_run(
    run: VerificationRun,
    *,
    verdict: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    close_logger: bool = False,
) -> VerificationRun:
    """
    Finalize a VerificationRun.

    Parameters
    ----------
    run:
        VerificationRun returned by create_verification_run().

    verdict:
        Final verification verdict.

        Typical values:

            PASS
            FAIL
            INCONCLUSIVE
            ERROR

    status:
        Explicit lifecycle status.

        If omitted, it is inferred from the verdict.

    metadata:
        Additional final metadata.

    close_logger:
        If True, close the underlying logger after finalization.

    Returns
    -------
    VerificationRun
        The updated run object.
    """

    final_metadata = dict(
        metadata or {}
    )

    if verdict is not None:
        run.final_verdict = str(
            verdict
        )

    # ------------------------------------------------------------------------
    # Infer status.
    # ------------------------------------------------------------------------

    if status is None:

        normalized_verdict = (
            str(
                run.final_verdict or ""
            )
            .strip()
            .upper()
        )

        if normalized_verdict in {
            "FAIL",
            "FAILED",
            "ERROR",
            "CRASH",
        }:

            status = "failed"

        else:

            status = "completed"

    normalized_status = (
        str(status)
        .strip()
        .lower()
    )

    # ------------------------------------------------------------------------
    # Finalize.
    # ------------------------------------------------------------------------

    if normalized_status == "failed":

        run.mark_failed(
            error=final_metadata.get(
                "error",
                "Verification run failed",
            ),
            metadata=final_metadata,
        )

    else:

        run.mark_completed(
            verdict=run.final_verdict,
            metadata=final_metadata,
        )

    # ------------------------------------------------------------------------
    # Persist final run metadata.
    # ------------------------------------------------------------------------

    final_manifest = {
        "run_id": run.run_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": utc_now(),
        "final_verdict": run.final_verdict,
        "metadata": safe_json_value(
            {
                **run.metadata,
                **final_metadata,
            }
        ),
        "run_directory": str(
            run.run_dir
        ),
    }

    run.logger.write_json(
        "final_run_summary.json",
        final_manifest,
        artifact_type="run_summary",
        agent="run_manager",
        description="Final verification run summary",
    )

    if close_logger:
        run.close()

    return run


# ============================================================================
# Finalize directly from LangGraph state
# ============================================================================

def _get_state_value(
    state: Any,
    key: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve a value from a LangGraph state object.

    Supports:

        dict
        Mapping
        simple objects
        dataclasses exposing attributes
    """

    if state is None:
        return default

    if isinstance(state, Mapping):
        return state.get(
            key,
            default,
        )

    try:
        return getattr(
            state,
            key,
            default,
        )

    except Exception:
        return default


def _extract_verdict(
    state: Any,
) -> Optional[str]:
    """
    Extract the final judge verdict from common state field names.
    """

    candidate_keys = [
        "final_verdict",
        "verdict",
        "judge_verdict",
        "verification_verdict",
        "final_result",
        "result",
    ]

    for key in candidate_keys:

        value = _get_state_value(
            state,
            key,
            None,
        )

        if value is None:
            continue

        if isinstance(value, str):

            value = value.strip()

            if value:
                return value

        elif isinstance(value, Mapping):

            nested = (
                value.get("verdict")
                or value.get("final_verdict")
                or value.get("status")
            )

            if nested:
                return str(nested)

    return None


def _extract_status(
    state: Any,
) -> Optional[str]:
    """
    Extract workflow status from common state field names.
    """

    candidate_keys = [
        "run_status",
        "status",
        "verification_status",
        "workflow_status",
    ]

    for key in candidate_keys:

        value = _get_state_value(
            state,
            key,
            None,
        )

        if value is None:
            continue

        if isinstance(value, str):

            value = value.strip()

            if value:
                return value

    return None


def finalize_from_state(
    state: Any,
    *,
    run: Optional[VerificationRun] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    close_logger: bool = False,
) -> Optional[VerificationRun]:
    """
    Finalize a verification run using LangGraph state.

    The function first tries to use an explicitly supplied run.

    If no run is supplied, it looks for:

        state["verification_run"]

    or:

        state["run"]

    If neither exists, it attempts to find the shared logger.

    Expected state example
    ----------------------

        {
            "run_id": "run_20260904...",
            "logger": logger,
            "verification_run": run,
            "final_verdict": "PASS",
        }

    Recommended usage
    ------------------

        run = create_verification_run(...)

        state = {
            "verification_run": run,
            "run_id": run.run_id,
            "logger": run.logger,
        }

        # LangGraph execution

        finalize_from_state(state)

    Returns
    -------

    VerificationRun or None
        None if a VerificationRun could not be identified.
    """

    # ------------------------------------------------------------------------
    # 1. Explicit run takes priority.
    # ------------------------------------------------------------------------

    resolved_run = run

    # ------------------------------------------------------------------------
    # 2. Look inside state.
    # ------------------------------------------------------------------------

    if resolved_run is None:

        candidate = _get_state_value(
            state,
            "verification_run",
            None,
        )

        if isinstance(
            candidate,
            VerificationRun,
        ):

            resolved_run = candidate

    if resolved_run is None:

        candidate = _get_state_value(
            state,
            "run",
            None,
        )

        if isinstance(
            candidate,
            VerificationRun,
        ):

            resolved_run = candidate

    # ------------------------------------------------------------------------
    # 3. If we don't have the run object but have a logger, reconstruct the
    #    minimum VerificationRun wrapper.
    # ------------------------------------------------------------------------

    if resolved_run is None:

        logger = _get_state_value(
            state,
            "logger",
            None,
        )

        if isinstance(
            logger,
            ActivityLogger,
        ):

            run_id = str(
                _get_state_value(
                    state,
                    "run_id",
                    logger.run_id,
                )
            )

            metadata_dict = dict(
                _get_state_value(
                    state,
                    "run_metadata",
                    {},
                )
                or {}
            )

            resolved_run = VerificationRun(
                run_id=run_id,
                run_dir=logger.run_dir,
                logger=logger,
                started_at=str(
                    _get_state_value(
                        state,
                        "started_at",
                        logger.created_at,
                    )
                ),
                metadata=metadata_dict,
                status="running",
            )

    # ------------------------------------------------------------------------
    # 4. Cannot finalize without run/logger.
    # ------------------------------------------------------------------------

    if resolved_run is None:
        return None

    # ------------------------------------------------------------------------
    # 5. Extract verdict/status.
    # ------------------------------------------------------------------------

    verdict = _extract_verdict(
        state
    )

    status = _extract_status(
        state
    )

    # ------------------------------------------------------------------------
    # 6. Add useful final-state metadata.
    # ------------------------------------------------------------------------

    final_metadata = dict(
        metadata or {}
    )

    final_metadata.setdefault(
        "finalized_from",
        "langgraph_state",
    )

    # Store iteration if available.
    iteration = _get_state_value(
        state,
        "iteration",
        None,
    )

    if iteration is not None:
        final_metadata.setdefault(
            "iteration",
            iteration,
        )

    # Store verification score if available.
    score = _get_state_value(
        state,
        "verification_score",
        None,
    )

    if score is not None:
        final_metadata.setdefault(
            "verification_score",
            score,
        )

    # Store coverage if available.
    coverage = _get_state_value(
        state,
        "coverage",
        None,
    )

    if coverage is not None:
        final_metadata.setdefault(
            "coverage",
            coverage,
        )

    # Store failures if available.
    failures = _get_state_value(
        state,
        "failures",
        None,
    )

    if failures is not None:

        if isinstance(
            failures,
            (list, tuple),
        ):

            final_metadata.setdefault(
                "failure_count",
                len(failures),
            )

        elif isinstance(
            failures,
            Mapping,
        ):

            final_metadata.setdefault(
                "failure_count",
                len(failures),
            )

    # ------------------------------------------------------------------------
    # 7. Finalize.
    # ------------------------------------------------------------------------

    return finalize_verification_run(
        resolved_run,
        verdict=verdict,
        status=status,
        metadata=final_metadata,
        close_logger=close_logger,
    )


# ============================================================================
# Convenience helpers
# ============================================================================

def get_run_directory(
    run: VerificationRun,
) -> Path:
    """
    Return the filesystem directory for a verification run.
    """

    return run.run_dir


def get_run_id(
    run: VerificationRun,
) -> str:
    """
    Return the run ID.
    """

    return run.run_id


def get_run_logger(
    run: VerificationRun,
) -> ActivityLogger:
    """
    Return the shared ActivityLogger.

    This helper makes it explicit that agents should use the same
    logger rather than creating their own.
    """

    return run.logger


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "VerificationRun",
    "create_run_id",
    "create_verification_run",
    "finalize_verification_run",
    "finalize_from_state",
    "get_run_directory",
    "get_run_id",
    "get_run_logger",
]

