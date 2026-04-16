"""SwiftBar output formatter and Theme class."""

from __future__ import annotations

from datetime import UTC, datetime

from cc_menubar.classifier import classify_aggregate
from cc_menubar.collectors.blocks import BlockInfo
from cc_menubar.collectors.jsonl import AggregateData
from cc_menubar.collectors.quota import QuotaInfo
from cc_menubar.config import Config
from cc_menubar.constants import BASH_TOOLS, EDIT_TOOLS, SECTION_SYMBOLS, THEME_PRESETS


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
        pair = self._colors.get(role, self._colors.get("text", ("#5c6166", "#bfbdb6")))
        return f"{pair[0]},{pair[1]}"

    def threshold_role(self, remaining: float) -> str:
        """Return theme role based on remaining quota fraction."""
        if remaining > 0.5:
            return "success"
        if remaining > 0.2:
            return "warning"
        return "error"


def _mini_bar(value: float, max_val: float, width: int = 10) -> str:
    """Render a small bar chart."""
    if max_val <= 0:
        return "\u00b7" * width
    filled = round((value / max_val) * width)
    return "\u2588" * min(filled, width) + "\u00b7" * max(width - filled, 0)


def _format_time_until(iso_str: str) -> str:
    """Format time until an ISO timestamp as human-readable string."""
    try:
        target = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        delta = target - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return "now"
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "?"


def _format_tokens(count: int) -> str:
    """Format token count as human-readable string."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


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
    """Get remaining fraction (1.0 - utilization) for a metric."""
    if not quota:
        return None
    if metric == "5h" and quota.five_hour:
        return max(0.0, 1.0 - quota.five_hour.utilization)
    if metric == "7d" and quota.seven_day:
        return max(0.0, 1.0 - quota.seven_day.utilization)
    return None


def _render_title(
    lines: list[str], config: Config, theme: Theme, remaining: float | None
) -> None:
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
    params = [f"sfimage={config.symbol}"]
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
    symbol_map = {
        "5h": "gauge.with.needle.fill",
        "7d": "gauge.with.needle.fill",
        "opusplan": "cpu",
        "context": "brain.head.profile",
    }
    symbol = symbol_map.get(metric, config.symbol)

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
    """Render Quota & Runway dropdown section."""
    sym = SECTION_SYMBOLS["quota"]
    lines.append(f"Quota & Runway | sfimage={sym} color={theme.color('header')} fold=true")

    if not quota:
        lines.append(f"--No quota data | color={theme.color('subtext')}")
        return

    for window, data, label in [
        ("5h", quota.five_hour, "5-Hour"),
        ("7d", quota.seven_day, "7-Day"),
    ]:
        if not data:
            continue
        remaining = max(0.0, 1.0 - data.utilization)
        pct = int(remaining * 100)
        role = theme.threshold_role(remaining)
        resets_in = _format_time_until(data.resets_at) if data.resets_at else "?"
        lines.append(
            f"--{label}: {pct}% remaining  (resets in {resets_in})"
            f" | color={theme.color(role)} font=Menlo size=12"
        )

    # Extra usage budget
    if config.extra_usage_budget > 0:
        lines.append(
            f"--Extra usage budget: ${config.extra_usage_budget:.2f}"
            f" | color={theme.color('subtext')} font=Menlo size=11"
        )

    # Burn rate from blocks
    if blocks and blocks.active_block:
        active = blocks.active_block
        block_calls = active.get("calls", active.get("turns", 0))
        block_duration = active.get("duration_minutes", active.get("duration", 0))
        if block_duration > 0:
            rate = block_calls / block_duration
            lines.append(
                f"--Burn rate: {rate:.1f} calls/min (current block)"
                f" | color={theme.color('subtext')} font=Menlo size=11"
            )


def _render_activity_section(
    lines: list[str], theme: Theme, data: AggregateData
) -> None:
    """Render Activity (7d) dropdown section."""
    sym = SECTION_SYMBOLS["activity"]
    lines.append(f"Activity (7d) | sfimage={sym} color={theme.color('header')} fold=true")

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
        one_shot_rate = f"{int(one_shot / total_sessions * 100)}%" if total_sessions > 0 else "-"
        lines.append(
            f"--{bar}  {name:<14} {count:>5} turns  {one_shot_rate:>4} 1-shot"
            f" | font=Menlo size=11 color={theme.color('text')}"
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
    lines.append(f"Projects | sfimage={sym} color={theme.color('header')} fold=true")

    if not data.project_counts:
        lines.append(f"--No project data | color={theme.color('subtext')}")
        return

    sorted_projects = sorted(data.project_counts.items(), key=lambda x: -x[1])

    for project, calls in sorted_projects:
        display_name = config.project_aliases.get(project, project)
        # Truncate long names
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        subagent_count = data.project_subagent_counts.get(project, 0)
        subagent_pct = ""
        if subagent_count > 0:
            subagent_pct = f"  ({int(subagent_count / calls * 100)}% subagent)"
        lines.append(
            f"--{display_name:<30} {calls:>5} calls{subagent_pct}"
            f" | font=Menlo size=11 color={theme.color('text')}"
        )


def _render_tools_section(
    lines: list[str], theme: Theme, data: AggregateData, config: Config
) -> None:
    """Render Tools & Commands dropdown section."""
    sym = SECTION_SYMBOLS["tools"]
    lines.append(f"Tools & Commands | sfimage={sym} color={theme.color('header')} fold=true")

    # Top tools
    sorted_tools = sorted(data.tool_counts.items(), key=lambda x: -x[1])[:config.tools_top_n]
    if sorted_tools:
        max_tool = sorted_tools[0][1]
        lines.append(f"--Top Tools | color={theme.color('accent')} size=12")
        for name, count in sorted_tools:
            bar = _mini_bar(count, max_tool)
            lines.append(
                f"--{bar}  {name:<20} {count:>5}"
                f" | font=Menlo size=11 color={theme.color('text')}"
            )

    # Top bash commands
    bash_commands: dict[str, int] = {}
    for session in data.sessions:
        for tool_idx, tool in enumerate(session.tools):
            if tool in BASH_TOOLS:
                for cmd in session.bash_commands:
                    bash_commands[cmd] = bash_commands.get(cmd, 0) + 1

    sorted_cmds = sorted(bash_commands.items(), key=lambda x: -x[1])[:config.tools_top_n]
    if sorted_cmds:
        max_cmd = sorted_cmds[0][1]
        lines.append("-----")
        lines.append(f"--Top Commands | color={theme.color('accent')} size=12")
        for name, count in sorted_cmds:
            bar = _mini_bar(count, max_cmd)
            lines.append(
                f"--{bar}  {name:<20} {count:>5}"
                f" | font=Menlo size=11 color={theme.color('text')}"
            )


def _calc_opus_pct(data: AggregateData) -> float | None:
    """Calculate Opus model usage percentage."""
    total = sum(data.model_counts.values())
    if total == 0:
        return None
    opus_count = sum(v for k, v in data.model_counts.items() if "opus" in k.lower())
    return opus_count / total


def _render_opusplan_section(
    lines: list[str], theme: Theme, data: AggregateData
) -> None:
    """Render Opusplan Health dropdown section (conditional)."""
    # Only show if Opus model detected
    opus_pct = _calc_opus_pct(data)
    if opus_pct is None:
        return

    has_opus = any("opus" in k.lower() for k in data.model_counts)
    if not has_opus:
        return

    sym = SECTION_SYMBOLS["opusplan"]
    lines.append(f"Opusplan Health | sfimage={sym} color={theme.color('header')} fold=true")

    # Model breakdown
    total = sum(data.model_counts.values())
    sorted_models = sorted(data.model_counts.items(), key=lambda x: -x[1])
    max_model = sorted_models[0][1] if sorted_models else 1

    for model_name, count in sorted_models:
        bar = _mini_bar(count, max_model)
        pct = int(count / total * 100) if total > 0 else 0
        lines.append(
            f"--{bar}  {model_name:<24} {pct:>3}%  {count:>5} calls"
            f" | font=Menlo size=11 color={theme.color('text')}"
        )

    # Explore agent count
    explore_tools = {"Grep", "Glob", "Read"}
    explore_count = sum(
        1 for s in data.sessions
        if s.is_subagent and any(t in explore_tools for t in s.tools)
    )
    if explore_count > 0:
        lines.append(
            f"--Explore agents: {explore_count}"
            f" | font=Menlo size=11 color={theme.color('subtext')}"
        )


def _render_context_section(
    lines: list[str], theme: Theme, data: AggregateData, config: Config
) -> None:
    """Render Context Efficiency dropdown section (conditional)."""
    # Only show if sufficient session data exists
    sessions_with_tokens = [
        s for s in data.sessions
        if s.input_tokens > 0 and not s.is_subagent
    ]
    if len(sessions_with_tokens) < 3:
        return

    sym = SECTION_SYMBOLS["context"]
    lines.append(f"Context Efficiency | sfimage={sym} color={theme.color('header')} fold=true")

    # Context sizes
    context_sizes = sorted([s.input_tokens for s in sessions_with_tokens])
    threshold = config.large_session_threshold
    large_count = sum(1 for s in sessions_with_tokens if s.input_tokens > threshold)
    large_pct = int(large_count / len(sessions_with_tokens) * 100)

    # P50/P90
    p50_idx = len(context_sizes) // 2
    p90_idx = int(len(context_sizes) * 0.9)
    p50 = context_sizes[p50_idx] if context_sizes else 0
    p90 = context_sizes[min(p90_idx, len(context_sizes) - 1)] if context_sizes else 0

    large_role = "error" if large_pct > 50 else ("warning" if large_pct > 25 else "success")
    lines.append(
        f"-->150K sessions: {large_pct}%"
        f" | font=Menlo size=12 color={theme.color(large_role)}"
    )
    lines.append(
        f"--P50 context: {_format_tokens(p50)}  P90: {_format_tokens(p90)}"
        f" | font=Menlo size=11 color={theme.color('text')}"
    )

    # Cache hit %
    total_input = data.total_input_tokens + data.total_cache_read_tokens
    if total_input > 0:
        cache_hit = int(data.total_cache_read_tokens / total_input * 100)
        lines.append(
            f"--Cache hit rate: {cache_hit}%"
            f" | font=Menlo size=11 color={theme.color('text')}"
        )


def _render_footer(lines: list[str], theme: Theme) -> None:
    """Render footer with refresh and actions."""
    lines.append("---")
    lines.append("Refresh | refresh=true")
    lines.append(
        "ccusage daily | terminal=true shell=ccusage param1=daily"
    )
    lines.append(
        "ccusage blocks | terminal=true shell=ccusage param1=blocks param2=--active"
    )
