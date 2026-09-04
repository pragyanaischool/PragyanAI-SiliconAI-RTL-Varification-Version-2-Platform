"""
PragyanAI SiliconAI
===================

Verification run manager.

Creates:
    runtime/runs/<run_id>/

and exactly one ActivityLogger for the run.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import RUN_ROOT

from observability.activity_logger import (
    ActivityLogger,
)


# ============================================================================
# Run ID
# ============================================================================


def create_run_id() -> str:
    """
    Generate a unique verification run ID.

    Example:
        20260904_100215_a82f71c4
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    short_uuid = uuid.uuid4().hex[:8]

    return (
        f"{timestamp}_{short_uuid}"
    )


# ============================================================================
# Verification Run
# ============================================================================


class VerificationRun:
    """
    Container for all run-level observability information.
    """

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        logger: ActivityLogger,
    ) -> None:

        self.run_id = run_id
        self.run_dir = run_dir
        self.logger = logger


# ============================================================================
# Run Creation
# ============================================================================


def create_verification_run(
    metadata: dict[str, Any] | None = None,
) -> VerificationRun:
    """
    Create a new verification run.

    The logger is initialized ONCE here.

    Every workflow node should reuse this logger.
    """

    run_id = create_run_id()

    run_dir = (
        Path(RUN_ROOT)
        / run_id
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger = ActivityLogger(
        run_id=run_id,
        run_dir=run_dir,
    )

    logger.run_started(
        metadata=metadata
    )

    logger.manifest(
        {
            "run_id": run_id,
            "status": "RUNNING",
            "metadata": metadata or {},
        }
    )

    return VerificationRun(
        run_id=run_id,
        run_dir=run_dir,
        logger=logger,
    )


# ============================================================================
# Finalization
# ============================================================================


def finalize_verification_run(
    run: VerificationRun,
    status: str,
    duration_seconds: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Finalize a verification run.
    """

    status = str(status).upper()

    if status in {
        "COMPLETED",
        "PASS",
        "PASSED",
    }:
        run.logger.run_completed(
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    elif status in {
        "FAILED",
        "FAIL",
    }:
        run.logger.run_failed(
            error=str(
                metadata.get("error", "Unknown error")
                if metadata
                else "Verification run failed"
            ),
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    else:
        run.logger.log_activity(
            event="run_finalized",
            status=status,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    run.logger.manifest(
        {
            "run_id": run.run_id,
            "status": status,
            "duration_seconds": duration_seconds,
            "metadata": metadata or {},
        }
    )
