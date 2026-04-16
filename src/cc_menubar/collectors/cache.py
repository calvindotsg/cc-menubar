"""Aggregate cache with configurable TTL and atomic writes."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_PATH = Path("/tmp/cc-menubar-cache.json")


def read_cache(ttl: int = 300) -> dict[str, Any] | None:
    """Read cache if it exists and is within TTL. Returns None if stale or missing."""
    try:
        if not CACHE_PATH.is_file():
            return None
        data = json.loads(CACHE_PATH.read_text())
        if time.time() - data.get("timestamp", 0) > ttl:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(data: dict[str, Any]) -> None:
    """Atomically write cache data with current timestamp."""
    data["timestamp"] = time.time()
    tmp_path = str(CACHE_PATH) + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        os.rename(tmp_path, CACHE_PATH)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
