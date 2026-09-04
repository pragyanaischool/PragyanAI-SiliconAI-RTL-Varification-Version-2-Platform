"""Structured per-run activity and artifact logging."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def safe_filename(value: str) -> str:
    """Convert text into a filesystem-safe filename."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))[:120] or "artifact"


def sha256_file(file_path: str | Path, chunk_size: int = 8192) -> str:
    """Compute the SHA256 hash of a file safely."""
    sha256_hash = hashlib.sha256()
    path = Path(file_path)
    if not path.exists():
        return ""
    try:
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""


def _safe_repr(
    value: Any,
    max_length: int = 2000,
) -> str:
    """
    Safely create a bounded repr().

    repr() itself can theoretically trigger recursion,
    so this function is also defensive.
    """
    try:
        text = repr(value)
        if len(text) > max_length:
            return text[:max_length] + "...<truncated>"
        return text
    except RecursionError:
        return "<repr-recursion-error>"
    except Exception:
        try:
            return f"<{type(value).__name__}>"
        except Exception:
            return "<unrepresentable>"


def safe_json_value(
    value: Any,
    *,
    max_depth: int = 6,
    _depth: int = 0,
    _seen: Optional[set[int]] = None,
) -> Any:
    """
    Convert arbitrary Python values into JSON-safe values.

    IMPORTANT:
    This serializer is deliberately cycle-safe.
    """
    if _seen is None:
        _seen = set()

    if _depth > max_depth:
        return "<max-depth>"

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, bytes):
        try:
            return {
                "type": "bytes",
                "length": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
            }
        except Exception:
            return "<bytes>"

    if isinstance(value, BaseException):
        try:
            return {
                "type": type(value).__name__,
                "message": str(value),
            }
        except Exception:
            return "<exception>"

    if isinstance(value, logging.Logger):
        try:
            return {
                "type": "Logger",
                "name": value.name,
            }
        except Exception:
            return "<logger>"

    try:
        object_id = id(value)
        if object_id in _seen:
            return "<circular-reference>"
        _seen.add(object_id)
    except Exception:
        object_id = None

    try:
        if isinstance(value, dict):
            result: Dict[str, Any] = {}
            for key, item in value.items():
                try:
                    key_text = str(key)
                    if key_text in {
                        "logger",
                        "verification_run",
                        "_logger",
                        "_run_manager",
                        "run_manager",
                        "python_logger",
                    }:
                        result[key_text] = "<runtime-object>"
                        continue

                    result[key_text] = safe_json_value(
                        item,
                        max_depth=max_depth,
                        _depth=_depth + 1,
                        _seen=_seen,
                    )
                except RecursionError:
                    result[str(key)] = "<recursion-error>"
                except Exception:
                    result[str(key)] = "<unserializable>"
            return result

        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                try:
                    result.append(
                        safe_json_value(
                            item,
                            max_depth=max_depth,
                            _depth=_depth + 1,
                            _seen=_seen,
                        )
                    )
                except RecursionError:
                    result.append("<recursion-error>")
                except Exception:
                    result.append("<unserializable>")
            return result

        if isinstance(value, (set, frozenset)):
            result = []
            try:
                items = sorted(value, key=str)
            except Exception:
                items = list(value)
            for item in items:
                try:
                    result.append(
                        safe_json_value(
                            item,
                            max_depth=max_depth,
                            _depth=_depth + 1,
                            _seen=_seen,
                        )
                    )
                except RecursionError:
                    result.append("<recursion-error>")
                except Exception:
                    result.append("<unserializable>")
            return result

        if hasattr(value, "__dict__"):
            try:
                class_name = type(value).__name__
                runtime_classes = {
                    "ActivityLogger",
                    "VerificationRun",
                    "RunManager",
                    "Logger",
                    "FileHandler",
                    "StreamHandler",
                    "RotatingFileHandler",
                    "TimedRotatingFileHandler",
                    "Formatter",
                }
                if class_name in runtime_classes:
                    return f"<{class_name}>"

                return {
                    "type": class_name,
                    "repr": _safe_repr(value),
                }
            except RecursionError:
                return "<repr-recursion-error>"
            except Exception:
                try:
                    return f"<{type(value).__name__}>"
                except Exception:
                    return "<object>"

        try:
            json.dumps(value)
            return value
        except Exception:
            pass

        return _safe_repr(value)

    except RecursionError:
        return "<recursion-error>"

    except Exception:
        try:
            return f"<unserializable:{type(value).__name__}>"
        except Exception:
            return "<unserializable>"

    finally:
        if object_id is not None:
            try:
                _seen.discard(object_id)
            except Exception:
                pass


class ActivityLogger:
    def __init__(self, run_dir: str | Path, run_id: str, metadata: dict[str, Any] | None = None):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.activity_file = self.run_dir / "agent_activity.jsonl"
        self.workflow_log = self.run_dir / "workflow.log"
        self.logger = logging.getLogger(f"PragyanAI.run.{run_id}")
        self._setup_file_logger()

    def _setup_file_logger(self):
        if any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            return
        handler = logging.FileHandler(self.workflow_log, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    @staticmethod
    def _safe(value: Any) -> Any:
        return safe_json_value(value)

    @staticmethod
    def _name(value: str) -> str:
        return safe_filename(value)

    def agent_dir(self, agent: str, step: int) -> Path:
        path = self.run_dir / f"{step:02d}_{self._name(agent)}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def log_activity(
        self,
        agent: str,
        activity: str,
        status: str = "INFO",
        message: str = "",
        step: int | None = None,
        iteration: int | None = None,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "timestamp": utc_now().isoformat(),
            "event_id": uuid.uuid4().hex[:12],
            "run_id": self.run_id,
            "agent": agent,
            "activity": activity,
            "status": status,
            "message": message,
            "step": step,
            "iteration": iteration,
            "duration_ms": duration_ms,
            "metadata": self._safe(metadata or {}),
        }
        with self.activity_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.logger.info("%s | %s | %s | %s", agent, activity, status, message)
        return event

    def write_text(self, agent: str, filename: str, content: Any, step: int) -> str:
        path = self.agent_dir(agent, step) / self._name(filename)
        path.write_text("" if content is None else str(content), encoding="utf-8")
        self.log_activity(
            agent,
            "ARTIFACT_WRITTEN",
            "SUCCESS",
            f"Wrote {path.name}",
            step=step,
            metadata={"path": str(path.relative_to(self.run_dir))},
        )
        return str(path)

    def write_code(self, agent: str, filename: str, code: str, step: int) -> str:
        return self.write_text(agent, filename, code, step)

    def write_json(self, agent: str, filename: str, data: Any, step: int) -> str:
        return self.write_text(
            agent,
            filename,
            json.dumps(self._safe(data), indent=2, ensure_ascii=False),
            step,
        )

    def started(self, agent: str, step: int, iteration: int, metadata: dict[str, Any] | None = None):
        return self.log_activity(
            agent,
            "EXECUTION_STARTED",
            "STARTED",
            f"{agent} started",
            step=step,
            iteration=iteration,
            metadata=metadata,
        )

    def completed(
        self,
        agent: str,
        step: int,
        iteration: int,
        duration_ms: float,
        metadata=None,
    ):
        return self.log_activity(
            agent,
            "EXECUTION_COMPLETED",
            "SUCCESS",
            f"{agent} completed",
            step=step,
            iteration=iteration,
            duration_ms=duration_ms,
            metadata=metadata,
        )

    def failed(self, agent: str, step: int, iteration: int, error: Exception):
        return self.log_activity(
            agent,
            "EXECUTION_FAILED",
            "ERROR",
            str(error),
            step=step,
            iteration=iteration,
            metadata={"exception": type(error).__name__},
        )

    def run_started(self, metadata: dict[str, Any] | None = None):
        return self.log_activity(
            "run_manager",
            "RUN_STARTED",
            "STARTED",
            f"Run {self.run_id} started",
            metadata=metadata,
        )

    def run_completed(self, verdict: str | None = None, metadata: dict[str, Any] | None = None):
        return self.log_activity(
            "run_manager",
            "RUN_COMPLETED",
            "SUCCESS",
            f"Run {self.run_id} completed with verdict {verdict}",
            metadata={"verdict": verdict, **(metadata or {})},
        )

    def run_failed(self, error: Any, metadata: dict[str, Any] | None = None):
        return self.log_activity(
            "run_manager",
            "RUN_FAILED",
            "ERROR",
            f"Run {self.run_id} failed: {error}",
            metadata=metadata,
        )

    def close(self):
        """Clean up logger handlers if needed."""
        for h in list(self.logger.handlers):
            h.close()
            self.logger.removeHandler(h)

    def manifest(self, data: dict[str, Any]):
        path = self.run_dir / "run_manifest.json"
        path.write_text(json.dumps(self._safe(data), indent=2), encoding="utf-8")
