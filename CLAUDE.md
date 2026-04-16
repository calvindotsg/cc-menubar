# CLAUDE.md

## Quick Commands

```bash
uv sync                           # Install dependencies
uv run ruff check src/ tests/     # Lint
uv run ruff format src/ tests/    # Format
uv run pytest                     # Test
uv run cc-menubar render          # Test render output
uv run cc-menubar config          # Show merged config
uv run cc-menubar install         # Install SwiftBar wrapper
```

## Architecture

```
cc-menubar/
├── src/cc_menubar/
│   ├── cli.py              # Typer CLI: render, install, uninstall, init, config
│   ├── config.py            # 3-layer TOML config merge (defaults → user → env)
│   ├── defaults.toml        # Bundled default config
│   ├── render.py            # SwiftBar output formatter + Theme class
│   ├── constants.py         # Categories, tool sets, theme presets
│   ├── classifier.py        # Activity classifier (CodeBurn port)
│   ├── bash_utils.py        # Shell command extraction (CodeBurn port)
│   └── collectors/
│       ├── quota.py         # Read /tmp/claude-statusline-usage.json
│       ├── blocks.py        # ccusage blocks --json subprocess
│       ├── jsonl.py         # Single-pass JSONL parser
│       └── cache.py         # Aggregate cache (300s TTL)
└── tests/
```

## Key Patterns

### TOML Config Merge
3 layers: bundled `defaults.toml` → user `~/.config/cc-menubar/config.toml` → `CC_MENUBAR_*` env vars. Deep merge at section level.

### SwiftBar Output DSL
- stdout = SwiftBar display, stderr = diagnostics
- `---` separates title from dropdown
- `sfimage=NAME` for SF Symbols, `sfvalue=0.0-1.0` for variable fill
- `color=#light,#dark` for automatic appearance switching
- `fold=true` for collapsible sections
- `dropdown=false` to hide cycling lines from dropdown
- `font=Menlo size=11` for monospace data rows

### Caching
- Quota: reads `/tmp/claude-statusline-usage.json` (written by statusline.py); includes extra_usage when available
- Blocks: `ccusage blocks --json --active` subprocess with timeout
- JSONL: single-pass parse of `~/.claude/projects/*/**.jsonl`, mtime-filtered
- Aggregate cache: `/tmp/cc-menubar-cache.json`, configurable TTL

### Graceful Degradation
- Each collector returns `None` on failure; render skips that section
- Render catches all exceptions; fallback to static `-- | sfimage=gauge.with.needle.fill`
- `sfvalue` requires macOS 13.0+ — older versions get static icon
- `fold=true` degrades to expanded sections on older SwiftBar versions

### Reusable Patterns
- **3-layer TOML config merge** (`config.py`): bundled defaults → user file → env vars, deep merge at section level
- **SwiftBar Output DSL** (`render.py`): `color=#light,#dark` dual-color format for automatic macOS appearance switching
- **Graceful collector pattern** (`collectors/*.py`): each returns `None` on failure, render skips that section
- **WCAG AA dual-color presets** (`constants.py`): light-mode colors darkened for 4.5:1 against #FFFFFF, dark-mode for #2B2B2B
- **Repository governance** ([calvindotsg/.github](https://github.com/calvindotsg/.github)): shared community health files (SECURITY.md, PR/issue templates) inherited by all repos + `scripts/setup-repo.sh` for squash-only merges, branch protection, security scanning — settings not discoverable by exploring the codebase

## Constraints

- **Minimal PATH**: Wrapper sets `/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH`
- **sfimage always monochrome**: SwiftBar forces `isTemplate = true` on all sfimage icons
- **ccusage optional**: blocks section gracefully skips if ccusage not installed
- **Quota read-only**: Only reads statusline.py cache, never calls OAuth directly
- **Typer sole dependency**: Rich is transitive via Typer

## Release Process

Conventional commits → release-please PR → PyPI (OIDC) → tap dispatch. Same flow as mac-upkeep.
