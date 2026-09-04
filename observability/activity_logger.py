"""
PragyanAI SiliconAI
===================

Run-level activity logger.

Responsibilities
----------------
- Create structured JSONL activity logs
- Create human-readable workflow logs
- Persist generated artifacts
- Track agent start/completion/failure
- Track duration
- Track metadata
- Maintain an artifact manifest
- Safely serialize arbitrary Python objects

IMPORTANT
---------
One ActivityLogger instance should be created for ONE verification run
and reused by every workflow node.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================================
# Helpers
# ============================================================================


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def safe_filename(value: str) -> str:
    """
    Convert arbitrary text into a filesystem-safe filename.
    """
    value = str(value).strip()

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_."
    )

    cleaned = "".join(
        char if char in allowed else "_"
        for char in value
    )

    cleaned = cleaned.strip("._")

    return cleaned or "artifact"


def safe_json_value(value: Any) -> Any:
    """
    Convert arbitrary Python values into JSON-compatible structures.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): safe_json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            safe_json_value(item)
            for item in value
        ]

    try:
        json.dumps(value)
        return value

    except (TypeError, ValueError):
        return str(value)


# ============================================================================
# Activity Logger
# ============================================================================


class ActivityLogger:
    """
    Structured run-level logger.

    A single instance should be created for a verification run.

    Example
    -------

        logger = ActivityLogger(
            run_id="20260904_100000_abcd1234",
            run_dir="/tmp/run",
        )

        logger.started(
            "rtl_analysis",
            metadata={
                "rtl_chars": 1200,
            },
        )

        logger.completed(
            "rtl_analysis",
            duration_seconds=0.25,
        )
    """

    def __init__(
        self,
        run_id: str,
        run_dir: str | Path,
    ) -> None:

        self.run_id = str(run_id)

        self.run_dir = Path(run_dir)

        self.run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.activity_file = (
            self.run_dir / "agent_activity.jsonl"
        )

        self.workflow_log_file = (
            self.run_dir / "workflow.log"
        )

        self.manifest_file = (
            self.run_dir / "artifact_manifest.json"
        )

        self.run_manifest_file = (
            self.run_dir / "run_manifest.json"
        )

        self._artifact_manifest: list[dict[str, Any]] = []

        self._configure_logger()

        self._write_initial_files()

    # ---------------------------------------------------------------------
    # Logging setup
    # ---------------------------------------------------------------------

    def _configure_logger(self) -> None:
        """
        Configure a dedicated Python logger for this verification run.

        It does not modify the root logger.
        """

        logger_name = (
            f"PragyanAI.run.{self.run_id}"
        )

        self.logger = logging.getLogger(
            logger_name
        )

        self.logger.setLevel(
            logging.INFO
        )

        self.logger.propagate = False

        # Avoid duplicate handlers if this object is recreated.
        if not self.logger.handlers:

            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            file_handler = logging.FileHandler(
                self.workflow_log_file,
                encoding="utf-8",
            )

            file_handler.setFormatter(
                formatter
            )

            self.logger.addHandler(
                file_handler
            )

    # ---------------------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------------------

    def _write_initial_files(self) -> None:
        """Create empty structured log files."""

        if not self.activity_file.exists():
            self.activity_file.touch()

        if not self.workflow_log_file.exists():
            self.workflow_log_file.touch()

        self._write_artifact_manifest()

    # ---------------------------------------------------------------------
    # Generic activity
    # ---------------------------------------------------------------------

    def log_activity(
        self,
        event: str,
        agent: str | None = None,
        status: str | None = None,
        duration_seconds: float | None = None,
        iteration: int | None = None,
        metadata: dict[str, Any] | None = None,
        message: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """
        Write one structured activity event.

        The event is appended to agent_activity.jsonl.
        """

        record: dict[str, Any] = {
            "timestamp": utc_now(),
            "run_id": self.run_id,
            "event": event,
        }

        if agent is not None:
            record["agent"] = agent

        if status is not None:
            record["status"] = status

        if duration_seconds is not None:
            record["duration_seconds"] = round(
                float(duration_seconds),
                6,
            )

        if iteration is not None:
            record["iteration"] = iteration

        if metadata:
            record["metadata"] = safe_json_value(
                metadata
            )

        if message:
            record["message"] = str(message)

        if error:
            record["error"] = str(error)

        serialized = json.dumps(
            record,
            ensure_ascii=False,
            default=str,
        )

        with self.activity_file.open(
            "a",
            encoding="utf-8",
        ) as fh:
            fh.write(
                serialized + "\n"
            )

        # Also write important events to workflow.log.
        log_message = self._format_workflow_message(
            record
        )

        if event == "agent_failed":
            self.logger.error(
                log_message
            )

        elif event in {
            "run_failed",
            "workflow_failed",
        }:
            self.logger.error(
                log_message
            )

        elif event in {
            "warning",
        }:
            self.logger.warning(
                log_message
            )

        else:
            self.logger.info(
                log_message
            )

        return record

    # ---------------------------------------------------------------------
    # Human-readable workflow log
    # ---------------------------------------------------------------------

    @staticmethod
    def _format_workflow_message(
        record: dict[str, Any],
    ) -> str:

        pieces = [
            f"event={record.get('event')}",
        ]

        if record.get("agent"):
            pieces.append(
                f"agent={record['agent']}"
            )

        if record.get("status"):
            pieces.append(
                f"status={record['status']}"
            )

        if record.get("iteration") is not None:
            pieces.append(
                f"iteration={record['iteration']}"
            )

        if record.get("duration_seconds") is not None:
            pieces.append(
                f"duration={record['duration_seconds']}s"
            )

        if record.get("message"):
            pieces.append(
                f"message={record['message']}"
            )

        if record.get("error"):
            pieces.append(
                f"error={record['error']}"
            )

        return " | ".join(pieces)

    # ---------------------------------------------------------------------
    # Agent lifecycle
    # ---------------------------------------------------------------------

    def started(
        self,
        agent: str,
        iteration: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent start."""

        self.log_activity(
            event="agent_started",
            agent=agent,
            status="RUNNING",
            iteration=iteration,
            metadata=metadata,
        )

    def completed(
        self,
        agent: str,
        duration_seconds: float,
        iteration: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log successful agent completion."""

        self.log_activity(
            event="agent_completed",
            agent=agent,
            status="COMPLETED",
            duration_seconds=duration_seconds,
            iteration=iteration,
            metadata=metadata,
        )

    def failed(
        self,
        agent: str,
        duration_seconds: float,
        error: str,
        iteration: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent failure including exception information."""

        self.log_activity(
            event="agent_failed",
            agent=agent,
            status="FAILED",
            duration_seconds=duration_seconds,
            iteration=iteration,
            metadata=metadata,
            error=error,
        )

    # ---------------------------------------------------------------------
    # Workflow lifecycle
    # ---------------------------------------------------------------------

    def run_started(
        self,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="run_started",
            status="RUNNING",
            metadata=metadata,
        )

    def run_completed(
        self,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="run_completed",
            status="COMPLETED",
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    def run_failed(
        self,
        error: str,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="run_failed",
            status="FAILED",
            duration_seconds=duration_seconds,
            metadata=metadata,
            error=error,
        )

    # ---------------------------------------------------------------------
    # Generic messages
    # ---------------------------------------------------------------------

    def info(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="info",
            status="INFO",
            metadata=metadata,
            message=message,
        )

    def warning(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="warning",
            status="WARNING",
            metadata=metadata,
            message=message,
        )

    def error(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.log_activity(
            event="error",
            status="ERROR",
            metadata=metadata,
            message=message,
        )

    # ---------------------------------------------------------------------
    # Artifact management
    # ---------------------------------------------------------------------

    def agent_dir(
        self,
        agent: str,
        sequence: int | None = None,
    ) -> Path:
        """
        Return/create the artifact directory for an agent.
        """

        prefix = ""

        if sequence is not None:
            prefix = f"{sequence:02d}_"

        directory = (
            self.run_dir
            / f"{prefix}{safe_filename(agent)}"
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    def write_text(
        self,
        relative_path: str | Path,
        content: Any,
        artifact_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write text content as a run artifact.
        """

        relative_path = Path(relative_path)

        output_path = (
            self.run_dir / relative_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        text = (
            content
            if isinstance(content, str)
            else str(content)
        )

        output_path.write_text(
            text,
            encoding="utf-8",
        )

        self._register_artifact(
            output_path=output_path,
            artifact_type=artifact_type,
            metadata=metadata,
        )

        return output_path

    def write_code(
        self,
        relative_path: str | Path,
        code: str,
        language: str = "verilog",
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write source code as an artifact.
        """

        return self.write_text(
            relative_path=relative_path,
            content=code,
            artifact_type=f"source:{language}",
            metadata=metadata,
        )

    def write_json(
        self,
        relative_path: str | Path,
        data: Any,
        artifact_type: str = "json",
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write JSON artifact.
        """

        relative_path = Path(relative_path)

        output_path = (
            self.run_dir / relative_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_data = safe_json_value(
            data
        )

        output_path.write_text(
            json.dumps(
                safe_data,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        self._register_artifact(
            output_path=output_path,
            artifact_type=artifact_type,
            metadata=metadata,
        )

        return output_path

    # ---------------------------------------------------------------------
    # Artifact manifest
    # ---------------------------------------------------------------------

    def _register_artifact(
        self,
        output_path: Path,
        artifact_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        try:
            relative_path = str(
                output_path.relative_to(
                    self.run_dir
                )
            )

        except ValueError:
            relative_path = str(
                output_path
            )

        try:
            size_bytes = (
                output_path.stat().st_size
            )

        except OSError:
            size_bytes = 0

        artifact = {
            "timestamp": utc_now(),
            "path": relative_path,
            "type": artifact_type,
            "size_bytes": size_bytes,
            "metadata": safe_json_value(
                metadata or {}
            ),
        }

        self._artifact_manifest.append(
            artifact
        )

        self._write_artifact_manifest()

        self.log_activity(
            event="artifact_created",
            status="CREATED",
            metadata=artifact,
        )

    def _write_artifact_manifest(self) -> None:
        """Persist artifact manifest."""

        self.manifest_file.write_text(
            json.dumps(
                self._artifact_manifest,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    # ---------------------------------------------------------------------
    # Run manifest
    # ---------------------------------------------------------------------

    def manifest(
        self,
        data: dict[str, Any],
    ) -> Path:
        """
        Write/update run_manifest.json.
        """

        payload = {
            "run_id": self.run_id,
            "updated_at": utc_now(),
            **safe_json_value(data),
        }

        self.run_manifest_file.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        return self.run_manifest_file

    # ---------------------------------------------------------------------
    # Exception helper
    # ---------------------------------------------------------------------

    def exception_text(
        self,
        exc: BaseException,
    ) -> str:
        """
        Return a complete traceback string.
        """

        return "".join(
            traceback.format_exception(
                type(exc),
                exc,
                exc.__traceback__,
            )
        )

    def log_exception(
        self,
        event: str,
        exc: BaseException,
        agent: str | None = None,
        iteration: int | None = None,
    ) -> None:
        """
        Log exception with complete traceback.
        """

        traceback_text = self.exception_text(
            exc
        )

        self.log_activity(
            event=event,
            agent=agent,
            status="FAILED",
            iteration=iteration,
            error=traceback_text,
        )
