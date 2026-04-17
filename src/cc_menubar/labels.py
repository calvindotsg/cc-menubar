"""User-facing display labels and tooltips for cc-menubar.

Single source of truth mapping Claude Code's canonical schema field names to
the plain-English strings rendered in the SwiftBar dropdown. Canonical schema:
https://code.claude.com/docs/en/statusline#full-json-schema

Conventions:
- Internal dataclass fields and the keys in this module stay snake_case,
  matching the Claude Code schema (`five_hour`, `seven_day`, `used_percentage`,
  `cache_read_input_tokens`, ...).
- Display strings are defined ONLY here. render.py imports from this module;
  never hardcode user-facing copy in render.py.
- Tooltips explain jargon that stays for brevity. SwiftBar surfaces them via
  the `tooltip=` per-item parameter.

Adding a label:
1. Add the canonical key to LABELS (and TOOLTIPS if the row needs a hover
   explanation).
2. Import via `from cc_menubar.labels import LABELS, TOOLTIPS` and reference
   by key from render.py.
"""

from __future__ import annotations

LABELS: dict[str, str] = {
    # Section headers
    "section.rate_limits": "Time Left & Limits",
    "section.activity": "Activity (last 7d)",
    "section.projects": "Projects",
    "section.tools": "Tools & Commands",
    "section.model_mix": "Model Mix",
    "section.context": "Context Size",
    # Quota rows
    "rate_limits.five_hour": "5-Hour",
    "rate_limits.seven_day": "7-Day",
    "rate_limits.seven_day_sonnet": "7-Day (Sonnet only)",
    "rate_limits.row_suffix": "{pct}% left  (resets {abs} \u00b7 in {rel})",
    "active_block.row": "Current 5h block: {parts}",
    # Activity
    "activity.one_shot": "{pct}% first-try",
    # Projects
    "projects.subagent": "({pct}% via agents)",
    # Model Mix
    "model_mix.research_agents": "Research agents: {n}",
    # Context Size
    "context.large_sessions": "Long conversations (>{threshold} tokens): {pct}%",
    "context.percentiles": "Typical: {p50}  Longest 10%: {p90}",
    "context.cache_reuse": "Context reuse: {pct}%",
    # Footer (ccusage)
    "footer.ccusage_daily": "Daily cost report (ccusage)",
    "footer.ccusage_blocks": "Active 5-hour block (ccusage)",
}

TOOLTIPS: dict[str, str] = {
    "rate_limits.five_hour": "Rolling 5-hour Claude Code usage window",
    "rate_limits.seven_day": "Rolling 7-day Claude Code usage window",
    "rate_limits.seven_day_sonnet": (
        "Separate 7-day window that tracks Sonnet \u2014 Claude's faster model \u2014 independently"
    ),
    "active_block.row": (
        "Current 5-hour ccusage block. Spend so far, hourly rate, time until the block closes."
    ),
    "activity.turns": "Each turn = one Claude response (message plus tool calls)",
    "activity.one_shot": "Share of edit sessions that didn't need a retry",
    "projects.subagent": "Share of turns delegated to sub-agents (Task / Agent tool)",
    "model_mix.header": "Which Claude model handled each turn over the last 7 days",
    "model_mix.research_agents": "Sub-agents that used search/read tools only (Grep, Glob, Read)",
    "context.percentiles": (
        "Input-token counts per session. Typical = median; Longest 10% = 90th percentile."
    ),
    "context.cache_reuse": (
        "Share of input tokens served from prompt cache \u2014 higher is more efficient"
    ),
    "footer.ccusage_daily": "Opens `ccusage daily` in Ghostty",
    "footer.ccusage_blocks": "Opens `ccusage blocks --active` in Ghostty",
}
