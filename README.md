# cc-menubar

Pace your quota — proactive forecasting for Claude Code Max, not retroactive tracking.

30+ Claude Code usage tools exist. Almost all show what you already spent. cc-menubar inverts this: instead of "how much did I use?", it answers "how far will my quota take me?"

![cc-menubar menu bar icon](https://raw.githubusercontent.com/calvindotsg/cc-menubar/main/demo/menubar.png)

![cc-menubar dropdown](https://raw.githubusercontent.com/calvindotsg/cc-menubar/main/demo/dropdown.png)

## Three Principles

| Principle | What it means |
|-----------|--------------|
| **Forecast remaining, don't sum spent** | Show what's LEFT (runway), not what's USED (cost). The gauge depletes like fuel — 1.0 to 0.0. |
| **Pace by phase** | Different work phases burn tokens differently. Activity classifier shows where tokens go. |
| **Maintain headroom** | Don't run hot. Context Efficiency and quota pacing give early awareness, not late alerts. |

## Install

```bash
brew install calvindotsg/tap/cc-menubar
brew install --cask swiftbar
cc-menubar install
open -a SwiftBar
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install cc-menubar
cc-menubar install
```

## Menu Bar Icon

A gauge icon showing remaining quota. The needle position reflects how much quota is left in the current window (default: 5-hour). Configurable text, color thresholds, and metric cycling.

## Dropdown Sections

| Section | Content | Visibility |
|---------|---------|------------|
| Quota & Runway | 5h / 7d / 7d Sonnet remaining, pace vs reset, burn rate | Always |
| Activity (7d) | Category bars with one-shot rate | Always |
| Projects | Per-project calls + subagent % | Always |
| Tools & Commands | Top tools, top bash commands | Always |
| Opusplan Health | Opus vs Haiku substitution % | When Opus model detected |
| Context Efficiency | >150K session %, P50/P90, cache hit % | When sufficient data exists |

## Configuration

Config at `~/.config/cc-menubar/config.toml`. Built-in defaults apply automatically.

```bash
cc-menubar init          # Generate commented config
cc-menubar config        # Show merged config
cc-menubar config --default  # Show all defaults
```

### Title Options

```toml
[title]
symbol = "gauge.with.needle.fill"  # SF Symbol name
text = "none"                       # "none" | "percent" | "label"
color = "monochrome"                # "monochrome" | "threshold" | "always"
metric = "5h"                       # "5h" | "7d"
cycle = []                          # ["5h", "7d", "opusplan", "context"]
```

### Theme

```toml
[theme]
preset = "ayu"   # "ayu" (default) or "catppuccin"

# Override individual roles
[theme.light]
success = "#custom"

[theme.dark]
success = "#custom"
```

### Sections

```toml
[quota]
enabled = true

[activity]
enabled = true
days = 7

[tools]
enabled = true
top_n = 10

[projects]
enabled = true
[projects.aliases]
# "-Users-me-myproject" = "My Project"
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `render` | Output SwiftBar text (called by wrapper) |
| `install` | Write SwiftBar wrapper + create config |
| `uninstall` | Remove SwiftBar wrapper |
| `init` | Generate config file |
| `config` | Show merged config |

## Data Sources

- **Quota**: Reads `/tmp/claude-statusline-usage.json` (written by Claude Code statusline)
- **Burn rate**: `ccusage blocks --json --active` (optional, install via `brew install ccusage`)
- **Activity, tools, models, context**: JSONL files in `~/.claude/projects/`

## Requirements

- macOS 13.0+ (for variable-value SF Symbols)
- Python 3.11+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) or [xbar](https://xbarapp.com/)

## License

MIT
