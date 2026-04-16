"""Tests for SwiftBar render output."""

from __future__ import annotations

from cc_menubar.collectors.quota import ExtraUsageData, QuotaData, QuotaInfo
from cc_menubar.config import Config
from cc_menubar.render import Theme, _format_project_display, render


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
        five_hour=QuotaData(utilization=five_hour_util, resets_at="2026-04-16T18:00:00Z"),
        seven_day=QuotaData(utilization=seven_day_util, resets_at="2026-04-20T00:00:00Z"),
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
        assert "Quota & Runway" in output

    def test_quota_section_disabled(self):
        config = _make_config(quota_enabled=False)
        output = render(config, _make_quota(), None, None)
        assert "Quota & Runway" not in output

    def test_footer_present(self):
        config = _make_config()
        output = render(config, None, None, None)
        assert "Refresh | refresh=true" in output

    def test_extra_usage_from_json(self):
        """Extra usage from JSON data renders in quota section."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=27.0, resets_at="2026-04-16T18:00:00Z"),
            seven_day=QuotaData(utilization=9.0, resets_at="2026-04-20T00:00:00Z"),
            cache_age=10.0,
            extra_usage=ExtraUsageData(
                spent=130.06, budget=200.0, resets_at="2026-05-01T00:00:00Z"
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
            five_hour=QuotaData(utilization=7.0, resets_at="2026-04-16T18:00:00Z"),
            seven_day=QuotaData(utilization=30.0, resets_at="2026-04-20T00:00:00Z"),
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        assert "5-Hour: 93% remaining" in output
        assert "7-Day: 70% remaining" in output

    def test_sonnet_row_present(self):
        """7-Day (Sonnet) row appears when seven_day_sonnet is populated."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(utilization=7.0, resets_at="2026-04-16T18:00:00Z"),
            seven_day=QuotaData(utilization=30.0, resets_at="2026-04-20T00:00:00Z"),
            cache_age=10.0,
            seven_day_sonnet=QuotaData(utilization=5.0, resets_at="2026-04-20T00:00:00Z"),
        )
        output = render(config, quota, None, None)
        assert "7-Day (Sonnet): 95% remaining" in output

    def test_sonnet_row_absent(self):
        """7-Day (Sonnet) row is omitted when seven_day_sonnet is None."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert "7-Day (Sonnet)" not in output


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
