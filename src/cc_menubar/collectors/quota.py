"""Read quota data from canonical Claude Code statusline JSON cache.

cc-menubar consumes the public Claude Code statusline schema verbatim:
https://code.claude.com/docs/en/statusline#full-json-schema

A producer (any tool wired into `~/.claude/settings.json` `statusLine`) writes
the stdin JSON to the cache file. See README §Quota setup for wiring recipes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QuotaData:
    """Quota utilization for one rate-limit window."""

    used_percentage: float  # 0.0-100.0 percent used (canonical rate_limits.*.used_percentage)
    resets_at: int  # Unix epoch seconds (canonical rate_limits.*.resets_at)


@dataclass
class QuotaInfo:
    """Combined quota info for both canonical windows."""

    five_hour: QuotaData | None
    seven_day: QuotaData | None
    cache_age: float  # seconds since cache file was last written (file mtime)


def _parse_window(window: object) -> QuotaData | None:
    if not isinstance(window, dict):
        return None
    used = window.get("used_percentage")
    resets = window.get("resets_at")
    if not isinstance(used, (int, float)) or isinstance(used, bool):
        return None
    if not isinstance(resets, int) or isinstance(resets, bool):
        return None
    return QuotaData(used_percentage=float(used), resets_at=resets)


def read_quota(cache_file: Path) -> QuotaInfo | None:
    """Read canonical-schema quota data from the given cache file.

    Returns None if the file is missing, unreadable, or malformed. Returns a
    QuotaInfo with `five_hour` / `seven_day` independently set to None when
    the whole `rate_limits` key or an individual window is absent, per the
    canonical schema's documented absence rules.
    """
    try:
        if not cache_file.is_file():
            return None
        data = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None

    cache_age = max(0.0, time.time() - cache_file.stat().st_mtime)
    rate_limits = data.get("rate_limits") or {}
    if not isinstance(rate_limits, dict):
        rate_limits = {}

    return QuotaInfo(
        five_hour=_parse_window(rate_limits.get("five_hour")),
        seven_day=_parse_window(rate_limits.get("seven_day")),
        cache_age=cache_age,
    )
