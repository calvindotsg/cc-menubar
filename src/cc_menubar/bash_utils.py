"""Shell command extraction from bash tool invocations."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


def _strip_quoted_strings(command: str) -> str:
    """Replace quoted strings with spaces to avoid splitting on quoted separators."""
    return re.sub(r'"[^"]*"|\'[^\']*\'', lambda m: " " * len(m.group(0)), command)


def extract_bash_commands(command: str) -> list[str]:
    """Extract base command names from a shell command string.

    Splits on &&, ;, | separators, takes the first token of each segment,
    extracts the basename, and skips 'cd'.
    """
    if not command or not command.strip():
        return []

    stripped = _strip_quoted_strings(command)

    # Find separator positions in the stripped version
    separator_re = re.compile(r"\s*(?:&&|;|\|)\s*")
    separators: list[tuple[int, int]] = []
    for match in separator_re.finditer(stripped):
        separators.append((match.start(), match.end()))

    # Build ranges between separators
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for start, end in separators:
        ranges.append((cursor, start))
        cursor = end
    ranges.append((cursor, len(command)))

    commands: list[str] = []
    for start, end in ranges:
        segment = command[start:end].strip()
        if not segment:
            continue

        first_token = segment.split()[0]
        base = PurePosixPath(first_token).name

        if base and base != "cd":
            commands.append(base)

    return commands
