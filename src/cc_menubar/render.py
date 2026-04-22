"""SwiftBar output formatter and Theme class.

User-facing display strings are centralized in `cc_menubar.labels`. Do not
hardcode dropdown copy here — import from `LABELS` / `TOOLTIPS` instead.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from cc_menubar.classifier import classify_aggregate
from cc_menubar.collectors.blocks import BlockInfo
from cc_menubar.collectors.jsonl import AggregateData
from cc_menubar.collectors.quota import QuotaInfo
from cc_menubar.config import Config
from cc_menubar.constants import EDIT_TOOLS, SECTION_SYMBOLS, THEME_PRESETS, TITLE_SYMBOLS
from cc_menubar.labels import LABELS, TOOLTIPS

_EDIT_CATEGORIES = frozenset({"coding", "debugging", "feature", "refactoring"})

CCUSAGE_HELPER_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "SwiftBar"
    / "plugins"
    / ".cc-menubar-ccusage.sh"
)


def _tooltip(key: str) -> str:
    """Return a SwiftBar `tooltip=...` param for the given TOOLTIPS key.

    Wraps in double quotes so apostrophes in content don't terminate the
    value (SwiftBar's quoted-value parser can't nest the same quote char).
    """
    return f'tooltip="{TOOLTIPS[key]}"'


def _caption(key: str, theme: Theme) -> str:
    """Render a disabled greyed-out caption row at the start of a submenu.

    Replaces section-header tooltips, which collide with submenu popovers
    in macOS — AppKit shows tooltip and submenu simultaneously on parent
    menu items. The caption is visible the moment the submenu opens: no
    hover delay, no popover collision.
    """
    return f"--{LABELS[key]} | size=10 color={theme.color('subtext')} font=Menlo disabled=true"


_MODEL_PATTERN = re.compile(r"^claude-(opus|sonnet|haiku)-(\d+)-(\d+)")


def _format_model_name(model_id: str) -> str:
    """claude-opus-4-6 -> 'Opus 4.6'; <synthetic> passthrough; unknowns verbatim."""
    if not model_id or model_id.startswith("<"):
        return model_id
    m = _MODEL_PATTERN.match(model_id)
    if not m:
        return model_id
    family, major, minor = m.groups()
    return f"{family.capitalize()} {major}.{minor}"


class Theme:
    """Color theme with light/dark pairs for SwiftBar."""

    def __init__(self, preset: str, light_overrides: dict, dark_overrides: dict) -> None:
        base = THEME_PRESETS.get(preset, THEME_PRESETS["ayu"])
        self._colors: dict[str, tuple[str, str]] = {}
        for role, (light, dark) in base.items():
            lo = light_overrides.get(role, light)
            do = dark_overrides.get(role, dark)
            self._colors[role] = (lo, do)

    def color(self, role: str) -> str:
        """Return 'light,dark' color string for SwiftBar."""
        pair = self._colors.get(role, self._colors.get("text", ("#6c7680", "#b3b1ad")))
        return f"{pair[0]},{pair[1]}"

    def threshold_role(self, remaining: float) -> str:
        """Return theme role based on remaining quota fraction.

        66% / 33% thirds, single-sourced with `_title_symbol` so icon glyph
        and text color flip at the same moments.
        """
        if remaining > 0.66:
            return "success"
        if remaining > 0.33:
            return "warning"
        return "error"


def _mini_bar(value: float, max_val: float, width: int = 10) -> str:
    """Render a small bar chart."""
    if max_val <= 0:
        return "\u00b7" * width
    filled = round((value / max_val) * width)
    return "\u2588" * min(filled, width) + "\u00b7" * max(width - filled, 0)


def _format_time_until(epoch: int) -> str:
    """Format time until a Unix-epoch timestamp as human-readable string.

    Returns "{d}d {h}h {m}m" when days > 0, else "{h}h {m}m" / "{m}m".
    """
    try:
        target = datetime.fromtimestamp(epoch, tz=UTC)
        now = datetime.now(UTC)
        delta = target - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return "now"
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes = remainder // 60
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError, OSError, OverflowError):
        return "?"


def _format_reset_absolute(epoch: int) -> str:
    """Format a Unix-epoch reset timestamp as a short local-tz wall-clock string.

    Same local date as now: "9am" / "12:30pm" (lowercase am/pm, no leading
    zero, omit minutes when :00). Different date: "Apr 24 at 7am".
    """
    try:
        target = datetime.fromtimestamp(epoch, tz=UTC).astimezone()
        now = datetime.now().astimezone()
    except (ValueError, TypeError, OSError, OverflowError):
        return "?"

    hour = target.hour % 12 or 12
    suffix = "am" if target.hour < 12 else "pm"
    clock = f"{hour}{suffix}" if target.minute == 0 else f"{hour}:{target.minute:02d}{suffix}"
    if target.date() == now.date():
        return clock
    return f"{target.strftime('%b')} {target.day} at {clock}"


def _format_tokens(count: int) -> str:
    """Format token count as human-readable string."""
    if count >= 1_000_000:
        val = count / 1_000_000
        return f"{val:.0f}M" if val == int(val) else f"{val:.1f}M"
    if count >= 1_000:
        val = count / 1_000
        return f"{val:.0f}K" if val == int(val) else f"{val:.1f}K"
    return str(count)


def _format_project_display(cwd: str) -> str:
    """Format a project cwd path for short display.

    /Users/calvin/Documents/github/calvindotsg/cc-menubar -> calvindotsg/cc-menubar
    /Users/calvin/.config -> .config
    """
    home = str(Path.home())
    rel = cwd[len(home) :].lstrip("/") if cwd.startswith(home) else cwd
    github_prefix = "Documents/github/"
    if rel.startswith(github_prefix):
        return rel[len(github_prefix) :]
    return rel


def render(
    config: Config,
    quota: QuotaInfo | None,
    blocks: BlockInfo | None,
    jsonl_data: AggregateData | None,
    debug: bool = False,
) -> str:
    """Render SwiftBar output string."""
    theme = Theme(config.theme_preset, config.theme_light, config.theme_dark)
    lines: list[str] = []

    # ── Title line(s) ──────────────────────────────────────────────────
    remaining = _get_remaining(quota, config.metric)
    _render_title(lines, config, theme, remaining)

    # ── Cycling lines ──────────────────────────────────────────────────
    for cycle_metric in config.cycle:
        if cycle_metric == config.metric:
            continue
        cycle_remaining = _get_remaining(quota, cycle_metric)
        _render_cycle_line(lines, config, theme, cycle_metric, cycle_remaining, jsonl_data)

    # ── Separator ──────────────────────────────────────────────────────
    lines.append("---")

    # ── Dropdown sections ──────────────────────────────────────────────
    if config.quota_enabled:
        _render_quota_section(lines, theme, quota, blocks, config)

    if config.activity_enabled and jsonl_data:
        _render_activity_section(lines, theme, jsonl_data)

    if config.projects_enabled and jsonl_data:
        _render_projects_section(lines, theme, jsonl_data, config)

    if config.tools_enabled and jsonl_data:
        _render_tools_section(lines, theme, jsonl_data, config)

    if config.opusplan_enabled and jsonl_data:
        _render_opusplan_section(lines, theme, jsonl_data)

    if config.context_enabled and jsonl_data:
        _render_context_section(lines, theme, jsonl_data, config)

    # ── Footer ─────────────────────────────────────────────────────────
    _render_footer(lines, theme)

    return "\n".join(lines)


def _get_remaining(quota: QuotaInfo | None, metric: str) -> float | None:
    """Get remaining fraction (1.0 - used_percentage/100) for a metric."""
    if not quota:
        return None
    if metric == "5h" and quota.five_hour:
        return max(0.0, 1.0 - quota.five_hour.used_percentage / 100.0)
    if metric == "7d" and quota.seven_day:
        return max(0.0, 1.0 - quota.seven_day.used_percentage / 100.0)
    return None


def _title_symbol(remaining: float | None) -> str:
    """Pick a gauge glyph reflecting remaining-quota fraction.

    Thresholds match ``Theme.threshold_role`` so icon state and (optional)
    text-color state flip at the same moments. Unknown remaining falls back
    to the medium glyph — a neutral visual in the absence of quota data.
    """
    if remaining is None:
        return TITLE_SYMBOLS["medium"]
    if remaining > 0.66:
        return TITLE_SYMBOLS["high"]
    if remaining > 0.33:
        return TITLE_SYMBOLS["medium"]
    return TITLE_SYMBOLS["low"]


def _render_title(lines: list[str], config: Config, theme: Theme, remaining: float | None) -> None:
    """Render the menu bar title line."""
    parts: list[str] = []

    # Text portion
    if config.text != "none" and remaining is not None:
        pct = f"{int(remaining * 100)}%"
        if config.text == "label":
            parts.append(f"{config.metric}: {pct}")
        else:
            parts.append(pct)

    text = " ".join(parts)

    # SwiftBar parameters
    params = [f"sfimage={_title_symbol(remaining)}"]
    if remaining is not None:
        params.append(f"sfvalue={remaining:.2f}")

    # Color (text only, icon is always monochrome template)
    if config.text != "none" and remaining is not None and config.color != "monochrome":
        if config.color == "always" or (config.color == "threshold" and remaining <= 0.5):
            role = theme.threshold_role(remaining)
            params.append(f"color={theme.color(role)}")

    line = f"{text} | {' '.join(params)}" if text else f"| {' '.join(params)}"
    lines.append(line)


def _render_cycle_line(
    lines: list[str],
    config: Config,
    theme: Theme,
    metric: str,
    remaining: float | None,
    jsonl_data: AggregateData | None,
) -> None:
    """Render a cycling title line (dropdown=false)."""
    non_quota_symbols = {
        "opusplan": "cpu",
        "context": "brain.head.profile",
    }
    if metric in ("5h", "7d"):
        symbol = _title_symbol(remaining)
    else:
        symbol = non_quota_symbols.get(metric, _title_symbol(None))

    if metric in ("5h", "7d"):
        pct = f"{int(remaining * 100)}%" if remaining is not None else "?"
        label = f"{metric}: {pct}"
        params = [f"sfimage={symbol}", "dropdown=false"]
        if remaining is not None:
            params.append(f"sfvalue={remaining:.2f}")
        lines.append(f"{label} | {' '.join(params)}")

    elif metric == "opusplan" and jsonl_data:
        opus_pct = _calc_opus_pct(jsonl_data)
        if opus_pct is not None:
            label = f"opus: {int(opus_pct * 100)}%"
            lines.append(f"{label} | sfimage={symbol} dropdown=false")

    elif metric == "context" and jsonl_data:
        # Sessions under threshold %
        pass  # TODO: implement context cycling metric


def _render_quota_section(
    lines: list[str],
    theme: Theme,
    quota: QuotaInfo | None,
    blocks: BlockInfo | None,
    config: Config,
) -> None:
    """Render the Plan usage limits dropdown section."""
    sym = SECTION_SYMBOLS["quota"]
    header = LABELS["section.rate_limits"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.rate_limits_caption", theme))

    if not quota:
        lines.append(
            f"--{LABELS['rate_limits.no_data']} | color={theme.color('subtext')} font=Menlo size=11"
        )
        return

    row_suffix = LABELS["rate_limits.row_suffix"]
    for key, data in [
        ("rate_limits.five_hour", quota.five_hour),
        ("rate_limits.seven_day", quota.seven_day),
    ]:
        if not data:
            continue
        pct_used = int(data.used_percentage)
        pct_left = max(0, 100 - pct_used)
        remaining = pct_left / 100.0
        role = theme.threshold_role(remaining)
        abs_reset = _format_reset_absolute(data.resets_at)
        rel_reset = _format_time_until(data.resets_at)
        row = f"{LABELS[key]}: " + row_suffix.format(
            used=pct_used, left=pct_left, abs=abs_reset, rel=rel_reset
        )
        lines.append(f"--{row} | color={theme.color(role)} font=Menlo size=12 {_tooltip(key)}")

    # Active 5h ccusage block: cost so far and hourly burn rate. The time-left
    # figure is omitted — it duplicates the 5-Hour reset countdown above.
    if blocks and blocks.active_block:
        active = blocks.active_block
        cost_so_far = active.get("costUSD", 0.0)
        cost_per_hr = active.get("burnRate", {}).get("costPerHour")
        parts: list[str] = []
        if cost_so_far:
            parts.append(f"${cost_so_far:.2f} so far")
        if cost_per_hr is not None:
            parts.append(f"${cost_per_hr:.1f}/hr")
        if parts:
            row = LABELS["active_block.row"].format(parts=" \u00b7 ".join(parts))
            lines.append(
                f"--{row} | color={theme.color('subtext')} font=Menlo size=11"
                f" {_tooltip('active_block.row')}"
            )


def _render_activity_section(lines: list[str], theme: Theme, data: AggregateData) -> None:
    """Render Activity (last 7d) dropdown section."""
    sym = SECTION_SYMBOLS["activity"]
    header = LABELS["section.activity"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.activity_caption", theme))

    categories = classify_aggregate(data)
    # Sort by count descending, filter zeros
    sorted_cats = [
        (name, count)
        for name, count in sorted(categories.items(), key=lambda x: -x[1])
        if count > 0
    ]

    if not sorted_cats:
        lines.append(f"--No activity data | color={theme.color('subtext')}")
        return

    max_count = sorted_cats[0][1] if sorted_cats else 1

    for name, count in sorted_cats[:8]:
        bar = _mini_bar(count, max_count)
        # Calculate one-shot rate for sessions with edits
        matching = [s for s in data.sessions if classify_session_category(s) == name]
        total_sessions = len(matching)
        one_shot = sum(1 for s in matching if _is_one_shot(s))
        if name not in _EDIT_CATEGORIES:
            first_try = "-"
            tooltip_suffix = f" {_tooltip('activity.turns')}"
        elif total_sessions > 0:
            first_try = LABELS["activity.one_shot"].format(pct=int(one_shot / total_sessions * 100))
            tooltip_suffix = f" {_tooltip('activity.one_shot')}"
        else:
            first_try = "-"
            tooltip_suffix = f" {_tooltip('activity.turns')}"
        lines.append(
            f"--{bar}  {name:<14} {count:>5} turns  {first_try:>16}"
            f" | font=Menlo size=11 color={theme.color('text')}{tooltip_suffix}"
        )


def classify_session_category(session) -> str:
    """Classify a single session for activity section."""
    from cc_menubar.classifier import classify_session

    return classify_session(session)


def _is_one_shot(session) -> bool:
    """Check if a session had edits without retries (Edit->Bash->Edit cycle)."""
    saw_edit = False
    saw_bash_after = False
    retries = 0
    for tool in session.tools:
        if tool in {"Edit", "Write", "FileEditTool", "FileWriteTool", "NotebookEdit"}:
            if saw_bash_after:
                retries += 1
            saw_edit = True
            saw_bash_after = False
        elif tool in {"Bash", "BashTool", "PowerShellTool"} and saw_edit:
            saw_bash_after = True
    has_edits = any(t in EDIT_TOOLS for t in session.tools)
    return has_edits and retries == 0


def _render_projects_section(
    lines: list[str], theme: Theme, data: AggregateData, config: Config
) -> None:
    """Render Projects dropdown section."""
    sym = SECTION_SYMBOLS["projects"]
    header = LABELS["section.projects"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.projects_caption", theme))

    if not data.project_counts:
        lines.append(f"--No project data | color={theme.color('subtext')}")
        return

    sorted_projects = [
        (p, c) for p, c in sorted(data.project_counts.items(), key=lambda x: -x[1]) if c > 0
    ]

    for project, turns in sorted_projects:
        if project in config.project_aliases:
            display_name = config.project_aliases[project]
        elif project in data.project_cwds:
            display_name = _format_project_display(data.project_cwds[project])
        else:
            display_name = project
        if len(display_name) > 30:
            display_name = "..." + display_name[-27:]
        subagent_count = data.project_subagent_counts.get(project, 0)
        suffix = ""
        tooltip_suffix = ""
        if subagent_count > 0:
            suffix = "  " + LABELS["projects.subagent"].format(
                pct=int(subagent_count / turns * 100)
            )
            tooltip_suffix = f" {_tooltip('projects.subagent')}"
        lines.append(
            f"--{display_name:<30} {turns:>5} turns{suffix}"
            f" | font=Menlo size=11 color={theme.color('text')}{tooltip_suffix}"
        )


def _render_tools_section(
    lines: list[str], theme: Theme, data: AggregateData, config: Config
) -> None:
    """Render Tools & Commands dropdown section."""
    sym = SECTION_SYMBOLS["tools"]
    header = LABELS["section.tools"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.tools_caption", theme))

    divider_style = f"size=10 color={theme.color('subtext')} font=Menlo disabled=true"

    # Top tools
    sorted_tools = sorted(data.tool_counts.items(), key=lambda x: -x[1])[: config.tools_top_n]
    if sorted_tools:
        max_tool = sorted_tools[0][1]
        lines.append(f"--Top Tools | {divider_style}")
        for name, count in sorted_tools:
            bar = _mini_bar(count, max_tool)
            lines.append(
                f"--{bar}  {name:<20} {count:>5} | font=Menlo size=11 color={theme.color('text')}"
            )

    # Top bash commands (pre-aggregated in JSONL collector)
    sorted_cmds = sorted(data.bash_command_counts.items(), key=lambda x: -x[1])[
        : config.tools_top_n
    ]
    if sorted_cmds:
        max_cmd = sorted_cmds[0][1]
        lines.append("-----")
        lines.append(f"--Top Commands | {divider_style}")
        for name, count in sorted_cmds:
            bar = _mini_bar(count, max_cmd)
            lines.append(
                f"--{bar}  {name:<20} {count:>5} | font=Menlo size=11 color={theme.color('text')}"
            )


def _calc_opus_pct(data: AggregateData) -> float | None:
    """Calculate Opus model usage percentage."""
    total = sum(data.model_counts.values())
    if total == 0:
        return None
    opus_count = sum(v for k, v in data.model_counts.items() if "opus" in k.lower())
    return opus_count / total


def _render_opusplan_section(lines: list[str], theme: Theme, data: AggregateData) -> None:
    """Render Model Mix dropdown section (conditional; renamed from Opusplan Health)."""
    # Only show if Opus model detected
    opus_pct = _calc_opus_pct(data)
    if opus_pct is None:
        return

    has_opus = any("opus" in k.lower() for k in data.model_counts)
    if not has_opus:
        return

    sym = SECTION_SYMBOLS["opusplan"]
    header = LABELS["section.model_mix"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.model_mix_caption", theme))

    # Model breakdown. Aggregation is keyed by raw id (so opus-4-6 and
    # opus-4-7 aggregate separately); only the display string goes through
    # _format_model_name.
    total = sum(data.model_counts.values())
    sorted_models = sorted(data.model_counts.items(), key=lambda x: -x[1])
    max_model = sorted_models[0][1] if sorted_models else 1

    for model_id, count in sorted_models:
        bar = _mini_bar(count, max_model)
        pct = int(count / total * 100) if total > 0 else 0
        display = _format_model_name(model_id)
        lines.append(
            f"--{bar}  {display:<24} {pct:>3}%  {count:>5} turns"
            f" | font=Menlo size=11 color={theme.color('text')}"
        )

    # Research agents (sub-agents that used search/read tools only).
    research_tools = {"Grep", "Glob", "Read"}
    research_count = sum(
        1 for s in data.sessions if s.is_subagent and any(t in research_tools for t in s.tools)
    )
    if research_count > 0:
        row = LABELS["model_mix.research_agents"].format(n=research_count)
        lines.append(
            f"--{row} | font=Menlo size=11 color={theme.color('subtext')}"
            f" {_tooltip('model_mix.research_agents')}"
        )


def _render_context_section(
    lines: list[str], theme: Theme, data: AggregateData, config: Config
) -> None:
    """Render Context Efficiency dropdown section (conditional)."""
    # Only show if sufficient session data exists
    sessions_with_tokens = [s for s in data.sessions if s.input_tokens > 0 and not s.is_subagent]
    if len(sessions_with_tokens) < 3:
        return

    sym = SECTION_SYMBOLS["context"]
    header = LABELS["section.context"]
    lines.append(f"{header} | sfimage={sym} color={theme.color('header')} fold=true")
    lines.append(_caption("section.context_caption", theme))

    # Context sizes
    context_sizes = sorted([s.input_tokens for s in sessions_with_tokens])
    threshold = config.large_session_threshold
    large_count = sum(1 for s in sessions_with_tokens if s.input_tokens > threshold)
    large_pct = int(large_count / len(sessions_with_tokens) * 100)

    # P50/P90 (displayed as Typical / Longest 10%)
    p50_idx = len(context_sizes) // 2
    p90_idx = int(len(context_sizes) * 0.9)
    p50 = context_sizes[p50_idx] if context_sizes else 0
    p90 = context_sizes[min(p90_idx, len(context_sizes) - 1)] if context_sizes else 0

    large_role = "error" if large_pct > 50 else ("warning" if large_pct > 25 else "success")
    threshold_label = _format_tokens(threshold)
    large_row = LABELS["context.large_sessions"].format(threshold=threshold_label, pct=large_pct)
    lines.append(
        f"--{large_row} | font=Menlo size=12 color={theme.color(large_role)}"
        f" {_tooltip('context.large_sessions')}"
    )
    pct_row = LABELS["context.percentiles"].format(p50=_format_tokens(p50), p90=_format_tokens(p90))
    lines.append(
        f"--{pct_row} | font=Menlo size=11 color={theme.color('text')}"
        f" {_tooltip('context.percentiles')}"
    )

    # Context reuse (cache-hit rate)
    total_input = data.total_input_tokens + data.total_cache_read_tokens
    if total_input > 0:
        cache_hit = int(data.total_cache_read_tokens / total_input * 100)
        reuse_row = LABELS["context.cache_reuse"].format(pct=cache_hit)
        lines.append(
            f"--{reuse_row} | font=Menlo size=11 color={theme.color('text')}"
            f" {_tooltip('context.cache_reuse')}"
        )


def _render_footer(lines: list[str], theme: Theme) -> None:
    """Render footer with refresh and ccusage actions (when helper present).

    The helper script owns the Ghostty spawn. We route with terminal=false
    so SwiftBar uses its Process path and bypasses the Ghostty AppleScript
    race (buildTerminalCommand's fish-syntax env preamble + no-delay
    `input text`). refresh=false keeps the menu stable while the terminal
    window is still open.
    """
    lines.append("---")
    lines.append("Refresh | refresh=true sfimage=arrow.clockwise")

    if CCUSAGE_HELPER_PATH.exists():
        helper_q = f'"{CCUSAGE_HELPER_PATH}"'
        lines.append(
            f"{LABELS['footer.ccusage_daily']} | sfimage=calendar bash={helper_q} param1=daily"
            f" terminal=false refresh=false {_tooltip('footer.ccusage_daily')}"
        )
        lines.append(
            f"{LABELS['footer.ccusage_blocks']} | sfimage=clock bash={helper_q} param1=blocks"
            f" param2=--active terminal=false refresh=false"
            f" {_tooltip('footer.ccusage_blocks')}"
        )
