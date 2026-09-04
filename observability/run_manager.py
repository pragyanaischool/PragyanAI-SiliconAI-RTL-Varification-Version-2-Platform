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
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
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

    # Convert datetime object to ISO string format safely before running re.sub
    if isinstance(timestamp, datetime):
        timestamp_str = timestamp.isoformat()
    else:
        timestamp_str = str(timestamp)

    timestamp_text = re.sub(
        r"[^0-9]",
        "",
        timestamp_str,
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

    def mark_running(self) -> None:
        """Mark this run as running."""
        self.status = "running"
        if hasattr(self.logger, "run_started"):
            self.logger.run_started(metadata=self.metadata)

    def mark_completed(
        self,
        verdict: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark this run as successfully completed."""
        self.status = "completed"

        if verdict is not None:
            self.final_verdict = str(verdict)

        if hasattr(self.logger, "run_completed"):
            self.logger.run_completed(
                verdict=self.final_verdict,
                metadata=metadata,
            )

    def mark_failed(
        self,
        error: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark this run as failed."""
        self.status = "failed"
        if hasattr(self.logger, "run_failed"):
            self.logger.run_failed(
                error,
                metadata=metadata,
            )

    def close(self) -> None:
        """Close the underlying ActivityLogger."""
        if hasattr(self.logger, "close"):
            self.logger.close()


# ============================================================================
# Directory helpers
# ============================================================================

def _resolve_run_root() -> Path:
    """Resolve the configured run root."""
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
    """Resolve the configured logging root."""
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
    """Create the run directory and common artifact directories."""
    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

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
    """Create exactly ONE verification run and ONE shared logger."""
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

    logger = ActivityLogger(
        run_id=final_run_id,
        run_dir=run_dir,
    )

    run = VerificationRun(
        run_id=final_run_id,
        run_dir=run_dir,
        logger=logger,
        started_at=utc_now().isoformat(),
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
    """Finalize a VerificationRun."""
    final_metadata = dict(
        metadata or {}
    )

    if verdict is not None:
        run.final_verdict = str(
            verdict
        )

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

    final_manifest = {
        "run_id": run.run_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": utc_now().isoformat(),
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

    if hasattr(run.logger, "write_json"):
        run.logger.write_json(
            agent="run_manager",
            filename="final_run_summary.json",
            data=final_manifest,
            step=99,
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
    """Safely retrieve a value from a LangGraph state object."""
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
    """Extract the final judge verdict from common state field names."""
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
    """Extract workflow status from common state field names."""
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
    """Finalize a verification run using LangGraph state."""
    resolved_run = run

    if resolved_run is None:
        candidate = _get_state_value(
            state,
            "verification_run",
            None,
        )
        if isinstance(candidate, VerificationRun):
            resolved_run = candidate

    if resolved_run is None:
        candidate = _get_state_value(
            state,
            "run",
            None,
        )
        if isinstance(candidate, VerificationRun):
            resolved_run = candidate

    if resolved_run is None:
        logger = _get_state_value(
            state,
            "logger",
            None,
        )
        if isinstance(logger, ActivityLogger):
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
                        utc_now().isoformat(),
                    )
                ),
                metadata=metadata_dict,
                status="running",
            )

    if resolved_run is None:
        return None

    verdict = _extract_verdict(state)
    status = _extract_status(state)

    final_metadata = dict(
        metadata or {}
    )

    final_metadata.setdefault(
        "finalized_from",
        "langgraph_state",
    )

    iteration = _get_state_value(
        state,
        "iteration",
        None,
    )
    if iteration is not None:
        final_metadata.setdefault("iteration", iteration)

    score = _get_state_value(
        state,
        "verification_score",
        None,
    )
    if score is not None:
        final_metadata.setdefault("verification_score", score)

    coverage = _get_state_value(
        state,
        "coverage",
        None,
    )
    if coverage is not None:
        final_metadata.setdefault("coverage", coverage)

    failures = _get_state_value(
        state,
        "failures",
        None,
    )
    if failures is not None:
        if isinstance(failures, (list, tuple, Mapping)):
            final_metadata.setdefault("failure_count", len(failures))

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

def get_run_directory(run: VerificationRun) -> Path:
    """Return the filesystem directory for a verification run."""
    return run.run_dir


def get_run_id(run: VerificationRun) -> str:
    """Return the run ID."""
    return run.run_id


def get_run_logger(run: VerificationRun) -> ActivityLogger:
    """Return the shared ActivityLogger."""
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
