"""Verification run creation."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from config.settings import RUNS_DIR
from .activity_logger import ActivityLogger

def create_verification_run(metadata=None):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = Path(RUNS_DIR) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = ActivityLogger(run_dir, run_id)
    logger.manifest({
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {},
    })
    return run_id, run_dir, logger
