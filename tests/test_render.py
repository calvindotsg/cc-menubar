"""Tests for SwiftBar render output."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cc_menubar.collectors.blocks import BlockInfo
from cc_menubar.collectors.quota import ExtraUsageData, QuotaData, QuotaInfo
from cc_menubar.config import Config
from cc_menubar.labels import LABELS
from cc_menubar.render import (
    Theme,
    _format_model_name,
    _format_project_display,
    _format_reset_absolute,
    _format_time_until,
    render,
)


def _iso_from_now(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    """Return ISO-8601 UTC timestamp offset from now."""
    t = datetime.now(UTC) + timedelta(days=days, hours=hours, minutes=minutes)
    return t.isoformat()


def _make_config(**kwargs) -> Config:
    """Create a Config with defaults, overriding specified fields."""
    defaults = {
        "symbol": "gauge.with.needle.fill",
        "text": "none",
        "color": "monochrome",
        "metric": "5h",
        "cycle": [],
        "quota_enabled": True,
        "blocks_enabled": False,
        "opusplan_enabled": False,
        "context_enabled": False,
        "activity_enabled": False,
        "tools_enabled": False,
        "projects_enabled": False,
        "extra_usage_budget": 0.0,
        "theme_preset": "ayu",
        "theme_light": {},
        "theme_dark": {},
    }
    defaults.update(kwargs)
    return Config(**defaults)


def _make_quota(five_hour_util: float = 27.0, seven_day_util: float = 9.0) -> QuotaInfo:
    return QuotaInfo(
        five_hour=QuotaData(utilization=five_hour_util, resets_at=_iso_from_now(hours=3)),
        seven_day=QuotaData(utilization=seven_day_util, resets_at=_iso_from_now(days=6, hours=18)),
        cache_age=10.0,
    )


class TestTheme:
    def test_default_preset(self):
        theme = Theme("ayu", {}, {})
        assert theme.color("success") == "#647f2e,#c2d94c"

    def test_override(self):
        theme = Theme("ayu", {"success": "#custom"}, {})
        assert theme.color("success") == "#custom,#c2d94c"

    def test_threshold_role(self):
        theme = Theme("ayu", {}, {})
        assert theme.threshold_role(0.8) == "success"
        assert theme.threshold_role(0.35) == "warning"
        assert theme.threshold_role(0.1) == "error"


class TestTitleLine:
    def test_icon_only_default(self):
        """Default config: icon only, no text."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        lines = output.split("\n")
        assert "sfimage=gauge.with.needle.fill" in lines[0]
        assert "sfvalue=0.73" in lines[0]
        # No text before the pipe
        assert lines[0].startswith("| ")

    def test_percent_text(self):
        config = _make_config(text="percent")
        output = render(config, _make_quota(), None, None)
        lines = output.split("\n")
        assert "73%" in lines[0]

    def test_label_text(self):
        config = _make_config(text="label")
        output = render(config, _make_quota(), None, None)
        lines = output.split("\n")
        assert "5h: 73%" in lines[0]

    def test_threshold_color_warning(self):
        """Threshold color at 38% remaining (warning)."""
        config = _make_config(text="percent", color="threshold")
        output = render(config, _make_quota(five_hour_util=62.0), None, None)
        lines = output.split("\n")
        assert "color=" in lines[0]

    def test_monochrome_no_color(self):
        """Monochrome: no color parameter on text."""
        config = _make_config(text="percent", color="monochrome")
        output = render(config, _make_quota(), None, None)
        lines = output.split("\n")
        assert "color=" not in lines[0]

    def test_no_quota_data(self):
        """No quota data: omit sfvalue."""
        config = _make_config()
        output = render(config, None, None, None)
        lines = output.split("\n")
        assert "sfvalue" not in lines[0]

    def test_fallback_on_error(self):
        """Render fallback is tested via CLI exception handler."""
        pass


class TestDropdown:
    def test_separator_present(self):
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert "---" in output

    def test_quota_section_present(self):
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert LABELS["section.rate_limits"] in output

    def test_quota_section_disabled(self):
        config = _make_config(quota_enabled=False)
        output = render(config, _make_quota(), None, None)
        assert LABELS["section.rate_limits"] not in output

    def test_footer_present(self):
        config = _make_config()
        output = render(config, None, None, None)
        assert "Refresh | refresh=true" in output

    def test_extra_usage_from_json(self):
        """Extra usage from JSON data renders in quota section.

        Label stays verbatim — 'Extra usage' is a common Claude term, not
        jargon to re-render.
        """
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=27.0, resets_at=_iso_from_now(hours=3)),
            seven_day=QuotaData(utilization=9.0, resets_at=_iso_from_now(days=6)),
            cache_age=10.0,
            extra_usage=ExtraUsageData(
                spent=130.06, budget=200.0, resets_at=_iso_from_now(days=14)
            ),
        )
        output = render(config, quota, None, None)
        assert "Extra usage: $130.06 / $200.00" in output

    def test_extra_usage_fallback_to_config(self):
        """Extra usage falls back to config when JSON absent."""
        config = _make_config(extra_usage_budget=100.0)
        output = render(config, _make_quota(), None, None)
        assert "Extra usage budget: $100.00" in output


class TestQuotaPercentSemantics:
    def test_percent_scale_rendering(self):
        """Guard against scale-bug regression: utilization 0-100 → correct remaining %."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=7.0, resets_at=_iso_from_now(hours=3)),
            seven_day=QuotaData(utilization=30.0, resets_at=_iso_from_now(days=6)),
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        assert "5-Hour: 93% left" in output
        assert "7-Day: 70% left" in output

    def test_sonnet_row_present(self):
        """7-Day (Sonnet only) row appears when seven_day_sonnet is populated."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=7.0, resets_at=_iso_from_now(hours=3)),
            seven_day=QuotaData(utilization=30.0, resets_at=_iso_from_now(days=6)),
            cache_age=10.0,
            seven_day_sonnet=QuotaData(utilization=5.0, resets_at=_iso_from_now(days=6)),
        )
        output = render(config, quota, None, None)
        assert "7-Day (Sonnet only): 95% left" in output

    def test_sonnet_row_absent(self):
        """7-Day (Sonnet only) row is omitted when seven_day_sonnet is None."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert "7-Day (Sonnet only)" not in output

    def test_days_in_runway(self):
        """Runways > 24h should use d/h/m formatting, not hours-only."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=50.0, resets_at=_iso_from_now(days=6, hours=18)),
            seven_day=None,
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        # Should contain day formatting for a 6-day-ish runway
        assert "6d" in output

    def test_burn_rate_from_ccusage(self):
        """Active 5h block row reads ccusage costUSD/costPerHour/remainingMinutes."""
        config = _make_config()
        quota = _make_quota()
        blocks = BlockInfo(
            blocks=[],
            active_block={
                "costUSD": 6.15,
                "burnRate": {"costPerHour": 11.4, "tokensPerMinute": 1234},
                "projection": {"remainingMinutes": 266},
                "startTime": _iso_from_now(hours=-2),
                "endTime": _iso_from_now(hours=3),
            },
        )
        output = render(config, quota, blocks, None)
        assert "Current 5h block:" in output
        assert "$6.15 so far" in output
        assert "$11.4/hr" in output
        assert "~266m left" in output

    def test_burn_rate_skipped_without_active_block(self):
        """No active block → no burn-rate row."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert "Current 5h block:" not in output


class TestFormatHelpers:
    def test_format_time_until_days(self):
        assert _format_time_until(_iso_from_now(days=2, hours=3, minutes=5)).startswith("2d 3h")

    def test_format_time_until_hours(self):
        result = _format_time_until(_iso_from_now(hours=2, minutes=30))
        assert "h" in result and "d" not in result

    def test_format_time_until_minutes(self):
        result = _format_time_until(_iso_from_now(minutes=45))
        assert result.endswith("m")
        assert "h" not in result

    def test_format_reset_absolute_same_day(self):
        # Something later today — don't assume future dates; just assert
        # no date prefix when we pick a same-day future time.
        now = datetime.now().astimezone()
        # pick a target well within today if possible, else tomorrow
        if now.hour < 22:
            target = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
            result = _format_reset_absolute(target.isoformat())
            assert "am" in result or "pm" in result
            assert " at " not in result

    def test_format_reset_absolute_future_date(self):
        target = datetime.now().astimezone() + timedelta(days=5)
        target = target.replace(hour=7, minute=0, second=0, microsecond=0)
        result = _format_reset_absolute(target.isoformat())
        assert " at " in result
        assert "7am" in result

    def test_format_reset_absolute_with_minutes(self):
        target = datetime.now().astimezone() + timedelta(days=1)
        target = target.replace(hour=12, minute=30, second=0, microsecond=0)
        result = _format_reset_absolute(target.isoformat())
        assert "12:30pm" in result

    def test_format_reset_absolute_noon(self):
        target = datetime.now().astimezone() + timedelta(days=1)
        target = target.replace(hour=12, minute=0, second=0, microsecond=0)
        result = _format_reset_absolute(target.isoformat())
        assert "12pm" in result

    def test_format_model_name_opus(self):
        assert _format_model_name("claude-opus-4-6") == "Opus 4.6"

    def test_format_model_name_haiku_with_suffix(self):
        assert _format_model_name("claude-haiku-4-5-20251001") == "Haiku 4.5"

    def test_format_model_name_sonnet(self):
        assert _format_model_name("claude-sonnet-4-6") == "Sonnet 4.6"

    def test_format_model_name_synthetic(self):
        assert _format_model_name("<synthetic>") == "<synthetic>"

    def test_format_model_name_unknown(self):
        assert _format_model_name("some-other-model") == "some-other-model"

    def test_format_model_name_empty(self):
        assert _format_model_name("") == ""


class TestFormatProjectDisplay:
    def test_github_path(self):
        from pathlib import Path

        home = str(Path.home())
        cwd = f"{home}/Documents/github/calvindotsg/cc-menubar"
        assert _format_project_display(cwd) == "calvindotsg/cc-menubar"

    def test_dotdir_path(self):
        from pathlib import Path

        home = str(Path.home())
        cwd = f"{home}/.config"
        assert _format_project_display(cwd) == ".config"
