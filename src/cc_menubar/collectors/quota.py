"""Read quota data from statusline usage cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

USAGE_CACHE_FILE = Path("/tmp/claude-statusline-usage.json")


@dataclass
class QuotaData:
    """Quota utilization for a time window."""

    utilization: float  # 0.0-100.0 percent used; matches statusline rate_limits.*.used_percentage
    resets_at: str  # ISO 8601 timestamp


@dataclass
class ExtraUsageData:
    """Extra usage billing data."""

    spent: float
    budget: float
    resets_at: str


@dataclass
class QuotaInfo:
    """Combined quota info for both windows."""

    five_hour: QuotaData | None
    seven_day: QuotaData | None
    cache_age: float  # seconds since cache was written
    extra_usage: ExtraUsageData | None = None
    seven_day_sonnet: QuotaData | None = None


def read_quota() -> QuotaInfo | None:
    """Read quota data from /tmp/claude-statusline-usage.json.

    This file is written by statusline.py during active Claude Code sessions.
    Returns None if the file doesn't exist or can't be parsed.
    """
    try:
        if not USAGE_CACHE_FILE.is_file():
            return None

        data = json.loads(USAGE_CACHE_FILE.read_text())

        import time

        cache_age = time.time() - data.get("timestamp", 0)

        five_hour = None
        if data.get("five_hour"):
            fh = data["five_hour"]
            five_hour = QuotaData(
                utilization=fh.get("utilization", 0.0),
                resets_at=fh.get("resets_at", ""),
            )

        seven_day = None
        if data.get("seven_day"):
            sd = data["seven_day"]
            seven_day = QuotaData(
                utilization=sd.get("utilization", 0.0),
                resets_at=sd.get("resets_at", ""),
            )

        extra_usage = None
        if data.get("extra_usage"):
            eu = data["extra_usage"]
            extra_usage = ExtraUsageData(
                spent=eu.get("spent", 0.0),
                budget=eu.get("budget", 0.0),
                resets_at=eu.get("resets_at", ""),
            )

        seven_day_sonnet = None
        if data.get("seven_day_sonnet"):
            sds = data["seven_day_sonnet"]
            seven_day_sonnet = QuotaData(
                utilization=sds.get("utilization", 0.0),
                resets_at=sds.get("resets_at", ""),
            )

        return QuotaInfo(
            five_hour=five_hour,
            seven_day=seven_day,
            cache_age=cache_age,
            extra_usage=extra_usage,
            seven_day_sonnet=seven_day_sonnet,
        )

    except (json.JSONDecodeError, OSError):
        return None
