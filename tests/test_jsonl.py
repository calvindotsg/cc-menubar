"""Tests for JSONL parser."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cc_menubar.collectors.jsonl import (
    _normalize_project_name,
    _parse_jsonl_file,
)


class TestNormalizeProjectName:
    def test_worktree_suffix_stripped(self):
        name = "-Users-calvin-ops--claude-worktrees-feat-branch"
        assert _normalize_project_name(name) == "-Users-calvin-ops"

    def test_non_worktree_preserved(self):
        name = "-Users-calvin-Documents-github-calvindotsg-cc-menubar"
        assert _normalize_project_name(name) == name

    def test_double_dash_dotdir_preserved(self):
        name = "-Users-calvin--config"
        assert _normalize_project_name(name) == name


class TestParseModelExtraction:
    def test_model_from_message_field(self):
        """Model should be extracted from entry.message.model, not entry.model."""
        entry = {
            "type": "assistant",
            "message": {
                "model": "claude-sonnet-4-20250514",
                "content": [],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(entry) + "\n")
            path = Path(f.name)

        session = _parse_jsonl_file(path, "test-project", False)
        assert session.models == ["claude-sonnet-4-20250514"]
        path.unlink()

    def test_model_at_root_level_ignored(self):
        """Model at entry root (wrong path) should not be extracted."""
        entry = {
            "type": "assistant",
            "model": "claude-sonnet-4-20250514",
            "message": {
                "content": [],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(entry) + "\n")
            path = Path(f.name)

        session = _parse_jsonl_file(path, "test-project", False)
        assert session.models == []
        path.unlink()


class TestParseCwdExtraction:
    def test_cwd_extracted_from_assistant(self):
        entry = {
            "type": "assistant",
            "cwd": "/Users/calvin/Documents/github/calvindotsg/cc-menubar",
            "message": {
                "content": [],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(entry) + "\n")
            path = Path(f.name)

        session = _parse_jsonl_file(path, "test-project", False)
        assert session.cwd == "/Users/calvin/Documents/github/calvindotsg/cc-menubar"
        path.unlink()

    def test_first_cwd_wins(self):
        """Only the first cwd should be stored."""
        entries = [
            {
                "type": "assistant",
                "cwd": "/first/path",
                "message": {"content": [], "usage": {"input_tokens": 10, "output_tokens": 5}},
            },
            {
                "type": "assistant",
                "cwd": "/second/path",
                "message": {"content": [], "usage": {"input_tokens": 10, "output_tokens": 5}},
            },
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
            path = Path(f.name)

        session = _parse_jsonl_file(path, "test-project", False)
        assert session.cwd == "/first/path"
        path.unlink()
