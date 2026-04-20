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
| Time Left & Limits | 5h / 7d remaining, pace vs reset, burn rate | Always |
| Activity (7d) | Category bars with one-shot rate | Always |
| Projects | Per-project calls + subagent % | Always |
| Tools & Commands | Top tools, top bash commands | Always |
| Model Mix | Opus vs Haiku substitution % | When Opus model detected |
| Context Size | >150K session %, P50/P90, cache hit % | When sufficient data exists |

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

## Quota setup

cc-menubar reads canonical-shape [Claude Code statusline](https://code.claude.com/docs/en/statusline#full-json-schema) JSON from `~/Library/Caches/cc-menubar/statusline-input.json` (override via `[quota] cache_file`). It ships no producer — you wire an existing statusline to write the cache file via POSIX `tee`. Pick the scenario that matches your setup and paste into `~/.claude/settings.json`.

### Scenario A — no existing statusline (fresh install)

```json
{
  "statusLine": {
    "type": "command",
    "command": "tee ~/Library/Caches/cc-menubar/statusline-input.json | jq -r '\"[\\(.model.display_name)] \\(.context_window.used_percentage // 0)% context\"'"
  }
}
```

Writes the cache file *and* renders a minimal Claude Code footer.

### Scenario B — existing custom script

```json
{
  "statusLine": {
    "type": "command",
    "command": "tee ~/Library/Caches/cc-menubar/statusline-input.json | ~/.claude/statusline.sh"
  }
}
```

Your script reads stdin as before; `tee` writes the cache as a side effect.

### Scenario C — existing published tool (`ccstatusline`, `CCometixLine`, `ccusage statusline`)

```json
{
  "statusLine": {
    "type": "command",
    "command": "tee ~/Library/Caches/cc-menubar/statusline-input.json | ccusage statusline"
  }
}
```

**Portability:** `tee` is POSIX (present in every shell); `jq` is needed only for Scenario A; `cc-menubar install` creates the cache directory so `tee` never fails on a missing parent.

## CLI Commands

| Command | Purpose |
|---------|---------|
| `render` | Output SwiftBar text (called by wrapper) |
| `install` | Write SwiftBar wrapper + create config |
| `uninstall` | Remove SwiftBar wrapper |
| `init` | Generate config file |
| `config` | Show merged config |

## Data Sources

- **Quota**: Reads canonical Claude Code statusline JSON cache (see [Quota setup](#quota-setup))
- **Burn rate**: `ccusage blocks --json --active` (optional, install via `brew install ccusage`)
- **Activity, tools, models, context**: JSONL files in `~/.claude/projects/`

## Requirements

- macOS 13.0+ (for variable-value SF Symbols)
- Python 3.11+
- [SwiftBar](https://github.com/swiftbar/SwiftBar) or [xbar](https://xbarapp.com/)

## License

MIT
