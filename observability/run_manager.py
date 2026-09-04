"""Verification Run Manager lifecycle management."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from config.settings import LOG_ROOT, RUNTIME_ROOT, RUN_ROOT
from observability.activity_logger import ActivityLogger, safe_json_value, utc_now


def create_run_id(prefix: str = "run") -> str:
    timestamp = utc_now()
    timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    timestamp_text = re.sub(r"[^0-9]", "", timestamp_str)[:15]
    unique = uuid.uuid4().hex[:8]
    clean_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", str(prefix).strip() or "run")
    return f"{clean_prefix}_{timestamp_text}_{unique}"


@dataclass
class VerificationRun:
    run_id: str
    run_dir: Path
    logger: ActivityLogger
    started_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "created"
    final_verdict: Optional[str] = None

    def mark_running(self) -> None:
        self.status = "running"
        if hasattr(self.logger, "run_started"):
            self.logger.run_started(metadata=self.metadata)

    def mark_completed(self, verdict: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.status = "completed"
        if verdict is not None:
            self.final_verdict = str(verdict)
        if hasattr(self.logger, "run_completed"):
            self.logger.run_completed(verdict=self.final_verdict, metadata=metadata)

    def mark_failed(self, error: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.status = "failed"
        if hasattr(self.logger, "run_failed"):
            self.logger.run_failed(error, metadata=metadata)

    def close(self) -> None:
        if hasattr(self.logger, "close"):
            self.logger.close()


def _resolve_run_root() -> Path:
    try:
        return Path(RUN_ROOT)
    except NameError:
        pass
    try:
        return Path(RUNTIME_ROOT) / "runs"
    except NameError:
        return Path("runtime/runs")


def _ensure_run_directories(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    for directory in [
        "state_snapshots", "01_rtl_analysis", "02_planning", "03_test_generation",
        "04_testbench_generation", "05_simulation", "06_failure_analysis",
        "07_coverage", "08_red_team", "09_mutation", "10_formal", "11_judge"
    ]:
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def create_verification_run(
    metadata: Optional[Mapping[str, Any]] = None,
    *,
    run_id: Optional[str] = None,
    prefix: str = "run",
    mark_running: bool = True,
) -> VerificationRun:
    final_run_id = str(run_id) if run_id else create_run_id(prefix)
    run_root = _resolve_run_root()
    run_dir = run_root / final_run_id
    _ensure_run_directories(run_dir)

    enriched_metadata = dict(metadata or {})
    enriched_metadata.setdefault("platform", "PragyanAI SiliconAI")
    enriched_metadata.setdefault("run_id", final_run_id)

    logger = ActivityLogger(run_id=final_run_id, run_dir=run_dir)
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


def finalize_verification_run(
    run: VerificationRun,
    *,
    verdict: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    close_logger: bool = False,
) -> VerificationRun:
    final_metadata = dict(metadata or {})
    if verdict is not None:
        run.final_verdict = str(verdict)

    if status is None:
        status = "failed" if str(run.final_verdict or "").strip().upper() in {"FAIL", "FAILED", "ERROR"} else "completed"

    if status == "failed":
        run.mark_failed(error=final_metadata.get("error", "Verification failed"), metadata=final_metadata)
    else:
        run.mark_completed(verdict=run.final_verdict, metadata=final_metadata)

    final_manifest = {
        "run_id": run.run_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": utc_now().isoformat(),
        "final_verdict": run.final_verdict,
        "metadata": safe_json_value({**run.metadata, **final_metadata}),
        "run_directory": str(run.run_dir),
    }

    if hasattr(run.logger, "write_json"):
        run.logger.write_json(agent="run_manager", filename="final_run_summary.json", data=final_manifest, step=99)

    if close_logger:
        run.close()
    return run


def finalize_from_state(state: Any, *, run: Optional[VerificationRun] = None, metadata: Optional[Mapping[str, Any]] = None, close_logger: bool = False) -> Optional[VerificationRun]:
    resolved_run = run or (state.get("verification_run") if isinstance(state, dict) else None)
    if resolved_run is None and isinstance(state, dict) and "logger" in state:
        logger = state["logger"]
        resolved_run = VerificationRun(
            run_id=state.get("run_id", logger.run_id),
            run_dir=logger.run_dir,
            logger=logger,
            started_at=str(state.get("started_at", utc_now().isoformat())),
            metadata=state.get("run_metadata", {}),
            status="running",
        )
    if resolved_run is None:
        return None
    return finalize_verification_run(resolved_run, metadata=metadata, close_logger=close_logger)

__all__ = ["VerificationRun", "create_run_id", "create_verification_run", "finalize_verification_run", "finalize_from_state"]
