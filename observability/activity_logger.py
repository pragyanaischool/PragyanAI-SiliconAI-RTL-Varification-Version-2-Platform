"""Structured per-run activity and artifact logging."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class ActivityLogger:
    def __init__(self, run_dir: str | Path, run_id: str):
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
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): ActivityLogger._safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [ActivityLogger._safe(v) for v in value]
        return str(value)

    @staticmethod
    def _name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))[:120] or "artifact"

    def agent_dir(self, agent: str, step: int) -> Path:
        path = self.run_dir / f"{step:02d}_{self._name(agent)}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def log_activity(self, agent: str, activity: str, status: str = "INFO",
                     message: str = "", step: int | None = None,
                     iteration: int | None = None, duration_ms: float | None = None,
                     metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
        self.log_activity(agent, "ARTIFACT_WRITTEN", "SUCCESS",
                          f"Wrote {path.name}", step=step,
                          metadata={"path": str(path.relative_to(self.run_dir))})
        return str(path)

    def write_code(self, agent: str, filename: str, code: str, step: int) -> str:
        return self.write_text(agent, filename, code, step)

    def write_json(self, agent: str, filename: str, data: Any, step: int) -> str:
        return self.write_text(
            agent, filename,
            json.dumps(self._safe(data), indent=2, ensure_ascii=False),
            step,
        )

    def started(self, agent: str, step: int, iteration: int):
        return self.log_activity(agent, "EXECUTION_STARTED", "STARTED",
                                 f"{agent} started", step, iteration)

    def completed(self, agent: str, step: int, iteration: int, duration_ms: float, metadata=None):
        return self.log_activity(agent, "EXECUTION_COMPLETED", "SUCCESS",
                                 f"{agent} completed", step, iteration, duration_ms, metadata)

    def failed(self, agent: str, step: int, iteration: int, error: Exception):
        return self.log_activity(agent, "EXECUTION_FAILED", "ERROR",
                                 str(error), step, iteration,
                                 metadata={"exception": type(error).__name__})

    def manifest(self, data: dict[str, Any]):
        path = self.run_dir / "run_manifest.json"
        path.write_text(json.dumps(self._safe(data), indent=2), encoding="utf-8")
