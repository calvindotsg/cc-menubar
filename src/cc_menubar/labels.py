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
- Section-level explanation goes in LABELS keyed `section.<name>_caption` and
  renders via `_caption()` as a disabled greyed-out row at the top of the
  submenu — never as a tooltip on a parent menu item. AppKit shows tooltip
  and submenu simultaneously on items with `--` children, so a tooltip on
  the parent collides with the submenu the user just opened. TOOLTIPS is
  reserved for leaf-row hover copy only.

Adding a label:
1. Add the canonical key to LABELS (and TOOLTIPS if the row needs a hover
   explanation).
2. Import via `from cc_menubar.labels import LABELS, TOOLTIPS` and reference
   by key from render.py.
"""

from __future__ import annotations

LABELS: dict[str, str] = {
    # Section headers. `section.rate_limits` matches claude.ai/settings/usage
    # and the `/usage` command heading. Row labels stay canonical `5-Hour` /
    # `7-Day` — see `rate_limits.five_hour` / `rate_limits.seven_day` below.
    "section.rate_limits": "Plan usage limits",
    "section.activity": "Activity",
    "section.projects": "Projects",
    "section.tools": "Tools & Commands",
    "section.model_mix": "Model Mix",
    "section.context": "Context Size",
    # Submenu caption rows (disabled greyed-out first row in submenu;
    # replaces section-header tooltips to avoid AppKit dual-popover collision).
    # One per section for uniform hierarchy.
    "section.rate_limits_caption": "Rolling 5-hour and 7-day usage windows",
    "section.activity_caption": "Activity by category over the last 7 days",
    "section.projects_caption": "Turns grouped by project over the last 7 days",
    "section.tools_caption": "Most-invoked tools and shell commands over the last 7 days",
    "section.model_mix_caption": "Which Claude model handled each turn over the last 7 days",
    "section.context_caption": "Conversation length and prompt-cache reuse over the last 7 days",
    # Quota rows — labels retain canonical field-derived names for parity with
    # the statusline schema (`rate_limits.five_hour` / `rate_limits.seven_day`).
    "rate_limits.five_hour": "5-Hour",
    "rate_limits.seven_day": "7-Day",
    # Dual framing: "% used" and "% left" both visible. Placeholders:
    # {used}, {left}, {abs}, {rel}.
    "rate_limits.row_suffix": "{used}% used • {left}% left  (resets {abs} · in {rel})",
    "rate_limits.no_data": (
        "No quota yet — run Claude Code once to seed"
        " ~/Library/Caches/cc-menubar/statusline-input.json"
    ),
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
    "rate_limits.five_hour": (
        "Rolling 5-hour Claude Code usage window (canonical statusline field rate_limits.five_hour)"
    ),
    "rate_limits.seven_day": (
        "Rolling 7-day Claude Code usage window (canonical statusline field rate_limits.seven_day)"
    ),
    "active_block.row": "Current 5-hour ccusage block — spend so far and hourly burn rate.",
    "activity.turns": "Each turn = one Claude response (message plus tool calls)",
    "activity.one_shot": "Share of edit sessions that didn't need a retry",
    "projects.subagent": "Share of turns delegated to sub-agents (Task / Agent tool)",
    "model_mix.research_agents": "Sub-agents that used search/read tools only (Grep, Glob, Read)",
    "context.large_sessions": (
        "Sessions whose total input tokens exceed your large_session_threshold setting"
    ),
    "context.percentiles": (
        "Input-token counts per session. Typical = median; Longest 10% = 90th percentile."
    ),
    "context.cache_reuse": (
        "Share of input tokens served from prompt cache — higher is more efficient"
    ),
    "footer.ccusage_daily": "Opens `ccusage daily` in a terminal",
    "footer.ccusage_blocks": "Opens `ccusage blocks --active` in a terminal",
}
