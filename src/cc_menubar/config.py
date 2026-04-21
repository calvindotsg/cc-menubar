"""Configuration loading: defaults.toml -> user TOML -> CC_MENUBAR_* env vars."""

from __future__ import annotations

import importlib.resources
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
DEFAULT_CONFIG_DIR = Path(_xdg) / "cc-menubar"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"


def _load_defaults() -> dict:
    """Load bundled defaults.toml via importlib.resources."""
    text = (
        importlib.resources.files("cc_menubar")
        .joinpath("defaults.toml")
        .read_text(encoding="utf-8")
    )
    return tomllib.loads(text)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(data: dict) -> dict:
    """Apply CC_MENUBAR_* environment variable overrides.

    Mapping: CC_MENUBAR_SECTION_KEY=value -> data[section][key] = value
    For booleans: "true"/"false" -> bool. For integers: parsed. Otherwise string.
    """
    prefix = "CC_MENUBAR_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        parts = env_key[len(prefix) :].lower().split("_", 1)
        if len(parts) != 2:
            continue
        section, key = parts
        if section not in data:
            continue
        if not isinstance(data[section], dict):
            continue

        # Type coercion
        if env_val.lower() in ("true", "false"):
            data[section][key] = env_val.lower() == "true"
        else:
            try:
                data[section][key] = int(env_val)
            except ValueError:
                try:
                    data[section][key] = float(env_val)
                except ValueError:
                    data[section][key] = env_val

    return data


@dataclass
class Config:
    """cc-menubar configuration loaded from 3-layer merge."""

    # [general]
    timezone: str = ""
    locale: str = ""
    cache_ttl: int = 300
    claude_data_dir: str = ""

    # [title]
    text: str = "none"
    color: str = "monochrome"
    metric: str = "5h"
    cycle: list[str] = field(default_factory=list)

    # [quota]
    quota_enabled: bool = True
    statusline_cache_file: str = ""

    # [blocks]
    blocks_enabled: bool = True
    session_length: int = 5
    ccusage_timeout: int = 15

    # [opusplan]
    opusplan_enabled: bool = True

    # [context]
    context_enabled: bool = True
    large_session_threshold: int = 150000

    # [activity]
    activity_enabled: bool = True
    activity_days: int = 7

    # [tools]
    tools_enabled: bool = True
    tools_top_n: int = 10

    # [projects]
    projects_enabled: bool = True
    project_aliases: dict[str, str] = field(default_factory=dict)

    # [theme]
    theme_preset: str = "ayu"
    theme_light: dict[str, str] = field(default_factory=dict)
    theme_dark: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> Config:
        """Load config from 3-layer merge: defaults -> user TOML -> env vars."""
        defaults = _load_defaults()

        # Layer 2: user TOML
        user_data: dict = {}
        if path.is_file():
            with open(path, "rb") as f:
                user_data = tomllib.load(f)

        merged = _deep_merge(defaults, user_data)

        # Layer 3: env var overrides
        merged = _apply_env_overrides(merged)

        return cls._from_dict(merged)

    @classmethod
    def _from_dict(cls, data: dict) -> Config:
        """Construct Config from merged TOML dict."""
        general = data.get("general", {})
        title = data.get("title", {})
        quota = data.get("quota", {})
        blocks = data.get("blocks", {})
        opusplan = data.get("opusplan", {})
        context = data.get("context", {})
        activity = data.get("activity", {})
        tools = data.get("tools", {})
        projects = data.get("projects", {})
        theme = data.get("theme", {})

        return cls(
            timezone=general.get("timezone", ""),
            locale=general.get("locale", ""),
            cache_ttl=general.get("cache_ttl", 300),
            claude_data_dir=general.get("claude_data_dir", ""),
            text=title.get("text", "none"),
            color=title.get("color", "monochrome"),
            metric=title.get("metric", "5h"),
            cycle=title.get("cycle", []),
            quota_enabled=quota.get("enabled", True),
            statusline_cache_file=quota.get("cache_file", ""),
            blocks_enabled=blocks.get("enabled", True),
            session_length=blocks.get("session_length", 5),
            ccusage_timeout=blocks.get("ccusage_timeout", 15),
            opusplan_enabled=opusplan.get("enabled", True),
            context_enabled=context.get("enabled", True),
            large_session_threshold=context.get("large_session_threshold", 150000),
            activity_enabled=activity.get("enabled", True),
            activity_days=activity.get("days", 7),
            tools_enabled=tools.get("enabled", True),
            tools_top_n=tools.get("top_n", 10),
            projects_enabled=projects.get("enabled", True),
            project_aliases=projects.get("aliases", {}),
            theme_preset=theme.get("preset", "ayu"),
            theme_light=theme.get("light", {}),
            theme_dark=theme.get("dark", {}),
        )

    def get_claude_data_dir(self) -> Path:
        """Resolve Claude data directory."""
        if self.claude_data_dir:
            return Path(self.claude_data_dir)
        env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        if env_dir:
            return Path(env_dir)
        return Path.home() / ".claude"

    def get_statusline_cache_file(self) -> Path:
        """Resolve the canonical statusline JSON cache file path."""
        if self.statusline_cache_file:
            return Path(self.statusline_cache_file).expanduser()
        return Path("~/Library/Caches/cc-menubar/statusline-input.json").expanduser()
