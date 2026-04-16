"""Constants for cc-menubar: categories, tool sets, theme presets."""

from __future__ import annotations

import re

# ── Activity classifier patterns ───────────────────────────────────────────

TEST_PATTERNS = re.compile(
    r"\b(test|pytest|vitest|jest|mocha|spec|coverage|npm\s+test|npx\s+vitest|npx\s+jest)\b",
    re.IGNORECASE,
)
GIT_PATTERNS = re.compile(
    r"\bgit\s+(push|pull|commit|merge|rebase|checkout|branch|stash|log|diff|status"
    r"|add|reset|cherry-pick|tag)\b",
    re.IGNORECASE,
)
BUILD_PATTERNS = re.compile(
    r"\b(npm\s+run\s+build|npm\s+publish|pip\s+install|docker|deploy|make\s+build"
    r"|npm\s+run\s+dev|npm\s+start|pm2|systemctl|brew|cargo\s+build)\b",
    re.IGNORECASE,
)
INSTALL_PATTERNS = re.compile(
    r"\b(npm\s+install|pip\s+install|brew\s+install|apt\s+install|cargo\s+add)\b",
    re.IGNORECASE,
)

DEBUG_KEYWORDS = re.compile(
    r"\b(fix|bug|error|broken|failing|crash|issue|debug|traceback|exception"
    r"|stack\s*trace|not\s+working|wrong|unexpected)\b",
    re.IGNORECASE,
)
FEATURE_KEYWORDS = re.compile(
    r"\b(add|create|implement|new|build|feature|introduce|set\s*up|scaffold|generate)\b",
    re.IGNORECASE,
)
REFACTOR_KEYWORDS = re.compile(
    r"\b(refactor|clean\s*up|rename|reorganize|simplify|extract|restructure"
    r"|move|migrate|split)\b",
    re.IGNORECASE,
)
BRAINSTORM_KEYWORDS = re.compile(
    r"\b(brainstorm|idea|what\s+if|explore|think\s+about|approach|strategy|design"
    r"|consider|how\s+should|what\s+would|opinion|suggest|recommend)\b",
    re.IGNORECASE,
)
RESEARCH_KEYWORDS = re.compile(
    r"\b(research|investigate|look\s+into|find\s+out|check|search|analyze|review"
    r"|understand|explain|how\s+does|what\s+is|show\s+me|list|compare)\b",
    re.IGNORECASE,
)

# ── Tool sets ──────────────────────────────────────────────────────────────

EDIT_TOOLS = frozenset({"Edit", "Write", "FileEditTool", "FileWriteTool", "NotebookEdit"})
READ_TOOLS = frozenset({"Read", "Grep", "Glob", "FileReadTool", "GrepTool", "GlobTool"})
BASH_TOOLS = frozenset({"Bash", "BashTool", "PowerShellTool"})
TASK_TOOLS = frozenset(
    {
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
        "TaskOutput",
        "TaskStop",
        "TodoWrite",
    }
)
SEARCH_TOOLS = frozenset({"WebSearch", "WebFetch", "ToolSearch"})

# ── Task categories ────────────────────────────────────────────────────────

CATEGORIES: list[str] = [
    "coding",
    "debugging",
    "feature",
    "refactoring",
    "testing",
    "git",
    "build/deploy",
    "exploration",
    "planning",
    "delegation",
    "brainstorming",
    "conversation",
    "general",
]

# ── Theme presets ──────────────────────────────────────────────────────────
# Each preset maps role -> (light_hex, dark_hex)

THEME_PRESETS: dict[str, dict[str, tuple[str, str]]] = {
    "ayu": {
        "success": ("#86b300", "#aad94c"),
        "warning": ("#ffaa33", "#e6b450"),
        "error": ("#f07171", "#f07178"),
        "info": ("#399ee6", "#59c2ff"),
        "accent": ("#a37acc", "#d2a6ff"),
        "secondary": ("#f29718", "#ff8f40"),
        "text": ("#5c6166", "#bfbdb6"),
        "subtext": ("#828c9a", "#7b91b3"),
        "overlay": ("#d8d8d7", "#2d3640"),
        "header": ("#a37acc", "#d2a6ff"),
    },
    "catppuccin": {
        "success": ("#40a02b", "#a6e3a1"),
        "warning": ("#df8e1d", "#f9e2af"),
        "error": ("#d20f39", "#f38ba8"),
        "info": ("#1e66f5", "#89b4fa"),
        "accent": ("#8839ef", "#cba6f7"),
        "secondary": ("#fe640b", "#fab387"),
        "text": ("#4c4f69", "#cdd6f4"),
        "subtext": ("#6c6f85", "#a6adc8"),
        "overlay": ("#9ca0b0", "#6c7086"),
        "header": ("#7287fd", "#b4befe"),
    },
}

# ── Dropdown section SF Symbols ────────────────────────────────────────────

SECTION_SYMBOLS: dict[str, str] = {
    "quota": "gauge.medium",
    "activity": "chart.bar.fill",
    "projects": "folder.fill",
    "tools": "wrench.fill",
    "opusplan": "cpu",
    "context": "brain.head.profile",
}
