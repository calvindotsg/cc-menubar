"""Fetch burn rate data via ccusage blocks subprocess."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class BlockInfo:
    """Burn rate data from ccusage blocks."""

    blocks: list[dict]
    active_block: dict | None


def read_blocks(timeout: int = 15, session_length: int = 5) -> BlockInfo | None:
    """Run ccusage blocks --json --active and parse output.

    Returns None if ccusage is not installed or the command fails.
    """
    if not shutil.which("ccusage"):
        return None

    try:
        result = subprocess.run(
            [
                "ccusage",
                "blocks",
                "--json",
                "--active",
                "--session-length",
                str(session_length),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        blocks = data if isinstance(data, list) else data.get("blocks", [])
        active = blocks[-1] if blocks else None

        return BlockInfo(blocks=blocks, active_block=active)

    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None
