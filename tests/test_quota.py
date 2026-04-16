"""Tests for quota collector."""

from __future__ import annotations

import json

from cc_menubar.collectors.quota import read_quota


def test_read_quota_missing_file(tmp_path, monkeypatch):
    """Returns None when cache file doesn't exist."""
    import cc_menubar.collectors.quota as mod

    monkeypatch.setattr(mod, "USAGE_CACHE_FILE", tmp_path / "nonexistent.json")
    assert read_quota() is None


def test_read_quota_valid(tmp_path, monkeypatch):
    """Parses valid cache file."""
    import time

    import cc_menubar.collectors.quota as mod

    cache_file = tmp_path / "usage.json"
    cache_file.write_text(
        json.dumps(
            {
                "timestamp": time.time(),
                "five_hour": {"utilization": 30.0, "resets_at": "2026-04-16T18:00:00Z"},
                "seven_day": {"utilization": 10.0, "resets_at": "2026-04-20T00:00:00Z"},
            }
        )
    )
    monkeypatch.setattr(mod, "USAGE_CACHE_FILE", cache_file)
    result = read_quota()
    assert result is not None
    assert result.five_hour is not None
    assert result.five_hour.utilization == 30.0
    assert result.seven_day is not None
    assert result.seven_day.utilization == 10.0


def test_read_quota_corrupt_json(tmp_path, monkeypatch):
    """Returns None on corrupt JSON."""
    import cc_menubar.collectors.quota as mod

    cache_file = tmp_path / "usage.json"
    cache_file.write_text("{invalid json")
    monkeypatch.setattr(mod, "USAGE_CACHE_FILE", cache_file)
    assert read_quota() is None


def test_read_quota_with_sonnet(tmp_path, monkeypatch):
    """Parses seven_day_sonnet field when present."""
    import time

    import cc_menubar.collectors.quota as mod

    cache_file = tmp_path / "usage.json"
    cache_file.write_text(
        json.dumps(
            {
                "timestamp": time.time(),
                "five_hour": {"utilization": 7.0, "resets_at": "2026-04-16T18:00:00Z"},
                "seven_day": {"utilization": 30.0, "resets_at": "2026-04-20T00:00:00Z"},
                "seven_day_sonnet": {"utilization": 5.0, "resets_at": "2026-04-20T00:00:00Z"},
            }
        )
    )
    monkeypatch.setattr(mod, "USAGE_CACHE_FILE", cache_file)
    result = read_quota()
    assert result is not None
    assert result.seven_day_sonnet is not None
    assert result.seven_day_sonnet.utilization == 5.0


def test_read_quota_sonnet_absent(tmp_path, monkeypatch):
    """seven_day_sonnet is None when field is absent from cache."""
    import time

    import cc_menubar.collectors.quota as mod

    cache_file = tmp_path / "usage.json"
    cache_file.write_text(
        json.dumps(
            {
                "timestamp": time.time(),
                "five_hour": {"utilization": 7.0, "resets_at": "2026-04-16T18:00:00Z"},
                "seven_day": {"utilization": 30.0, "resets_at": "2026-04-20T00:00:00Z"},
            }
        )
    )
    monkeypatch.setattr(mod, "USAGE_CACHE_FILE", cache_file)
    result = read_quota()
    assert result is not None
    assert result.seven_day_sonnet is None
