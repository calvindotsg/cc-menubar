"""Single-pass JSONL parser for Claude Code session data."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SessionData:
    """Aggregated data from a single JSONL session file."""

    project: str
    session_id: str
    tools: list[str] = field(default_factory=list)
    bash_commands: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    turns: int = 0
    is_subagent: bool = False


@dataclass
class AggregateData:
    """Aggregated JSONL data across all sessions."""

    sessions: list[SessionData] = field(default_factory=list)
    tool_counts: dict[str, int] = field(default_factory=dict)
    bash_command_counts: dict[str, int] = field(default_factory=dict)
    model_counts: dict[str, int] = field(default_factory=dict)
    project_counts: dict[str, int] = field(default_factory=dict)
    project_subagent_counts: dict[str, int] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_write_tokens: int = 0


def _find_jsonl_files(claude_dir: Path, max_age_days: int) -> list[tuple[Path, str, bool]]:
    """Find JSONL files modified within max_age_days.

    Returns list of (path, project_name, is_subagent).
    """
    cutoff = time.time() - (max_age_days * 86400)
    results: list[tuple[Path, str, bool]] = []
    projects_dir = claude_dir / "projects"

    if not projects_dir.is_dir():
        return results

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        project_name = project_dir.name

        # Direct JSONL files
        for jsonl_file in project_dir.glob("*.jsonl"):
            try:
                if jsonl_file.stat().st_mtime >= cutoff:
                    results.append((jsonl_file, project_name, False))
            except OSError:
                continue

        # Subagent JSONL files
        for jsonl_file in project_dir.glob("*/subagents/*.jsonl"):
            try:
                if jsonl_file.stat().st_mtime >= cutoff:
                    results.append((jsonl_file, project_name, True))
            except OSError:
                continue

    return results


def _parse_jsonl_file(path: Path, project: str, is_subagent: bool) -> SessionData:
    """Parse a single JSONL file into SessionData."""
    session = SessionData(
        project=project,
        session_id=path.stem,
        is_subagent=is_subagent,
    )

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = entry.get("type")

                if msg_type == "assistant":
                    session.turns += 1
                    model = entry.get("model", "")
                    if model:
                        session.models.append(model)

                    # Extract tool use from content blocks
                    for block in entry.get("message", {}).get("content", []):
                        if block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name:
                                session.tools.append(tool_name)

                    # Token usage
                    usage = entry.get("message", {}).get("usage", {})
                    session.input_tokens += usage.get("input_tokens", 0)
                    session.output_tokens += usage.get("output_tokens", 0)
                    session.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
                    session.cache_write_tokens += usage.get("cache_creation_input_tokens", 0)

    except OSError:
        pass

    return session


def read_jsonl(claude_dir: Path, max_age_days: int = 7) -> AggregateData | None:
    """Parse all JSONL files within max_age_days. Returns None on failure."""
    try:
        files = _find_jsonl_files(claude_dir, max_age_days)
        if not files:
            return None

        agg = AggregateData()

        for path, project, is_subagent in files:
            session = _parse_jsonl_file(path, project, is_subagent)
            agg.sessions.append(session)

            # Aggregate tool counts
            for tool in session.tools:
                agg.tool_counts[tool] = agg.tool_counts.get(tool, 0) + 1

            # Aggregate model counts
            for model in session.models:
                agg.model_counts[model] = agg.model_counts.get(model, 0) + 1

            # Aggregate project counts
            agg.project_counts[project] = agg.project_counts.get(project, 0) + session.turns
            if is_subagent:
                agg.project_subagent_counts[project] = (
                    agg.project_subagent_counts.get(project, 0) + session.turns
                )

            # Aggregate tokens
            agg.total_input_tokens += session.input_tokens
            agg.total_output_tokens += session.output_tokens
            agg.total_cache_read_tokens += session.cache_read_tokens
            agg.total_cache_write_tokens += session.cache_write_tokens

        return agg

    except OSError:
        return None
