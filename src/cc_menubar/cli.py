"""cc-menubar CLI — glanceable macOS menu bar quota forecasting for Claude Code Max."""

from __future__ import annotations

import importlib.resources
import shutil
import signal
import stat
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer

from cc_menubar.config import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_PATH, Config

app = typer.Typer(
    help="Pace your quota — proactive forecasting for Claude Code Max.\n\n"
    "Glanceable macOS menu bar widget showing remaining quota,\n"
    "activity breakdown, and context efficiency.\n\n"
    "Quick start: cc-menubar install",
    no_args_is_help=True,
)


def _handle_signal(signum: int, _frame: object) -> None:
    sys.exit(130)


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def _version_callback(value: bool) -> None:
    if value:
        try:
            v = pkg_version("cc-menubar")
        except Exception:
            v = "unknown"
        typer.echo(f"cc-menubar {v}")
        raise typer.Exit()


@app.callback()
def main(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-v", callback=_version_callback, is_eager=True, help="Show version."
        ),
    ] = None,
) -> None:
    """Pace your quota — proactive forecasting for Claude Code Max."""
    if sys.platform != "darwin":
        typer.echo("cc-menubar requires macOS.", err=True)
        raise typer.Exit(code=1)


@app.command()
def render(
    debug: Annotated[bool, typer.Option("--debug", help="Show diagnostics on stderr.")] = False,
) -> None:
    """Output SwiftBar text to stdout.

    Called by the SwiftBar wrapper script every 5 minutes.
    All diagnostic output goes to stderr.
    """
    try:
        config = Config.load()

        from cc_menubar.collectors.blocks import read_blocks
        from cc_menubar.collectors.jsonl import read_jsonl
        from cc_menubar.collectors.quota import read_quota
        from cc_menubar.render import render as do_render

        quota = read_quota(config.get_statusline_cache_file())
        blocks = (
            read_blocks(
                timeout=config.ccusage_timeout,
                session_length=config.session_length,
            )
            if config.blocks_enabled
            else None
        )
        jsonl_data = read_jsonl(
            config.get_claude_data_dir(),
            max_age_days=config.activity_days,
        )

        output = do_render(config, quota, blocks, jsonl_data, debug=debug)
        typer.echo(output)

    except Exception:
        if debug:
            import traceback

            print(traceback.format_exc(), file=sys.stderr)
        # Fallback: show static icon so menu bar item doesn't disappear
        typer.echo("-- | sfimage=gauge.with.needle.fill")


def _get_swiftbar_plugin_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "SwiftBar" / "plugins"


def _get_xbar_plugin_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "xbar" / "plugins"


WRAPPER_SCRIPT = """\
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cc-menubar render 2>/dev/null || echo "-- | sfimage=gauge.with.needle.fill"
"""

PLUGIN_FILENAME = "cc-menubar.5m.sh"
CCUSAGE_HELPER_FILENAME = ".cc-menubar-ccusage.sh"
GHOSTTY_APP_PATH = Path("/Applications/Ghostty.app")


def _install_ccusage_helper(plugin_dir: Path) -> Path | None:
    """Write the ccusage helper script into plugin_dir if prerequisites exist.

    Returns the installed helper path, or None if skipped (missing ccusage or
    Ghostty.app). The leading `.` in the filename hides the script from
    SwiftBar's plugin scan (it's invoked by bash=, not as a plugin).
    """
    ccusage_path = shutil.which("ccusage")
    if not ccusage_path or not GHOSTTY_APP_PATH.is_dir():
        return None

    template = (
        importlib.resources.files("cc_menubar")
        .joinpath("ccusage_helper.sh")
        .read_text(encoding="utf-8")
    )
    script = template.replace("@@CCUSAGE_PATH@@", ccusage_path)
    helper_path = plugin_dir / CCUSAGE_HELPER_FILENAME
    helper_path.write_text(script)
    helper_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return helper_path


@app.command()
def install() -> None:
    """Install SwiftBar wrapper and create config if missing.

    Detects SwiftBar or xbar plugin directory, writes the wrapper script,
    and runs init if no config exists.
    """
    swiftbar_dir = _get_swiftbar_plugin_dir()
    xbar_dir = _get_xbar_plugin_dir()

    if swiftbar_dir.is_dir():
        plugin_dir = swiftbar_dir
        app_name = "SwiftBar"
    elif xbar_dir.is_dir():
        plugin_dir = xbar_dir
        app_name = "xbar"
    else:
        plugin_dir = swiftbar_dir
        app_name = "SwiftBar"
        plugin_dir.mkdir(parents=True, exist_ok=True)

    plugin_path = plugin_dir / PLUGIN_FILENAME
    plugin_path.write_text(WRAPPER_SCRIPT)
    plugin_path.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    # Ensure the statusline cache directory exists so `tee` producer recipes
    # in the README never fail on a missing parent dir.
    Path("~/Library/Caches/cc-menubar").expanduser().mkdir(parents=True, exist_ok=True)

    typer.echo(f"Plugin installed: {plugin_path}")

    helper_path = _install_ccusage_helper(plugin_dir)
    if helper_path:
        typer.echo(f"ccusage helper installed: {helper_path}")
    else:
        reason = (
            "ccusage not on PATH"
            if not shutil.which("ccusage")
            else "Ghostty.app not found in /Applications"
        )
        typer.echo(f"ccusage helper skipped ({reason}). Footer actions will be hidden.")

    # Auto-init config if missing
    if not DEFAULT_CONFIG_PATH.is_file():
        _do_init()
        typer.echo(f"Config created: {DEFAULT_CONFIG_PATH}")

    # Guidance
    swiftbar_installed = (
        Path("/Applications/SwiftBar.app").is_dir()
        or (Path.home() / "Applications" / "SwiftBar.app").is_dir()
    )
    xbar_installed = (
        Path("/Applications/xbar.app").is_dir()
        or (Path.home() / "Applications" / "xbar.app").is_dir()
    )

    if swiftbar_installed or xbar_installed:
        typer.echo(f"{app_name} detected — plugin should appear in your menu bar shortly.")
        typer.echo(f"If not, open {app_name} and refresh plugins.")
    else:
        typer.echo()
        typer.echo("To see cc-menubar in your menu bar, install SwiftBar:")
        typer.echo("  brew install --cask swiftbar")
        typer.echo()
        typer.echo("Then launch SwiftBar — the plugin will load automatically.")

    typer.echo()
    typer.echo(
        "To populate the quota dropdown, wire a Claude Code statusline producer"
        " per README §Quota setup."
    )


@app.command()
def uninstall() -> None:
    """Remove wrapper from SwiftBar and xbar plugin directories."""
    paths = [
        _get_swiftbar_plugin_dir() / PLUGIN_FILENAME,
        _get_xbar_plugin_dir() / PLUGIN_FILENAME,
        _get_swiftbar_plugin_dir() / CCUSAGE_HELPER_FILENAME,
        _get_xbar_plugin_dir() / CCUSAGE_HELPER_FILENAME,
    ]

    removed = False
    for p in paths:
        if p.is_file():
            p.unlink()
            typer.echo(f"Removed: {p}")
            removed = True

    if not removed:
        typer.echo("No menu bar plugin found.")


def _do_init(force: bool = False) -> None:
    """Internal init logic (shared by install and init commands)."""
    if DEFAULT_CONFIG_PATH.is_file() and not force:
        return

    defaults_text = (
        importlib.resources.files("cc_menubar")
        .joinpath("defaults.toml")
        .read_text(encoding="utf-8")
    )

    # Generate a commented config showing defaults
    config_lines = [
        "# cc-menubar configuration",
        "# https://github.com/calvindotsg/cc-menubar",
        "#",
        "# Built-in defaults apply automatically. Uncomment to override.",
        "",
    ]

    for line in defaults_text.splitlines():
        if line.strip() and not line.startswith("#"):
            config_lines.append(f"# {line}")
        else:
            config_lines.append(line)

    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG_PATH.write_text("\n".join(config_lines) + "\n")


@app.command()
def init(
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing config.")] = False,
) -> None:
    """Generate a config file with auto-detected values.

    Creates ~/.config/cc-menubar/config.toml with all defaults commented out.
    """
    if DEFAULT_CONFIG_PATH.is_file() and not force:
        typer.echo(f"Config already exists: {DEFAULT_CONFIG_PATH}")
        typer.echo("Use --force to overwrite.")
        raise typer.Exit(1)

    _do_init(force=True)
    typer.echo(f"Created {DEFAULT_CONFIG_PATH}")
    typer.echo("Edit the file to customize. Run 'cc-menubar config' to see merged settings.")


@app.command()
def config(
    default: Annotated[bool, typer.Option("--default", help="Show bundled defaults.")] = False,
) -> None:
    """Show merged configuration.

    With --default: outputs bundled defaults.toml.
    Without --default: outputs the merged config (defaults + user overrides + env vars).
    """
    if default:
        text = (
            importlib.resources.files("cc_menubar")
            .joinpath("defaults.toml")
            .read_text(encoding="utf-8")
        )
        typer.echo(text.rstrip())
    else:
        cfg = Config.load()
        # Display as key-value pairs
        typer.echo("[general]")
        typer.echo(f'timezone = "{cfg.timezone}"')
        typer.echo(f'locale = "{cfg.locale}"')
        typer.echo(f"cache_ttl = {cfg.cache_ttl}")
        typer.echo(f'claude_data_dir = "{cfg.claude_data_dir}"')
        typer.echo()
        typer.echo("[title]")
        typer.echo(f'symbol = "{cfg.symbol}"')
        typer.echo(f'text = "{cfg.text}"')
        typer.echo(f'color = "{cfg.color}"')
        typer.echo(f'metric = "{cfg.metric}"')
        typer.echo(f"cycle = {cfg.cycle}")
        typer.echo()
        typer.echo("[quota]")
        typer.echo(f"enabled = {str(cfg.quota_enabled).lower()}")
        typer.echo(f'cache_file = "{cfg.statusline_cache_file}"')
        typer.echo()
        typer.echo("[blocks]")
        typer.echo(f"enabled = {str(cfg.blocks_enabled).lower()}")
        typer.echo(f"session_length = {cfg.session_length}")
        typer.echo(f"ccusage_timeout = {cfg.ccusage_timeout}")
        typer.echo()
        typer.echo("[opusplan]")
        typer.echo(f"enabled = {str(cfg.opusplan_enabled).lower()}")
        typer.echo()
        typer.echo("[context]")
        typer.echo(f"enabled = {str(cfg.context_enabled).lower()}")
        typer.echo(f"large_session_threshold = {cfg.large_session_threshold}")
        typer.echo()
        typer.echo("[activity]")
        typer.echo(f"enabled = {str(cfg.activity_enabled).lower()}")
        typer.echo(f"days = {cfg.activity_days}")
        typer.echo()
        typer.echo("[tools]")
        typer.echo(f"enabled = {str(cfg.tools_enabled).lower()}")
        typer.echo(f"top_n = {cfg.tools_top_n}")
        typer.echo()
        typer.echo("[projects]")
        typer.echo(f"enabled = {str(cfg.projects_enabled).lower()}")
        typer.echo()
        typer.echo("[theme]")
        typer.echo(f'preset = "{cfg.theme_preset}"')
