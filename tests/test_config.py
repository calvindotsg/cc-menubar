"""Tests for config loading and merging."""

from __future__ import annotations

from cc_menubar.config import Config, _deep_merge, _load_defaults


def test_load_defaults():
    """Bundled defaults.toml loads successfully."""
    defaults = _load_defaults()
    assert "general" in defaults
    assert "title" in defaults
    assert "quota" in defaults
    assert "theme" in defaults


def test_deep_merge_basic():
    """Deep merge overrides nested keys without clobbering siblings."""
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"x": 10}}
    result = _deep_merge(base, override)
    assert result == {"a": {"x": 10, "y": 2}, "b": 3}


def test_deep_merge_new_keys():
    """Deep merge adds new keys."""
    base = {"a": 1}
    override = {"b": 2}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": 2}


def test_config_defaults(tmp_path):
    """Config.load with no user file returns defaults."""
    config = Config.load(path=tmp_path / "nonexistent.toml")
    assert config.text == "none"
    assert config.color == "monochrome"
    assert config.metric == "5h"
    assert config.cycle == []
    assert config.quota_enabled is True
    assert config.activity_days == 7
    assert config.tools_top_n == 10
    assert config.theme_preset == "ayu"


def test_config_user_override(tmp_path):
    """User TOML overrides specific fields."""
    user_config = tmp_path / "config.toml"
    user_config.write_text(
        '[title]\ntext = "percent"\nmetric = "7d"\n\n[theme]\npreset = "catppuccin"\n'
    )
    config = Config.load(path=user_config)
    assert config.text == "percent"
    assert config.metric == "7d"
    assert config.theme_preset == "catppuccin"
    # Unoverridden fields stay default
    assert config.color == "monochrome"


def test_config_no_symbol_attribute(tmp_path):
    """[title].symbol knob was removed in v2.0.0 (dynamic _title_symbol supersedes)."""
    config = Config.load(path=tmp_path / "nonexistent.toml")
    assert not hasattr(config, "symbol")


def test_config_env_override(tmp_path, monkeypatch):
    """CC_MENUBAR_* env vars override config."""
    monkeypatch.setenv("CC_MENUBAR_TITLE_TEXT", "label")
    monkeypatch.setenv("CC_MENUBAR_QUOTA_ENABLED", "false")
    config = Config.load(path=tmp_path / "nonexistent.toml")
    assert config.text == "label"
    assert config.quota_enabled is False


def test_get_claude_data_dir_default(tmp_path):
    """Default claude data dir is ~/.claude."""
    config = Config.load(path=tmp_path / "nonexistent.toml")
    assert config.get_claude_data_dir().name == ".claude"


def test_get_claude_data_dir_env(tmp_path, monkeypatch):
    """CLAUDE_CONFIG_DIR env var overrides default."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/custom/claude")
    config = Config.load(path=tmp_path / "nonexistent.toml")
    config.claude_data_dir = ""  # Ensure fallback to env
    assert str(config.get_claude_data_dir()) == "/custom/claude"


def test_statusline_cache_file_default(tmp_path):
    """statusline_cache_file defaults to empty string (sentinel for built-in path)."""
    config = Config.load(path=tmp_path / "nonexistent.toml")
    assert config.statusline_cache_file == ""


def test_get_statusline_cache_file_default(tmp_path):
    """Unset cache_file → ~/Library/Caches/cc-menubar/statusline-input.json."""
    config = Config.load(path=tmp_path / "nonexistent.toml")
    path = config.get_statusline_cache_file()
    assert path.name == "statusline-input.json"
    assert "Library/Caches/cc-menubar" in str(path)


def test_get_statusline_cache_file_override(tmp_path):
    """User config cache_file is honored, with ~ expansion."""
    user_config = tmp_path / "config.toml"
    user_config.write_text('[quota]\ncache_file = "~/custom/statusline.json"\n')
    config = Config.load(path=user_config)
    path = config.get_statusline_cache_file()
    assert path.name == "statusline.json"
    assert "~" not in str(path)
