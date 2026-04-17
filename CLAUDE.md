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
- Quota: reads `/tmp/claude-statusline-usage.json` (written by statusline.py). Three windows: five_hour, seven_day, seven_day_sonnet. extra_usage is config-fallback only (no public API — anthropics/claude-code#34348 closed).
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
- **Canonical schema alignment at value level** (`collectors/quota.py`): when caching upstream API data, pin **value semantics** (scale, units) to the canonical schema source — not just field names. cc-menubar documents `utilization` as percent 0–100 (matching [Claude Code statusline rate_limits.*.used_percentage](https://code.claude.com/docs/en/statusline#full-json-schema)) even though the cache field name comes from the OAuth endpoint (`utilization`). Field renames across producer + consumer are deferred as cosmetic; value-semantics alignment is the load-bearing decision.
- **Canonical vs display split** (`labels.py`): internal code uses Claude Code statusline schema field names (snake_case — `five_hour`, `seven_day`, `used_percentage`); all user-facing copy lives in `src/cc_menubar/labels.py` (`LABELS` / `TOOLTIPS` dicts). Never inline display strings in `render.py` — import from labels. The `_tooltip(key)` helper in `render.py` wraps tooltip values in double quotes so apostrophes in content don't terminate SwiftBar's quoted-value parser. **Section-level explanation** goes in `LABELS` as a `section.<name>_caption` key and renders via `_caption()` as a disabled greyed-out row at the top of the submenu — never as a tooltip on a parent menu item. AppKit shows tooltip and submenu simultaneously on items with `--` children, so a tooltip on the parent collides with the submenu the user just opened. `TOOLTIPS` is reserved for leaf-row hover copy.

## Constraints

- **Minimal PATH**: Wrapper sets `/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH`
- **sfimage always monochrome**: SwiftBar forces `isTemplate = true` on all sfimage icons
- **ccusage optional**: blocks section gracefully skips if ccusage not installed
- **Quota read-only**: Only reads statusline.py cache, never calls OAuth directly
- **Typer sole dependency**: Rich is transitive via Typer
- **Quota scale**: `utilization` is 0–100 percent, not 0.0–1.0 fraction. Matches Claude Code statusline `rate_limits.*.used_percentage` canonical schema. Render divides by 100 for `sfvalue` (0.0–1.0).

## Release Process

Conventional commits → release-please PR → PyPI (OIDC) → tap dispatch. Same flow as mac-upkeep.
