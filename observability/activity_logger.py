"""
PragyanAI SiliconAI
===================

Run-level observability and artifact management for the
Agentic RTL / Verilog Verification Platform.

Design goals
------------

1. Create ONE ActivityLogger per verification run.
2. Log every agent start/completion/failure.
3. Log workflow events and iteration information.
4. Log LLM activity.
5. Log simulation activity.
6. Persist generated artifacts.
7. Maintain an artifact manifest with SHA-256 hashes.
8. Maintain a run manifest.
9. Write machine-readable JSONL logs.
10. Write a human-readable workflow.log.
11. Capture exceptions and tracebacks.
12. Keep the logger independent from LangGraph.
13. Avoid creating a package named "logging" because Python already
    provides a standard-library module named logging.

Expected run directory
----------------------

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

The logger is intentionally tolerant of arbitrary Python values so
that agents can safely log dictionaries, lists, Paths, exceptions,
and other objects without crashing the verification run.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Time utilities
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """
    Return the current UTC time as an ISO-8601 string.

    Example:
        2026-09-04T08:30:15.123456+00:00
    """
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Filesystem / serialization helpers
# ---------------------------------------------------------------------------

def safe_filename(value: Any, default: str = "artifact") -> str:
    """
    Convert arbitrary text into a filesystem-safe filename.

    Examples
    --------
    >>> safe_filename("RTL Analysis")
    'RTL_Analysis'

    >>> safe_filename("foo/bar.v")
    'foo_bar.v'
    """
    text = str(value).strip()

    if not text:
        text = default

    # Replace path separators and control characters.
    text = text.replace("/", "_")
    text = text.replace("\\", "_")
    text = re.sub(r"[\x00-\x1f\x7f]", "_", text)

    # Keep common filename characters.
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)

    # Collapse repeated underscores.
    text = re.sub(r"_+", "_", text)

    # Avoid names consisting only of dots.
    if text in {".", ".."}:
        text = default

    # Prevent excessively long filenames.
    return text[:180]


def safe_json_value(value: Any) -> Any:
    """
    Convert a Python value into something that can be serialized by JSON.

    This function is intentionally defensive because agent state can
    contain Path objects, exceptions, sets, tuples, dataclasses, or
    arbitrary custom objects.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "length": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }

    if isinstance(value, Exception):
        return {
            "type": type(value).__name__,
            "message": str(value),
        }

    if isinstance(value, dict):
        result: Dict[str, Any] = {}

        for key, item in value.items():
            result[str(key)] = safe_json_value(item)

        return result

    if isinstance(value, (list, tuple)):
        return [safe_json_value(item) for item in value]

    if isinstance(value, set):
        return [safe_json_value(item) for item in sorted(value, key=str)]

    # Handle objects exposing a useful dictionary.
    if hasattr(value, "__dict__"):
        try:
            return {
                "type": type(value).__name__,
                "data": safe_json_value(vars(value)),
            }
        except Exception:
            pass

    # Last-resort representation.
    return str(value)


def sha256_file(path: Path) -> str:
    """
    Calculate SHA-256 for a file.

    The file is read in chunks so large simulation outputs or waveform
    files do not need to be loaded entirely into memory.
    """

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Activity Logger
# ---------------------------------------------------------------------------

class ActivityLogger:
    """
    Structured logger for exactly one verification run.

    The recommended lifecycle is:

        run = create_verification_run(...)

        logger = run.logger

        logger.started(...)
        logger.completed(...)
        logger.failed(...)

    The same logger should be passed through the entire LangGraph
    verification workflow.

    Parameters
    ----------
    run_id:
        Unique verification run identifier.

    run_dir:
        Directory where all logs and artifacts for this run are stored.

    metadata:
        Optional metadata describing the run.
    """

    def __init__(
        self,
        run_id: str,
        run_dir: Path | str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:

        self.run_id = str(run_id)
        self.run_dir = Path(run_dir)

        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.metadata = dict(metadata or {})

        self.created_at = utc_now()

        self._lock = Lock()

        self._agent_sequence = 0

        self._artifact_sequence = 0

        self._artifacts: list[Dict[str, Any]] = []

        self._agent_events: list[Dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Core files
        # ------------------------------------------------------------------

        self.activity_file = self.run_dir / "agent_activity.jsonl"

        self.workflow_log_file = self.run_dir / "workflow.log"

        self.artifact_manifest_file = (
            self.run_dir / "artifact_manifest.json"
        )

        self.run_manifest_file = (
            self.run_dir / "run_manifest.json"
        )

        # ------------------------------------------------------------------
        # Python logging logger
        # ------------------------------------------------------------------

        logger_name = f"pragyanai.verification.{self.run_id}"

        self.python_logger = logging.getLogger(logger_name)

        self.python_logger.setLevel(logging.INFO)

        self.python_logger.propagate = False

        # Avoid duplicate handlers if this object is reconstructed.
        self.python_logger.handlers.clear()

        file_handler = logging.FileHandler(
            self.workflow_log_file,
            encoding="utf-8",
        )

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler.setFormatter(formatter)

        self.python_logger.addHandler(file_handler)

        # ------------------------------------------------------------------
        # Initial manifests
        # ------------------------------------------------------------------

        self._write_initial_manifests()

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _write_initial_manifests(self) -> None:
        """
        Create initial run and artifact manifests.
        """

        run_manifest = {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "updated_at": self.created_at,
            "status": "created",
            "metadata": safe_json_value(self.metadata),
            "run_directory": str(self.run_dir),
        }

        self._atomic_write_json(
            self.run_manifest_file,
            run_manifest,
        )

        self._write_artifact_manifest()

    def _atomic_write_json(
        self,
        path: Path,
        payload: Any,
    ) -> None:
        """
        Write JSON safely using a temporary file followed by replace().
        """

        path.parent.mkdir(parents=True, exist_ok=True)

        temporary = path.with_suffix(
            path.suffix + ".tmp"
        )

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                safe_json_value(payload),
                handle,
                indent=2,
                ensure_ascii=False,
            )

            handle.write("\n")

        temporary.replace(path)

    def _append_jsonl(
        self,
        payload: Dict[str, Any],
    ) -> None:
        """
        Append one structured event to agent_activity.jsonl.
        """

        with self.activity_file.open(
            "a",
            encoding="utf-8",
        ) as handle:

            handle.write(
                json.dumps(
                    safe_json_value(payload),
                    ensure_ascii=False,
                )
            )

            handle.write("\n")

    def _format_workflow_message(
        self,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format a human-readable workflow log message.
        """

        text = (
            f"[run={self.run_id}] "
            f"{message}"
        )

        if metadata:
            compact = json.dumps(
                safe_json_value(metadata),
                ensure_ascii=False,
                sort_keys=True,
            )

            text += f" | {compact}"

        return text

    def _write_artifact_manifest(self) -> None:
        """
        Persist the artifact manifest.
        """

        manifest = {
            "run_id": self.run_id,
            "updated_at": utc_now(),
            "artifact_count": len(self._artifacts),
            "artifacts": self._artifacts,
        }

        self._atomic_write_json(
            self.artifact_manifest_file,
            manifest,
        )

    def _update_run_manifest(
        self,
        **updates: Any,
    ) -> None:
        """
        Update fields in run_manifest.json.
        """

        existing: Dict[str, Any] = {}

        if self.run_manifest_file.exists():

            try:
                with self.run_manifest_file.open(
                    "r",
                    encoding="utf-8",
                ) as handle:

                    loaded = json.load(handle)

                    if isinstance(loaded, dict):
                        existing = loaded

            except Exception:
                existing = {}

        existing.update(updates)

        existing["updated_at"] = utc_now()

        self._atomic_write_json(
            self.run_manifest_file,
            existing,
        )

    # -----------------------------------------------------------------------
    # Generic activity logging
    # -----------------------------------------------------------------------

    def log_activity(
        self,
        event_type: str,
        message: str = "",
        *,
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
        status: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
    ) -> Dict[str, Any]:
        """
        Write a generic structured activity event.

        This is the central logging primitive used by the specialized
        helper methods below.
        """

        event = {
            "timestamp": utc_now(),
            "run_id": self.run_id,
            "event_type": str(event_type),
            "message": str(message),
            "agent": agent,
            "iteration": iteration,
            "status": status,
            "duration_seconds": duration_seconds,
            "metadata": safe_json_value(metadata or {}),
        }

        with self._lock:

            self._append_jsonl(event)

            level_upper = str(level).upper()

            workflow_message = self._format_workflow_message(
                level_upper,
                message or event_type,
                metadata,
            )

            if level_upper == "DEBUG":
                self.python_logger.debug(workflow_message)

            elif level_upper == "WARNING":
                self.python_logger.warning(workflow_message)

            elif level_upper == "ERROR":
                self.python_logger.error(workflow_message)

            else:
                self.python_logger.info(workflow_message)

        return event

    # -----------------------------------------------------------------------
    # Run lifecycle
    # -----------------------------------------------------------------------

    def run_started(
        self,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record verification run start.
        """

        merged = dict(self.metadata)

        if metadata:
            merged.update(metadata)

        self.metadata = merged

        self._update_run_manifest(
            status="running",
            started_at=utc_now(),
            metadata=safe_json_value(self.metadata),
        )

        return self.log_activity(
            "run_started",
            "Verification run started",
            metadata=self.metadata,
            status="running",
        )

    def run_completed(
        self,
        *,
        verdict: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record successful completion of a verification run.
        """

        final_metadata = dict(metadata or {})

        if verdict is not None:
            final_metadata["verdict"] = verdict

        self._update_run_manifest(
            status="completed",
            completed_at=utc_now(),
            final_verdict=verdict,
            metadata=safe_json_value(
                {
                    **self.metadata,
                    **final_metadata,
                }
            ),
        )

        return self.log_activity(
            "run_completed",
            "Verification run completed",
            status="completed",
            metadata=final_metadata,
        )

    def run_failed(
        self,
        error: Any,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record failed verification run.
        """

        error_text = str(error)

        final_metadata = dict(metadata or {})

        final_metadata["error"] = error_text

        self._update_run_manifest(
            status="failed",
            failed_at=utc_now(),
            error=error_text,
            metadata=safe_json_value(
                {
                    **self.metadata,
                    **final_metadata,
                }
            ),
        )

        return self.log_activity(
            "run_failed",
            "Verification run failed",
            status="failed",
            metadata=final_metadata,
            level="ERROR",
        )

    # -----------------------------------------------------------------------
    # Agent lifecycle
    # -----------------------------------------------------------------------

    def next_agent_sequence(self) -> int:
        """
        Return the next sequential agent number for this run.
        """

        with self._lock:
            self._agent_sequence += 1

            return self._agent_sequence

    def agent_dir(
        self,
        agent_name: str,
        sequence: Optional[int] = None,
    ) -> Path:
        """
        Create and return an artifact directory for an agent.

        Example:

            01_rtl_analysis
            02_planning
            03_test_generation
        """

        if sequence is None:
            sequence = self.next_agent_sequence()

        clean_name = safe_filename(
            agent_name,
            default="agent",
        ).lower()

        directory = self.run_dir / (
            f"{sequence:02d}_{clean_name}"
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return directory

    def started(
        self,
        agent: str,
        *,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record agent start.
        """

        event = self.log_activity(
            "agent_started",
            f"{agent} started",
            agent=agent,
            iteration=iteration,
            status="running",
            metadata=metadata,
        )

        self._agent_events.append(event)

        return event

    def completed(
        self,
        agent: str,
        *,
        iteration: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record agent completion.
        """

        event = self.log_activity(
            "agent_completed",
            f"{agent} completed",
            agent=agent,
            iteration=iteration,
            status="completed",
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

        self._agent_events.append(event)

        return event

    def failed(
        self,
        agent: str,
        error: Any,
        *,
        iteration: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record agent failure.
        """

        final_metadata = dict(metadata or {})

        final_metadata["error"] = str(error)

        event = self.log_activity(
            "agent_failed",
            f"{agent} failed",
            agent=agent,
            iteration=iteration,
            status="failed",
            duration_seconds=duration_seconds,
            metadata=final_metadata,
            level="ERROR",
        )

        self._agent_events.append(event)

        return event

    def agent_event(
        self,
        agent: str,
        event_type: str,
        message: str = "",
        *,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
    ) -> Dict[str, Any]:
        """
        Record a custom event associated with an agent.
        """

        return self.log_activity(
            event_type,
            message or f"{agent}: {event_type}",
            agent=agent,
            iteration=iteration,
            metadata=metadata,
            level=level,
        )

    # -----------------------------------------------------------------------
    # LLM lifecycle
    # -----------------------------------------------------------------------

    def llm_started(
        self,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        prompt_chars: Optional[int] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record LLM request start.

        The actual prompt text should generally NOT be logged here.
        Store prompt hashes or sizes instead if needed.
        """

        final_metadata = dict(metadata or {})

        if model is not None:
            final_metadata["model"] = model

        if prompt_chars is not None:
            final_metadata["prompt_chars"] = prompt_chars

        return self.log_activity(
            "llm_started",
            "LLM request started",
            agent=agent,
            iteration=iteration,
            status="running",
            metadata=final_metadata,
        )

    def llm_completed(
        self,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        response_chars: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record successful LLM request.
        """

        final_metadata = dict(metadata or {})

        if model is not None:
            final_metadata["model"] = model

        if response_chars is not None:
            final_metadata["response_chars"] = response_chars

        return self.log_activity(
            "llm_completed",
            "LLM request completed",
            agent=agent,
            iteration=iteration,
            status="completed",
            duration_seconds=duration_seconds,
            metadata=final_metadata,
        )

    def llm_failed(
        self,
        error: Any,
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record failed LLM request.
        """

        final_metadata = dict(metadata or {})

        final_metadata["error"] = str(error)

        if model is not None:
            final_metadata["model"] = model

        return self.log_activity(
            "llm_failed",
            "LLM request failed",
            agent=agent,
            iteration=iteration,
            status="failed",
            duration_seconds=duration_seconds,
            metadata=final_metadata,
            level="ERROR",
        )

    # -----------------------------------------------------------------------
    # Simulation lifecycle
    # -----------------------------------------------------------------------

    def simulation_started(
        self,
        *,
        agent: Optional[str] = None,
        command: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record simulation start.
        """

        final_metadata = dict(metadata or {})

        if command is not None:
            final_metadata["command"] = command

        return self.log_activity(
            "simulation_started",
            "Simulation started",
            agent=agent,
            iteration=iteration,
            status="running",
            metadata=final_metadata,
        )

    def simulation_completed(
        self,
        *,
        agent: Optional[str] = None,
        return_code: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record successful simulation completion.
        """

        final_metadata = dict(metadata or {})

        if return_code is not None:
            final_metadata["return_code"] = return_code

        return self.log_activity(
            "simulation_completed",
            "Simulation completed",
            agent=agent,
            iteration=iteration,
            status="completed",
            duration_seconds=duration_seconds,
            metadata=final_metadata,
        )

    def simulation_failed(
        self,
        error: Any,
        *,
        agent: Optional[str] = None,
        return_code: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record failed simulation.
        """

        final_metadata = dict(metadata or {})

        final_metadata["error"] = str(error)

        if return_code is not None:
            final_metadata["return_code"] = return_code

        return self.log_activity(
            "simulation_failed",
            "Simulation failed",
            agent=agent,
            iteration=iteration,
            status="failed",
            duration_seconds=duration_seconds,
            metadata=final_metadata,
            level="ERROR",
        )

    # -----------------------------------------------------------------------
    # Artifact management
    # -----------------------------------------------------------------------

    def _register_artifact(
        self,
        path: Path,
        *,
        artifact_type: str = "file",
        agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a generated file in artifact_manifest.json.
        """

        path = path.resolve()

        self._artifact_sequence += 1

        try:
            relative_path = path.relative_to(
                self.run_dir.resolve()
            )

            relative_text = str(relative_path)

        except ValueError:
            relative_text = str(path)

        exists = path.exists()

        size_bytes = (
            path.stat().st_size
            if exists
            else 0
        )

        sha256 = (
            sha256_file(path)
            if exists and path.is_file()
            else None
        )

        artifact = {
            "artifact_id": f"artifact_{self._artifact_sequence:05d}",
            "created_at": utc_now(),
            "run_id": self.run_id,
            "path": relative_text,
            "absolute_path": str(path),
            "artifact_type": artifact_type,
            "agent": agent,
            "description": description,
            "exists": exists,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "metadata": safe_json_value(metadata or {}),
        }

        self._artifacts.append(artifact)

        self._write_artifact_manifest()

        self.log_activity(
            "artifact_created",
            f"Artifact created: {relative_text}",
            agent=agent,
            metadata={
                "artifact_id": artifact["artifact_id"],
                "path": relative_text,
                "artifact_type": artifact_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
            },
        )

        return artifact

    def write_text(
        self,
        relative_path: str | Path,
        content: Any,
        *,
        artifact_type: str = "text",
        agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Write text into the run directory and register it as an artifact.

        Example:

            logger.write_text(
                "03_test_generation/tests.txt",
                generated_tests,
                artifact_type="generated_test",
                agent="test_generator",
            )
        """

        relative = Path(relative_path)

        path = self.run_dir / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            str(content),
            encoding="utf-8",
        )

        self._register_artifact(
            path,
            artifact_type=artifact_type,
            agent=agent,
            description=description,
            metadata=metadata,
        )

        return path

    def write_code(
        self,
        relative_path: str | Path,
        code: Any,
        *,
        language: Optional[str] = None,
        agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Write source code and register it as an artifact.
        """

        final_metadata = dict(metadata or {})

        if language:
            final_metadata["language"] = language

        artifact_type = (
            "source_code"
            if language
            else "code"
        )

        return self.write_text(
            relative_path,
            code,
            artifact_type=artifact_type,
            agent=agent,
            description=description,
            metadata=final_metadata,
        )

    def write_json(
        self,
        relative_path: str | Path,
        payload: Any,
        *,
        artifact_type: str = "json",
        agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Serialize an object as JSON and register it as an artifact.
        """

        relative = Path(relative_path)

        path = self.run_dir / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                safe_json_value(payload),
                handle,
                indent=2,
                ensure_ascii=False,
            )

            handle.write("\n")

        self._register_artifact(
            path,
            artifact_type=artifact_type,
            agent=agent,
            description=description,
            metadata=metadata,
        )

        return path

    def write_bytes(
        self,
        relative_path: str | Path,
        content: bytes,
        *,
        artifact_type: str = "binary",
        agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Write binary content and register it as an artifact.
        """

        relative = Path(relative_path)

        path = self.run_dir / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(content)

        self._register_artifact(
            path,
            artifact_type=artifact_type,
            agent=agent,
            description=description,
            metadata=metadata,
        )

        return path

    # -----------------------------------------------------------------------
    # State snapshots
    # -----------------------------------------------------------------------

    def write_state_snapshot(
        self,
        state: Any,
        *,
        name: str = "state_snapshot",
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> Path:
        """
        Persist a snapshot of LangGraph verification state.

        This is useful for debugging and reproducibility.

        Large fields can be filtered by the workflow before calling this
        function if required.
        """

        clean_name = safe_filename(
            name,
            default="state_snapshot",
        )

        filename = (
            f"{clean_name}"
            f"_iteration_{iteration if iteration is not None else 0}"
            f".json"
        )

        return self.write_json(
            Path("state_snapshots") / filename,
            state,
            artifact_type="state_snapshot",
            agent=agent,
            description="LangGraph verification state snapshot",
            metadata={
                "iteration": iteration,
            },
        )

    # -----------------------------------------------------------------------
    # Exceptions
    # -----------------------------------------------------------------------

    def exception_text(
        self,
        error: BaseException,
    ) -> str:
        """
        Convert an exception into a complete traceback string.
        """

        return "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__,
            )
        )

    def log_exception(
        self,
        event_type: str,
        error: BaseException,
        *,
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Log an exception including its traceback.
        """

        final_metadata = dict(metadata or {})

        final_metadata.update(
            {
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "traceback": self.exception_text(error),
            }
        )

        return self.log_activity(
            event_type,
            f"{type(error).__name__}: {error}",
            agent=agent,
            iteration=iteration,
            status="failed",
            metadata=final_metadata,
            level="ERROR",
        )

    # -----------------------------------------------------------------------
    # Convenience logging
    # -----------------------------------------------------------------------

    def info(
        self,
        message: str,
        *,
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Write an informational event.
        """

        return self.log_activity(
            "info",
            message,
            agent=agent,
            iteration=iteration,
            metadata=metadata,
            level="INFO",
        )

    def warning(
        self,
        message: str,
        *,
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Write a warning event.
        """

        return self.log_activity(
            "warning",
            message,
            agent=agent,
            iteration=iteration,
            metadata=metadata,
            level="WARNING",
        )

    def error(
        self,
        message: str,
        *,
        agent: Optional[str] = None,
        iteration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Write an error event.
        """

        return self.log_activity(
            "error",
            message,
            agent=agent,
            iteration=iteration,
            metadata=metadata,
            level="ERROR",
        )

    # -----------------------------------------------------------------------
    # Manifest / inspection helpers
    # -----------------------------------------------------------------------

    def manifest(self) -> Dict[str, Any]:
        """
        Return the current in-memory run manifest.
        """

        return {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "created_at": self.created_at,
            "metadata": safe_json_value(self.metadata),
            "artifact_count": len(self._artifacts),
            "agent_event_count": len(self._agent_events),
            "artifacts": safe_json_value(self._artifacts),
        }

    @property
    def artifacts(self) -> list[Dict[str, Any]]:
        """
        Return a copy of the registered artifact list.
        """

        return list(self._artifacts)

    @property
    def agent_events(self) -> list[Dict[str, Any]]:
        """
        Return a copy of recorded agent lifecycle events.
        """

        return list(self._agent_events)

    # -----------------------------------------------------------------------
    # Cleanup
    # -----------------------------------------------------------------------

    def close(self) -> None:
        """
        Flush and close file handlers.

        Usually not required during a Streamlit run, but useful for tests,
        CLI execution, and clean process shutdown.
        """

        for handler in list(self.python_logger.handlers):

            try:
                handler.flush()
                handler.close()

            finally:
                self.python_logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "ActivityLogger",
    "utc_now",
    "safe_filename",
    "safe_json_value",
    "sha256_file",
]
