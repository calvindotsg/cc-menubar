"""Tests for bash command extraction."""

from __future__ import annotations

from cc_menubar.bash_utils import extract_bash_commands


def test_empty_input():
    assert extract_bash_commands("") == []
    assert extract_bash_commands("  ") == []


def test_single_command():
    assert extract_bash_commands("git status") == ["git"]


def test_piped_commands():
    assert extract_bash_commands("cat file.txt | grep pattern | wc -l") == [
        "cat",
        "grep",
        "wc",
    ]


def test_chained_commands():
    assert extract_bash_commands("npm install && npm run build") == ["npm", "npm"]


def test_semicolon_separated():
    assert extract_bash_commands("echo hello; echo world") == ["echo", "echo"]


def test_cd_skipped():
    assert extract_bash_commands("cd /tmp && ls -la") == ["ls"]


def test_full_path():
    assert extract_bash_commands("/usr/local/bin/python3 script.py") == ["python3"]


def test_quoted_strings_preserved():
    """Separators inside quotes should not split commands."""
    assert extract_bash_commands('echo "hello && world"') == ["echo"]


def test_mixed_separators():
    assert extract_bash_commands("git add . && git commit -m 'msg'; git push") == [
        "git",
        "git",
        "git",
    ]
