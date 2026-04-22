"""Tests for cli.install ccusage helper management."""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_menubar import cli


@pytest.fixture
def fake_plugin_dir(tmp_path: Path) -> Path:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    return plugin_dir


def test_install_helper_writes_script(fake_plugin_dir: Path, tmp_path: Path):
    """_install_ccusage_helper writes helper with ccusage path substituted, mode 0755."""
    fake_ccusage = tmp_path / "bin" / "ccusage"
    fake_ccusage.parent.mkdir()
    fake_ccusage.touch()

    with patch.object(cli.shutil, "which", return_value=str(fake_ccusage)):
        helper = cli._install_ccusage_helper(fake_plugin_dir)

    assert helper is not None
    assert helper.exists()
    assert helper.name == ".cc-menubar-ccusage.sh"

    text = helper.read_text()
    assert "@@CCUSAGE_PATH@@" not in text
    assert str(fake_ccusage) in text
    assert "open -na Ghostty.app --args -e /bin/bash -c" in text
    assert "open -a Terminal.app" in text
    assert 'open -a Ghostty.app "$tmpf"' not in text
    assert '--args -e "' not in text

    mode = helper.stat().st_mode & 0o777
    assert mode & stat.S_IXUSR
    assert mode == 0o755


def test_install_helper_skipped_when_ccusage_missing(fake_plugin_dir: Path):
    """No ccusage on PATH → helper skipped, returns None."""
    with patch.object(cli.shutil, "which", return_value=None):
        helper = cli._install_ccusage_helper(fake_plugin_dir)
    assert helper is None
    assert not (fake_plugin_dir / ".cc-menubar-ccusage.sh").exists()


def test_install_helper_works_without_ghostty(fake_plugin_dir: Path, tmp_path: Path):
    """Ghostty.app absent is no longer a blocker — Terminal.app fallback handles it."""
    fake_ccusage = tmp_path / "bin" / "ccusage"
    fake_ccusage.parent.mkdir()
    fake_ccusage.touch()

    with patch.object(cli.shutil, "which", return_value=str(fake_ccusage)):
        helper = cli._install_ccusage_helper(fake_plugin_dir)
    assert helper is not None
    assert helper.exists()


def test_uninstall_removes_helper(fake_plugin_dir: Path):
    """uninstall removes the .cc-menubar-ccusage.sh file when present."""
    helper = fake_plugin_dir / ".cc-menubar-ccusage.sh"
    helper.write_text("#!/bin/bash\n")
    main_plugin = fake_plugin_dir / "cc-menubar.5m.sh"
    main_plugin.write_text("#!/bin/bash\n")

    with patch.object(cli, "_get_swiftbar_plugin_dir", return_value=fake_plugin_dir):
        with patch.object(cli, "_get_xbar_plugin_dir", return_value=fake_plugin_dir / "xbar"):
            from typer.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(cli.app, ["uninstall"])

    assert result.exit_code == 0
    assert not helper.exists()
    assert not main_plugin.exists()
