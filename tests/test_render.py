"""Tests for SwiftBar render output."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cc_menubar.collectors.blocks import BlockInfo
from cc_menubar.collectors.quota import QuotaData, QuotaInfo
from cc_menubar.config import Config
from cc_menubar.labels import LABELS
from cc_menubar.render import (
    Theme,
    _caption,
    _format_model_name,
    _format_project_display,
    _format_reset_absolute,
    _format_time_until,
    _title_symbol,
    render,
)


def _epoch_from_now(days: int = 0, hours: int = 0, minutes: int = 0) -> int:
    """Return Unix epoch seconds offset from now."""
    t = datetime.now(UTC) + timedelta(days=days, hours=hours, minutes=minutes)
    return int(t.timestamp())


def _make_config(**kwargs) -> Config:
    """Create a Config with defaults, overriding specified fields."""
    defaults = {
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
        "theme_preset": "ayu",
        "theme_light": {},
        "theme_dark": {},
    }
    defaults.update(kwargs)
    return Config(**defaults)


def _make_quota(five_hour_util: float = 27.0, seven_day_util: float = 9.0) -> QuotaInfo:
    return QuotaInfo(
        five_hour=QuotaData(used_percentage=five_hour_util, resets_at=_epoch_from_now(hours=3)),
        seven_day=QuotaData(
            used_percentage=seven_day_util, resets_at=_epoch_from_now(days=6, hours=18)
        ),
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
        # 66% / 33% thirds, aligned with _title_symbol thresholds.
        assert theme.threshold_role(0.70) == "success"
        assert theme.threshold_role(0.50) == "warning"
        assert theme.threshold_role(0.20) == "error"

    def test_threshold_role_boundaries(self):
        """Boundary values: 0.66 and 0.33 fall into the lower role."""
        theme = Theme("ayu", {}, {})
        assert theme.threshold_role(0.66) == "warning"
        assert theme.threshold_role(0.33) == "error"


class TestTitleLine:
    def test_icon_only_default(self):
        """Default config: dynamic gauge icon, no text. 73% remaining → high glyph."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        lines = output.split("\n")
        assert "sfimage=gauge.with.dots.needle.bottom.100percent" in lines[0]
        assert "sfvalue=0.73" in lines[0]
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

    def test_ccusage_footer_quotes_helper_path(self, monkeypatch):
        """Helper path must be double-quoted in bash= — SwiftBar's unquoted-value
        parser splits on the first whitespace and does not honor `\\ ` escapes,
        so a backslash-escaped space in the path silently breaks click actions
        (helper never runs). Regression guard: SwiftBar plugins dir is
        `~/Library/Application Support/` which always contains a space.
        """
        import cc_menubar.render as render_mod

        monkeypatch.setattr(render_mod.Path, "exists", lambda self: True)
        output = render(_make_config(), None, None, None)
        assert f'bash="{render_mod.CCUSAGE_HELPER_PATH}"' in output
        # Anti-pattern: backslash-escape of spaces in bash= value
        assert "Application\\ Support" not in output


class TestQuotaPercentSemantics:
    def test_percent_scale_rendering(self):
        """Guard against scale-bug regression: used_percentage 0-100 → correct used/left %."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(used_percentage=7.0, resets_at=_epoch_from_now(hours=3)),
            seven_day=QuotaData(used_percentage=30.0, resets_at=_epoch_from_now(days=6)),
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        assert "5-Hour: 7% used" in output
        assert "93% left" in output
        assert "7-Day: 30% used" in output
        assert "70% left" in output

    def test_days_in_runway(self):
        """Runways > 24h should use d/h/m formatting, not hours-only."""
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(used_percentage=50.0, resets_at=_epoch_from_now(days=6, hours=18)),
            seven_day=None,
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        assert "6d" in output

    def test_burn_rate_from_ccusage(self):
        """Active 5h block row reads ccusage costUSD and burnRate.costPerHour.

        The remainingMinutes figure is deliberately NOT rendered — it
        duplicates the 5-Hour reset countdown on the row above.
        """
        config = _make_config()
        quota = _make_quota()
        blocks = BlockInfo(
            blocks=[],
            active_block={
                "costUSD": 6.15,
                "burnRate": {"costPerHour": 11.4, "tokensPerMinute": 1234},
                "projection": {"remainingMinutes": 266},
                "startTime": "",
                "endTime": "",
            },
        )
        output = render(config, quota, blocks, None)
        assert "Current 5h block:" in output
        assert "$6.15 so far" in output
        assert "$11.4/hr" in output
        assert "m left" not in output

    def test_burn_rate_skipped_without_active_block(self):
        """No active block → no burn-rate row."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        assert "Current 5h block:" not in output


class TestFormatHelpers:
    def test_format_time_until_days(self):
        assert _format_time_until(_epoch_from_now(days=2, hours=3, minutes=5)).startswith("2d 3h")

    def test_format_time_until_hours(self):
        result = _format_time_until(_epoch_from_now(hours=2, minutes=30))
        assert "h" in result and "d" not in result

    def test_format_time_until_minutes(self):
        result = _format_time_until(_epoch_from_now(minutes=45))
        assert result.endswith("m")
        assert "h" not in result

    def test_format_time_until_past(self):
        """Past timestamp → 'now'."""
        assert _format_time_until(_epoch_from_now(hours=-1)) == "now"

    def test_format_reset_absolute_same_day(self):
        now = datetime.now().astimezone()
        if now.hour < 22:
            target = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
            result = _format_reset_absolute(int(target.timestamp()))
            assert "am" in result or "pm" in result
            assert " at " not in result

    def test_format_reset_absolute_future_date(self):
        target = datetime.now().astimezone() + timedelta(days=5)
        target = target.replace(hour=7, minute=0, second=0, microsecond=0)
        result = _format_reset_absolute(int(target.timestamp()))
        assert " at " in result
        assert "7am" in result

    def test_format_reset_absolute_with_minutes(self):
        target = datetime.now().astimezone() + timedelta(days=1)
        target = target.replace(hour=12, minute=30, second=0, microsecond=0)
        result = _format_reset_absolute(int(target.timestamp()))
        assert "12:30pm" in result

    def test_format_reset_absolute_noon(self):
        target = datetime.now().astimezone() + timedelta(days=1)
        target = target.replace(hour=12, minute=0, second=0, microsecond=0)
        result = _format_reset_absolute(int(target.timestamp()))
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


class TestCaption:
    """_caption() renders a disabled submenu child for section-level copy."""

    def _theme(self) -> Theme:
        return Theme("ayu", {}, {})

    def test_caption_is_submenu_child(self):
        row = _caption("section.activity_caption", self._theme())
        assert row.startswith("--"), f"Caption must be a submenu child: {row!r}"

    def test_caption_has_label_text(self):
        row = _caption("section.model_mix_caption", self._theme())
        assert LABELS["section.model_mix_caption"] in row

    def test_caption_is_disabled(self):
        row = _caption("section.context_caption", self._theme())
        assert "disabled=true" in row

    def test_caption_uses_subtext_color(self):
        theme = self._theme()
        row = _caption("section.activity_caption", theme)
        assert f"color={theme.color('subtext')}" in row

    def test_caption_styling(self):
        row = _caption("section.activity_caption", self._theme())
        assert "size=10" in row
        assert "font=Menlo" in row


class TestTitleSymbol:
    """_title_symbol() maps remaining fraction → SF Symbols 5 gauge glyph."""

    def test_unknown_returns_medium(self):
        assert _title_symbol(None) == "gauge.with.dots.needle.bottom.50percent"

    def test_high_returns_100percent(self):
        assert _title_symbol(0.80) == "gauge.with.dots.needle.bottom.100percent"

    def test_medium_returns_50percent(self):
        assert _title_symbol(0.50) == "gauge.with.dots.needle.bottom.50percent"

    def test_low_returns_0percent(self):
        assert _title_symbol(0.20) == "gauge.with.dots.needle.bottom.0percent"

    def test_boundary_66_is_medium(self):
        """0.66 is NOT > 0.66, so falls into medium."""
        assert _title_symbol(0.66) == "gauge.with.dots.needle.bottom.50percent"

    def test_boundary_33_is_low(self):
        """0.33 is NOT > 0.33, so falls into low."""
        assert _title_symbol(0.33) == "gauge.with.dots.needle.bottom.0percent"


class TestQuotaDualFraming:
    """`rate_limits.row_suffix` renders both used and left percentages."""

    def test_five_hour_dual_framing(self):
        config = _make_config()
        quota = QuotaInfo(
            five_hour=QuotaData(used_percentage=55.0, resets_at=_epoch_from_now(hours=4)),
            seven_day=None,
            cache_age=10.0,
        )
        output = render(config, quota, None, None)
        matching = [ln for ln in output.splitlines() if ln.startswith("--5-Hour:")]
        assert matching, f"No 5-Hour row in output: {output!r}"
        row = matching[0]
        assert "% used" in row
        assert "% left" in row
        assert "55% used" in row
        assert "45% left" in row
        assert "resets" in row

    def test_quota_caption_row_present(self):
        """Quota section emits a caption row immediately after its header."""
        config = _make_config()
        output = render(config, _make_quota(), None, None)
        lines = output.splitlines()
        header_label = LABELS["section.rate_limits"]
        header_idx = next(
            i for i, ln in enumerate(lines) if header_label in ln and "fold=true" in ln
        )
        next_line = lines[header_idx + 1]
        assert LABELS["section.rate_limits_caption"] in next_line
        assert "disabled=true" in next_line


class TestQuotaNoDataFallback:
    """When quota is None, an actionable no_data label renders in the submenu."""

    def test_no_data_label_renders(self):
        config = _make_config()
        output = render(config, None, None, None)
        assert LABELS["rate_limits.no_data"] in output

    def test_no_legacy_no_quota_data(self):
        config = _make_config()
        output = render(config, None, None, None)
        assert "No quota data" not in output


class TestDemotedDividers:
    """Top Tools / Top Commands dividers match the caption style."""

    def _full_config(self) -> Config:
        return _make_config(tools_enabled=True)

    def _make_data(self):
        from cc_menubar.collectors.jsonl import AggregateData, SessionData

        agg = AggregateData(
            sessions=[
                SessionData(
                    project="demo",
                    session_id="s1",
                    tools=["Edit", "Bash"],
                    bash_commands=["ls"],
                    models=["claude-opus-4-6"],
                    input_tokens=1000,
                    output_tokens=100,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    turns=2,
                    is_subagent=False,
                    cwd="/tmp",
                )
            ]
        )
        agg.tool_counts = {"Edit": 3, "Bash": 2}
        agg.bash_command_counts = {"ls": 2}
        return agg

    def test_top_tools_is_disabled_caption(self):
        output = render(self._full_config(), None, None, self._make_data())
        matching = [ln for ln in output.splitlines() if "Top Tools" in ln]
        assert matching, f"No Top Tools line in output: {output!r}"
        line = matching[0]
        assert "disabled=true" in line
        assert "size=10" in line

    def test_top_tools_not_accent_colored(self):
        output = render(self._full_config(), None, None, self._make_data())
        matching = [ln for ln in output.splitlines() if "Top Tools" in ln]
        for line in matching:
            assert "accent" not in line

    def test_top_commands_is_disabled_caption(self):
        output = render(self._full_config(), None, None, self._make_data())
        matching = [ln for ln in output.splitlines() if "Top Commands" in ln]
        assert matching
        line = matching[0]
        assert "disabled=true" in line


class TestFooterIcons:
    def test_refresh_has_sfimage(self):
        config = _make_config()
        output = render(config, None, None, None)
        matching = [ln for ln in output.splitlines() if ln.startswith("Refresh")]
        assert matching
        assert "sfimage=arrow.clockwise" in matching[0]
