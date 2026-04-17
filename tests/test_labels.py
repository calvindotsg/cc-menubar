"""Tests for the labels module and legacy-string absence in rendered output."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cc_menubar.collectors.jsonl import AggregateData, SessionData
from cc_menubar.collectors.quota import QuotaData, QuotaInfo
from cc_menubar.config import Config
from cc_menubar.labels import LABELS, TOOLTIPS
from cc_menubar.render import render


def _iso_from_now(days: int = 0, hours: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(days=days, hours=hours)).isoformat()


def _make_full_config() -> Config:
    return Config(
        symbol="gauge.with.needle.fill",
        text="none",
        color="monochrome",
        metric="5h",
        cycle=[],
        quota_enabled=True,
        blocks_enabled=False,
        opusplan_enabled=True,
        context_enabled=True,
        activity_enabled=True,
        tools_enabled=True,
        projects_enabled=True,
        extra_usage_budget=0.0,
        theme_preset="ayu",
        theme_light={},
        theme_dark={},
    )


def _make_full_data() -> AggregateData:
    sessions = [
        SessionData(
            project="demo",
            session_id=f"s{i}",
            tools=["Edit", "Bash", "Read"],
            bash_commands=["ls"],
            models=["claude-opus-4-6"],
            input_tokens=10000 + i * 500,
            output_tokens=100,
            cache_read_tokens=5000,
            cache_write_tokens=1000,
            turns=3,
            is_subagent=False,
            cwd="/tmp/demo",
        )
        for i in range(5)
    ]
    # Add a subagent session using only research tools
    sessions.append(
        SessionData(
            project="demo",
            session_id="sub1",
            tools=["Grep", "Read"],
            bash_commands=[],
            models=["claude-sonnet-4-6"],
            input_tokens=2000,
            output_tokens=50,
            cache_read_tokens=0,
            cache_write_tokens=0,
            turns=2,
            is_subagent=True,
            cwd="/tmp/demo",
        )
    )
    agg = AggregateData(sessions=sessions)
    agg.tool_counts = {"Edit": 5, "Bash": 5, "Read": 6, "Grep": 1}
    agg.bash_command_counts = {"ls": 5}
    agg.model_counts = {"claude-opus-4-6": 15, "claude-sonnet-4-6": 2}
    agg.project_counts = {"demo": 17}
    agg.project_subagent_counts = {"demo": 2}
    agg.project_cwds = {"demo": "/tmp/demo"}
    agg.total_input_tokens = sum(s.input_tokens for s in sessions)
    agg.total_cache_read_tokens = sum(s.cache_read_tokens for s in sessions)
    return agg


def _render_full() -> str:
    config = _make_full_config()
    quota = QuotaInfo(
        five_hour=QuotaData(utilization=27.0, resets_at=_iso_from_now(hours=3)),
        seven_day=QuotaData(utilization=9.0, resets_at=_iso_from_now(days=6, hours=18)),
        seven_day_sonnet=QuotaData(utilization=5.0, resets_at=_iso_from_now(days=6)),
        cache_age=10.0,
    )
    return render(config, quota, None, _make_full_data())


class TestLabelsAndTooltipsDicts:
    def test_labels_all_strings(self):
        assert all(isinstance(v, str) and v for v in LABELS.values())

    def test_tooltips_all_strings(self):
        assert all(isinstance(v, str) and v for v in TOOLTIPS.values())

    def test_tooltip_values_no_double_quotes(self):
        """Double quotes in tooltip values would break SwiftBar's quoted parser."""
        for key, val in TOOLTIPS.items():
            assert '"' not in val, f"TOOLTIPS[{key}] contains a double quote"


class TestLegacyStringsAbsent:
    """Rendered output must not contain old jargon labels."""

    LEGACY = [
        "Quota & Runway",
        "Opusplan Health",
        "Context Efficiency",
        "1-shot",
        " subagent",  # leading space avoids matching "sub-agent" in tooltips
        "Explore agents",
        "P50",
        "P90",
        "Cache hit rate",
        "Large sessions (>",
        "% remaining",
    ]

    def test_no_legacy_strings_in_output(self):
        output = _render_full()
        for token in self.LEGACY:
            assert token not in output, f"Legacy token {token!r} leaked into rendered output"


class TestNewLabelsPresent:
    def test_section_headers_rendered(self):
        output = _render_full()
        for key in (
            "section.rate_limits",
            "section.activity",
            "section.projects",
            "section.tools",
            "section.model_mix",
            "section.context",
        ):
            assert LABELS[key] in output, f"section header {key} missing"

    def test_footer_labels_skip_without_helper(self):
        """Footer ccusage rows are absent when helper file doesn't exist."""
        output = _render_full()
        # Test machine may or may not have the helper installed. Just verify
        # that when present, both labels appear together — xor when absent.
        has_daily = LABELS["footer.ccusage_daily"] in output
        has_blocks = LABELS["footer.ccusage_blocks"] in output
        assert has_daily == has_blocks


class TestTooltipsPresent:
    def test_tooltips_emitted_on_jargon_rows(self):
        output = _render_full()
        # At least these jargon rows must carry a tooltip= param
        for needle in (
            TOOLTIPS["rate_limits.five_hour"],
            TOOLTIPS["context.percentiles"],
            TOOLTIPS["context.cache_reuse"],
            TOOLTIPS["model_mix.header"],
        ):
            assert needle in output, f"Tooltip missing: {needle!r}"
