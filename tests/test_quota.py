"""Tests for the canonical-schema quota collector."""

from __future__ import annotations

import json

from cc_menubar.collectors.quota import read_quota


def _canonical(five_hour: dict | None = None, seven_day: dict | None = None) -> dict:
    rate_limits: dict = {}
    if five_hour is not None:
        rate_limits["five_hour"] = five_hour
    if seven_day is not None:
        rate_limits["seven_day"] = seven_day
    return {"rate_limits": rate_limits}


def test_read_quota_missing_file(tmp_path):
    """Returns None when cache file doesn't exist."""
    assert read_quota(tmp_path / "nonexistent.json") is None


def test_read_quota_valid(tmp_path):
    """Parses canonical rate_limits fields for both windows."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text(
        json.dumps(
            _canonical(
                five_hour={"used_percentage": 30.0, "resets_at": 1745164800},
                seven_day={"used_percentage": 10.0, "resets_at": 1745596800},
            )
        )
    )
    result = read_quota(cache_file)
    assert result is not None
    assert result.five_hour is not None
    assert result.five_hour.used_percentage == 30.0
    assert result.five_hour.resets_at == 1745164800
    assert result.seven_day is not None
    assert result.seven_day.used_percentage == 10.0
    assert result.seven_day.resets_at == 1745596800


def test_read_quota_corrupt_json(tmp_path):
    """Returns None on corrupt JSON."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text("{invalid json")
    assert read_quota(cache_file) is None


def test_read_quota_rate_limits_absent(tmp_path):
    """rate_limits key absent → both windows None, QuotaInfo still returned."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text(json.dumps({"model": {"id": "claude-opus-4-7"}}))
    result = read_quota(cache_file)
    assert result is not None
    assert result.five_hour is None
    assert result.seven_day is None


def test_read_quota_one_window_absent(tmp_path):
    """five_hour present, seven_day absent → only five_hour populated."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text(
        json.dumps(_canonical(five_hour={"used_percentage": 42.0, "resets_at": 1745164800}))
    )
    result = read_quota(cache_file)
    assert result is not None
    assert result.five_hour is not None
    assert result.seven_day is None


def test_read_quota_wrong_types(tmp_path):
    """Windows with non-canonical value types are rejected, not coerced."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text(
        json.dumps(
            _canonical(
                five_hour={"used_percentage": "nope", "resets_at": 1},
                seven_day={"used_percentage": 10.0, "resets_at": "2026-04-20T00:00:00Z"},
            )
        )
    )
    result = read_quota(cache_file)
    assert result is not None
    assert result.five_hour is None
    assert result.seven_day is None


def test_read_quota_cache_age_from_mtime(tmp_path):
    """cache_age is derived from file mtime (canonical schema has no timestamp)."""
    cache_file = tmp_path / "statusline-input.json"
    cache_file.write_text(json.dumps(_canonical()))
    result = read_quota(cache_file)
    assert result is not None
    assert result.cache_age >= 0.0
    assert result.cache_age < 10.0  # just written
