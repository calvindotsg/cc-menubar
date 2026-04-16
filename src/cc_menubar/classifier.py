"""Activity classifier — Python port of CodeBurn classifier.ts.

Two-phase classification: tool pattern -> keyword refinement. 13 categories.
"""

from __future__ import annotations

from cc_menubar.collectors.jsonl import AggregateData, SessionData
from cc_menubar.constants import (
    BASH_TOOLS,
    BRAINSTORM_KEYWORDS,
    BUILD_PATTERNS,
    CATEGORIES,
    DEBUG_KEYWORDS,
    EDIT_TOOLS,
    FEATURE_KEYWORDS,
    GIT_PATTERNS,
    INSTALL_PATTERNS,
    READ_TOOLS,
    REFACTOR_KEYWORDS,
    RESEARCH_KEYWORDS,
    SEARCH_TOOLS,
    TASK_TOOLS,
    TEST_PATTERNS,
)


def _has_tools(tools: list[str], tool_set: frozenset[str]) -> bool:
    return any(t in tool_set for t in tools)


def _classify_by_tool_pattern(tools: list[str], user_message: str) -> str | None:
    """Phase 1: classify by tool usage pattern."""
    if not tools:
        return None

    has_edits = _has_tools(tools, EDIT_TOOLS)
    has_reads = _has_tools(tools, READ_TOOLS)
    has_bash = _has_tools(tools, BASH_TOOLS)
    has_tasks = _has_tools(tools, TASK_TOOLS)
    has_search = _has_tools(tools, SEARCH_TOOLS)
    has_mcp = any(t.startswith("mcp__") for t in tools)

    if has_bash and not has_edits:
        if TEST_PATTERNS.search(user_message):
            return "testing"
        if GIT_PATTERNS.search(user_message):
            return "git"
        if BUILD_PATTERNS.search(user_message) or INSTALL_PATTERNS.search(user_message):
            return "build/deploy"

    if has_edits:
        return "coding"
    if has_bash and has_reads:
        return "exploration"
    if has_bash:
        return "coding"
    if has_search or has_mcp:
        return "exploration"
    if has_reads and not has_edits:
        return "exploration"
    if has_tasks and not has_edits:
        return "planning"

    return None


def _refine_by_keywords(category: str, user_message: str) -> str:
    """Phase 2: refine category using user message keywords."""
    if category == "coding":
        if DEBUG_KEYWORDS.search(user_message):
            return "debugging"
        if REFACTOR_KEYWORDS.search(user_message):
            return "refactoring"
        if FEATURE_KEYWORDS.search(user_message):
            return "feature"
        return "coding"

    if category == "exploration":
        if RESEARCH_KEYWORDS.search(user_message):
            return "exploration"
        if DEBUG_KEYWORDS.search(user_message):
            return "debugging"
        return "exploration"

    return category


def _classify_conversation(user_message: str) -> str:
    """Fallback classification for turns with no tools."""
    if BRAINSTORM_KEYWORDS.search(user_message):
        return "brainstorming"
    if RESEARCH_KEYWORDS.search(user_message):
        return "exploration"
    if DEBUG_KEYWORDS.search(user_message):
        return "debugging"
    if FEATURE_KEYWORDS.search(user_message):
        return "feature"
    return "conversation"


def classify_session(session: SessionData) -> str:
    """Classify a session into one of 13 categories."""
    if not session.tools:
        return "conversation"

    tool_category = _classify_by_tool_pattern(session.tools, "")
    if tool_category:
        return tool_category
    return "general"


def classify_aggregate(data: AggregateData) -> dict[str, int]:
    """Classify all sessions and return category counts."""
    counts: dict[str, int] = {cat: 0 for cat in CATEGORIES}

    for session in data.sessions:
        category = classify_session(session)
        if category in counts:
            counts[category] += session.turns

    return counts
